# AUDIO-QA — Phased Implementation Plan
**Project:** Classical Arabic Poem → Suno AI → Audacity Pipeline — Pre-Assembly QA Script
**Brief reference:** `audio_qa_brief.md`
**Plan version:** v1.0 — Session 2 — ✅ Signed Off
**Status:** Awaiting user sign-off before any coding begins

---

## 1. Executive Summary & Locked Decisions

### Current State vs. Goal

| | State |
|---|---|
| **Now** | No script exists. `audio_qa_brief.md` is complete and signed off. |
| **End of Plan** | A working CLI Python script that accepts a reference track + one or more Suno-generated chunks, extracts 12 audio features, scores consistency, and outputs paste-ready Markdown diagnostic reports. |

### Locked Decisions — Not Open for Debate

| Decision | Rationale |
|---|---|
| Reference track = user's Happy Accident MP3 | Only valid same-genre reference. Commercial tracks are genre-mismatched and explicitly excluded as targets. |
| MP3 input is acceptable | Suno compression artifacts are uniform across chunks from the same project — will not skew comparative deltas. |
| No vocal classification (Baritone/Tenor) | Unreliable without clean stem separation. Not the core problem. Out of scope for all phases. |
| Core libraries: `librosa` + `pyloudnorm` | Standard, well-supported, Colab-compatible. No alternatives to be introduced. |
| No GUI — CLI only | Consistent with user tooling philosophy. No UI scaffolding at any phase. |
| Output default: Markdown | JSON output is a flag, not the default. Both are explicit in FR-5. |
| LLM-ready diagnostic summary block (FR-6) | Non-negotiable output requirement. Every report must end with this block. |
| MFCC output | Full 13-row per-coefficient detail block in report + scalar distance in score. Both are always present. ~130 token overhead per chunk — acceptable. |
| Consistency Score formula | Weighted continuous scoring. Not binary flag-count. Weights and thresholds in `config.py`. Calibration pass after first real-data run. |
| Demucs / stem separation | Out of scope for all phases in this plan. Do not scaffold toward it. |
| Threshold calibration (FR-4) | Initial values are heuristic. A calibration pass happens after Phase 3 runs against real chunks — not before. |
| FR-9 Ceiling Analysis | Optional. Last phase. Do not implement or scaffold until all prior phases are complete and signed off. |

---

## 2. Pre-Coding Checklist & Baseline Assumptions

**This checklist runs at the start of Phase 1 before any code is written. Do not proceed to Phase 1 if any item fails.**

```bash
# 1. Confirm Python version
python --version   # Must be 3.9+

# 2. Install core dependencies
pip install librosa pyloudnorm soundfile numpy

# 3. Verify librosa loads an MP3 without error
python -c "import librosa; y, sr = librosa.load('YOUR_REFERENCE.mp3', mono=False); print(y.shape, sr)"

# 4. Verify pyloudnorm loads and meters without error
python -c "import pyloudnorm as pyln; import soundfile as sf; data, rate = sf.read('YOUR_REFERENCE.mp3'); meter = pyln.Meter(rate); print(meter.integrated_loudness(data))"

# 5. Confirm the reference file is stereo (shape[0] == 2 for librosa mono=False)
# If shape returns (N,) — file is mono. Stereo width metric will return 0. Log this as a known limitation, do not error out.
```

**Hard Gate:** If steps 3 or 4 raise an error, stop. Do not write any feature extraction code until the import + load chain is confirmed working on the actual reference file.

---

## 3. Phases

---

### Phase 0 — Problem Definition & Brief
**Status: ✅ COMPLETE**
Deliverable: `audio_qa_brief.md`

---

### Phase 1 — Core Contract Validation (Highest Risk)

**Goal:** Prove that all 12 features can be extracted from a real MP3 in a consistent, meaningful way — before any surrounding architecture is built.

**Why this is Phase 1:** If `librosa.beat.tempo` is unreliable on non-rhythmic Arabic poetry, or if pyloudnorm rejects the sample rate, or if MFCC comparison methodology is unsound — everything downstream is built on a broken foundation. This must be settled first, in isolation.

#### Task 1.1 — Stub Feature Extractor

**File:** `extractor.py` (new file, project root)
**What to build:** A single function `extract_features(filepath: str) -> dict` that loads one audio file and returns a flat dictionary of all 12 feature values.

Features to extract and their exact implementation notes:

