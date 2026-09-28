"""Offline integration check: python3 -m unittest discover -s tests -v"""
import base64
import copy
import importlib.util
import html
import io
import json
import os
import re
from pathlib import Path
import tempfile
import struct
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer
import wave

spec = importlib.util.spec_from_file_location('tts', Path(__file__).parents[1] / 'scripts/tts.py')
tts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tts)


class Flow(unittest.TestCase):
    def test_published_examples_stay_readable_and_offline(self):
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as folder, patch.object(tts, 'call', side_effect=AssertionError('Examples must stay offline')):
            cfg = Path(folder) / 'route.json'
            tts.save(cfg, {'provider': 'google', 'model': 'gemini-3.8-flash-tts'})
            for name, count in (('assets/dialogue-plan.json', 1), ('assets/crowd-plan.json', 4),
                                ('examples/the-magic-finger/plan.json', 6)):
                result = tts.render(tts.config(cfg), tts.read(root / name), Path(folder) / 'audio', dry=True)
                self.assertEqual(len(result['requests']), count)
            self.assertFalse((Path(folder) / 'audio').exists())
        example = root / 'examples/the-magic-finger'
        page = (example / 'director.html').read_text()
        plan = tts.read(example / 'plan.json')
        blocks = re.findall(r'<p class="spoken">(.*?)</p>', page, re.S)
        self.assertEqual(len(blocks), len(plan['clips']))
        for block, clip in zip(blocks, plan['clips']):
            plain, events = '', []
            for part in re.split(r'(<span class="event"[^>]*>.*?</span>)', block):
                if part.startswith('<span'):
                    events.append({'at': len(plain), 'tag': html.unescape(re.sub(r'<[^>]+>', '', part))})
                else:
                    plain += html.unescape(part)
            self.assertEqual(plain, clip['source_text'])
            self.assertEqual(plain, clip['text'])
            self.assertEqual(events, clip.get('events', []))
            self.assertIn(clip['source_text'], (example / 'director.md').read_text())

    def test_native_dialogue_lifecycle(self):
        plan = tts.read(Path(__file__).parents[1] / 'assets/dialogue-plan.json')
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'TTS_TEST_KEY': 'local-test-only'}):
            root = Path(folder)
            tts.save(root / 'route.json', {'provider': 'google', 'model': 'gemini-3.8-flash-tts', 'key_env': 'TTS_TEST_KEY'})
            c = tts.config(root / 'route.json')
            out = root / 'audio'
            audio = tts.wav_data(b'\x01\x00' * 240, 'audio/pcm', 24000)
            response = json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'inlineData': {'data': base64.b64encode(audio).decode(), 'mimeType': 'audio/wav'}}]}}]}).encode()
            with patch.object(tts, 'call', return_value=(response, 'application/json', None)) as call:
                preview = tts.render(c, plan, out, dry=True)
                call.assert_not_called()
                self.assertFalse(out.exists())
                self.assertEqual(len(preview['requests']), 1)
                body = preview['requests'][0]['body']
                self.assertEqual(body['generationConfig']['speechConfig'], {'multiSpeakerVoiceConfig': {'speakerVoiceConfigs': [
                    {'speaker': 'Alex', 'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': 'Charon'}}},
                    {'speaker': 'Sam', 'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': 'Kore'}}}]}})
                self.assertEqual(body['contents'][0]['parts'], [
                    {'text': "<breath>About yesterday,|I'm listening.|I'd like to explain.", 'speech_metadata': {'speaker': 'Alex', 'style': 'Hesitant, speaking softly'}},
                    {'text': "Take your time,|Really?|I'm not upset.", 'speech_metadata': {'speaker': 'Sam', 'style': 'Gentle and reassuring'}}])
                m = tts.render(c, plan, out)
                tts.render(c, plan, out)
                self.assertEqual(call.call_count, 1)
                self.assertEqual(m['clips']['conversation']['takes'][0]['request'], body)
                result = tts.export(out, root / 'dialogue.wav')
                self.assertEqual(Path(result['audio']).read_bytes(), audio)
                self.assertEqual(len(tts.read(result['timeline'])['segments']), 1)
                changed = copy.deepcopy(plan)
                changed['clips'][0]['turns'][1]['style'] = 'Distant'
                m = tts.render(c, changed, out)
                self.assertEqual(call.call_count, 2)  # One entire joint take, not two speaker calls.
                self.assertEqual(len(m['clips']['conversation']['takes']), 2)
                with self.assertRaises(ValueError):
                    tts.export(out, root / 'stale.wav')
                # Reject malformed/unsupported dialogue before the first paid call, even after a valid clip.
                bad_clips = []
                for field, value in (('speakers', {'Alex': 'Kore'}), ('speakers', {'Alex': 'Kore', 'Sam': 'Puck', 'Taylor': 'Orus'}),
                                     ('speakers', {'Alex': 'voice_custom', 'Sam': 'Kore'}), ('turns', []), ('voice', 'Kore')):
                    bad_clips.append({**plan['clips'][0], field: value})
                for turn in ({'speaker': 'Taylor', 'text': 'Hello.'}, {'speaker': 'Alex', 'text': 'Wait|Hmm'},
                             {'speaker': 'Alex', 'text': 'Wait||Tell me more.'}, {'speaker': 'Alex', 'text': 'Only me.'}):
                    bad_clips.append({**plan['clips'][0], 'turns': [turn]})
                for clip in bad_clips:
                    with self.assertRaises(ValueError):
                        tts.render(c, {'clips': [{'id': 'intro', 'text': 'Start.', 'voice': 'Charon'}, clip]}, root / 'bad')
                max_turn = max(len(p['text']) for p in body['contents'][0]['parts'])
                for route in ({**c, 'protocol': 'speech'}, {**c, 'schema': 'legacy'}, {**c, 'max_chars': max_turn}):
                    with self.assertRaises(ValueError):
                        tts.render(route, plan, root / 'bad')
                with self.assertRaises(ValueError):
                    tts.render(c, {'clips': [{'id': 'solo', 'voice': 'Kore', 'text': 'Hello|Hmm|Goodbye'}]}, root / 'bad')
                self.assertEqual(call.call_count, 2)
                self.assertFalse((root / 'bad').exists())
                # Extended prebuilt names are not restricted to the original 30 voices.
                extended = copy.deepcopy(plan['clips'][0])
                extended['speakers']['Alex'] = 'Bodi'
                tts.request(c, extended)
                mixed = {'clips': [{'id': 'intro', 'text': 'They discussed what happened yesterday.', 'voice': 'Charon'}, plan['clips'][0]]}
                tts.render(c, mixed, root / 'mixed')
                self.assertEqual(call.call_count, 4)
                result = tts.export(root / 'mixed', root / 'mixed.wav')
                timeline = tts.read(result['timeline'])
                self.assertEqual([s['clip'] for s in timeline['segments']], ['intro', 'conversation'])
                self.assertEqual(timeline['segments'][-1]['end'], .02)

    def test_scene_mixing_and_remix_without_tts(self):
        def wav(value):
            stream = io.BytesIO()
            with wave.open(stream, 'wb') as f:
                f.setparams((1, 2, 1000, 0, 'NONE', 'not compressed'))
                f.writeframes(struct.pack('<10h', *([value] * 10)))
            return stream.getvalue()

        def samples(path):
            with wave.open(str(path), 'rb') as f:
                return list(struct.unpack('<' + str(f.getnframes()) + 'h', f.readframes(f.getnframes())))

        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'TTS_TEST_KEY': 'local-test-only'}):
            root = Path(folder)
            cfg = root / 'route.json'
            tts.save(cfg, {'provider': 'aihubmix', 'model': 'gemini-3.8-flash-tts', 'key_env': 'TTS_TEST_KEY'})
            c = tts.config(cfg)
            plan = {'clips': [{'id': v, 'text': v, 'voice': 'Kore'} for v in ('a', 'b', 'c')], 'scenes': [
                {'id': 'intro', 'layers': [{'clip': 'a'}]},
                {'id': 'crowd', 'layers': [{'clip': 'a'}, {'clip': 'b', 'start_ms': 3, 'gain_db': -6.0206}, {'clip': 'c', 'start_ms': 6, 'gain_db': -6.0206}]}]}
            out = root / 'audio'
            with patch.object(tts, 'call', side_effect=[(wav(v), 'audio/wav', None) for v in (1000, 2000, 3000)]) as call:
                preview = tts.render(c, plan, out, dry=True)
                self.assertEqual(preview['scenes'], plan['scenes'])
                call.assert_not_called()
                tts.render(c, plan, out)
                tts.render(c, plan, out)
                self.assertEqual(call.call_count, 3)
            with patch.object(tts, 'call', side_effect=AssertionError('Remix must stay offline')):
                result = tts.export(out, root / 'mixed.wav')
                self.assertEqual(samples(result['audio']), [1000] * 10 + [1000] * 3 + [2000] * 3 + [3500] * 4 + [2500] * 3 + [1500] * 3)
                timeline = tts.read(result['timeline'])
                self.assertEqual(timeline['segments'][-1]['start'], .016)
                self.assertEqual(timeline['scenes'][-1]['end'], .026)
                remix = copy.deepcopy(plan)
                remix['scenes'] = [{'id': 'loud', 'layers': [{'clip': v, 'gain_db': 12} for v in ('a', 'b', 'c', 'c')]}]
                result = tts.export(out, root / 'remixed.wav', remix)
                self.assertEqual(samples(result['audio']), [32767] * 10)
                self.assertLess(tts.read(result['timeline'])['scenes'][0]['peak_scale'], 1)
                self.assertEqual(tts.read(out / 'manifest.json')['scenes'], plan['scenes'])
                remix['clips'][0]['text'] = 'changed'
                with self.assertRaises(ValueError):
                    tts.export(out, root / 'unrendered.wav', remix)
                for layers in ([{'clip': 'missing'}], [{'clip': 'a', 'start_ms': -1}], [{'clip': 'a', 'gain_db': float('nan')}], [{'clip': 'a'}]):
                    bad = {**plan, 'scenes': [{'id': 'bad', 'layers': layers}]}
                    with self.assertRaises(ValueError):
                        tts.render(c, bad, root / 'bad')
                self.assertFalse((root / 'bad').exists())
            for tag in ('snicker', 'heavy breath', 'chuckle', 'exhales'):
                _, body = tts.request(c, {'id': 'tag', 'text': 'Hello', 'voice': 'Kore', 'events': [{'at': 0, 'tag': tag}]})
                self.assertEqual(body['input'], f'<{tag}>Hello')

    def test_offline_end_to_end(self):
        pcm = b'\x00\x00' * 240
        stream = io.BytesIO()
        with wave.open(stream, 'wb') as f:
            f.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            f.writeframes(pcm)
        wav = stream.getvalue()
        requests = []

        class Handler(BaseHTTPRequestHandler):
            mode = 'ok'
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path, body))
                if self.mode == 'redirect':
                    self.send_response(307)
                    self.send_header('Location', '/stolen')
                    self.end_headers()
                    return
                if self.mode == 'broken':
                    data, mime = b'{"error":"test"}', 'application/json'
                elif ':generateContent' in self.path:
                    data = json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'inlineData': {'data': base64.b64encode(wav).decode(), 'mimeType': 'audio/wav'}}]}}], 'usageMetadata': {'totalTokenCount': 12}}).encode()
                    mime = 'application/json'
                else:
                    data = pcm if body['response_format'] == 'pcm' else wav
                    mime = 'audio/pcm' if body['response_format'] == 'pcm' else 'audio/wav'
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old = os.environ.get('TTS_TEST_KEY')
        os.environ['TTS_TEST_KEY'] = 'secret-test-only'
        try:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                clip = {'id': 'a', 'text': 'Café.', 'voice': 'Kore', 'style': 'Restrained and soft', 'events': [{'at': 4, 'tag': 'sigh'}]}
                plan = {'clips': [clip, {**clip, 'id': 'b', 'voice': 'Puck'}]}
                for provider in ('aihubmix', 'openrouter', 'google'):
                    path = root / 'config.json'
                    tts.save(path, {'provider': provider, 'model': 'gemini-3.8-flash-tts', 'base_url': f'http://127.0.0.1:{server.server_port}', 'key_env': 'TTS_TEST_KEY'})
                    c = tts.config(path)
                    url, body = tts.request(c, clip)
                    if provider == 'openrouter':
                        self.assertEqual(body['provider']['options']['google-ai-studio']['speech_metadata']['style'], clip['style'])
                    if provider == 'aihubmix':
                        self.assertEqual(body['instructions'], clip['style'])
                        _, ordered = tts.request(c, {**clip, 'events': [{'at': 0, 'tag': 'sigh'}, {'at': 0, 'tag': 'breath'}]})
                        self.assertEqual(ordered['input'], '<sigh><breath>Café.')
                    if provider == 'google':
                        self.assertEqual(body['contents'][0]['parts'][0]['text'], 'Café<sigh>.')
                    before = len(requests)
                    tts.render(c, plan, root / provider, dry=True)
                    self.assertEqual(len(requests), before)
                    out = root / provider
                    m = tts.render(c, plan, out)
                    self.assertEqual(len(requests), before + 2)
                    tts.render(c, plan, out)
                    self.assertEqual(len(requests), before + 2)
                    self.assertNotIn('secret-test-only', (out / 'manifest.json').read_text())
                    result = tts.export(out, root / f'{provider}.wav')
                    with wave.open(result['audio'], 'rb') as f:
                        self.assertEqual(f.getnframes(), 480)
                    self.assertEqual(tts.read(result['timeline'])['segments'][1]['start'], 0.01)
                    with self.assertRaises(ValueError):
                        tts.export(out, root / f'{provider}.wav')
                    # Only the changed clip renders; old selection remains, export blocks stale audio.
                    changed = {'clips': [{**clip, 'style': 'Distant'}, plan['clips'][1]]}
                    m = tts.render(c, changed, out)
                    self.assertEqual(len(requests), before + 3)
                    self.assertEqual(len(m['clips']['a']['takes']), 2)
                    with self.assertRaises(ValueError):
                        tts.export(out, root / f'{provider}-stale.wav')
                # Unsupported style must fail before a request, not be silently dropped.
                c['protocol'] = 'speech'
                c['response_format'] = 'wav'
                c['style_field'] = None
                with self.assertRaises(ValueError):
                    tts.render(c, plan, root / 'unsupported')
                c['style_field'] = 'instructions'
                Handler.mode = 'broken'
                with self.assertRaises(ValueError):
                    tts.render(c, plan, root / 'uncertain')
                before = len(requests)
                with self.assertRaises(ValueError):
                    tts.render(c, plan, root / 'uncertain')
                self.assertEqual(len(requests), before)
                Handler.mode = 'ok'
                tts.render(c, plan, root / 'uncertain', retry=True)
                Handler.mode = 'redirect'
                before = len(requests)
                with self.assertRaises(RuntimeError):
                    tts.render(c, plan, root / 'redirect')
                self.assertEqual(len(requests), before + 1)
                self.assertNotEqual(requests[-1][0], '/stolen')
                with self.assertRaises(ValueError):
                    tts.wav_data(wav[:-2], 'audio/wav', 24000)
                with self.assertRaises(ValueError):
                    tts.request(c, {**clip, 'id': '../escape'})
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            if old is None:
                os.environ.pop('TTS_TEST_KEY', None)
            else:
                os.environ['TTS_TEST_KEY'] = old


if __name__ == '__main__':
    unittest.main()
