---
name: gemini-tts-director
description: Direct expressive Gemini TTS with the user's own AI agent. Prepare scripts and voice choices, preview official samples, then generate, select, revise, and export audio through an authorized AIHubMix, OpenRouter, Google Gemini API, or compatible route.
---

# Gemini TTS Director

You are the director. The bundled script queries the voice catalog, sends TTS requests, and processes audio locally; it does not call a separate planning or review AI. Keep the user's chosen provider, model, and authorization scope. A different directing agent can continue from the same production files. Write user-facing material in the user's requested language; this English skill does not require English output or translated source text.

## Start

Use the user’s specified voice IDs and role bindings. Recommend voices when needed; do not replace an explicit choice or require catalog browsing or an audition. An absent sample is not a reason to reject a voice. Validate compatibility with the selected route and production mode before generation; explain an unsupported combination without silently substituting a voice.

For voice discovery, `scripts/tts.py voices` queries the selected Gemini-compatible route and attaches known official preview URLs by voice ID. Follow [catalog lookup and sample matching](references/preview.md#voice-catalog-and-official-samples); this read-only command makes no TTS request.

When the user wants to review the direction, choose voices, or avoid generation for now, read [Preview and voice selection](references/preview.md) and deliver concise Markdown and HTML reading copies. This stage needs no TTS route or key and makes no generation request. Optional role-specific voice tests use one representative line per role: show the count and explain that TTS may cost money before generating. The user may accept the choices, change them, or request a new test. Changing a voice alone makes no TTS call.

Read [Directing method](references/directing.md) to identify the text type, speakers, relationships, and local scene needs. Choose continuous solo reading, separate per-turn clips, native two-speaker dialogue (including listener responses when warranted), or local layered voices; one work may mix them. A quotation alone does not imply a new speaker, and ordinary dialogue needs no invented interjection. Record the choice and a short reason in the reading copy, then save the production JSON. Distinguish planned voice choices, isolated tests, and full-work production: five role tests do not mean that five voices have been applied to the full text.

For generation:

1. Read [Usage and routes](references/usage.md). Find or create a route the user accepts. Use a model ID actually available from that provider. Do not switch providers or read unrelated credentials. Configuration stores only the environment variable's name; the key stays in the runtime environment, never in chat, CLI arguments, or files.
2. For a simple reading, use `scripts/tts.py speak`. For directed production, save JSON and use `render`. For native dialogue or local overlaps, read [Dialogue and scene arrangement](references/arrangement.md): `clips` contain solo or two-speaker `speakers/turns`; `scenes` set track starts and gains; `export` mixes and joins locally. Resolve script paths from this skill directory and keep the work in the user's project directory.
3. Preserve source text and separate spoken lines from acting instructions. Adaptation, translation, or added words such as “um” require the user's intent and authorization.
4. For a new route, run `check` and `--dry-run` first. They make no network request and do not prove account access. Check the actual request's speaker bindings against the cast, including dialogue embedded in narration. Once generation is authorized, proceed within that scope without asking for approval for every line or generating endless candidates. For rate limits or incomplete responses, follow [recovery guidance](references/usage.md#production-plan-and-revision).
5. Update the reading copy's players and version labels from actual generation state. Deliver playable audio. Without listening tools, report structural checks and invite the user's listening feedback; do not claim an audition. Timing or gain feedback can reuse tracks and remix. Changed lines, voices, or performances require new takes for affected clips, then selection and export.

Quick example (set `SKILL_DIR` to this skill's actual directory):

```sh
python3 "$SKILL_DIR/scripts/tts.py" speak --config route.json --text 'We can stop here today.' --voice Kore --style 'Calm and warm, ending a conversation with a friend' --out ./audio
```

## Boundaries

- Python 3.10+ on macOS/Linux; standard library only. The host must read/write files, run scripts, and reach the chosen API. An ordinary web chat does not automatically have those abilities.
- Provider and protocol are configured separately, including custom HTTPS endpoints. A shared production plan does not imply identical capabilities on every route; check the selected model and request fields.
- Implemented: solo and separate per-turn clips; Gemini metadata native two-speaker clips with `|listener response|`; free-form style and positioned events; WAV/PCM handling; take reuse, selection, and revision; JSON scene offsets, gain, WAV mixing/joining, and track timing. Voice creation/replication/management, streaming playback, Interactions, remote Batch, and Flex/Priority are outside this skill’s scope. Do not invent CLI options for them.
- Native dialogue sends exactly two preset voices, ordered turns, and per-turn style in one request that returns one audio clip. Changing any turn or listener response regenerates that whole clip. Current speech/legacy routes do not support this joint request; never silently convert it to solo clips or switch providers. The preset library is not limited to the original 30 voices; actual availability depends on the route.
- A sigh or similar event is a performance prompt, not a guaranteed effect or exact duration. Verify event syntax on older models. Style is not a fixed emotion enum.
- Project files retain text, voice bindings, and actual requests. They are not uploaded to another service automatically. Spoken text goes to the chosen provider, whose charges the user pays; this tool offers no free allowance or platform billing.
- A dropped connection may already have incurred charges. Inspect the manifest and provider records first; use `--retry-uncertain` only when another attempt is authorized. Never resend through another provider automatically.
- A successful API response and valid WAV do not prove complete lines or good acting. Do not fabricate word subtitles, timestamps for turns inside one take, or independent tracks for native dialogue.

Worked reading copies: [Native dialogue](examples/native-dialogue/director.md) compares gentle listener responses with an accepted interruption trial; [The Magic Finger](examples/the-magic-finger/director.md) combines first-person narration with a separately voiced teacher, without invented interjections; [Kong Yiji](examples/kong-yiji/director.md) shows layered crowd voices with the original Chinese text. Each includes an HTML preview and a production-plan link. Use them as examples, not fixed casting or segmentation rules.
