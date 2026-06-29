# AUDIO-QA

Pre-assembly quality assurance for Suno AI-generated audio chunks.

Classical Arabic Poem → Suno AI → Audacity pipeline. Catches deviant chunks _before_ Audacity assembly and produces paste-ready diagnostic reports for LLM-assisted prompt debugging and mix-character analysis.

---

## Installation

```bash
# Core dependencies (required for all modes)
pip install librosa pyloudnorm soundfile numpy scipy

# Stem separation (required for --stems only)
pip install "audio-separator[cpu]" praat-parselmouth
```

Python 3.9+ required. No GUI. CLI only.

`audio-separator` downloads the BS-Roformer model on first `--stems` run (~500 MB). This is a one-time download cached locally by the library.

---

## Quick Start

```bash
# Single chunk QA — report to stdout
python main.py --reference data/audio/REF_01.mp3 --chunk data/audio/CHUNK_B.mp3

# Batch folder — one report per chunk + ranked summary
python main.py --reference data/audio/REF_01.mp3 --batch data/audio/WAV/

# Prompt debug — QA report + Suno prompt implications
python main.py --reference data/audio/REF_01.mp3 --chunk data/audio/CHUNK_B.mp3 --mode prompt-debug

# Ceiling analysis — production hygiene red-flag check
python main.py --ceiling data/audio/elisa_maktooba_leek.mp3 --chunk data/audio/CHUNK_B.mp3

# Style gap analysis — neutral mix-character briefing
python main.py --style-compare data/audio/elisa_maktooba_leek.mp3 --chunk data/audio/CHUNK_B.mp3

# Stem separation + vocal metrics (single-chunk only)
python main.py --reference data/audio/REF_01.mp3 --chunk data/audio/CHUNK_B.mp3 --stems
```

---

## CLI Modes

`--reference`, `--ceiling`, and `--style-compare` are mutually exclusive. Use exactly one per invocation.

`--stems` is a single-chunk modifier. It cannot be combined with `--batch`, `--ceiling`, or `--style-compare` — attempting to do so exits immediately with an error.

---

### 1. Single Chunk QA

```bash
python main.py --reference <ref.mp3|wav> --chunk <chunk.mp3|wav>
python main.py --reference <ref.mp3|wav> --chunk <chunk.mp3|wav> --output reports/chunk_01.md
python main.py --reference <ref.mp3|wav> --chunk <chunk.mp3|wav> --json
python main.py --reference <ref.mp3|wav> --chunk <chunk.mp3|wav> --stems
```

Compares one chunk against the reference. Outputs a Markdown (default) or JSON report to stdout or a file.

**Report sections (always present):**

1. Header — chunk name, Consistency Score (0–100), verdict
2. Feature comparison table — Reference / Chunk / Delta / Flag for all 12 features
3. MFCC detail — 13-coefficient breakdown with role labels
4. Flagged deviations — plain-English label per flagged feature
5. Diagnostic summary — paste-ready LLM block (FR-6)

**`--stems` optional section (inserted before Diagnostic Summary when flag is active):**

6. Stem Analysis — raw Mix / Vocal / Instrumental values for all 11 scalar features, plus 5 vocal-specific metrics (see below). No scoring, no thresholds, no deltas. Does **not** affect the Consistency Score.

**Verdict bands:**

| Score  | Verdict                                              |
| ------ | ---------------------------------------------------- |
| 85–100 | PASS — within reference family                       |
| 65–84  | REVIEW — minor deviations present                    |
| 50–64  | CAUTION — notable deviations, consider re-generation |
| 0–49   | FAIL — significant drift from reference              |

**Stop condition:** If a chunk that sounds correct to your ear scores below 50, recalibrate `THRESHOLDS` in `config.py` before treating scores as authoritative.

---

### 2. Batch Mode

```bash
python main.py --reference <ref.mp3|wav> --batch <folder/>
python main.py --reference <ref.mp3|wav> --batch <folder/> --json
```

Processes every `.mp3` / `.wav` file in the folder. Writes:

- `reports/<chunk_stem>_report.md` — one report per chunk
- `reports/summary.md` — ranked table, worst chunk first

Natively prints a terminal-friendly **🏆 TOP 5 MOST SIMILAR CHUNKS (BEST FIRST)** console summary upon completion.

