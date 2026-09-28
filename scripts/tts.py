#!/usr/bin/env python3
"""Gemini TTS execution only. Python 3.10+, standard library."""
import argparse
from array import array
import base64
import copy
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave

PROFILES = {
    'aihubmix': dict(protocol='speech', base_url='https://aihubmix.com/v1', key_env='AIHUBMIX_API_KEY', auth='bearer', response_format='wav', style_field='instructions', max_chars=4096),
    'openrouter': dict(protocol='speech', base_url='https://openrouter.ai/api/v1', key_env='OPENROUTER_API_KEY', auth='bearer', response_format='pcm', style_field='provider.options.google-ai-studio.speech_metadata.style'),
    'google': dict(protocol='gemini', base_url='https://generativelanguage.googleapis.com/v1beta', key_env='GEMINI_API_KEY', auth='google', schema='metadata'),
}
TAGS = set('argh,breath,heavy breath,exhales,cackle,cheer,chuckle,chuckles,cough,cry,gasp,giggle,groan,growl,grunt,grr,hiss,laugh,laughter,moan,pant,pff,phew,scream,shout,shriek,sigh,sighs,sneeze,snicker,snort,sob,throat-clearing,tsk,whimper,whispers,whispering,yawn,short pause,long pause'.split(','))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def config(path):
    raw = read(path)
    require(isinstance(raw, dict), '配置必须是 JSON 对象')
    allowed = {'provider', 'protocol', 'base_url', 'key_env', 'auth', 'model', 'schema', 'response_format', 'style_field', 'max_chars', 'sample_rate', 'extra_body', 'events'}
    require(not set(raw) - allowed, '配置含未知字段；凭据只能通过 key_env 读取')
    provider = raw.get('provider')
    require(provider in (*PROFILES, 'custom'), 'provider: aihubmix/openrouter/google/custom')
    c = {**PROFILES.get(provider, {}), **raw}
    require(c.get('protocol') in ('speech', 'gemini'), 'protocol: speech 或 gemini')
    require(c.get('auth') in ('bearer', 'google'), 'auth: bearer 或 google')
    for key in ('base_url', 'key_env', 'model'):
        require(isinstance(c.get(key), str) and c[key].strip(), f'缺少 {key}')
    require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', c['key_env']), 'key_env 必须是环境变量名')
    url = urllib.parse.urlsplit(c['base_url'])
    require(url.scheme == 'https' or (url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1', '::1')), '地址必须使用 HTTPS（本机测试除外）')
    require(url.hostname and not url.username and not url.password and not url.query and not url.fragment, 'base_url 不允许凭据、查询或 fragment')
    c['base_url'] = c['base_url'].rstrip('/')
    c.setdefault('schema', 'metadata')
    require(c['schema'] in ('metadata', 'legacy'), 'schema: metadata 或 legacy')
    if c['protocol'] == 'speech':
        require(c.get('response_format') in ('wav', 'pcm'), 'response_format 必须是 wav 或 pcm')
    require(isinstance(c.get('sample_rate', 24000), int) and 8000 <= c.get('sample_rate', 24000) <= 192000, 'sample_rate 无效')
    # Older Google models require an explicit legacy contract, not guessed fields.
    if re.search(r'gemini-(2\.5|3\.1)', c['model']):
        require(c['protocol'] != 'gemini' or c['schema'] == 'legacy', '旧 Gemini 模型请配置 schema=legacy')
        if provider == 'openrouter' and 'style_field' not in raw:
            c['style_field'] = None
    return c


def put(body, dotted, value):
    keys = dotted.split('.')
    require(keys[0] not in ('model', 'input', 'voice', 'response_format'), 'style_field 不能覆盖核心字段')
    for key in keys[:-1]:
        body = body.setdefault(key, {})
        require(isinstance(body, dict), 'style_field 与 extra_body 冲突')
    require(keys[-1] not in body, 'style_field 与 extra_body 冲突')
    body[keys[-1]] = value


def transcript(c, clip, dialogue=False):
    require(isinstance(clip.get('text'), str) and clip['text'].strip(), '片段缺少 text')
    style = clip.get('style', '')
    require(isinstance(style, str), 'style 必须是字符串')
    text = clip['text']
    if '|' in text:
        require(dialogue, '|回应| 仅用于原生双人 turns；要朗读竖线请在制作稿写出读法并保留 source_text')
        segments = text.split('|')
        require(len(segments) % 2 == 1 and all(s.strip() for s in segments[1::2]), '|回应| 必须成对且内容非空')
    events = clip.get('events', [])
    require(isinstance(events, list), 'events 必须是数组')
    require(not events or c.get('events', 'gemini-3.8' in c['model']), '该模型的事件语法未验证；请先确认，再显式配置 events=true')
    for event in events:
        require(isinstance(event, dict) and set(event) == {'at', 'tag'}, '事件需要 at/tag')
        require(type(event['at']) is int and 0 <= event['at'] <= len(text), '事件位置必须是原 text 的字符偏移')
        require(event['tag'] in TAGS, '未支持的事件标签')
    for event in reversed(sorted(events, key=lambda e: e['at'])):
        text = text[:event['at']] + '<' + event['tag'] + '>' + text[event['at']:]
    require(len(text) <= c.get('max_chars', 100000), '文本超过路由长度限制，请拆分')
    return text, style


def request(c, clip):
    require(isinstance(clip, dict), '片段必须是对象')
    cid = clip.get('id')
    require(isinstance(cid, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', cid), '片段 id 仅允许字母数字下划线和短横线')
    dialogue = 'turns' in clip or 'speakers' in clip
    if dialogue:
        require(not set(clip) - {'id', 'source_text', 'speakers', 'turns'}, '双人片段仅支持 id/source_text/speakers/turns')
        require(c['protocol'] == 'gemini' and c['schema'] == 'metadata', '原生双人需要 Gemini metadata 协议；不自动降级或换供应商')
        speakers, turns = clip.get('speakers'), clip.get('turns')
        require(isinstance(speakers, dict) and len(speakers) == 2, '原生双人需要恰好两位 speakers')
        voices = []
        for speaker, voice in speakers.items():
            require(isinstance(speaker, str) and speaker.strip() and speaker == speaker.strip(), 'speaker 名称不能为空或含首尾空白')
            require(isinstance(voice, str) and voice.strip(), 'speaker 缺少音色')
            require(not voice.startswith(('voice_', 'voicekey_')), '原生双人的 prebuiltVoiceConfig 需预置音色；自定义声音请逐轮制作')
            voices.append({'speaker': speaker, 'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}})
        require(isinstance(turns, list) and turns, 'turns 必须为非空数组')
        parts, used = [], set()
        for turn in turns:
            require(isinstance(turn, dict) and not set(turn) - {'speaker', 'text', 'source_text', 'style', 'events'}, '轮次仅支持 speaker/text/source_text/style/events')
            speaker = turn.get('speaker')
            require(isinstance(speaker, str) and speaker in speakers, '轮次引用未定义的 speaker')
            text, style = transcript(c, turn, dialogue=True)
            used.add(speaker)
            if '|' in text:
                used.update(speakers)  # The other speaker performs the pipe reaction.
            metadata = {'speaker': speaker}
            if style:
                metadata['style'] = style
            parts.append({'text': text, 'speech_metadata': metadata})
        require(used == set(speakers), '两位 speaker 均需发言或作为 |回应| 的听者')
        require(sum(len(p['text']) for p in parts) <= c.get('max_chars', 100000), '对话总长度超过路由限制，请按场景拆分')
        speech = {'multiSpeakerVoiceConfig': {'speakerVoiceConfigs': voices}}
    else:
        require(not set(clip) - {'id', 'text', 'source_text', 'voice', 'style', 'events'}, '片段包含未知字段')
        require(isinstance(clip.get('voice'), str) and clip['voice'].strip(), '片段缺少 voice')
        require(not clip['voice'].startswith('voicekey_'), '临时 voice key 暂未实现安全存储；请使用预置声音或存储式 ID')
        text, style = transcript(c, clip)
    body = copy.deepcopy(c.get('extra_body', {}))
    require(isinstance(body, dict), 'extra_body 必须是对象')
    if c['protocol'] == 'speech':
        require(not set(body) & {'model', 'input', 'voice', 'response_format'}, 'extra_body 不得覆盖核心字段')
        body.update(model=c['model'], input=text, voice=clip['voice'], response_format=c['response_format'])
        if style:
            require(c.get('style_field'), '此路由未配置表演指令映射；不能静默丢弃 style')
            put(body, c['style_field'], style)
        return c['base_url'] + '/audio/speech', body
    require(not set(body) & {'contents', 'generationConfig'}, 'extra_body 不得覆盖 contents/generationConfig')
    if not dialogue:
        if c['schema'] == 'metadata':
            part = {'text': text}
            if style:
                part['speech_metadata'] = {'style': style}
            voice = {'voice': clip['voice']}
        else:
            part = {'text': (f'Read the following text with this delivery: {style}\nText:\n' if style else '') + text}
            voice = {'prebuiltVoiceConfig': {'voiceName': clip['voice']}}
        parts, speech = [part], {'voiceConfig': voice}
    body.update(contents=[{'role': 'user', 'parts': parts}], generationConfig={'responseModalities': ['AUDIO'], 'speechConfig': speech})
    return c['base_url'] + '/models/' + urllib.parse.quote(c['model'], safe='') + ':generateContent', body


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def call(c, url, body):
    secret = os.environ.get(c['key_env'])
    require(secret, f"未配置环境变量 {c['key_env']}")
    headers = {'Content-Type': 'application/json'}
    headers['Authorization' if c['auth'] == 'bearer' else 'x-goog-api-key'] = ('Bearer ' if c['auth'] == 'bearer' else '') + secret
    req = urllib.request.Request(url, json.dumps(body).encode(), headers)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=180) as response:
            data = response.read(128 * 1024 * 1024 + 1)
            require(len(data) <= 128 * 1024 * 1024, '响应超过 128 MiB 限制')
            return data, response.headers.get('Content-Type', ''), response.headers.get('X-Generation-Id')
    except urllib.error.HTTPError as e:
        # Never print upstream bodies: they can echo credentials or private input.
        raise RuntimeError(f'HTTP {e.code}；未重试，请检查接入商控制台') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError('网络请求未完成；可能已计费，未自动重试') from None


def wav_data(data, mime, rate):
    if data.startswith(b'RIFF') and data[8:12] == b'WAVE':
        with wave.open(io.BytesIO(data), 'rb') as f:
            params = f.getparams()
            frames = f.readframes(params.nframes)
        require(params.comptype == 'NONE' and params.nframes > 0 and len(frames) == params.nframes * params.nchannels * params.sampwidth, 'WAV 为空或不完整')
        return data
    require(mime.split(';')[0].strip().lower() in ('audio/pcm', 'audio/l16', 'audio/lpcm', 'application/octet-stream'), '预期 WAV/PCM，收到其他类型')
    require(data and len(data) % 2 == 0 and not data.lstrip().startswith((b'{', b'<')), 'PCM 为空、损坏或是错误响应')
    matched = re.search(r'rate=(\d+)', mime)
    if matched:
        rate = int(matched.group(1))
    out = io.BytesIO()
    with wave.open(out, 'wb') as f:
        f.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        f.writeframes(data)
    return out.getvalue()


def decode(c, data, mime):
    usage = None
    if c['protocol'] == 'gemini':
        result = json.loads(data)
        candidates = result.get('candidates', [])
        require(len(candidates) == 1 and candidates[0].get('finishReason') == 'STOP', 'Gemini 未返回单个完成的音频结果')
        parts = candidates[0].get('content', {}).get('parts', [])
        audio = [p['inlineData'] for p in parts if 'inlineData' in p]
        require(len(audio) == 1, '预期一个完整音频 part；未自动拼接未知分块')
        data = base64.b64decode(audio[0]['data'], validate=True)
        mime = audio[0]['mimeType']
        usage = result.get('usageMetadata')
    elif c['response_format'] == 'wav':
        require(data.startswith(b'RIFF'), '请求 WAV 但收到非 WAV 内容')
    return wav_data(data, mime, c.get('sample_rate', 24000)), usage


def fingerprint(c, clip):
    return hashlib.sha256(json.dumps([c, clip], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def scenes_for(plan, ids):
    """Validate the arrangement before any paid requests; omitted scenes concatenate."""
    if 'scenes' not in plan:
        return [{'id': cid, 'layers': [{'clip': cid}]} for cid in ids]
    scenes = plan['scenes']
    require(isinstance(scenes, list) and scenes, 'scenes 必须为非空数组')
    seen, used = set(), set()
    for scene in scenes:
        require(isinstance(scene, dict) and set(scene) == {'id', 'layers'}, '场景需要 id/layers')
        sid = scene['id']
        require(isinstance(sid, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', sid) and sid not in seen, '场景 id 无效或重复')
        seen.add(sid)
        require(isinstance(scene['layers'], list) and scene['layers'], '场景需要非空 layers')
        for layer in scene['layers']:
            require(isinstance(layer, dict) and not set(layer) - {'clip', 'start_ms', 'gain_db'}, '轨道仅支持 clip/start_ms/gain_db')
            cid = layer.get('clip')
            require(isinstance(cid, str) and cid in ids, '轨道引用不存在的 clip')
            used.add(cid)
            start, gain = layer.get('start_ms', 0), layer.get('gain_db', 0)
            require(type(start) is int and start >= 0, 'start_ms 必须为非负整数')
            require(type(gain) in (int, float) and -60 <= gain <= 12, 'gain_db 范围为 -60 到 12')
    require(used == set(ids), 'scenes 必须覆盖所有 clips，避免生成未使用的音频')
    return scenes


def render(c, plan, directory, dry=False, only=None, new_take=False, retry=False):
    require(isinstance(plan, dict) and set(plan) <= {'title', 'clips', 'scenes'} and isinstance(plan.get('clips'), list) and plan['clips'], '制作稿需要非空 clips 数组')
    compiled = [(clip, request(c, clip)) for clip in plan['clips']]
    ids = [clip['id'] for clip, _ in compiled]
    require(len(ids) == len(set(ids)), '片段 id 重复')
    scenes = scenes_for(plan, ids)
    require(only is None or only in ids, '--clip 不存在')
    if dry:
        return {'requests': [{'clip': clip['id'], 'url': url, 'body': body} for clip, (url, body) in compiled if only is None or clip['id'] == only], 'scenes': scenes, 'account_verified': False}
    require(os.environ.get(c['key_env']), f"未配置环境变量 {c['key_env']}")
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    with (out / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = out / 'manifest.json'
        m = read(path) if path.exists() else {'version': 1, 'clips': {}}
        m['order'] = ids
        m['scenes'] = scenes
        for clip, _ in compiled:
            entry = m['clips'].setdefault(clip['id'], {'takes': [], 'selected': None})
            entry['current'] = fingerprint(c, clip)
            entry['script'] = clip
        save(path, m)
        for clip, (url, body) in compiled:
            if only is not None and clip['id'] != only:
                continue
            entry = m['clips'][clip['id']]
            matching = [t for t in entry['takes'] if t['fingerprint'] == entry['current']]
            done = [t for t in matching if t['status'] == 'complete']
            if done and not new_take:
                for take in done:
                    require((out / take['file']).exists(), '已完成的音频文件缺失；用 --new-take 显式重做')
                    wav_data((out / take['file']).read_bytes(), 'audio/wav', c.get('sample_rate', 24000))
                continue
            require(retry or not any(t['status'] in ('running', 'uncertain') for t in matching), '上次请求结果不确定；检查供应商后用 --retry-uncertain 显式重试')
            tid = uuid.uuid4().hex[:12]
            take = {'id': tid, 'fingerprint': entry['current'], 'status': 'running', 'file': f"{clip['id']}-{tid}.wav", 'route': {'provider': c['provider'], 'base_url': c['base_url'], 'model': c['model']}, 'script': clip, 'request': body}
            entry['takes'].append(take)
            save(path, m)
            try:
                data, mime, generation = call(c, url, body)
                audio, usage = decode(c, data, mime)
                with (out / take['file']).open('xb') as f:
                    f.write(audio)
                take.update(status='complete', usage=usage, generation_id=generation, transcript_checked=False)
                if entry['selected'] is None:
                    entry['selected'] = tid
                save(path, m)
            except BaseException:
                take['status'] = 'uncertain'
                save(path, m)
                raise
        return m


def mix_scene(scene, audio, fmt):
    require(fmt[1] == 2, '重叠混音仅支持 16-bit PCM WAV')
    tracks = []
    for layer in scene['layers']:
        item = audio[layer['clip']]
        start = (layer.get('start_ms', 0) * fmt[2] + 500) // 1000
        tracks.append((layer, item, start))
    count = max(start + item['count'] for _, item, start in tracks)
    # ponytail: buffer one scene; stream in blocks if long scenes exceed memory.
    require(count * fmt[0] * 8 <= 256 * 1024 * 1024, '场景混音缓冲超过 256 MiB，请按场景拆分')
    mixed = array('d', [0.0]) * (count * fmt[0])
    for layer, item, start in tracks:
        samples = array('h')
        samples.frombytes(item['frames'])
        if sys.byteorder != 'little':
            samples.byteswap()
        gain = 10 ** (layer.get('gain_db', 0) / 20)
        for i, value in enumerate(samples, start * fmt[0]):
            mixed[i] += value * gain
    peak = max((abs(value) for value in mixed), default=0)
    scale = min(1.0, 32767 / peak) if peak else 1.0
    result = array('h', (round(value * scale) for value in mixed))
    if sys.byteorder != 'little':
        result.byteswap()
    return result.tobytes(), count, scale, tracks


def export(directory, output, plan=None):
    out = Path(directory)
    with (out / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m = read(out / 'manifest.json')
        if plan is not None:
            require(isinstance(plan, dict) and set(plan) <= {'title', 'clips', 'scenes'}, '制作稿包含未知字段')
            require(plan.get('clips') == [m['clips'][cid]['script'] for cid in m['order']], 'export --plan 只能调整编排；台词或表演变化请先 render')
        scenes = scenes_for(plan if plan is not None else m, m['order'])
        chunks, timeline, scene_times, audio, fmt, offset = [], [], [], {}, None, 0
        for cid in m['order']:
            entry = m['clips'][cid]
            take = next((t for t in entry['takes'] if t['id'] == entry['selected']), None)
            require(take and take['status'] == 'complete' and take['fingerprint'] == entry['current'], f'{cid} 缺少当前稿的已选音频，请 select')
            with wave.open(str(out / take['file']), 'rb') as f:
                current = (f.getnchannels(), f.getsampwidth(), f.getframerate())
                frames, count = f.readframes(f.getnframes()), f.getnframes()
            require(count > 0 and f.getcomptype() == 'NONE' and len(frames) == count * current[0] * current[1], '音频损坏')
            require(fmt is None or fmt == current, '音频格式不同；请先使用同一采样率重新生成或显式转换')
            fmt = current
            audio[cid] = {'frames': frames, 'count': count, 'take': take['id']}
        for scene in scenes:
            layers = scene['layers']
            layer = layers[0]
            if len(layers) == 1 and layer.get('start_ms', 0) == 0 and layer.get('gain_db', 0) == 0:
                item = audio[layer['clip']]
                frames, count, scale, tracks = item['frames'], item['count'], 1.0, [(layer, item, 0)]
            else:
                frames, count, scale, tracks = mix_scene(scene, audio, fmt)
            for layer, item, start in tracks:
                timeline.append({'scene': scene['id'], 'clip': layer['clip'], 'take': item['take'], 'start': (offset + start) / fmt[2], 'end': (offset + start + item['count']) / fmt[2], 'gain_db': layer.get('gain_db', 0)})
            scene_times.append({'id': scene['id'], 'start': offset / fmt[2], 'end': (offset + count) / fmt[2], 'peak_scale': scale})
            offset += count
            chunks.append(frames)
        target = Path(output)
        require(target.suffix.lower() == '.wav', '当前导出仅支持 .wav；压缩格式请用本地音频工具转换')
        sidecar = target.with_suffix('.timeline.json')
        require(not target.exists() and not sidecar.exists(), '输出已存在，请换文件名')
        with target.open('xb') as raw:
            with wave.open(raw, 'wb') as f:
                f.setparams((*fmt, 0, 'NONE', 'not compressed'))
                for frames in chunks:
                    f.writeframes(frames)
        save(sidecar, {'segments': timeline, 'scenes': scene_times, 'word_timestamps': False})
        return {'audio': str(target.resolve()), 'timeline': str(sidecar.resolve())}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('check', 'speak', 'render'):
        q = sub.add_parser(name)
        q.add_argument('--config', required=True)
        if name == 'check':
            continue
        q.add_argument('--out', required=True)
        q.add_argument('--dry-run', action='store_true')
        q.add_argument('--new-take', action='store_true')
        q.add_argument('--retry-uncertain', action='store_true')
        if name == 'render':
            q.add_argument('--plan', required=True)
            q.add_argument('--clip')
        else:
            group = q.add_mutually_exclusive_group(required=True)
            group.add_argument('--text')
            group.add_argument('--text-file')
            q.add_argument('--voice', required=True)
            q.add_argument('--style', default='')
    for name in ('inspect', 'select', 'export'):
        q = sub.add_parser(name)
        q.add_argument('--out', required=True)
        if name == 'select':
            q.add_argument('--clip', required=True)
            q.add_argument('--take', required=True)
        if name == 'export':
            q.add_argument('--output', required=True)
            q.add_argument('--plan', help='只调整场景编排，复用已有选片，不调用 TTS')
    a = p.parse_args()
    if a.command in ('check', 'speak', 'render'):
        c = config(a.config)
        if a.command == 'check':
            return {'provider': c['provider'], 'protocol': c['protocol'], 'model': c['model'], 'key_configured': bool(os.environ.get(c['key_env'])), 'account_verified': False, 'style_configured': c['protocol'] == 'gemini' or bool(c.get('style_field')), 'implemented': ['single-speaker', 'split-dialogue', 'native-dialogue', 'style', 'takes', 'resume', 'scene-mixing', 'wav-export'], 'native_dialogue_route': c['protocol'] == 'gemini' and c['schema'] == 'metadata', 'not_implemented': ['streaming', 'voices-management', 'batch', 'interactions']}
        plan = read(a.plan) if a.command == 'render' else {'clips': [{'id': 'speech', 'text': Path(a.text_file).read_text(encoding='utf-8') if a.text_file else a.text, 'voice': a.voice, 'style': a.style}]}
        result = render(c, plan, a.out, a.dry_run, getattr(a, 'clip', None), a.new_take, a.retry_uncertain)
        if not a.dry_run:
            return {'manifest': str((Path(a.out) / 'manifest.json').resolve()), 'clips': {cid: {'selected': entry['selected'], 'takes': [{k: t[k] for k in ('id', 'status', 'file')} for t in entry['takes']]} for cid, entry in result['clips'].items()}}
        return result
    if a.command == 'export':
        return export(a.out, a.output, read(a.plan) if a.plan else None)
    path = Path(a.out) / 'manifest.json'
    if a.command == 'select':
        with (Path(a.out) / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            m = read(path)
            entry = m['clips'][a.clip]
            require(any(t['id'] == a.take and t['status'] == 'complete' and t['fingerprint'] == entry['current'] for t in entry['takes']), '只能选择当前稿的已完成 take')
            entry['selected'] = a.take
            save(path, m)
        return {'selected': a.take}
    return read(path)


if __name__ == '__main__':
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, wave.Error) as error:
        print(f'错误：{error}', file=sys.stderr)
        sys.exit(1)