| Feature | Implementation note |
|---|---|
| LUFS | `pyloudnorm.Meter(sr).integrated_loudness(data)` — requires float64, shape `(N,)` or `(N, 2)` |
| RMS energy | `librosa.feature.rms(y=y_mono).mean()` |
| Dynamic range (crest factor) | `20 * log10(peak / rms)` — compute from raw waveform |
| Spectral centroid | `librosa.feature.spectral_centroid(y=y_mono, sr=sr).mean()` |
| Spectral rolloff | `librosa.feature.spectral_rolloff(y=y_mono, sr=sr).mean()` |
| Low-mid energy (200–500 Hz) | Band-pass filter or FFT bin sum between 200–500 Hz |
| Presence band (1k–4kHz) | FFT bin sum between 1000–4000 Hz |
| High shelf (8kHz+) | FFT bin sum above 8000 Hz |
| Stereo width | `mean(abs(L - R))` — if mono, return 0.0 and log warning |
| Tempo | `librosa.beat.tempo(y=y_mono, sr=sr)[0]` — known to be unreliable on speech/poetry; log raw value, do not error if implausible |
| MFCCs (13 coefficients) | `librosa.feature.mfcc(y=y_mono, sr=sr, n_mfcc=13).mean(axis=1)` — returns array of 13 values. Store the full array. Scalar distance computed in Phase 2. |
| Zero crossing rate | `librosa.feature.zero_crossing_rate(y_mono).mean()` |

**Minimum change rule:** Build only `extract_features()`. Do not build comparison logic, scoring, or reporting in this task.

#### Task 1.2 — Manual Validation Print

**File:** `extractor.py` — add a `__main__` block
**What to build:** Run `extract_features()` on the reference file, pretty-print all 12 values to console.

**Success criteria:**
- Script runs without error on the reference MP3
- All 12 keys are present in the output dictionary
- LUFS value is a negative float (e.g. `-14.2`)
- MFCC is a list/array of exactly 13 values
- Stereo width is non-zero if the file is stereo
- Tempo prints a plausible BPM (even if wrong for poetry — it must not crash)

**Stop condition:** If pyloudnorm raises `ValueError: Audio must be at least 0.5 seconds` or a sample rate error — STOP. Do not work around it silently. Report the error and the exact file metadata (duration, sr, channels).

**Rollback:** Delete `extractor.py`. Nothing else exists yet.

---

### Phase 2 — Reference Profiling & Chunk Delta (FR-1, FR-2, FR-3)

**Depends on:** Phase 1 complete and validated.

#### Task 2.1 — Reference Profile Builder

**File:** `profiler.py` (new file)
**What to build:** Function `build_reference_profile(filepath: str) -> dict` — calls `extract_features()`, stores result in memory as the baseline. Optionally serialise to `reference_profile.json` for reuse across runs.

**Minimum change rule:** Do not modify `extractor.py`. Call it, do not refactor it.

#### Task 2.2 — Chunk Analyser

**File:** `profiler.py` — add function `analyze_chunk(chunk_path: str, reference_profile: dict) -> dict`

**What to build:**
- Call `extract_features()` on the chunk
- For each scalar feature: `delta = chunk_value - reference_value`
- For MFCCs: compute **two** representations:
  - `mfcc_scalar_distance = mean(abs(chunk_mfccs - reference_mfccs))` — used in scoring
  - `mfcc_detail = list of 13 per-coefficient deltas` — used in the detail report block for LLM consumption
  - Store both in the analysis dict under `mfcc_distance` and `mfcc_deltas` respectively
- Return a dict with keys: `chunk_values`, `reference_values`, `deltas`

**Minimum change rule:** Do not implement scoring or flagging in this task. Return raw deltas only.

**Success criteria:**
- Delta for a chunk identical to the reference = 0.0 for all scalar features
- MFCC delta for identical files = 0.0
- Negative delta on LUFS means chunk is quieter than reference
- Function handles a mono chunk vs stereo reference without crashing (stereo width delta = `0.0 - reference_width`, logged as "chunk is mono")

**Stop condition:** If MFCC distance is non-zero for a file compared against itself — STOP. There is a numerical stability or normalisation bug. Do not proceed to scoring.

---

### Phase 3 — Deviation Scoring & Report Generation (FR-4, FR-5, FR-6)

**Depends on:** Phase 2 complete and validated.

