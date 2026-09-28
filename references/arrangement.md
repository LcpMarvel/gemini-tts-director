# JSON 场景编排与混音

导演先交付可审阅的 JSON，生成和后期都以它为准。`clips` 描述单人或原生双人表演；`scenes` 按数组顺序播放，每个场景的 `layers` 可错位重叠。省略 `scenes` 时按 clips 顺序拼接，兼容原有制作稿。

## 原生双人及听者回应

先由导演按 [文本与关系](directing.md#先判断文本再决定怎么演) 选择是否需要联合表演。完整可执行稿见 [双人回应示例](../assets/dialogue-plan.json)（原创示例，未生成音频）：

```json
{
  "id": "conversation",
  "speakers": {"甲": "Charon", "乙": "Kore"},
  "turns": [
    {"speaker": "甲", "text": "昨天的事，|嗯，我听着。|我想再解释一下。", "style": "有些迟疑，轻声开口"},
    {"speaker": "乙", "text": "你慢慢说，|真的？|我没有怪你。", "style": "温和，带一点安慰"}
  ]
}
```

- 一个双人 clip 使用恰好两位 `speakers`，名称与 `turns[].speaker` 精确对应。每轮拥有 `text`、可选 `style/events/source_text`；clip 可保留整个场景的 `source_text`。不同时设置单人 `voice/text/style/events`。
- `|...|` 内是另一位听者的回应：第一轮由乙说“嗯，我听着”，第二轮由甲说“真的”。可有多段回应，也可以完全不用竖线，仅按轮次说话。符号须成对、内容非空；正文原有竖线要先决定读法，不能当作标记误传。
- `events.at` 仍以该轮原始 `text` 的字符偏移定位，包含竖线及回应文字。尽量让动作的所属角色清晰；独白中的 `<sigh>` 不表示另一个人插话。
- 请求使用 Gemini `schema=metadata`，每轮独立 part，传 `speech_metadata.speaker/style` 与 `multiSpeakerVoiceConfig.speakerVoiceConfigs[].voiceConfig.prebuiltVoiceConfig.voiceName`。当前依据 Gemini 3.8 [官方双人和回应文档](https://ai.google.dev/gemini-api/docs/generate-content/speech-generation#backchannels-and-overlapping-speech) 实现；其他模型和兼容地址须核对契约。预置音色没有 30 种白名单；自定义 `voice_...`/临时 key 不塞入预置字段。
- 一条双人 clip 只发一次 TTS 请求，得到一条联合 WAV，复用现有 render/inspect/select/export 流程；可像其他 clip 一样放入 scenes 拼接。它不提供双方独立声轨或轮内时间戳。改回应、任意一轮或某一方音色，都会生成整段新 take；先说明这个重做范围，不重复生成其他片段。

```sh
python3 "$TTS" render --config route.json --plan dialogue-plan.json --out dialogue-audio --dry-run
# 在生成授权范围内执行：
python3 "$TTS" render --config route.json --plan dialogue-plan.json --out dialogue-audio
python3 "$TTS" export --out dialogue-audio --output dialogue.wav
```

阅读稿逐轮显示说话人、台词和短 style，在对应位置标“乙插话：嗯，我听着”。整段只有一个播放器；生成前写“待制作”。不要将联合 WAV 的前后两个切片冒充两人的独立音轨。当前双人实现已离线验证请求及文件流程，实际回应是否自然、是否串声仍待生成试听。

## 群声示例

复制 [酒客群声制作稿](../assets/crowd-plan.json)。它包含一句旁白和三条不同酒客的同一句台词，共四次 TTS 请求；既有授权未覆盖时，先说明数量与费用。正文原句不改，重复由三名演员分别表演。

```json
{
  "id": "crowd",
  "layers": [
    {"clip": "lead", "start_ms": 0, "gain_db": 0},
    {"clip": "guest-2", "start_ms": 180, "gain_db": -7},
    {"clip": "guest-3", "start_ms": 420, "gain_db": -9}
  ]
}
```

主声先挑头，另两声错落跟进、稍轻，避免齐声朗诵。各人的短 style 分别安排语速、重音和语气；具体音色由用户与导演选择，不固定为示例中的声音。

这份示例已在 2026-09-28 使用 Google Gemini 3.8 Flash TTS 实际生成四条分轨，再本地导出约 6.22 秒混音，用户试听后接受。它是可运行的参考，不是通用预设：人数、音色、180/420 毫秒错位和音量均应随文本关系调整。

`start_ms` 是相对本场景起点的文件起声时间，默认 0，非负整数；它包含 TTS 自带的开头静音或呼吸，并非逐字对齐。`gain_db` 默认 0，范围 -60 到 +12 dB。场景长度由最晚结束的轨道决定，下一场紧接其后。同一 clip 可复用，但所有 clips 必须被场景引用，避免白生成。

## 生成与后期

```sh
python3 "$TTS" render --config route.json --plan crowd-plan.json --out crowd-audio --dry-run
# 用户授权后才运行：
python3 "$TTS" render --config route.json --plan crowd-plan.json --out crowd-audio
python3 "$TTS" export --out crowd-audio --output crowd.wav
```

`dry-run` 展示实际 TTS 请求与场景编排，不发请求。`render` 只生成独立分轨，保存原始 WAV、真实请求、用量与选片；`export` 读取已有选片，在本地叠声、拼接，不调用 TTS。

只调整时间或音量时，改 JSON 的 `scenes` 后运行：

```sh
python3 "$TTS" export --out crowd-audio --plan crowd-plan.json --output crowd-remix.wav
```

这种重混不需要 Key，也不产生 TTS 费用。`--plan` 中 clips 必须与已登记制作稿完全一致；改了台词、音色、style 或事件时先 render，只生成受影响片段，再 select 新 take 后导出。旧录音和旧成品不覆盖。

先把用户反馈翻译为最小改动：“后面的人太响”改 gain_db；“听着太整齐”改 start_ms；“不够讥讽”改对应 clip 的 style；“这个声音不合适”改 voice。前两种只重混，后两种才需新的 TTS；混合反馈分别处理，不重复生成未改的角色。带编号保存新混音，并在原位置更新试听，保留旧版供比较。

## 导演稿怎么呈现

在群声发生处标“群声”，用小表列出角色、音色、进入时间和音量，提供 JSON 链接；没有生成前写“待制作”。普通独白无需展开混音参数。不向单个 voice 的 style 填“几个人同时说”来冒充多条声音，也不私自补“对啊”“就是”等原文没有的词。

本地错位叠声适用于七嘴八舌、应和和合唱意图；两人之间的自然倾听与插话可选上面的原生联合表演。前者能独立调音，后者由模型共同表演，按文本和返工需要选择。

## 可验证边界

- 混音输入须为相同采样率、声道数的 16-bit PCM WAV；不自动变速、重采样或制造空间声。普通无重叠拼接保持原字节。
- 叠加峰值超出范围时，整个场景等比例降低音量，保持相对关系，避免硬削波。实际缩放系数写在 `*.timeline.json` 的 `scenes[].peak_scale`。
- 时间线保存每条选片的实际 start/end、take、gain_db 和场景边界，可出现重叠；不是逐字字幕。混音对齐不保证模型精确读出每个动作，最终仍须试听。
- 使用标准库，逐场景在内存混音，单场景浮点缓冲上限 256 MiB；超出时拆分场景。适合本地短场景制作，长篇按场景拼接。
