# Bug Report — TRACK_QA Codebase
**Date:** 2026-05-18
**Investigator:** Post-discrepancy audit (style_gap.md vs report.txt)
**Scope:** `src/extractor.py`, `src/profiler.py`, `src/scorer.py`, `src/config.py`, `README.md`

---

## BUG-TQ-01 — `dynamic_range` key misidentifies crest factor as dynamic range

| Field | Detail |
|---|---|
| **ID** | BUG-TQ-01 |
| **Severity** | 🟠 High |
| **Files** | `extractor.py`, `config.py`, `README.md` (and all downstream consumers in `reporter.py`, `main.py`) |
| **Type** | Naming / Semantic error |

### Description

`extract_features()` stores the **crest factor** under the key `dynamic_range`. These are different metrics:

- **Crest factor** — `20 × log10(peak / RMS)`. Measures transient punchiness. A short loud drum hit over a quiet bed gives a high value regardless of how much the song's overall loudness varies.
- **Dynamic range** — the difference in level between the loudest and quietest musical sections (e.g., RMS p95 − p5 spread). Measures macro-level contrast.

The bug is present in three places simultaneously:

**`extractor.py` — formula is crest factor, key says `dynamic_range`:**
```python
# Comment says "crest factor in dB" but the dict key says "dynamic_range"
dynamic_range = float(20.0 * np.log10(peak / rms_raw))   # ← crest factor
...
return {
    ...
    "dynamic_range": dynamic_range,   # ← misnamed key
    ...
}
```

**`config.py` — threshold calibrated against crest factor values, column header says "Dynamic range":**
```python
"dynamic_range": 3.0,   # ±3.0 dB — but this is a crest factor threshold
```

**`README.md` — feature table entry is also wrong:**
```
| Dynamic range (crest factor) | dB | librosa | 20·log10(peak/RMS) |
```
The parenthetical `(crest factor)` acknowledges the issue but the primary label is still wrong, propagating the error to any consumer reading the docs.

### Impact

- Report output labels crest factor as "Dynamic range" — misleading to any human reading it.
- The LLM briefing block fed to downstream prompts will describe crest factor deltas using dynamic range language. This is semantically incorrect input for mix-character reasoning.
- `audio_analyser.py`'s `report.txt` correctly distinguishes crest factor (`crest_db`) from dynamic range (`dynamic_range_db`). When both outputs are read together, "Dynamic range" in `style_gap.md` does not mean the same thing as "Dynamic range" in `report.txt` — they are different metrics with the same name.

### Reproduction

Run `python extractor.py <any_audio.mp3>` and observe the `dynamic_range` value. For a heavily limited track it will read ~6–8 dB (typical crest factor for brickwall-limited material). A real dynamic range measurement of a heavily limited track would be closer to 2–4 dB — a meaningfully different number.

### Fix

**Step 1 — rename the key in `extractor.py`:**
```python
# Before
"dynamic_range": dynamic_range,

# After
"crest_factor_db": dynamic_range,
```

**Step 2 — update `config.py`:**
```python
# Before
THRESHOLDS = { "dynamic_range": 3.0, ... }
WEIGHTS    = { "dynamic_range": 1.0, ... }

# After
THRESHOLDS = { "crest_factor_db": 3.0, ... }
WEIGHTS    = { "crest_factor_db": 1.0, ... }
```

**Step 3 — update all downstream consumers** (`profiler.py` scalar_keys list, `reporter.py` display names, `main.py` `_SUMMARY_NAMES`, `README.md` feature table and calibration table). The integrity check in `config.py` will catch any missed rename at import time.

**Step 4 (optional but recommended)** — add a real dynamic range metric using the RMS percentile spread already implemented in `audio_analyser.py`'s `compute_dynamics()`. This requires a new threshold in `config.py` and a calibration pass.

---

## BUG-TQ-02 — Two different RMS computations within `extract_features()`

| Field | Detail |
|---|---|
| **ID** | BUG-TQ-02 |
| **Severity** | 🟡 Medium |
| **File** | `extractor.py` |
| **Type** | Methodological inconsistency |

