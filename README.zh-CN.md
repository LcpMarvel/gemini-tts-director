# Gemini TTS Director

[English](README.md) · 简体中文

让你的 AI Agent 当声音导演：读懂文本，安排角色、语气与插话，先交付能看、能试听的导演稿，再按你的授权生成音频。

支持单人朗读、分角色对话、原生双人回应和多人群声。导演由你正在使用的 Agent 担任；执行脚本只负责 TTS、保存候选和本地混音，不另调用规划模型。

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
python3 scripts/tts.py render --config /path/to/route.json --plan assets/dialogue-plan.json --out /path/to/audio --dry-run
```

真实生成需要相应接入商的 Key 环境变量及用户授权。Key 不写入制作 JSON 或 HTML；TTS 费用由接入商收取。具体配置、生成和返工命令见 [使用与接入](references/usage.md)。

## 文档与示例

- [英文文学示例](examples/the-magic-finger/director.md)：《The Magic Finger》开篇至四声枪响，包含课堂回忆与打猎段落。
- [中文文学示例](examples/kong-yiji/director.md)：《孔乙己》的错位群声，保留中文原句，导演说明为英文。
- [Skill 入口](SKILL.md)：给 Agent 的执行指引。
- [导演方法](references/directing.md)：文本判断、表演选择、原文与改编边界。
- [导演稿与试听](references/preview.md)：可读页面、音色样本和可选试音。
- [双人与群声编排](references/arrangement.md)：JSON 契约、混音和返工范围。
- [双人示例](assets/dialogue-plan.json)、[群声示例](assets/crowd-plan.json)：可直接 dry-run 的制作稿。
- [产品需求](PRD.md)：已实现范围和后续目标。

下载仓库后可直接打开示例目录里的 `director.html`。提供的《The Magic Finger》EPUB 是连续故事，没有编号章节；英文示例取开篇的 50 个非空段落，共 13 段制作计划，读到“BANG! BANG! BANG! BANG! went the guns.”为止。播放器只播放官方已有音色样本，没有为该示例生成 TTS。

`scripts/` 是执行器，`tests/` 是离线集成测试，`assets/` 保存可复用示例与官方样本地址。`examples/` 是整理后的公开导演稿；完整工作目录、录音、密钥和本地安装副本不随仓库发布。

## 验证

```sh
python3 -m unittest discover -s tests -v
```

测试使用模拟响应和本机 HTTP 服务，不调用付费 TTS。覆盖请求格式、候选复用、改稿后选片、原生双人、混音、导出和错误恢复。

Google 路由已实际生成过五个角色短句与四条群声分轨；原生双人目前通过离线验证，尚未验证真实 API 与听感。模型名称、音色和供应商能力会变化，使用前按当前接入方式核对。
