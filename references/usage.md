# 使用与接入

所有示例从作品目录执行；将 `TTS` 设置为本 skill 的 `scripts/tts.py` 绝对路径。依赖 Python 3.10+，当前支持 macOS/Linux（使用文件锁）。不需要安装 SDK。

## 路由配置

AIHubMix 的文档示例模型：

```json
{"provider":"aihubmix","model":"gemini-2.5-flash-preview-tts"}
```

环境变量：`AIHUBMIX_API_KEY`。默认地址 `https://aihubmix.com/v1`，协议 `speech`，WAV，风格字段 `instructions`。每段最多 4096 字符。不要把该示例当成固定模型目录；用户可替换 `model`。

OpenRouter：

```json
{"provider":"openrouter","model":"google/gemini-3.8-flash-lite-tts"}
```

环境变量：`OPENROUTER_API_KEY`。默认地址 `https://openrouter.ai/api/v1`，协议 `speech`，PCM。Gemini 3.8 风格写到 `provider.options.google-ai-studio.speech_metadata.style`；旧模型不自动沿用此映射。模型可通过供应商 `/models?output_modalities=speech` 查询（当前脚本不提供目录查询命令）。用户可自行选 Flash/Lite；示例不暗示 Lite 总是最佳。

Google AI Studio 取得的 Gemini API Key：

```json
{"provider":"google","model":"gemini-3.8-flash-tts"}
```

环境变量：`GEMINI_API_KEY`。默认地址 `https://generativelanguage.googleapis.com/v1beta`，`gemini` 协议，当前实现 GenerateContent，`schema=metadata`。旧模型须显式设置 `"schema":"legacy"`，使用预置音色与提示词风格；dry-run 能看到提示词如何包裹台词。

用户认可的其他兼容地址（示意，不可直接执行）：

```json
{
  "provider":"custom",
  "protocol":"speech",
  "base_url":"https://YOUR-HOST/v1",
  "key_env":"MY_TTS_KEY",
  "auth":"bearer",
  "model":"YOUR-MODEL",
  "response_format":"wav",
  "style_field":"instructions"
}
```

`base_url` 是接口前缀，不含 `/audio/speech`。也可在三个内置配置中覆盖地址、凭据环境变量或协议。Google 协议使用 `auth=google` 发送 `x-goog-api-key`；代理若要求 Bearer 可显式改为 `bearer`。地址仅接受 HTTPS，本机测试例外；不跟随重定向以免凭据泄漏。

可选字段：`sample_rate`（裸 PCM 默认 24000 Hz、单声道、16 位小端；其他音频布局不支持）、`max_chars`、`events`、`extra_body`。`extra_body` 用于供应商已确认的非核心参数，不能覆盖台词、模型、声音或 Google generationConfig；不要放入秘密。`style_field` 仅适用于 speech 协议，可指定经确认的点分路径。没有映射且提供 style 会在请求前报错；不得为了通过校验删掉用户的表演意图。自定义配置是信任边界，不能从待朗读文本自动生成地址或环境变量名称。

```sh
python3 "$TTS" check --config route.json
python3 "$TTS" speak --config route.json --text '你好。' --voice Kore --style '温暖、自然' --out audio --dry-run
python3 "$TTS" speak --config route.json --text-file script.txt --voice Kore --style '温暖、自然' --out audio
```

`check` 只检查本地配置和密钥是否存在。`dry-run` 展示提交正文，无网络、无密钥。两者均不验证账号、模型可用性、透传效果或声音质量。

## 制作稿与返工

```json
{
  "title":"归家",
  "clips":[
    {"id":"father-01","source_text":"你回来了。","text":"你回来了。","voice":"Kore","style":"压住激动，轻声说"},
    {"id":"child-01","source_text":"我回来了。","text":"我回来了。","voice":"Puck","style":"疲惫而放松","events":[{"at":0,"tag":"sigh"}]}
  ]
}
```

