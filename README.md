# AUDIO-QA

**Pre-assembly quality assurance for Suno AI-generated audio chunks.**

Classical Arabic Poem → Suno AI → Audacity pipeline.  
Catches deviant chunks _before_ Audacity assembly. Produces paste-ready diagnostic reports for LLM-assisted prompt debugging.

---

## Installation

```bash
pip install librosa pyloudnorm soundfile numpy
```

Python 3.9+ required. No GUI. CLI only.

---

## Quick Start

```bash
# Single chunk — report to stdout
python main.py --reference data/audio/REF_01.mp3 --chunk data/audio/CHUNK_B.mp3

# Batch folder — one report per chunk + ranked summary
python main.py --reference data/audio/REF_01.mp3 --batch data/audio/WAV/

# Production hygiene check against a commercial track
python main.py --ceiling data/audio/elisa_maktooba_leek.mp3 --chunk data/audio/CHUNK_B.mp3
```

---

## CLI Modes

### 1. Single Chunk QA

```bash
python main.py --reference <ref.mp3|wav> --chunk <chunk.mp3|wav>
python main.py --reference <ref.mp3|wav> --chunk <chunk.mp3|wav> --output reports/chunk_01.md
python main.py --reference <ref.mp3|wav> --chunk <chunk.mp3|wav> --json
```

Compares one chunk against the reference. Outputs a Markdown (default) or JSON report to stdout or a file.

**Report sections (all always present):**

1. Header — chunk name, Consistency Score (0–100), verdict
2. Feature comparison table — Reference / Chunk / Delta / Flag for all 12 features
3. MFCC detail — 13-coefficient breakdown with role labels
4. Flagged deviations — plain-English label per flagged feature
5. Diagnostic summary — paste-ready LLM block (FR-6)

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

The reference profile is extracted once and cached to `reference_profile.json`. Subsequent runs against the same reference skip extraction.

**Summary table format:**

```
| Rank | Chunk       | Consistency Score | Flagged Features           |
|:----:|:------------|------------------:|:---------------------------|
| 1    | CHUNK_C.mp3 | 78/100            | Spectral centroid, MFCC    |
| 2    | CHUNK_G.mp3 | 91/100            | LUFS                       |
```

---

### 3. Prompt Debug Mode

```bash
python main.py --reference <ref.mp3|wav> --chunk <new_gen.mp3> --mode prompt-debug
```

Same as single chunk QA, with an additional **Suno Prompt Implications** section appended. Maps each flagged feature to a likely Suno prompt cause.

**Example implications:**

- Spectral centroid brighter → "Check for descriptors pushing high-frequency energy (e.g. 'crisp', 'bright', 'airy')"
- MFCC distance high → "Check whether reference audio was attached to this generation"
- Presence band low → "Consider adding 'vocal-forward', 'clear vocals', 'intimate'"

Implication map v1.1 covers 8 features with directional entries (12 total entries). Features not in the map (`rms`, `dynamic_range`, `zcr`) render a fallback note if they are the only flags.

Single-chunk only — `--mode prompt-debug` is noted but ignored in batch mode.

---

### 4. Ceiling Analysis Mode (Phase 6)

```bash
python main.py --ceiling <commercial_track.mp3> --chunk <chunk.mp3>
python main.py --ceiling <commercial_track.mp3> --chunk <chunk.mp3> --output reports/ceiling.md
```

**Purpose:** Production hygiene red-flag check. Detects gross production failures only — not genre differences.

**What it checks (9 of 12 features):** LUFS, RMS energy, Dynamic range, Spectral centroid, Spectral rolloff, Low-mid energy, Presence band, Zero crossing rate, MFCC distance.

**Explicitly excluded (genre-specific — never compared):** High shelf (8kHz+), Stereo width, Tempo.

**Thresholds** are intentionally wide (roughly 2–3× QA thresholds). A flag here is a genuine production hygiene failure, not a stylistic difference.

**Report framing:** Every ceiling report opens with a mandatory disclaimer — _"PRODUCTION HYGIENE CHECK — NOT A STYLE TARGET."_ Every red flag label includes a hygiene reminder. The commercial track values are never presented as targets.

Single-chunk only — `--ceiling` with `--batch` errors explicitly.

---

## File Map

```
project_root/
├── extractor.py          # Phase 1 — feature extraction (12 features)
├── profiler.py           # Phase 2 — reference profile + chunk delta
├── scorer.py             # Phase 3 — consistency score + flagging
├── reporter.py           # Phase 3/5/6 — Markdown report generation
├── config.py             # Phase 3/6 — thresholds, weights, ceiling thresholds
├── main.py               # Phase 3+ — CLI entry point, all mode dispatch
├── reference_profile.json  # auto-created on first run, reused as cache
└── reports/              # auto-created in batch mode
    ├── <chunk>_report.md
    ├── summary.md
    └── ceiling_<chunk>.md
```

No file outside this map should be created without explicit decision.

---

## Features Extracted

