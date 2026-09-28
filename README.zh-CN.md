# Gemini TTS Director

[English](README.md) · 简体中文

让你的 AI Agent 当声音导演：读懂文本，安排角色、语气与插话，先交付能看、能试听的导演稿，再按你的授权生成音频。

支持单人朗读、分角色对话、原生双人回应和多人群声。导演由你正在使用的 Agent 担任；执行脚本只负责 TTS、保存候选和本地混音，不另调用规划模型。

你可以直接指定音色 ID，也可以让导演推荐；可用性取决于所选接口。这个 skill 聚焦导演稿、表演、生成、返工和本地拼接，不负责创建或管理音色，也不提供流式播放、Interactions、远程 Batch 或服务档位管理。

## 安装

使用 [vercel-labs/skills](https://github.com/vercel-labs/skills)：

```sh
npx skills add LcpMarvel/gemini-tts-director
```

只安装到当前项目的 Codex 或 Claude Code：

```sh
npx skills add LcpMarvel/gemini-tts-director --skill gemini-tts-director --agent codex claude-code
```

添加 `--global` 可安装到用户目录。安装 CLI 需要 Node.js/npm；生成脚本需要 macOS/Linux 和 Python 3.10+，只使用 Python 标准库。

## 开始使用

安装后，把文本交给 Agent，例如：

> 用 gemini-tts-director 处理这篇文章。先判断文本类型，给我简洁的 Markdown 和 HTML 导演稿，角色表放在题名前面。先不要 TTS。

> 让选好的角色各读一句自己的代表台词，告诉我共几条。确认后再生成。

> 这段两个人有插话，用原生双人回应；后面的三个人起哄用分轨群声。先给制作 JSON。

> 后面两个人太响，稍微压低音量、错开一点，复用录音重新混音。

导演会按文本和人物关系选择表演方式，同一作品可以混用。官方现成音色样本可直接试听；换候选音色不触发生成。提供的 70 条样本地址是已验证快照，不是音色总量上限。

## 能做什么

| 能力 | 实现方式 |
| --- | --- |
| 导演稿与选声 | Agent 制作 Markdown/HTML、角色表及官方样本试听 |
| 音色查询 | 分页查询预置音色、按特征筛选并匹配官方试听地址，不调用 TTS |
| 语气与动作 | 逐段 style 与定位的人声、呼吸、停顿标签 |
| 原生双人 | 同一 clip 内的 speakers/turns，支持听者 `\|回应\|` |
| 群声 | 多条录音按 scenes 错位叠加、调音量、避免削波 |
| 局部返工 | 保留候选、显式选片；只改时间和音量可免费本地重混 |
| 多接入商 | Google GenerateContent、AIHubMix、OpenRouter 及兼容 HTTPS 路由 |

原生双人当前使用 Gemini metadata 协议与预置音色；其他路由不会自动降级或换供应商。联合录音是一整条 WAV，修改其中一句会重做整段，不提供双方独立声轨或轮内时间戳。

## 不生成音频的检查

从仓库目录运行；使用已安装 skill 时，把路径改成安装位置：

```sh
python3 scripts/tts.py --help
```

在自己的作品目录创建 `route.json`，例如：

```json
{"provider":"google","model":"gemini-3.8-flash-tts"}
```

先检查实际请求，`--dry-run` 无需 Key，不联网、不计费：

```sh
python3 scripts/tts.py render --config /path/to/route.json --plan examples/native-dialogue/plan.json --out /path/to/audio --dry-run
```

真实生成需要相应接入商的 Key 环境变量及用户授权。Key 不写入制作 JSON 或 HTML；TTS 费用由接入商收取。具体配置、生成和返工命令见 [使用与接入](references/usage.md)。

## 查询音色与试听

设置 `GEMINI_API_KEY` 并配置 Google 路由后，可以查询预置音色，不生成音频：

```sh
python3 scripts/tts.py voices --config /path/to/route.json --output voices.json
python3 scripts/tts.py voices --config /path/to/route.json --language-code en-GB --gender female --search warm --output filtered-voices.json
```

脚本会读取所有分页，保留真实音色 ID，并关联已确认的官方 `sample_url`。暂无样本的音色仍可选择，其 `sample_url` 为 `null`。附带的 70 条试听地址是已验证快照，不是音色数量上限。完整筛选参数和样本扩充方法见 [音色查询与预览](references/preview.md#voice-catalog-and-official-samples)。

## 文档与示例

- [原生双人示例](examples/native-dialogue/director.md)：原创英文短对话，标清双方的主句与听者回应；含 HTML 和制作 JSON。
- [英文文学示例](examples/the-magic-finger/director.md)：《The Magic Finger》开篇至四声枪响，包含课堂回忆与打猎段落。
- [中文文学示例](examples/kong-yiji/director.md)：《孔乙己》的错位群声，保留中文原句，导演说明为英文。
- [Skill 入口](SKILL.md)：给 Agent 的执行指引。
- [导演方法](references/directing.md)：文本判断、表演选择、原文与改编边界。
- [导演稿与试听](references/preview.md)：可读页面、音色样本和可选试音。
- [双人与群声编排](references/arrangement.md)：JSON 契约、混音和返工范围。
- [双人示例](examples/native-dialogue/plan.json)、[群声示例](examples/kong-yiji/plan.json)：可直接 dry-run 的制作稿。

下载仓库后可直接打开示例目录里的 `director.html`。提供的《The Magic Finger》EPUB 是连续故事，没有编号章节；英文示例取开篇的 50 个非空段落，共 13 段制作计划，读到“BANG! BANG! BANG! BANG! went the guns.”为止。公开页面播放官方已有音色样本；本地已生成试听录音，录音不随仓库发布。英文示例仍缺两段被供应商过滤的录音，不能当作完整成品。

`scripts/` 是执行器，`tests/` 是离线集成测试，`assets/` 保存可复用示例与官方样本地址。`examples/` 是整理后的公开导演稿；完整工作目录、录音、密钥和本地安装副本不随仓库发布。

## 验证

```sh
python3 -m unittest discover -s tests -v
```

测试使用模拟响应和本机 HTTP 服务，不调用付费 TTS。覆盖请求格式、候选复用、改稿后选片、原生双人、混音、导出和错误恢复。

Google 路由已实际生成过五个角色短句与四条群声分轨。最初的双人示例插话不明显；改过的原生争论片段和老师使用独立音色的课堂片段，均获用户试听认可。这些是具体片段的结果，不代表所有文本或路由的效果。模型名称、音色和供应商能力会变化，使用前按当前接入方式核对。
