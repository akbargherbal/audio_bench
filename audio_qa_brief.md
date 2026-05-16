# Client Brief: Audio QA Python Script
**Project: Classical Arabic Poem → Suno AI → Audacity Pipeline**
**Purpose: Pre-assembly quality assurance of generated audio chunks**

---

## Background

The user splits long classical Arabic poems (Fusha) into chunks of ~12 verses each, generates each chunk separately in Suno AI using a consistent prompt and reference audio, then assembles them in Audacity using crossfade. The problem: some chunks drift from the reference in ways that are only discovered late — during or after Audacity assembly. The goal is to catch these deviations **before assembly**.

Additionally, when iterating on Suno prompts, the user needs a way to describe *what a prompt produced* in measurable terms — so that an LLM can help diagnose and improve the prompt.

---

## The Reference Track

- The user's **Happy Accident** track(s) — Suno-generated, same voice, same genre
- NOT a commercial track (different genre norms would make comparison misleading)
- The reference defines what "correct" looks and sounds like for this specific project
- Genre: deep male Basso-Baritone, classical Arabic Fusha vocal, minimalist rock accompaniment

---

## Two Use Cases

### Use Case 1 — Pre-Assembly Chunk QA
> *"Does this chunk belong to the same family as my reference?"*

Run before Audacity assembly. Flag deviant chunks for re-generation in Suno.

### Use Case 2 — Prompt Debugging
> *"This Suno prompt produced a track with these characteristics — help me fix the prompt."*

Run after a Suno generation that feels wrong. Feed the report to an LLM with a description of what was heard.

---

## Functional Requirements

### FR-1: Reference Profiling
- Accept a reference audio file (WAV or MP3)
- Extract and store a full feature profile of the reference
- This profile becomes the baseline all chunks are compared against

### FR-2: Chunk Analysis
- Accept one or multiple audio chunk files
- Extract the same feature set as the reference
- Output per-chunk values alongside reference values and the delta

### FR-3: Feature Extraction (what the script measures)

| Feature | Why it matters | Library |
|---|---|---|
| **LUFS (integrated loudness)** | Perceived loudness consistency | `pyloudnorm` |
| **RMS energy** | Overall loudness level | `librosa` |
| **Dynamic range** (crest factor) | Is it squashed / over-compressed? | `librosa` |
| **Spectral centroid** | Brightness — where the tonal weight sits | `librosa` |
| **Spectral rolloff** | How much high-frequency energy | `librosa` |
| **Low-mid energy (200–500 Hz)** | Muddiness indicator | `librosa` |
| **Presence band (1k–4kHz)** | Vocal clarity / cut-through | `librosa` |
| **High shelf (8kHz+)** | Air / harshness indicator | `librosa` |
| **Stereo width** | Spatial feel — wide vs narrow | `librosa` (L/R diff) |
| **Tempo estimate** | Pacing consistency | `librosa` |
| **MFCCs (13 coefficients)** | Timbre fingerprint — overall tonal character | `librosa` |
| **Zero crossing rate** | Noisiness / distortion indicator | `librosa` |

### FR-4: Deviation Scoring
- For each feature, compute delta between chunk and reference
- Flag features that exceed a configurable deviation threshold
- Assign an overall **Consistency Score** per chunk (0–100, where 100 = identical to reference)

### FR-5: Structured Report Output
- Output a human-readable + LLM-readable report per chunk
- Format: Markdown or JSON (configurable)
- Report must include:
  - Per-feature values (chunk vs reference vs delta)
  - Flagged deviations with plain-English labels (e.g. "Low-mid buildup — possible muddiness")
  - Overall Consistency Score
  - A short **diagnostic summary** paragraph ready to paste into an LLM prompt

### FR-6: LLM-Ready Summary Block
Each report ends with a block like:

```
DIAGNOSTIC SUMMARY — CHUNK 3
Consistency Score: 61/100
Flagged issues:
- Low-mid energy (+8 dB vs reference at 200–500 Hz) → candidate: muddiness
- LUFS -3.2 dB below reference → chunk feels quieter than surrounding parts
- Stereo width 18% narrower than reference → feels more mono/closed
- Spectral centroid lower → overall mix is darker than reference

Subjective note from user: [paste what you hear here]
```

This block is designed to be pasted directly into an LLM conversation.

### FR-7: Batch Mode
- Accept a folder of chunks + one reference file
- Output one report per chunk + a summary table ranking all chunks by Consistency Score
- Clearly identify the worst offenders

### FR-8: Prompt Debugging Mode (Use Case 2)
- Same extraction as above, but framing is different
- Output includes a section: **"Suno Prompt Implications"**
- Maps measured problems to likely prompt causes, e.g.:
  - Low-mid buildup → "Your prompt may lack explicit vocal-forward / mix clarity instruction"
  - Low LUFS → "Suno generated a quieter, more restrained performance — check energy/intensity descriptors"

---

### FR-9: Reference Ceiling Analysis (optional mode)
- Accept a commercial, professionally mixed track as a **ceiling reference** (e.g. Elissa — Maktooba Leek)
- Extract the same feature set from the commercial track
- Do NOT use commercial values as targets — use them as **extreme deviation detectors**
- Flag only where the user's chunk is in gross violation of commercial norms, e.g.:
  - Vocal buried significantly below mix average (commercial tracks don't do this)
  - Low-mid buildup far beyond what any well-mixed track carries
  - Dynamic range crushed well below commercial floor
  - Stereo width collapsed to near-mono
- Report framing must be explicit: *"This is a red flag check, not a genre match. These are production hygiene failures, not style differences."*
- Genre-specific features (high-frequency air, bass treatment, stereo width targets) are explicitly excluded from ceiling comparison with a note explaining why

---

## What the Script Does NOT Do
- Does not fix or alter any audio
- Does not make final decisions — it flags and explains
- Does not use commercial tracks as style or genre targets
- Does not replace the user's ear — it directs it

---

## Output Modes
| Mode | Input | Output |
|---|---|---|
| Single chunk QA | 1 reference + 1 chunk | 1 report |
| Batch QA | 1 reference + N chunks | N reports + summary table |
| Prompt debug | 1 reference + 1 new generation | Report + Suno prompt implications |
| Ceiling analysis | 1 commercial track + 1 chunk | Red flag report (production hygiene only) |

---

## Technical Constraints
- Python 3.x
- Primary library: `librosa`
- Loudness: `pyloudnorm`
- Input formats: WAV preferred, MP3 acceptable
- Output: Markdown report (default) or JSON (flag)
- No GUI required — CLI script

---

## Definition of Done
The script is complete when:
1. A user can run it on a folder of Suno chunks + a reference track
2. Get a ranked list of which chunks are most deviant
3. Get a paste-ready diagnostic summary per chunk
4. Take that summary to an LLM, add what they heard, and get actionable prompt improvement advice