| Feature                      | Unit       | Library      | Notes                                      |
| ---------------------------- | ---------- | ------------ | ------------------------------------------ |
| LUFS (integrated loudness)   | LUFS       | `pyloudnorm` | Perceived loudness — must be negative      |
| RMS energy                   | —          | `librosa`    | Overall energy level                       |
| Dynamic range (crest factor) | dB         | `librosa`    | 20·log10(peak/RMS)                         |
| Spectral centroid            | Hz         | `librosa`    | Brightness — tonal weight                  |
| Spectral rolloff             | Hz         | `librosa`    | High-frequency content rolloff             |
| Low-mid energy (200–500 Hz)  | frac [0,1] | `librosa`    | Muddiness indicator                        |
| Presence band (1k–4kHz)      | frac [0,1] | `librosa`    | Vocal clarity / cut-through                |
| High shelf (8kHz+)           | frac [0,1] | `librosa`    | Air / harshness                            |
| Stereo width                 | —          | `librosa`    | Side/Mid RMS ratio; 0.0 if mono            |
| Tempo                        | BPM        | `librosa`    | Unreliable on poetry — disabled in scoring |
| MFCCs (13 coefficients)      | —          | `librosa`    | Timbre fingerprint                         |
| Zero crossing rate           | —          | `librosa`    | Noisiness / distortion indicator           |

Band energies (low-mid, presence, high shelf) are expressed as a **fraction of total spectral power** — length-independent and directly comparable across chunks of different duration.

---

## Scoring Formula

```
# Per feature:
raw_penalty     = max(0.0, abs(delta) / threshold − 1.0)
capped_penalty  = min(raw_penalty, 2.0)
weighted_penalty = capped_penalty × weight

# Final score:
score = 100 − (sum(weighted_penalties) / sum(all_weights)) × 100
score = max(0, round(score, 1))
```

Binary flags (`abs(delta) > threshold`) are used only for report labels — the score itself is continuous and scales with severity.

---

## Calibration Notes

**Current thresholds and weights are v1 heuristics** calibrated after real-chunk runs in Sessions 3–5.

Key calibration decisions locked:

| Parameter                 | Value   | Note                                                                    |
| ------------------------- | ------- | ----------------------------------------------------------------------- |
| `lufs` threshold          | ±3.0 LU | Widened from ±2.0 after Session 3 real-chunk run                        |
| `mfcc_distance` threshold | ±7.0    | Widened from ±5.0 after Session 3 real-chunk run                        |
| `tempo` weight            | 0.0     | Disabled — librosa beat estimation is unreliable on Arabic poetry       |
| `tempo` threshold         | 999.0   | Effectively infinite — tempo never flags                                |
| `high_shelf` threshold    | ±0.05   | Watch point: baseline is only ~0.018 frac; may need tightening to ±0.02 |

To recalibrate: edit `config.py` directly — `THRESHOLDS` and `WEIGHTS` are plain Python dicts. No other mechanism exists by design.

**Ceiling thresholds** (`CEILING_THRESHOLDS` in `config.py`) are separate from QA thresholds and are not covered by the integrity check. They are intentionally wide.

### Presence Band Interpretation Rule

When a `presence_band` flag fires, cross-reference it with `low_mid_energy` in the same chunk's report before treating it as a vocal recession:

- If `presence_band` drops **and** `low_mid_energy` spikes: the drop is likely caused by low-end energy inflating the total spectral power denominator, not by a genuinely recessed vocal. Check for bass buildup or proximity-effect rumble in this chunk.
- If `presence_band` drops **alone** (low-mid is within threshold): the vocal may genuinely have less 1k–4kHz cut-through. Consider re-generation or prompt adjustment.

Source: Expert B (Mastering), Session 8 consultation.

## Known Limitations

- **Tempo disabled.** `librosa.beat.tempo()` produces implausible estimates on non-rhythmic Arabic poetry. Weight is 0.0 and threshold is 999.0. Tempo is extracted and displayed but does not affect the Consistency Score.
- **Prompt implication map v1.1 covers 8 features.** `rms`, `dynamic_range`, and `zcr` have no map entry — they do not translate cleanly to Suno prompt language. If these are the only flagged features, a fallback note renders in the Prompt Implications section.
- **Mono chunks.** If a chunk is mono and the reference is stereo, `stereo_width` delta is `0.0 − reference_width` and will be negative. This is logged with an INFO note. It does not crash.
- **Stereo width threshold requires recalibration.** The `stereo_width` metric was corrected in Session 8 from an absolute amplitude formula (`mean(abs(L−R))`) to an amplitude-normalised Side/Mid RMS ratio. The threshold (`±0.15` in `config.py`) was calibrated against the old formula and is no longer valid. Do not treat stereo width flags as authoritative until `THRESHOLDS["stereo_width"]` has been recalibrated against a batch run using the new metric.
- **MP3 acceptable.** Suno compression artifacts are uniform across chunks from the same project and will not skew comparative deltas.
- **No stem separation.** Vocal isolation (Demucs etc.) is out of scope. All features reflect the full mix, including accompaniment.
- **Ceiling analysis is single-chunk only.** `--ceiling` with `--batch` errors explicitly.
- **Commercial track genre mismatch.** The ceiling analysis is designed specifically for this. Genre-specific features are excluded. The report framing is mandatory — do not remove the disclaimer.

## What the Script Does NOT Do

- Does not fix or alter any audio
- Does not make final re-generation decisions — it flags and explains
- Does not use commercial tracks as style or genre targets
- Does not replace the user's ear — it directs it