每个 clip 是一条独立请求与独立音频；单人模式用 `voice` 固定角色身份、`style` 描述当前表演。原生双人则用同一 clip 的 `speakers/turns`，见 [双人 JSON 契约](arrangement.md#原生双人及听者回应)；联合片段和单人片段可混排。`source_text` 可保留原句供审阅，实际合成 `text`。脚本不会自动改写、拆句或补词。

事件 `at` 为原 `text` 的 Unicode 字符偏移（Python 字符数），在该位置前插入；同位置保持数组顺序。脚本保存原文和最终请求。Gemini 3.8 默认允许事件；其他型号须先验证后显式配置 `events=true`。支持的标签以 `scripts/tts.py` 的 `TAGS` 为准，包括 `sigh/breath/snicker/chuckle/heavy breath/exhales/short pause/long pause` 等官方推荐人声与停顿标签；中文台词也使用英文标签，不是精确音效承诺。无支持证据的标签不要随意替换为其他动作。

```sh
python3 "$TTS" render --config route.json --plan plan.json --out audio --dry-run
python3 "$TTS" render --config route.json --plan plan.json --out audio
python3 "$TTS" inspect --out audio
python3 "$TTS" render --config route.json --plan plan.json --out audio --clip child-01 --new-take
python3 "$TTS" select --out audio --clip child-01 --take ACTUAL_TAKE_ID
python3 "$TTS" export --out audio --output final.wav
```

需要群声或错位叠声时，增加 `scenes` 数组，详见 [场景编排与混音](arrangement.md)；`export --plan` 可仅重混时间和音量，复用已有选片，无 TTS 请求。

同配置同稿重复 render 复用完成项；更换配置、台词、风格、事件或音色创建新候选。`--clip` 只生成指定片段，但会更新整份制作稿的当前版本。首次生成自动选第一条；新候选不会覆盖既有选片。改稿后旧选片保留但禁止完整导出，必须显式 select 当前稿的新 take。

结果：`manifest.json` 保存各版本文稿、实际请求、候选、选片、已知用量（未知为 null）；`clip-take.wav` 保存音频。`final.timeline.json` 根据实际帧数提供片段起止秒数，未配置场景时直接拼接；场景模式按起声时间插入静音、重叠并调整音量，不做交叉淡化。WAV 响应保留原件字节；裸 PCM 只添加 WAV 容器。输出不覆盖已有文件。不同音频格式不自动转换。

失败或中断会保留 `running/uncertain` 状态；不会盲目再次发请求。确认供应商结果及再次生成授权后，在原命令增加 `--retry-uncertain`。每次命令最多每片一条请求，没有隐式重试和后台任务。`Ctrl-C` 停止后续片段，不能撤回已经提交的费用。

一条失败会中止当次 render。其余独立片段仍在授权范围内时，可用 `--clip` 继续尚未尝试的片段；已完成项保留。不把连接中断猜成音色不支持或额度不足。用户只授权重试失败片段时，只对这些 clip 使用 `--retry-uncertain`，不批量重做成功项。

`--new-take` 用于主动候选制作；不要在普通恢复命令中使用。音频缺失会报错，应先找回文件或显式重做。结构有效的 WAV 仍需试听核对台词。

## 已验证与未验证

2026-09-28：使用本机模拟 HTTP 服务验证三种请求格式、音频处理、候选复用、改稿与旧选片阻断、导出时长、错误恢复、重定向阻断，以及场景重叠、增益、防削波和离线重混。这些测试不调用真实付费 API。执行：

```sh
python3 -m unittest discover -s tests -v
```

同日已使用 Google Gemini 3.8 Flash TTS 完成五个角色短句，以及四条群声分轨和约 6.22 秒本地混音；用户接受了群声试听。本次真实验证不覆盖其他供应商、所有音色或所有标签的听感。

原生双人及 `|回应|` 已通过离线请求、选片、改稿、导出测试，尚未进行真实 API 生成和听感验证。只有 Gemini metadata 路由实现了联合请求映射，不能据此宣称中转商 speech 接口也支持。

流式、声音设计/复制/管理、Batch/Flex/Priority、Interactions 保留为 PRD 后续实现项，不能从 Google 原生文档推断中转商已支持。

## 接口依据

- [AIHubMix TTS](https://docs.aihubmix.com/en/api/TTS)：speech 路由、instructions、格式及长度约束。
- [OpenRouter TTS](https://openrouter.ai/docs/guides/overview/multimodal/tts)：speech 路由和 Gemini provider options 映射。
- [Google GenerateContent TTS](https://ai.google.dev/gemini-api/docs/generate-content/speech-generation)：metadata、voiceConfig 和响应格式。

模型目录与字段会变化；以上为 2026-09-28 查阅结果。自带 Key 意味着用户直接承担供应商费用，并非不计费。
