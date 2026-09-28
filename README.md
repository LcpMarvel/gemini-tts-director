# Gemini TTS Director

English · [简体中文](README.zh-CN.md)

Let your AI agent direct the performance: understand the text, cast the voices, plan delivery and listener reactions, and present a readable script before generating audio.

The skill supports narration, separate character takes, native two-speaker dialogue, and layered crowd scenes. Your existing agent makes the creative decisions; a Python script handles TTS requests, takes, and local mixing. No second planning model is required.

Use your own voice IDs or ask the director to recommend voices; availability depends on your route. The skill focuses on scripts, performance, generation, revision, and local assembly. Voice creation and account management, streaming playback, Interactions, remote Batch, and service-tier management are outside its scope.

## Install

Using [vercel-labs/skills](https://github.com/vercel-labs/skills):

```sh
npx skills add LcpMarvel/gemini-tts-director
```

To target Codex and Claude Code in the current project:

```sh
npx skills add LcpMarvel/gemini-tts-director --skill gemini-tts-director --agent codex claude-code
```

Add `--global` for a user-level installation. The installer requires Node.js/npm. The execution script requires macOS/Linux and Python 3.10+, with no third-party Python dependencies.

## Try it

Give your agent a text and a request such as:

> Use gemini-tts-director for this story. First identify the text type and prepare a concise Markdown and HTML director's script. Put the cast table before the title reading. Do not generate audio yet.

> Pick one distinctive line for each character to audition. Show me the lines and total request count before generating anything.

> Use native dialogue for the two speakers interrupting each other, then separate tracks for the crowd. Show me the production JSON first.

> The background voices are too loud and too synchronized. Lower them and stagger their entrances using the existing recordings.

The director chooses a production method from the text and character relationships; one work can combine methods. Official prerecorded voice samples can be played without TTS. Changing a candidate voice does not generate audio. The included 70 sample URLs are a dated snapshot, not a limit on the voice library.

## Examples

| Example | What it demonstrates | Files |
| --- | --- | --- |
| *Let me finish* — original dialogue | Two speakers interrupt each other in a native joint performance accepted after listening. | [Director’s script](examples/native-dialogue/director.md) · [HTML preview](examples/native-dialogue/director.html) · [Production JSON](examples/native-dialogue/plan.json) |
| *The Magic Finger* — Roald Dahl | An English opening excerpt through the four gunshots: first-person narration, the classroom flashback, and the duck hunt. No invented listener reactions. | [Director's script](examples/the-magic-finger/director.md) · [HTML preview](examples/the-magic-finger/director.html) · [Production JSON](examples/the-magic-finger/plan.json) |
| *Kong Yiji* — Lu Xun | A Chinese crowd scene: one leading heckler and two quieter, staggered voices. English direction with the original Chinese lines preserved. | [Director's script](examples/kong-yiji/director.md) · [HTML preview](examples/kong-yiji/director.html) · [Production JSON](examples/kong-yiji/plan.json) |

Download or clone the repository and open any example HTML file in a browser. Players use Google's existing voice samples; generated recordings are not included. The supplied *The Magic Finger* EPUB has one continuous story rather than numbered chapters, so the example clearly identifies an opening excerpt ending at “BANG! BANG! BANG! BANG! went the guns.” rather than labeling it “Chapter 1.”

## Capabilities

| Capability | How it works |
| --- | --- |
| Readable scripts and casting | Agent-authored Markdown/HTML, a compact cast table, and official voice samples |
| Voice discovery | Paginated preset catalog queries, filters, and matching official preview URLs; no TTS |
| Delivery and vocal events | Per-turn `style` plus positioned breaths, vocalizations, and pauses |
| Native dialogue | Two speakers in one clip, with ordered turns and optional listener `\|reactions\|` |
| Crowds | Separate takes layered with scene offsets, relative gain, and peak protection |
| Revisions | Keep candidates and explicit selections; timing/gain-only changes remix locally |
| Providers | Google GenerateContent, AIHubMix, OpenRouter, and compatible HTTPS routes |

Native dialogue currently uses the Gemini metadata protocol and prebuilt voices. Unsupported routes do not silently switch providers or fall back. A joint take is one WAV: changing a line regenerates that whole clip, and it does not provide separate speaker stems or timestamps inside the take.

## Inspect requests without generating audio

From a repository checkout, run:

```sh
python3 scripts/tts.py --help
```

Create `route.json` in your own work directory, for example:

```json
{"provider":"google","model":"gemini-3.8-flash-tts"}
```

Inspect a plan with `--dry-run`. It needs no key, makes no network requests, and incurs no TTS cost:

```sh
python3 scripts/tts.py render --config /path/to/route.json --plan examples/the-magic-finger/plan.json --out /path/to/audio --dry-run
```

For an installed skill, replace the script and plan paths with their installed locations. Actual generation requires the provider's key environment variable and user authorization. Keys never belong in production JSON or HTML. Providers charge for TTS; see [Usage and routing](references/usage.md) for configuration, generation, and revision commands.

## Find voices and preview samples

With `GEMINI_API_KEY` set and a Google route configured, query the preset library without generating audio:

```sh
python3 scripts/tts.py voices --config /path/to/route.json --output voices.json
python3 scripts/tts.py voices --config /path/to/route.json --language-code en-GB --gender female --search warm --output filtered-voices.json
```

The command follows every page and preserves each exact voice ID. Known official samples appear as `sample_url`; voices without a known sample remain available with `sample_url: null`. The bundled mapping covers 70 verified sample URLs, not the whole library. See [voice discovery](references/preview.md#voice-catalog-and-official-samples) for all filters and how to extend sample coverage.

## Documentation

- [Skill entry point](SKILL.md): instructions for the directing agent.
- [Directing](references/directing.md): text analysis, production choices, and faithful reading versus adaptation.
- [Scripts and auditions](references/preview.md): readable previews, sample discovery, and optional line auditions.
- [Dialogue and scene arrangement](references/arrangement.md): JSON contracts, mixing, and revision scope.
- [Interruption example](examples/native-dialogue/plan.json): the revised native argument accepted after listening.

`scripts/` contains the executor, `tests/` the offline integration checks, `assets/` reusable plans and sample URLs, and `examples/` the curated public director's scripts. Full local work directories, recordings, credentials, and installed copies stay outside version control. Repository instructions are in English; user-facing scripts follow the requested language and preserve the source language unless translation is requested.

## Validation

```sh
python3 -m unittest discover -s tests -v
```

Tests use mock responses and a local HTTP server, not paid TTS. They cover request mapping, take reuse, stale selections, native dialogue, mixing, export, and error recovery.

The Google route has generated five character auditions and four crowd stems in a local trial. The original native dialogue returned audio but did not convey interruption to the user; the revised argument and separately voiced classroom scenes were accepted after listening. These are specific listening results, not guarantees for other texts or routes. Model names, voice availability, and provider capabilities can change—check the route you intend to use.