The reference profile is extracted once and cached to `reference_profile.json`. Subsequent runs against the same reference skip extraction.

**Summary table format:**

```
| Rank | Chunk       | Consistency Score | Flagged Features           |
|:----:|:------------|------------------:|:---------------------------|
| 1    | CHUNK_C.mp3 | 79/100            | Spectral centroid, MFCC    |
| 2    | CHUNK_G.mp3 | 91/100            | LUFS                       |
```

Sorted worst-first. `--mode prompt-debug` is noted but ignored in batch mode — run single-chunk mode for prompt debugging.

---

### 3. Prompt Debug Mode

```bash
python main.py --reference <ref.mp3|wav> --chunk <new_gen.mp3> --mode prompt-debug
```

Identical to Single Chunk QA with one additional section appended: **Suno Prompt Implications**. Maps each flagged feature to a likely Suno prompt cause.

**Implication map v1.1 covers 8 features** with directional entries (12 total entries). Features not in the map (`rms`, `crest_factor_db`, `high_shelf`, `zcr`) render a fallback note if they are the only flags.

**Example implications:**

- Spectral centroid brighter → "Check for descriptors pushing high-frequency energy (e.g. 'crisp', 'bright', 'airy')"
- MFCC distance high → "Check whether reference audio was attached to this generation"
- Presence band low → "Consider adding 'vocal-forward', 'clear vocals', 'intimate'"

Single-chunk only. `--mode prompt-debug` is ignored in batch mode.

---

### 4. Ceiling Analysis Mode

```bash
python main.py --ceiling <commercial_track.mp3> --chunk <chunk.mp3>
python main.py --ceiling <commercial_track.mp3> --chunk <chunk.mp3> --output reports/ceiling.md
python main.py --ceiling <commercial_track.mp3> --chunk <chunk.mp3> --json
```

**Purpose:** Production hygiene red-flag check. Detects gross production failures only — not genre differences.

**What it checks (9 of 12 features):** LUFS, RMS energy, Crest factor, Spectral centroid, Spectral rolloff, Low-mid energy, Presence band, Zero crossing rate, MFCC distance.

**Explicitly excluded (genre-specific — never compared):** High shelf (8kHz+), Stereo width, Tempo.

**Thresholds** are intentionally wide (roughly 2–3× QA thresholds). A flag here is a genuine production hygiene failure, not a stylistic difference.

**Report framing:** Every ceiling report opens with a mandatory disclaimer — _"PRODUCTION HYGIENE CHECK — NOT A STYLE TARGET."_ Every red flag label includes a hygiene reminder. The commercial track values are never presented as targets.

Single-chunk only — `--ceiling` with `--batch` errors explicitly.

---

### 5. Style Gap Analysis Mode

```bash
python main.py --style-compare <commercial_track.mp3> --chunk <chunk.mp3>
python main.py --style-compare <commercial_track.mp3> --chunk <chunk.mp3> --output reports/style_gap.md
python main.py --style-compare <commercial_track.mp3> --chunk <chunk.mp3> --json
```

**Purpose:** Neutral mix-character briefing. Compares 10 mix-relevant features between a Suno chunk and a commercial reference track. No score, no thresholds, no pass/fail. Output is a paste-ready Markdown block for LLM-assisted mix-character reasoning.

**What it compares (10 of 12 features):** LUFS, RMS energy, Crest factor, Spectral centroid, Spectral rolloff, Low-mid energy, Presence band, High shelf, Stereo width, MFCC distance.

**Explicitly excluded:**

- **Tempo** — unreliable on Arabic poetry (librosa beat estimation artefact)
- **Zero crossing rate** — noise/distortion indicator, not a mix-character metric

**Report framing:** Every style gap report opens with _"STYLE GAP BRIEFING — NOT A QA VERDICT."_ The report uses direction arrows (↑/↓/≈) instead of flag symbols (⚠/✓) — there are no thresholds to flag against. The commercial track values are mix-character context only; genre differences are expected and intentional.

**Report sections (all always present):**

1. Header — framing note, file names, feature count
2. Feature comparison table — Commercial / Suno / Delta / Direction for 10 features
3. Perceptual notes — plain-English directional description per feature
4. Style Gap Briefing Block — paste-ready block with genre context and a suggested LLM prompt

**Difference from Ceiling Analysis:** Ceiling mode is a binary red-flag check with wide thresholds and a hygiene framing. Style Gap is threshold-free, directional, and designed for LLM-assisted mix-character reasoning — not defect detection.

