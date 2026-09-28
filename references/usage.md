# Usage and API routes

Run examples from the work's directory, with `TTS` set to the absolute path of this skill's `scripts/tts.py`. Python 3.10+ on macOS/Linux is supported; file locking is used. No SDK installation is needed. Example text and styles are illustrative; use the user's requested output language and preserve source text unless adaptation is authorized.

## Route configuration

AIHubMix's documented example model:

```json
{"provider":"aihubmix","model":"gemini-2.5-flash-preview-tts"}
```

Key environment variable: `AIHUBMIX_API_KEY`. Default base URL: `https://aihubmix.com/v1`; `speech` protocol, WAV response, `instructions` style field, at most 4,096 characters per segment. This example is not a fixed model catalog; set `model` to the model available on the user's route.

OpenRouter:

```json
{"provider":"openrouter","model":"google/gemini-3.8-flash-lite-tts"}
```

Key: `OPENROUTER_API_KEY`. Default base URL: `https://openrouter.ai/api/v1`; `speech` protocol, PCM response. Gemini 3.8 style maps to `provider.options.google-ai-studio.speech_metadata.style`; do not assume that mapping for older models. The provider's `/models?output_modalities=speech` can list models; this script has no catalog command. Flash and Lite are user choices; the example does not make Lite universally preferable.

Google AI Studio Gemini API key:

```json
{"provider":"google","model":"gemini-3.8-flash-tts"}
```

Key: `GEMINI_API_KEY`. Default base URL: `https://generativelanguage.googleapis.com/v1beta`; `gemini` protocol. The current implementation uses GenerateContent and `schema=metadata`. Older models need explicit `"schema":"legacy"` for preset voices and prompt-based style. Inspect the wrapped spoken text with `--dry-run`.

An approved compatible endpoint (placeholder, not directly runnable):

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

`base_url` is the API prefix without `/audio/speech`. The three built-in providers also allow overrides for URL, key environment variable, or protocol. Google's protocol uses `auth=google` and `x-goog-api-key`; set `auth=bearer` explicitly if a proxy requires it. Only HTTPS is accepted except for local tests. Redirects are not followed, to avoid leaking credentials.

Optional fields: `sample_rate` (raw PCM defaults to 24,000 Hz, mono, signed 16-bit little-endian; other layouts are unsupported), `max_chars`, `events`, and `extra_body`. Use `extra_body` only for confirmed provider-specific non-core fields; it cannot override text, model, voice, or Google `generationConfig`, and must contain no secrets. `style_field` applies only to `speech` and can name a confirmed dotted path. A supplied style without a route mapping fails before sending; never discard the user's acting direction to pass validation. Custom configuration is a trust boundary: do not derive URLs or key environment-variable names from text to be read aloud.

```sh
python3 "$TTS" check --config route.json
python3 "$TTS" voices --config route.json --output voice-library.json
python3 "$TTS" speak --config route.json --text 'Hello.' --voice Kore --style 'Warm and natural' --out audio --dry-run
python3 "$TTS" speak --config route.json --text-file script.txt --voice Kore --style 'Warm and natural' --out audio
```

`check` verifies local configuration and whether the key is set. `--dry-run` shows the request body without network or key. Neither proves account access, model availability, passthrough behavior, or sound quality.