### Description

`extract_features()` computes two different RMS values inside the same function and uses each for a different purpose, without documenting the discrepancy:

```python
# Line ~90 — frame-based RMS (reported as the "rms" feature)
rms = float(librosa.feature.rms(y=y_mono).mean())

# Line ~95 — global waveform RMS (used internally for crest factor only)
rms_raw = float(np.sqrt(np.mean(y_mono**2)))
if rms_raw > 0.0:
    dynamic_range = float(20.0 * np.log10(peak / rms_raw))
```

`librosa.feature.rms()` computes RMS over overlapping short-time frames (default `frame_length=2048`, `hop_length=512`) and returns one value per frame. The `.mean()` then averages those frame-level RMS values. In this averaging, every frame contributes equally regardless of how loud it is — quiet frames pull the mean down as much as loud frames push it up.

`np.sqrt(np.mean(y**2))` (global RMS) weights each sample by its squared amplitude. Louder moments dominate. This is the standard definition of signal RMS.

On a typical mastered track with dynamic variation, the frame-based mean will read lower than the global RMS. The `rms` feature being reported to users (and scored by `scorer.py`) uses the frame-based value, while `rms_raw` (used for crest factor, not exposed) uses global. The two are silently inconsistent.

### Impact

- The reported `rms` feature and the internal `rms_raw` used for `crest_factor_db` are on different scales. Changing `rms` to global RMS would slightly shift crest factor values as well (since `rms_raw` would then be identical to the reported `rms`).
- `audio_analyser.py` uses global RMS exclusively. Comparing `rms` values between the two codebases produces a systematic offset (see Discrepancy Report, BUG noted for reference track: 0.2527 vs 0.2852).
- The `rms` threshold in `config.py` (`±0.05`) was calibrated against frame-based values. Switching to global RMS requires a recalibration pass.

### Fix

Standardise on global waveform RMS throughout `extract_features()`. Replace both computations with one:

```python
# Single computation — used for both the reported feature and crest factor
rms = float(np.sqrt(np.mean(y_mono**2)))

peak = float(np.max(np.abs(y_mono)))
crest_factor_db = float(20.0 * np.log10(peak / (rms + 1e-10)))

return {
    "rms": rms,
    "crest_factor_db": crest_factor_db,   # combined with BUG-TQ-01 fix
    ...
}
```

After making this change, run the existing batch of 6 chunks against the reference and compare scores to the post-Session 9 baseline. Adjust the `rms` threshold in `config.py` if scores shift materially.

---

## BUG-TQ-03 — Stale docstring in `scorer.py`

| Field | Detail |
|---|---|
| **ID** | BUG-TQ-03 |
| **Severity** | 🔵 Low |
| **File** | `src/scorer.py` |
| **Type** | Documentation error (cosmetic, no functional impact) |

### Description

The module-level docstring in `scorer.py` describes the MFCC distance computation incorrectly:

```python
# Current (wrong):
"""
Note on mfcc_distance:
    mfcc_distance is a non-negative scalar (mean absolute MFCC delta).
"""
```

The actual computation (in `profiler.py`) is a **cosine distance**, not a mean absolute delta:

```python
# profiler.py — actual formula
mfcc_distance = round(float(cosine(chunk_mfccs[1:], ref_mfccs[1:])), 6)
```

Cosine distance is bounded [0, 2] and is orientation-invariant (scale-independent). Mean absolute delta is unbounded and scale-dependent. These are not the same thing. A developer reading `scorer.py` in isolation will misunderstand what the `mfcc_distance` value represents and why the threshold is `±7.0` (which would make no sense for cosine distance bounded at 2, but is correct for the normalised L2 variant used historically — see BUG-TQ-03 note below).

> **Note:** The `mfcc_distance ±7.0` threshold in `config.py` also deserves scrutiny. Cosine distance is bounded at [0, 2], so a threshold of 7.0 means the feature can never actually flag (it will always be < 2 < 7). If the threshold was set when the formula was mean absolute delta and never updated after the switch to cosine, the `mfcc_distance` feature is silently non-functional in the scorer. This should be verified: if `mfcc_distance` has never flagged in any batch run, the threshold is the wrong order of magnitude.

