# Directing method

Make the relationships and motives in the lines audible. Do not cover every sentence with emotion words or sighs. A short line may need no style prompt.

## Read the text before choosing a mode

This is the host agent's judgment, not a keyword classifier or another planning model. Identify genre, who speaks, where narration ends and dialogue begins, whether speakers take turns or respond at once, and whether the user wants faithful reading or adaptation. Choose directly when the evidence is sufficient; ask only when a crucial relationship is unclear.

| Text and relationship | Usual approach | Watch for |
| --- | --- | --- |
| Essays, explanation, news, monologue | Continuous solo reading | A quotation can remain part of the narration. |
| Fiction, stories, audio drama | Combine narrator and characters by scene | Stage directions are not spoken lines; one work need not use one mode throughout. |
| Interviews, podcasts, ordinary two-person talk | Native dialogue for connected turns | Add `|listener response|` only for real listening, agreement, interruption, or overlap. |
| Argument, questioning, interruptions | Native two-speaker responses when compatible | Their placement expresses acting intent, not millisecond timing. |
| Three or more voices, independent gain, or precise file offsets | Generate separate tracks and use `scenes` | Native dialogue is limited to two preset voices; use separate turns for custom voices or incompatible routes. |

State the choice in one or two sentences in the reading copy and mark local exceptions near their paragraphs. Do not invent “yes,” “uh-huh,” or other lines just to demonstrate a feature. Existing listener responses may move into the relevant `|...|` turn while `source_text` preserves the source; new responses are adaptations. `<sigh>` is an event by the current speaker, while `|...|` contains the other listener's spoken response. Name that listener in the reading copy.

## From dramatic intent to a request

Keep the source, actual spoken words, stable character voice, current-turn performance, and momentary events distinct. Start with a voice reading a real line, then change one principal factor in response to feedback. The script does not choose voices, judge acting, or invent audition results.

For “You finally came home,” relief might call for one soft sigh before the line and a style such as “relieved after a long wait; low volume, no blame.” It does not require adding “oh.” Disappointment calls for a different acting direction, not merely more volume.

- **Identity:** bind each role to a preset voice or stored voice ID available on the route. Do not randomly change it line by line. “Read the teacher sternly” changes delivery, not voice identity. When distinct character voices are intended, assign their quoted words to actual speaker bindings and keep reporting clauses with the narrator; verify these bindings in the compiled request.
- **Sustained delivery:** describe tiredness, whispering, restrained excitement, pace, or loudness in short free-form `style` text.
- **Momentary actions:** place sighs, breaths, laughter, and pauses in `events`, with offsets in the untagged spoken text. Events do not change `source_text`.
- **Reading copy:** show “tone” and “actions” separately. Identify who acts and where. Every displayed action must correspond to an event in the JSON and must not conflict with the style. An action is optional; a written mention of laughing need not become audible laughter. Do not pass prose annotations as spoken text or event tags.
- Use only tags supported by the script and selected model. An Expression option in a provider UI does not establish route support. After changing actions, keep the old recording labeled as an older version until regenerated.
- Literal angle brackets or `|` in source text may conflict with control syntax. Determine whether the user wants the characters spoken before submitting.
- Added spoken words are script edits requiring authorization. Keep role names, stage notes, and plot summaries out of spoken text.

## Route and model differences

Gemini 3.8 separates style and events. Native Google, OpenRouter, and AIHubMix map these into different request fields. AIHubMix's documented example uses 2.5; support for `instructions` alone does not establish support for 3.8 event tags. Do not change providers just to use tags. On older prompt-based models, a style prompt may be read aloud, so audition it.

Choose [native dialogue or scene arrangement](arrangement.md) according to the text: native dialogue makes one connected two-person clip; separate per-turn WAVs permit focused revisions; crowd voices are generated separately and layered locally. Keep a long continuous passage by the same speaker together when possible rather than splitting at every punctuation mark. If a provider length limit forces division, split at a meaningful boundary.

Use short, concrete Gemini 3.8 style prompts. Voice identity belongs to `voice`, so avoid repeating a character biography or saying “keep the same voice” every turn. User-facing direction may be richer, but do not copy the whole analysis into each TTS request.

In [The Magic Finger](../examples/the-magic-finger/plan.json), the girl is also the narrator: both use Leda, while Mrs Winter's direct speech uses Kore in two joint scenes. Only those two scenes needed rerecording when the single-voice version failed to distinguish the teacher; the user accepted the revision. These are example choices, not required voices. After splitting source prose into turns, check that their ordered text reconstructs the original passage, including reporting clauses.

## Revision and delivery

If the user says “the last line is too forceful,” change the affected clip's style while keeping its words and voice. Generate one candidate and let the user, or an authorized host with audio listening ability, choose it. The revision unit is the whole clip; native dialogue includes both speakers' turns and responses.

File checks detect format or truncation problems, not missing words, speaker swaps, or emotional quality. Use an existing authorized listening tool if available. Otherwise, ask the user to audition the specific clip. Never turn “API succeeded” into “sounds natural.” Exact pause seconds, deterministic waveforms, word timestamps, and perfect voice consistency are not guaranteed. The current script cannot create, clone, or delete voices; synthetic consent audio is never a substitute for a real person's consent.
