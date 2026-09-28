# Reading copy, voice samples, and optional auditions

Help the user understand the direction and hear available samples before deciding on generation. If the user has already authorized generation, proceed within that scope without forcing a preview stage. Write the reading copy in the user's requested language; preserve original literature unless translation or adaptation is authorized.

## Reading copy

- Keep the source in the work directory. Create `director.md` and a directly openable `director.html`. List apparent typos or encoding problems separately and explain any provisional correction; do not silently rewrite.
- Open with one short paragraph on the performance. Put the role table before the titled reading passage, then one or two necessary directing sentences per paragraph. Keep technical configuration in the JSON rather than burdening the reader with process language.
- Design and display tone and Expression actions separately, following the [directing method](directing.md). In HTML, mark an action where it occurs, for example `〔inhale · breath〕`, and say the marker is not spoken. Do not hide every action in a paragraph preface. The role table may expand for performance details. If the script changes without a new recording, label the current audition as an older version.
- Show each role's tone, candidate voice, and audition. Include only a few candidates relevant to this work. Clearly identify solo versus multi-role plans; a candidate is not necessarily applied to the full work.
- Use native `<audio controls preload="none">` for available official samples and name the voice. Play one at a time, and stop players removed by filtering. Link the same samples in Markdown.
- Put the wider voice catalog in a separate `voices.html`, searchable and filterable by language and voice characteristics. Default to voices with samples and show about ten results at once. Label unavailable samples “No sample available”; never render them as playable.

## Keep text, choices, and recordings aligned

Production JSON controls execution; HTML/Markdown are reading views; the manifest records actual requests and takes. Edit JSON before updating the reading copy's tone, actions, or crowd arrangement. Every displayed action or scene marker must correspond to a real `events` or `scenes` entry, rather than decorative text.

Changing a voice in the browser chooses a candidate. When the user later asks to produce audio, read the selected role and exact voice ID, update the right JSON, then dry-run. Never infer an ID from its display name. A solo main reading, role auditions, and crowd tracks may have separate plans; label each use and do not silently apply a role audition's choice to the full work.

After generation or remix, update players, recorded voices, and version labels from completed selected takes and actual exports. A revised but unrecorded passage keeps its “Older audition” label. On partial success, deliver real completed items and mark the rest accurately; never link a nonexistent file. Before delivery, check explained source edits, event positions, scene references, and links. Format and duration checks do not establish artistic quality. Record user listening feedback as that user's judgment, not a general guarantee.

## Voice catalog and official samples

Do not turn one user's preference, a one-off API failure, or the example voices into a universal restriction. Users can browse and choose the wider library. Before generating, check whether the selected route supports the exact voice. An official sample's availability does not prove generation works on this route. Let the user choose another voice or route when needed.

Use the [Google AI Studio voice picker](https://aistudio.google.com/generate-speech) for discovery. Do not substitute old Google Cloud or Chirp samples for Gemini samples.

The [sample URL catalog](../assets/voice-samples.json) records 70 official static samples verified reachable on 2026-09-28: 30 original voices and 40 additional named voices. This is a snapshot, not a voice-count ceiling. It needs no key or TTS request. Preserve URL case:

- Original voice: `https://www.gstatic.com/aistudio/voices/samples/Charon.wav`
- Additional named voice: `https://www.gstatic.com/aistudio/voices/samples/daikon/en-us-bodi.wav`

Reuse the catalog first. To add a voice, observe its actual resource URL through AI Studio's **Play voice sample**, then verify that the discovered target returns audio. Do not click a preview control that generates content. Never assume every extended voice has a `daikon/{id}.wav` file; show “No sample available” when absent rather than generating one without authorization.

For a truly complete live catalog, an authorized Gemini key can call `GET https://generativelanguage.googleapis.com/v1beta/voices?type=prebuilt&page_size=1000`, following each next-page token with `page_token`. Preserve the real voice ID, source, and retrieval date. Catalog lookup authorization is distinct from generation authorization. Reuse an existing catalog when sufficient. The current script has no voice catalog command; do not invent one.

Send a key only in the server-side `x-goog-api-key` header, never HTML, URLs, CLI arguments, or catalog snapshots. If the user points to a key file, read only the needed key, without sourcing or printing the file. The voice catalog omitting a preset sample URL does not imply no static sample exists. A voice's language metadata does not prove the model can speak only those languages.

## Optional role-specific auditions

This is optional fine tuning, not a prerequisite to production. The user can accept the director's choices, listen only to official samples, or switch voices without extra TTS calls.

For each selected speaking role, choose one distinctive original line that conveys character or relationship and generate one short audition in that role's own candidate voice. Choose narration for a narrator; do not invent a line for a silent role. Do not have multiple roles read the same line by default; same-line comparisons are useful when the user explicitly compares candidates for one role.

Show the roles, voice IDs, exact source lines, acting direction, and total number of requests first, explaining provider/model charges. Generate directly when existing authorization covers those roles and counts; otherwise, present the specific proposal for the user's choice. Do not invent an unverified price or promise free use.

For example, a *Kong Yiji* audition can pair distinct roles with their own lines. The quotations below are **original source lines in Chinese**, not English UI copy or mandatory voice choices:

| Role | Original source line (Chinese) |
| --- | --- |
| Narrator | 我到现在终于没有见——大约孔乙己的确死了。 |
| Kong Yiji | 窃书不能算偷……窃书！……读书人的事，能算偷么？ |

Use the exact passage supplied by the user. The number of roles depends on the work; five is not a preset.

After authorization, verify the route and model using [Usage and routes](usage.md). Keep auditions in a separate plan/output directory, one clip per role, preserving the full-work plan. In the role table, distinguish user-line auditions from official voice samples. Report actual files and usage. Without listening ability, do not claim to have heard or judged them.

### Change a voice and optionally re-audition

- Offer a per-role voice selector leading to the separate searchable, playable catalog. Save the exact new voice ID for that role, leaving other roles intact. If it has not been applied to the full-work plan, identify it as a proposal only.
- **Choosing a voice does not call TTS.** The user can stop there or request only this role's new audition. A selection click cannot trigger a paid request.
- Retain old auditions with their true recorded voice labels. Mark a newly chosen, ungenerated voice “Not auditioned”; its official sample may still play.
- For a re-audition, keep the representative line and direction, change only `voice`, make one new take for that role, and keep the old candidate for comparison. Do not repeat approval within an existing authorization scope.
- Audition authorization does not authorize the whole work or unlimited candidates. Static pages store no key and do not secretly call a generation API. Browser-local selection should state its scope; the agent reads it and updates the plan only when the user requests production.

For native two-speaker passages, show speakers and listener responses turn by turn and explain that the passage is jointly generated. `|listener response|` belongs to the other speaker, not the primary speaker. Do not fabricate two separate players or per-turn timestamps for one joint WAV. Explain mode choice briefly at the opening and mark local exceptions beside their passages.