Single-chunk only — `--style-compare` with `--batch` errors explicitly.

---

## File Map

```
TRACK_QA/
├── README.md
└── src/
    ├── config.py               # Phases 3/6 — QA thresholds, weights, ceiling thresholds
    ├── extractor.py            # Phase 1 — feature extraction (12 mix features + 5 stem metrics)
    ├── main.py                 # Phase 3+ — CLI entry point, all mode dispatch
    ├── profiler.py             # Phase 2 — reference profile + chunk delta
    ├── reference_profile.json  # auto-created on first --reference run, reused as cache
    ├── reporter.py             # Phases 3/5/6/7 — Markdown report generation (all modes)
    ├── scorer.py               # Phase 3 — consistency score + flagging
    └── reports/                # auto-created in batch mode
        ├── <chunk>_report.md
        ├── summary.md
        └── ceiling_<chunk>.md
```

All scripts must be run from `src/`. No file outside this map should be created without explicit decision. Style Gap Analysis produces no new files beyond those listed.

---

## Features Extracted

All 12 features are extracted from every file by `extractor.py`. Modes differ in which features they use.

| Feature                     | Unit       | Library      | Notes                                                          |
| --------------------------- | ---------- | ------------ | -------------------------------------------------------------- |
| LUFS (integrated loudness)  | LUFS       | `pyloudnorm` | Perceived loudness — must be negative                          |
| RMS energy                  | —          | `librosa`    | Overall energy level                                           |
| Crest factor                | dB         | `librosa`    | 20·log10(peak/RMS)                                             |
| Spectral centroid           | Hz         | `librosa`    | Brightness — tonal weight                                      |
| Spectral rolloff            | Hz         | `librosa`    | High-frequency content rolloff                                 |
| Low-mid energy (200–500 Hz) | frac [0,1] | `librosa`    | Muddiness indicator — fraction of total spectral power         |
| Presence band (1k–4kHz)     | frac [0,1] | `librosa`    | Vocal clarity / cut-through                                    |
| High shelf (8kHz+)          | frac [0,1] | `librosa`    | Air / harshness                                                |
| Stereo width                | —          | `librosa`    | Side/Mid RMS ratio; 0.0 if mono                                |
| Tempo                       | BPM        | `librosa`    | Unreliable on poetry — disabled in QA scoring                  |
| MFCCs (13 coefficients)     | —          | `librosa`    | Timbre fingerprint; cosine distance on C02–C13 used in scoring |
| Zero crossing rate          | —          | `librosa`    | Noisiness / distortion indicator                               |

Band energies (low-mid, presence, high shelf) are expressed as a **fraction of total spectral power** — length-independent and directly comparable across chunks of different duration.

### Stem-Specific Metrics (`--stems` only)

Extracted from the UVR5-separated vocal and instrumental stems. These metrics never enter the consistency scorer — they are reported as raw values only.

| Metric                             | Unit | Notes                                                                                                                      |
| ---------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------- |
| HNR (Harmonics-to-Noise Ratio)     | dB   | Via Praat/parselmouth. Higher = cleaner vocal, less noise or stem bleed.                                                   |
| VAR (Vocal-to-Accompaniment Ratio) | dB   | Absolute power ratio in 1k–4kHz presence band. Positive = vocal louder than instrumental.                                  |
| Pitch Confidence (voiced frames)   | —    | Mean voiced probability, masked to voiced frames only. Arabic consonants (ع, ح, خ, ق) are unvoiced and correctly excluded. |
| Pitch Stability (F0 variance)      | Hz²  | Variance of F0 across voiced frames. Lower = more consistent pitch.                                                        |
| Spectral Flatness (vocal stem)     | —    | Near 0 = tonal/harmonic; near 1 = noise-like/breathy.                                                                      |

**Feature usage by mode:**