#### Task 3.1 — Consistency Score & Flagging

**File:** `scorer.py` (new file)
**What to build:** Function `score_chunk(analysis: dict, thresholds: dict, weights: dict) -> dict`

**Scoring formula — Weighted Continuous:**

Binary flag/no-flag is explicitly rejected. Each feature receives a continuous penalty that scales with how far its delta exceeds the threshold, multiplied by a perceptual weight:

```python
# Per feature:
raw_penalty = max(0.0, abs(delta) / threshold - 1.0)  # 0 if within threshold, grows linearly beyond
capped_penalty = min(raw_penalty, 2.0)                 # cap runaway outliers at 2× threshold
weighted_penalty = capped_penalty * weight

# Final score:
score = 100 - (sum(weighted_penalties) / sum(all_weights)) * 100
score = max(0, round(score, 1))
```

**Why continuous over binary:** A delta of 1.99 (just under threshold) and 2.01 (just over) are perceptually equivalent. A binary flag treats them as categorically different. The continuous formula gives partial credit and scales naturally with severity.

**Retain binary flag for reporting:** A feature is still marked as `flagged = True` if `abs(delta) > threshold` — used for the plain-English label list and the LLM summary block. The continuous penalty is used only for the score.

**Weights (configurable in `config.py`):**

| Feature | Weight | Rationale |
|---|---|---|
| LUFS | 1.5 | Loudness mismatch is immediately audible across chunks |
| MFCC distance | 1.5 | Core timbre fingerprint — voice identity |
| Presence band (1k–4kHz) | 1.2 | Vocal clarity — critical for poetry intelligibility |
| Spectral centroid | 1.0 | Brightness drift — noticeable |
| Low-mid energy | 1.0 | Muddiness — noticeable |
| Stereo width | 1.0 | Spatial feel |
| Dynamic range | 1.0 | Compression consistency |
| RMS energy | 0.8 | Correlated with LUFS — lower weight to avoid double-counting |
| Spectral rolloff | 0.8 | Less perceptually salient |
| High shelf | 0.7 | Harshness — relevant but secondary |
| Zero crossing rate | 0.5 | Noise indicator — lowest perceptual priority |
| Tempo | 0.5 | Arabic poetry meter is irregular — tempo estimate unreliable; low weight accordingly |

**Note:** Weights are heuristic v1 values. A calibration pass after first real-data run is mandatory before treating scores as authoritative. Weights live in `config.py` and are adjustable without touching scorer logic.

**Initial heuristic thresholds (configurable via `config.py`):**

| Feature | Threshold |
|---|---|
| LUFS | ±2.0 LU |
| RMS energy | ±0.05 |
| Dynamic range | ±3.0 dB |
| Spectral centroid | ±500 Hz |
| Spectral rolloff | ±1000 Hz |
| Low-mid energy | ±0.10 |
| Presence band | ±0.10 |
| High shelf | ±0.05 |
| Stereo width | ±0.15 |
| Tempo | ±10 BPM |
| MFCC distance | ±5.0 |
| Zero crossing rate | ±0.05 |

**File:** `config.py` (new file)
**What to build:** Two plain dictionaries — `THRESHOLDS` and `WEIGHTS`. No config file parser. No CLI overrides. Direct Python dict edits only.

`WEIGHTS` mirrors the weights table in Task 3.1. Same keys as `THRESHOLDS`. Both are adjusted by editing `config.py` directly — no other mechanism.

#### Task 3.2 — Markdown Report Generator

**File:** `reporter.py` (new file)
**What to build:** Function `generate_report(chunk_name: str, analysis: dict, score: dict) -> str`

Report must include, in order:
1. Header: chunk filename, Consistency Score
2. Feature table: `| Feature | Reference | Chunk | Delta | Flag |` — scalar values for all features including `MFCC distance`
3. MFCC detail block — always present, immediately after the feature table:
   ```
   MFCC Detail (13 coefficients):
   | Coeff | Reference | Chunk  | Delta  |
   |-------|-----------|--------|--------|
   | 01    | -412.3    | -389.1 | +23.2  |  ← energy
   | 02    |  87.4     |  91.2  |  +3.8  |  ← tonal character
   ...
   | 13    |   4.1     |   4.0  |  -0.1  |  ← fine texture
   ```
   Include coefficient role labels (energy / tonal character / mid-range timbre / fine texture) as a static comment column — these guide LLM interpretation.
