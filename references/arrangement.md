# Dialogue, scene arrangement, and mixing

First deliver reviewable JSON. Generation and postproduction both follow it. `clips` define solo or native two-speaker performances; `scenes` play in array order and their `layers` may overlap at offsets. Without `scenes`, clips concatenate in plan order.

## Native two-speaker dialogue and listener responses

Choose joint performance only after [reading the text and relationships](directing.md#read-the-text-before-choosing-a-mode). The [complete dialogue plan](../examples/native-dialogue/plan.json) is an original example recorded locally through the Google route; audio is not bundled:

```json
{
  "id": "overlap-conversation",
  "speakers": {
    "Alex": "Charon",
    "Sam": "Kore"
  },
  "turns": [
    {
      "speaker": "Alex",
      "text": "I was trying to tell you |I know,| why I left early |I was there!| but you wouldn't let me finish.",
      "style": "Frustrated, speaking insistently at a brisk pace, continuing through the listener’s interruptions without yielding the floor."
    },
    {
      "speaker": "Sam",
      "text": "Because you keep saying |That's not| nobody told you |what I said!| when I called you twice.",
      "style": "Defensive and quick, talking over the listener’s protest and continuing the sentence without waiting."
    }
  ]
}
```

- A native dialogue clip has exactly two `speakers`; keys must match `turns[].speaker`. Each turn has `text` and optional `style`, `events`, and `source_text`. The clip may keep the scene's `source_text`. Do not also set solo `voice/text/style/events`.
- Text inside `|...|` is spoken by the *other* speaker: Sam interrupts in Alex's turn above, and Alex interrupts in Sam's. Multiple responses or none are valid. Bars must be paired and contain text. Resolve literal bars in the source before submission.
- A short response at a comma may sound like orderly turn-taking. For intended interruption, place responses inside an unfinished thought, optionally across multiple paired segments, and direct the leading speaker to continue without yielding. Preserve the source words; do not invent an argument or add interjections to faithful readings. Audition the result: bars express intent and do not guarantee simultaneous speech. Use explicit local layering when independent timing control is needed, and label that mode accurately.
- `events.at` is a Unicode character offset in that turn's original `text`, including bars and response text. Keep the action's speaker clear. A solo `<sigh>` does not mean a listener interjects.
- Requests use Gemini `schema=metadata`, one part per turn, `speech_metadata.speaker/style`, and `multiSpeakerVoiceConfig.speakerVoiceConfigs[].voiceConfig.prebuiltVoiceConfig.voiceName`. This follows [Google's dialogue and backchannel guide](https://ai.google.dev/gemini-api/docs/generate-content/speech-generation#backchannels-and-overlapping-speech). Verify other models and routes. There is no 30-voice preset allowlist. Do not put a custom `voice_...` ID or temporary key into a preset field.
- One native clip makes one request and one joint WAV; it uses normal render/inspect/select/export. It can join scenes, but supplies neither separate speaker tracks nor turn timestamps. Changing any turn, response, or voice requires one new take for the whole clip. Do not regenerate unrelated clips.

```sh
python3 "$TTS" render --config route.json --plan dialogue-plan.json --out dialogue-audio --dry-run
# Run within the user's generation authorization:
python3 "$TTS" render --config route.json --plan dialogue-plan.json --out dialogue-audio
python3 "$TTS" export --out dialogue-audio --output dialogue.wav
```

Show each turn's speaker, words, and short style in the reading copy. Label a listener's response at its position. One joint clip gets one player; before generation, label it “Pending.” Do not present sliced portions as independent recordings.

In the 2026-09-28 Google Gemini 3.8 Flash TTS trial, the user heard no noticeable interruption in an earlier 11.96-second gentle dialogue. The [revised original argument](../examples/native-dialogue/plan.json) used two listener segments inside each leading turn and directions to keep speaking. It returned a 7.8-second joint WAV, with no local overlap mixing, and the user accepted it. This is one listening result, not a guarantee for other scripts or routes.

## Layered crowd example

The [crowd plan](../examples/kong-yiji/plan.json) contains narration and three different voices saying the same source line: four TTS requests. State the count and potential cost if authorization does not already cover it. The repeated performance does not rewrite the source.

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

Let one voice lead and stagger quieter responses. Give performers distinct pace, stress, and attitude as needed; the user and director choose voices. An earlier Chinese-direction version of this plan generated four Google Gemini 3.8 Flash TTS tracks on 2026-09-28, then mixed locally into about 6.22 seconds; the user accepted that audition. The English styles in the current asset have not been regenerated, so its request bytes and audio do not match that trial. It is an example, not a preset. Change voice count, voices, offsets, and gains to suit the text.

`start_ms` is a nonnegative integer file offset relative to the scene, default 0. It includes any initial silence or breath from TTS and is not word alignment. `gain_db` defaults to 0 and ranges from -60 to +12 dB. The latest-ending layer sets the scene length; the next scene follows immediately. A clip may be reused, but every clip must appear in a scene to avoid wasted generation.

## Generate, then remix locally

```sh
python3 "$TTS" render --config route.json --plan crowd-plan.json --out crowd-audio --dry-run
# Run only within generation authorization:
python3 "$TTS" render --config route.json --plan crowd-plan.json --out crowd-audio
python3 "$TTS" export --out crowd-audio --output crowd.wav
```

`--dry-run` shows TTS requests and arrangement without sending them. `render` creates separate original WAV tracks and records requests, usage, and takes. `export` reads selected takes and mixes/joins locally; it sends no TTS request. For timing or gain only, edit `scenes` and run:

```sh
python3 "$TTS" export --out crowd-audio --plan crowd-plan.json --output crowd-remix.wav
```

This remix needs no key and incurs no TTS charge. The `--plan` clips must match the registered plan exactly. Changed text, voice, style, or events require rendering only affected clips, selecting new takes, and exporting. Preserve older recordings and exports.

Translate feedback into the smallest change: “the back voices are too loud” changes `gain_db`; “too synchronized” changes `start_ms`; “not sarcastic enough” changes one clip's `style`; “wrong voice” changes its `voice`. The first two need only a remix. Save new mixes with distinct names and update the reading copy while preserving comparison with the old version.

At a crowd passage, mark the layered voices and show a small table of roles, voices, starts, and gains plus a JSON link. Before generation say “Pending.” Keep mixing parameters out of ordinary solo prose. Never prompt one voice to sound like several people or silently add words absent from the source. Local layering serves crowds, call-and-response, or chorus; native dialogue serves connected two-person listening and interruption when its route is compatible.

## Verifiable limits

- Inputs must be 16-bit PCM WAV with matching sample rate and channel count. No automatic time stretch, resampling, or spatial audio. Plain concatenation preserves bytes when there is no overlap.
- If a mixed peak exceeds range, the whole scene is scaled proportionally to avoid hard clipping while preserving relative levels. The actual factor is `scenes[].peak_scale` in `*.timeline.json`.
- The timeline records selected take, actual track start/end, gain, and scene boundaries; overlaps are possible. It is not a word subtitle track or a guarantee that every prompted action was performed. Audition the result.
- Standard-library mixing uses an in-memory floating-point buffer capped at 256 MiB per scene. Divide longer work into scenes.