| Feature            | QA / Batch | Prompt Debug | Ceiling | Style Gap |  `--stems`   |
| ------------------ | :--------: | :----------: | :-----: | :-------: | :----------: |
| LUFS               |     ✓      |      ✓       |    ✓    |     ✓     | Mix+Voc+Inst |
| RMS energy         |     ✓      |      ✓       |    ✓    |     ✓     | Mix+Voc+Inst |
| Dynamic range      |     ✓      |      ✓       |    ✓    |     ✓     | Mix+Voc+Inst |
| Spectral centroid  |     ✓      |      ✓       |    ✓    |     ✓     | Mix+Voc+Inst |
| Spectral rolloff   |     ✓      |      ✓       |    ✓    |     ✓     | Mix+Voc+Inst |
| Low-mid energy     |     ✓      |      ✓       |    ✓    |     ✓     | Mix+Voc+Inst |
| Presence band      |     ✓      |      ✓       |    ✓    |     ✓     | Mix+Voc+Inst |
| High shelf         |     ✓      |      ✓       |    —    |     ✓     | Mix+Voc+Inst |
| Stereo width       |     ✓      |      ✓       |    —    |     ✓     | Mix+Voc+Inst |
| MFCC distance      |     ✓      |      ✓       |    ✓    |     ✓     |      —       |
| Tempo              |  scored=0  |   scored=0   |    —    |     —     | Mix+Voc+Inst |
| Zero crossing rate |     ✓      |      ✓       |    ✓    |     —     | Mix+Voc+Inst |
| HNR                |     —      |      —       |    —    |     —     |  Vocal only  |
| VAR (dB)           |     —      |      —       |    —    |     —     |  Vocal only  |
| Pitch Confidence   |     —      |      —       |    —    |     —     |  Vocal only  |
| Pitch Stability    |     —      |      —       |    —    |     —     |  Vocal only  |
| Spectral Flatness  |     —      |      —       |    —    |     —     |  Vocal only  |

---

## Scoring Formula

Used in QA, Batch, and Prompt Debug modes only. Ceiling and Style Gap modes do not produce a Consistency Score.

```
# Per feature:
raw_penalty      = max(0.0, abs(delta) / threshold − 1.0)
capped_penalty   = min(raw_penalty, 2.0)
weighted_penalty = capped_penalty × weight

# Final score:
score = 100 − (sum(weighted_penalties) / sum(all_weights)) × 100
score = max(0, round(score, 1))
```

Binary flags (`abs(delta) > threshold`) are used only for report labels — the score itself is continuous and scales with severity. `tempo` weight is 0.0 (disabled) so it never contributes to the score regardless of its delta.

---

## Calibration

### QA Thresholds and Weights

Current values in `config.py` — v1 heuristics calibrated through Sessions 3–9.