4. Flagged deviations with plain-English labels (see label map below)
5. LLM-ready diagnostic summary block (FR-6) — **mandatory**, always present

**Plain-English deviation label map:**

| Feature flagged | Label |
|---|---|
| Low-mid energy high | "Low-mid buildup — possible muddiness (200–500 Hz)" |
| LUFS below reference | "Chunk is quieter than reference — energy/intensity mismatch" |
| LUFS above reference | "Chunk is louder than reference — may clip or dominate assembly" |
| Stereo width narrow | "Stereo image narrower than reference — sounds more closed/mono" |
| Spectral centroid low | "Mix darker than reference — tonal weight shifted down" |
| Spectral centroid high | "Mix brighter than reference — possible harshness" |
| Tempo deviation | "Tempo drift — pacing inconsistency" |
| MFCC distance high | "Timbre fingerprint mismatch — overall tonal character differs" |
| Dynamic range low | "Over-compressed — dynamic range squashed vs reference" |
| Presence band low | "Vocal presence reduced — less cut-through in 1k–4kHz range" |
| High shelf high | "Excessive high-frequency air or harshness above 8kHz" |
| Zero crossing rate high | "Elevated noise floor or distortion indicator" |

**Success criteria:**
- Report renders as valid Markdown
- Diagnostic summary block is always present, even if Consistency Score = 100
- Feature table has correct column alignment
- No raw Python dict or array notation appears in the report output

#### Task 3.3 — Single Chunk End-to-End Run

**File:** `main.py` (new file — thin CLI entry point)
**What to build:** Wire `profiler → scorer → reporter` for a single reference + single chunk.

```bash
python main.py --reference happy_accident.mp3 --chunk chunk_01.mp3
```

Outputs the Markdown report to stdout.

**Success criteria:**
- Command runs end-to-end without error
- Markdown report appears in terminal
- Paste the diagnostic summary block into a chat with an LLM and confirm it reads coherently

**Stop condition:** STOP if the Consistency Score for a chunk that sounds correct to the user's ear is below 50. The scoring formula or thresholds are wrong. Do not proceed to batch mode. Recalibrate thresholds first.

---

### Phase 4 — Batch Mode (FR-7)

**Depends on:** Phase 3 single-chunk run validated against at least 2 real chunks.

**File:** `main.py` — add `--batch` mode

```bash
python main.py --reference happy_accident.mp3 --batch ./chunks/
```

**What to build:**
- Iterate over all `.mp3` / `.wav` files in the folder
- Run `profiler → scorer → reporter` per chunk
- Write each report to `reports/chunk_N_report.md`
- Write a summary table to `reports/summary.md` — ranked by Consistency Score ascending (worst first)

**Summary table format:**
```
| Rank | Chunk | Consistency Score | Flagged Features |
|------|-------|-------------------|-----------------|
| 1 | chunk_03.mp3 | 54/100 | LUFS, Low-mid, Stereo width |
| 2 | chunk_07.mp3 | 67/100 | MFCC distance, Tempo |
```

**Minimum change rule:** Do not modify `extractor.py`, `profiler.py`, `scorer.py`, or `reporter.py`. Batch logic lives in `main.py` only.

**Success criteria:**
- Running on a folder of 5 chunks produces 5 individual reports + 1 summary
- Summary is sorted worst-first
- No chunk is silently skipped — if a file errors, log it in the summary as `ERROR: [reason]` and continue

**Stop condition:** STOP if more than one file silently produces no output. Silent failures must be surfaced.

---

### Phase 5 — Prompt Debug Mode (FR-8)

**Depends on:** Phase 4 complete.

**File:** `reporter.py` — add `generate_prompt_debug_report(chunk_name, analysis, score) -> str`

```bash
python main.py --reference happy_accident.mp3 --chunk new_gen.mp3 --mode prompt-debug
```

**What to build:**
- Same report as Phase 3, plus an additional section: **"Suno Prompt Implications"**
- Maps each flagged deviation to a likely Suno prompt cause

**Prompt implication map (v1 — to be refined with user):**

