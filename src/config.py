"""
config.py — Phase 3: Deviation Thresholds & Perceptual Weights
Audio QA — Classical Arabic Poem → Suno AI → Audacity Pipeline

Two plain Python dicts — edit these directly, no other mechanism.
No config file parser. No CLI overrides. No YAML. No TOML.

All values are v1 heuristics. A calibration pass is MANDATORY after the
first end-to-end run against a real chunk. Do not treat scores as
authoritative before calibration.

THRESHOLDS — how far a feature delta may travel before being flagged.
WEIGHTS    — perceptual importance multiplier in the consistency score.
             Higher weight = this feature dominates the score more.

Both dicts must have the same 12 keys. scorer.py will raise KeyError if
a key is present in one but missing from the other.
"""

# ---------------------------------------------------------------------------
# Deviation thresholds
# Source: AUDIO_QA_Phased_Plan.md, Phase 3, Task 3.1
#
# CALIBRATION WATCH POINTS (from Session 3 Handover):
#   high_shelf  ±0.05  — baseline is only 0.018 (fractional energy). This
#                        threshold may be too loose for such a small baseline.
#                        Flag if high_shelf fires unexpectedly; tighten to
#                        ±0.02 or ±0.015 if needed after first real-chunk run.
#   low_mid_energy ±0.10, presence_band ±0.10 — written before band energies
#                        were normalized to [0,1]. These are heuristic;
#                        verify against first run results.
#   tempo ±10 BPM       — Arabic poetry meter is irregular. 112.5 BPM from
#                        reference is almost certainly an artefact. Weight is
#                        low (0.5) but threshold may need widening. Monitor.
#   mfcc_distance ±5.0  — MFCC coefficients have varying scales. If real
#                        chunks that sound correct score >5.0, widen to ±8.0.
# ---------------------------------------------------------------------------

THRESHOLDS: dict[str, float] = {
    "lufs":              3.0,     # ±3.0 LU    — loudness consistency (widened from 2.0)
    "rms":               0.05,    # ±0.05       — overall energy level
    "dynamic_range":     3.0,     # ±3.0 dB     — compression consistency
    "spectral_centroid": 500.0,   # ±500 Hz     — brightness drift
    "spectral_rolloff":  1000.0,  # ±1000 Hz    — high-frequency content
    "low_mid_energy":    0.10,    # ±0.10 frac  — muddiness band [0,1]
    "presence_band":     0.10,    # ±0.10 frac  — vocal clarity band [0,1]
    "high_shelf":        0.05,    # ±0.05 frac  — air/harshness [0,1] ⚠ watch
    "stereo_width":      0.15,    # ±0.15       — spatial consistency
    "tempo":             999.0,   # Disabled    — pacing (unreliable on poetry)
    "mfcc_distance":     7.0,     # ±7.0        — timbre fingerprint (widened from 5.0)
    "zcr":               0.05,    # ±0.05       — noise/distortion indicator
}

# ---------------------------------------------------------------------------
# Perceptual weights
# Source: AUDIO_QA_Phased_Plan.md, Phase 3, Task 3.1
#
# Rationale summary:
#   1.5  lufs, mfcc_distance — highest priority: loudness and voice identity
#   1.2  presence_band       — vocal clarity is critical for poetry
#   1.0  centroid, low_mid, stereo_width, dynamic_range — noticeable, equal
#   0.8  rms, rolloff        — correlated/secondary to higher-weight features
#   0.7  high_shelf          — relevant but secondary
#   0.5  zcr, tempo          — lowest perceptual priority / unreliable estimate
# ---------------------------------------------------------------------------

WEIGHTS: dict[str, float] = {
    "lufs":              1.5,
    "mfcc_distance":     1.5,
    "presence_band":     1.2,
    "spectral_centroid": 1.0,
    "low_mid_energy":    1.0,
    "stereo_width":      1.0,
    "dynamic_range":     1.0,
    "rms":               0.8,
    "spectral_rolloff":  0.8,
    "high_shelf":        0.7,
    "zcr":               0.5,
    "tempo":             0.0,     # Disabled (removed from score calculation)
}

# ---------------------------------------------------------------------------
# Integrity check — run on import to catch editing mistakes immediately
# ---------------------------------------------------------------------------
_missing_in_weights    = set(THRESHOLDS) - set(WEIGHTS)
_missing_in_thresholds = set(WEIGHTS)    - set(THRESHOLDS)

if _missing_in_weights:
    raise ValueError(
        f"config.py integrity error: keys in THRESHOLDS but missing from WEIGHTS: "
        f"{sorted(_missing_in_weights)}"
    )
if _missing_in_thresholds:
    raise ValueError(
        f"config.py integrity error: keys in WEIGHTS but missing from THRESHOLDS: "
        f"{sorted(_missing_in_thresholds)}"
    )

# ---------------------------------------------------------------------------
# Phase 6 — Ceiling Analysis Thresholds (FR-9)
# Source: AUDIO_QA_Phased_Plan.md, Phase 6
#
# PURPOSE: Red-flag detection of gross production hygiene failures only.
# NOT a style match. NOT targets. NOT genre norms.
#
# Excluded features (genre-specific — do NOT add them here):
#   high_shelf   — genre-specific air/harshness treatment
#   stereo_width — genre-specific spatial feel
#   tempo        — unreliable on poetry; not a commercial norm
#
# Thresholds are intentionally wide (roughly 2–3× QA thresholds).
# Only egregious violations should fire — a single flag here is a
# genuine production hygiene problem, not a stylistic difference.
#
# These thresholds are NOT covered by the THRESHOLDS/WEIGHTS integrity
# check — ceiling analysis has no scoring formula, only binary flags.
# ---------------------------------------------------------------------------

CEILING_THRESHOLDS: dict[str, float] = {
    "lufs":              8.0,     # ±8.0 LU    — truly buried or crushed
    "rms":               0.15,    # ±0.15      — gross energy mismatch
    "dynamic_range":     8.0,     # ±8.0 dB    — severely squashed or expanded
    "spectral_centroid": 2500.0,  # ±2500 Hz   — extremely dark or harsh
    "spectral_rolloff":  4000.0,  # ±4000 Hz   — grossly different freq. balance
    "low_mid_energy":    0.25,    # ±0.25 frac — severe muddiness buildup
    "presence_band":     0.25,    # ±0.25 frac — vocal severely buried or peaked
    "zcr":               0.15,    # ±0.15      — gross noise or distortion
    "mfcc_distance":     20.0,    # ±20.0      — completely different timbre
}