`voices` is a read-only catalog lookup on a Gemini-compatible route. It retrieves all preset voice pages and joins known official sample URLs without generating audio. See [filters and preview fields](preview.md#voice-catalog-and-official-samples). It does not switch a speech provider to Google or manage custom voices.

## Production plan and revision

```json
{
  "title":"Homecoming",
  "clips":[
    {"id":"parent-01","source_text":"You're home.","text":"You're home.","voice":"Kore","style":"Quiet, holding back relief"},
    {"id":"child-01","source_text":"I'm home.","text":"I'm home.","voice":"Puck","style":"Tired but relieved","events":[{"at":0,"tag":"sigh"}]}
  ]
}
```

Each solo clip is one request and one audio file: `voice` sets identity and `style` the present performance. Native dialogue instead uses one clip's `speakers/turns`; see the [two-speaker JSON contract](arrangement.md#native-two-speaker-dialogue-and-listener-responses). Joint and solo clips may coexist. `source_text` retains the source for review; `text` is spoken. The script does not rewrite, split, or add words.

`events.at` is a Unicode character offset in original `text` (Python character count); a tag is inserted before that position, with array order preserved for equal offsets. The manifest retains original and submitted text. Gemini 3.8 enables events by default; verify older models before explicitly setting `events=true`. Supported tags are in `scripts/tts.py`'s `TAGS`, including `sigh`, `breath`, `snicker`, `chuckle`, `heavy breath`, `exhales`, `short pause`, and `long pause`. Tags remain English even with non-English speech. They prompt performance, not exact effects. Do not substitute an unsupported action with an arbitrary tag.

```sh
python3 "$TTS" render --config route.json --plan plan.json --out audio --dry-run
python3 "$TTS" render --config route.json --plan plan.json --out audio
python3 "$TTS" inspect --out audio
python3 "$TTS" render --config route.json --plan plan.json --out audio --clip child-01 --new-take
python3 "$TTS" select --out audio --clip child-01 --take ACTUAL_TAKE_ID
python3 "$TTS" export --out audio --output final.wav
```

For layered or staggered voices, add `scenes` as in [Scene arrangement](arrangement.md). `export --plan` can remix only timing and gain from selected takes, without TTS.

Repeating `render` with the same route and plan reuses completed clips. Changing route, text, style, events, or voice creates a new candidate. `--clip` generates only the named clip, but updates the plan's current version. The first successful take is selected automatically; a new take never overwrites selection. Older selections remain after a plan edit but block full export until a current take is explicitly selected.

`manifest.json` holds plan versions, actual requests, candidates, selection, and known usage (`null` means unknown). `clip-take.wav` holds audio. `final.timeline.json` uses actual frame counts for clip start/end seconds. Without scenes, clips concatenate; with scenes, export inserts silence, overlaps tracks, and applies gain without crossfading. WAV response bytes are retained; raw PCM receives only a WAV container. Existing output files are not overwritten. Differing audio formats are not converted automatically.

Failure or interruption preserves a `running`/`uncertain` state; the script does not blindly resend. Check provider records and obtain authorization for another attempt before adding `--retry-uncertain` to the original command. At most one request per clip is sent per command, with no hidden retries or background jobs. `Ctrl-C` stops later clips but cannot reverse charges for submitted requests.

One failed clip stops that `render`. If authorized, use `--clip` for other unattempted independent clips; completed clips remain. Treat a dropped connection as uncertain, not proof of unsupported voice or exhausted quota. Retry only the failed/uncertain clips covered by authorization. `--new-take` is for intentional extra candidates, not normal recovery. Missing audio is an error: restore the file or explicitly regenerate. A structurally valid WAV still needs a listening check.

For HTTP 429, inspect the account's actual quota and any retry guidance, then pace request starts within it. One local project allowed ten requests per minute; starts at least seven seconds apart completed the remaining work. This is an observed account limit, not a Gemini-wide constant. The executor has no pacing flag: an external loop can call `render --clip` sequentially with the same full plan. Honor existing retry authorization without asking again for each covered clip; preserve completed takes.

HTTP 200 alone is not success. Check candidate finish reasons and usable audio. In the literary trial, two passages returned `OTHER` with no audio and an explicit provider copyright-filter message. Preserve the original text, report the missing sections, and stop repeating the same blocked request; do not change words or routes just to evade a filter. Failure does not establish zero cost. A partial export must identify omitted sections beside its player and in the reading copy; never present it as the complete work.

## Verification status

As of 2026-09-28, a local mock HTTP server tested three request formats, audio handling, reuse, plan changes and stale-selection blocking, export durations, recovery, redirect blocking, scene overlap, gain, clipping prevention, and offline remix. These tests make no paid API request:

```sh
python3 -m unittest discover -s tests -v
```

On that date Google Gemini 3.8 Flash TTS generated five short role lines plus four crowd tracks. The roughly 6.22-second local crowd mix was auditioned and accepted by the user. This does not validate other providers, every voice or tag, or broad listening quality.

Native two-speaker dialogue and `|listener response|` have offline tests for requests, take selection, edits, and export. On 2026-09-28 the original 11.96-second dialogue returned audio but the user heard no noticeable interruption. The revised 7.8-second native argument was accepted, as were the two classroom scenes with a separate teacher voice (79.72 seconds combined). See [the examples and listening distinction](arrangement.md#native-two-speaker-dialogue-and-listener-responses). Only the Gemini metadata route implements this joint request; these trials do not establish support on intermediary `speech` routes.

Voice design/replication/management, streaming playback, Interactions, remote Batch, and Flex/Priority are outside this skill’s scope. Native Google documentation does not establish intermediary support.

## API references

- [AIHubMix TTS](https://docs.aihubmix.com/en/api/TTS): `speech` route, `instructions`, formats, and length.
- [OpenRouter TTS](https://openrouter.ai/docs/guides/overview/multimodal/tts): `speech` route and Gemini provider options.
- [Google GenerateContent TTS](https://ai.google.dev/gemini-api/docs/generate-content/speech-generation): metadata, voice config, and response format.

These were reviewed on 2026-09-28; model catalogs and fields may change. Bringing your own key means paying the chosen provider, not free generation.