### Fix

**Docstring fix in `scorer.py`:**
```python
# After
"""
Note on mfcc_distance:
    mfcc_distance is a cosine distance computed in profiler.py over
    MFCC coefficients C02–C13 (C01 dropped). Range: [0, 2].
    A value of 0 means identical timbre direction; 2 means opposite.
"""
```

**Threshold audit in `config.py`:**

If the cosine distance has never exceeded 0.3 in any run, recalibrate:
```python
"mfcc_distance": 0.15,   # example — set from observed batch distribution
```

If the threshold was intentionally set wide as a "never fires" safety rail, document that explicitly rather than leaving an implausible value.

---

## BUG-TQ-04 — No explicit sample rate normalisation on load

| Field | Detail |
|---|---|
| **ID** | BUG-TQ-04 |
| **Severity** | 🔵 Low (latent) |
| **File** | `extractor.py` |
| **Type** | Latent consistency risk |

### Description

`extractor.py` loads audio at its native sample rate:

```python
y, sr = librosa.load(filepath, mono=False, sr=None)   # sr=None = native rate
```

If a reference file is at 44100 Hz and a chunk is at 48000 Hz (possible if Suno changes its export format, or if a reference track from a different source is used), the two signals are analysed at different sample rates. The feature functions all receive `sr` as a parameter and normalise correctly, so reported Hz values will be comparable. However:

- The global FFT in `_band_energy_fraction()` operates on signals of different lengths (proportional to sample rate × duration). For a 3-minute file: 44100 × 180 = 7,938,000 samples vs 48000 × 180 = 8,640,000 samples. The FFT frequency resolution differs.
- `librosa.feature.mfcc()` builds a mel filterbank scaled to `sr`. At different sample rates the filterbank covers the same Hz range, but the number of FFT bins per mel band differs — meaning MFCC coefficient values are not directly comparable across different sample rates.
- The reference profile is cached to `reference_profile.json` with no record of the sample rate used. If a subsequent run loads a chunk at a different rate, there is no warning.

This will not produce wrong results as long as all files in a project are at the same native sample rate — which is the normal case. It becomes a silent bug if sample rates diverge.

### Fix

Pin sample rate explicitly on load:

```python
TARGET_SR = 44100   # define once at module level

y, sr = librosa.load(filepath, mono=False, sr=TARGET_SR)
```

Add `"_sr"` to the reference profile JSON alongside `"_source"` so any sample rate mismatch is detectable on cache load:

```python
profile["_sr"] = TARGET_SR
```

In `main.py`'s `_load_or_build_reference()`, add a check:
```python
if cached.get("_sr") != TARGET_SR:
    print("[MAIN] Cache sample rate mismatch — rebuilding.")
```

---

## Summary

| ID | Severity | File(s) | Description | Effort |
|---|---|---|---|---|
| BUG-TQ-01 | 🟠 High | `extractor.py`, `config.py`, `README.md` | `dynamic_range` key stores crest factor — naming error across the full pipeline | Medium — rename + downstream sweep |
| BUG-TQ-02 | 🟡 Medium | `extractor.py` | Two different RMS formulas in one function — frame-based for reported feature, global for internal crest factor | Low — consolidate to one formula + recalibrate threshold |
| BUG-TQ-03 | 🔵 Low | `scorer.py`, `config.py` | Stale docstring ("mean absolute MFCC delta" vs actual cosine distance) + possible non-functional threshold | Low — docstring fix; threshold audit requires one test run |
| BUG-TQ-04 | 🔵 Low | `extractor.py`, `main.py` | `sr=None` on load — no sample rate normalisation or cache validation | Low — pin `sr=TARGET_SR`, add `_sr` to cache |

**Recommended fix order:** TQ-01 → TQ-02 → TQ-04 → TQ-03