| Feature             | Threshold  | Weight | Notes                                                                                                                                                      |
| ------------------- | ---------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lufs`              | ±3.0 LU    | 1.5    | Widened from ±2.0 after Session 3 real-chunk run                                                                                                           |
| `rms`               | ±0.05      | 0.8    |                                                                                                                                                            |
| `crest_factor_db`   | ±3.0 dB    | 1.0    |                                                                                                                                                            |
| `spectral_centroid` | ±500 Hz    | 1.0    |                                                                                                                                                            |
| `spectral_rolloff`  | ±1000 Hz   | 0.8    |                                                                                                                                                            |
| `low_mid_energy`    | ±0.10 frac | 1.0    |                                                                                                                                                            |
| `presence_band`     | ±0.10 frac | 1.2    | Vocal clarity — higher weight                                                                                                                              |
| `high_shelf`        | ±0.05 frac | 0.7    | ⚠ Baseline is ~0.018; may need tightening to ±0.02                                                                                                         |
| `stereo_width`      | ±0.10      | 1.0    | Recalibrated Session 9 (S/M RMS ratio scale; old ±0.15 was abs(L-R))                                                                                       |
| `tempo`             | 999.0      | 0.0    | Disabled — unreliable on Arabic poetry                                                                                                                     |
| `mfcc_distance`     | ±0.10      | 1.5    | Calibrated Session 18: 7 same-voice chunks all scored < 0.05 (max 0.0287, Part C). Tightened from interim ±0.15. Gives 3.5× headroom above worst observed. |
| `zcr`               | ±0.05      | 0.5    |                                                                                                                                                            |

To recalibrate: edit `THRESHOLDS` and `WEIGHTS` in `config.py` directly. No other mechanism exists by design.

### Ceiling Thresholds

Defined separately as `CEILING_THRESHOLDS` in `config.py`. Intentionally wide — roughly 2–3× QA thresholds. A single ceiling flag is a genuine production hygiene failure. These are not covered by the `THRESHOLDS`/`WEIGHTS` integrity check.

### Presence Band Interpretation Rule

When a `presence_band` flag fires, cross-reference it with `low_mid_energy` before treating it as a vocal recession:

- `presence_band` drops **and** `low_mid_energy` spikes → the drop is likely caused by low-end energy inflating the spectral power denominator, not a genuinely recessed vocal. Check for bass buildup or proximity-effect rumble.
- `presence_band` drops **alone** → the vocal may genuinely have less 1k–4kHz cut-through. Consider re-generation or prompt adjustment.

Source: Expert B (Mastering), Session 8 consultation.

### Current Batch Scores (post-Session 18, post-fix)

| Rank | Chunk                   |     Score | Flagged                             |
| :--: | :---------------------- | --------: | :---------------------------------- |
|  1   | FULL_qais_part_C        |  79.3/100 | Spectral centroid, Spectral rolloff |
|  2   | FULL_qais_part_A_02     |  98.3/100 | Spectral centroid, Spectral rolloff |
|  3   | FULL_qais_part_F (Edit) |  99.7/100 | Spectral rolloff                    |
| 4–6  | Parts B, E, G           | 100.0/100 | —                                   |

Part C is a persistent outlier (+1061.7 Hz centroid, +2453.0 Hz rolloff, MFCC distance 0.0287). Decision pending — timbre is within family; deviation is spectral/arrangement only.

---

## Known Limitations

**Tempo disabled.** `librosa.beat.tempo()` produces implausible estimates on non-rhythmic Arabic poetry. Weight is 0.0 and threshold is 999.0. Tempo is extracted and displayed but does not affect the Consistency Score and is excluded from Ceiling and Style Gap modes entirely.

**Prompt implication map v1.1 covers 8 features.** `rms`, `crest_factor_db`, `high_shelf`, and `zcr` have no map entry — they do not translate cleanly to Suno prompt language. A fallback note renders if these are the only flagged features.

**Mono chunks.** If a chunk is mono and the reference is stereo, `stereo_width` delta is `0.0 − reference_width` and will be negative. This is logged with an INFO note. It does not crash.

**Stereo width recalibrated Session 9.** The metric was corrected from absolute amplitude (`mean(abs(L−R))`) to amplitude-normalised Side/Mid RMS ratio. The threshold was updated to ±0.10 (old ±0.15 was calibrated against the obsolete formula and is no longer valid). Monitor: tighten to ±0.07 if false negatives emerge.

**MP3 acceptable.** Suno compression artefacts are uniform across chunks from the same project and will not skew comparative deltas.

**`--stems` is single-chunk and CPU-only.** Stem separation via BS-Roformer (`audio-separator`) runs on CPU by default. Separation of a typical 3–5 minute chunk takes 1–5 minutes depending on hardware. GPU support requires a different `audio-separator` install target. `--stems` cannot be combined with `--batch`, `--ceiling`, or `--style-compare`. The first run downloads the BS-Roformer model (~500 MB).

**Stem metrics are advisory only.** HNR, VAR, and pitch metrics are extracted from UVR5-separated stems. If BS-Roformer produces bleed (dense low-mid content can cause this), HNR readings may be artefacts. Always cross-reference HNR against VAR: if VAR is negative at the same moment HNR drops, the HNR reading is likely a bleed artefact. None of the stem metrics affect the Consistency Score.

**Ceiling and Style Gap are single-chunk only.** Both `--ceiling` and `--style-compare` with `--batch` error explicitly.

**Style Gap direction arrows, not thresholds.** The ↑/↓/≈ direction in style gap reports reflects sign and magnitude of the delta only. Magnitude is not benchmarked against any norm — the LLM receiving the briefing block reasons about significance.

**Commercial track genre mismatch.** Both ceiling and style gap modes are designed for this. Genre-specific features are excluded from ceiling analysis. Style gap makes no exclusions for genre — it is explicitly framed as mix-character context, not a style target.

**`reports/` is gitignored.** Keep manual copies of significant batch runs if needed.

---

## What the Script Does NOT Do

- Does not fix or alter any audio
- Does not make final re-generation decisions — it flags and explains
- Does not use commercial tracks as style or genre targets
- Does not score Suno tracks against commercial production targets
- Does not replace the user's ear — it directs it
- Does not call any LLM API — all LLM interaction is manual (paste the summary block)