| Flagged | Prompt implication |
|---|---|
| Low-mid buildup | "Prompt may lack explicit vocal-forward or mix clarity instruction" |
| Low LUFS | "Suno generated a quieter, more restrained performance — check energy/intensity descriptors" |
| High LUFS | "Suno generated a louder, more intense performance — check for words like 'powerful', 'full'" |
| Narrow stereo | "Prompt may be producing a more intimate/close recording — check spatial descriptors" |
| Dark spectral centroid | "Mix is darker than reference — prompt may lack brightness or air descriptors" |
| Low presence band | "Vocal is less forward — consider adding 'vocal-forward', 'clear vocals', 'intimate'" |
| MFCC distance high | "Overall timbre has drifted — check whether reference audio was attached to this generation" |
| Tempo drift | "Pacing has changed — Suno may have interpreted rhythm cues differently" |

**Minimum change rule:** Add a new function to `reporter.py`. Do not touch `scorer.py`, `profiler.py`, or `extractor.py`.

**Success criteria:**
- Output includes "Suno Prompt Implications" section with at least one entry when any feature is flagged
- Section is absent (or replaced with "No significant prompt issues flagged") when Consistency Score = 100
- Report is paste-ready into an LLM chat

---

### Phase 6 — Ceiling Analysis Mode (FR-9) — Optional

**Depends on:** Phases 1–5 complete, signed off, and user explicitly requests this phase.

**File:** `main.py` — add `--mode ceiling` flag

```bash
python main.py --ceiling commercial_track.mp3 --chunk chunk_01.mp3
```

**What to build:**
- Extract features from the commercial track
- Compare chunk against commercial track on a **red flag only** basis
- Features explicitly excluded from ceiling comparison: high shelf, stereo width, tempo — these are genre-specific
- Report framing must include the explicit disclaimer: *"This is a production hygiene check, not a genre match. These are red flags, not style targets."*

**Minimum change rule:** Ceiling analysis uses `extract_features()` and a new `generate_ceiling_report()` function. It does not share code paths with the reference-based QA pipeline.

---

## 4. Strict Scope Boundaries

### In Scope (this plan)
- Feature extraction from MP3/WAV via `librosa` and `pyloudnorm`
- Consistency scoring against a user-provided reference
- Markdown report generation with LLM-ready diagnostic block
- Batch folder processing with ranked summary
- Prompt debug mode with Suno implication mapping
- Optional ceiling analysis (Phase 6)

### Out of Scope — Do Not Implement, Do Not Scaffold
- GUI of any kind
- Demucs stem separation or vocal isolation
- Vocal type classification (Baritone/Tenor)
- Commercial track style matching
- YAML/TOML config file parsing
- Automated Suno API integration
- Audio editing or modification of any kind
- Real-time monitoring or file watching
- Cloud storage or remote file handling

---

## 5. File Map

```
project_root/
├── extractor.py       # Phase 1 — feature extraction only
├── profiler.py        # Phase 2 — reference profile + chunk delta
├── scorer.py          # Phase 3 — consistency score + flagging
├── reporter.py        # Phase 3/5 — Markdown report + LLM block + prompt debug
├── config.py          # Phase 3 — thresholds dictionary
├── main.py            # Phase 3+ — CLI entry point
└── reports/           # Phase 4 — batch output directory (auto-created)
    ├── chunk_N_report.md
    └── summary.md
```

**Rule:** No file not on this map is to be created without user approval.

---

## 6. Global Stop Conditions

These apply across all phases. If any of these are met, stop immediately and report to the user:

- Any phase's pre-coding check fails
- A file that should compare identically to itself produces a non-zero delta
- Consistency Score for a subjectively "correct" chunk is below 50
- More than one file is silently skipped in batch mode
- Any existing function signature is changed without explicit instruction
- Any file outside the approved file map is created

---

## 7. Session Handover Protocol

*(Reproduced from Session 1 — standing protocol, always included)*

At the end of every session produce `Session_N_Handover.md` covering:
1. What we did — tasks completed, files changed, key decisions
2. Artefacts produced — table of new/modified files and their role
3. Current project state — active phase, last confirmed working state of each script
4. Next session work items — ordered list, first command to run
5. Known issues / watch points — anything fragile, deferred, or asymmetric

**Rules:** One page. Produce even if session ended early. The handover replaces memory. Incoming LLM must read latest handover + `audio_qa_brief.md` before doing anything else.

---

## Sign-Off

| | |
|---|---|
| **Plan version** | v1.0 |
| **User sign-off** | ✅ Signed off — Session 2 |
| **Coding begins** | Phase 1 — next session |
