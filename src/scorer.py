"""
scorer.py — Phase 3: Consistency Score & Deviation Flagging
Audio QA — Classical Arabic Poem → Suno AI → Audacity Pipeline

Task 3.1 — score_chunk(analysis, thresholds, weights) -> dict

Implements the weighted continuous scoring formula from the plan.

SCORING FORMULA (per feature):
    raw_penalty     = max(0.0, abs(delta) / threshold - 1.0)
                      ^ 0 if within threshold; grows linearly beyond it
    capped_penalty  = min(raw_penalty, 2.0)
                      ^ caps runaway outliers at 2× threshold violation
    weighted_penalty = capped_penalty * weight

FINAL SCORE:
    score = 100 - (sum(weighted_penalties) / sum(all_weights)) * 100
    score = max(0, round(score, 1))

Binary flag (abs(delta) > threshold) is retained for report labels only.
It does NOT affect the score — the continuous formula handles severity.

Does NOT modify extractor.py, profiler.py, or config.py.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_chunk(analysis: dict, thresholds: dict, weights: dict) -> dict:
    """
    Score one chunk's analysis against the reference using configured
    thresholds and perceptual weights.

    Args:
        analysis:   Dict returned by profiler.analyze_chunk()
                    Required keys: analysis["deltas"] containing all 12
                    scored feature keys (11 scalar + mfcc_distance).
        thresholds: Dict of per-feature deviation thresholds (from config.py).
        weights:    Dict of per-feature perceptual weights (from config.py).

    Returns:
        dict with keys:
            consistency_score       float  — 0–100, higher = closer to reference
            flagged_features        list   — keys where abs(delta) > threshold
            scored_features         dict   — per-feature scoring breakdown
            total_weighted_penalty  float  — raw sum before normalisation
            total_weight            float  — sum of all weights (denominator)

    Note on mfcc_distance:
        mfcc_distance is a cosine distance computed in profiler.py over
        MFCC coefficients C02–C13 (C01 dropped to prevent loudness differences
        from dominating the timbre metric). Range: [0, 2].
        A value of 0 means identical timbre direction; 2 means opposite.
        abs(mfcc_distance) == mfcc_distance, so the scoring formula is unchanged.
        mfcc_deltas (the 13-element list) is NOT used in scoring — only in
        the report's MFCC detail block.
        
        ⚠ CALIBRATION NOTE: The previous threshold was ±7.0, which was set
        against the old mean-absolute-delta formula and was unreachable by
        cosine distance (max 2.0). The feature was non-functional for all
        prior sessions. Current threshold is ±0.15 — recalibrate after the
        first real batch run if same-voice chunks consistently score below 0.05.
    """
    deltas      = analysis["deltas"]
    total_weight = sum(weights.values())

    scored_features: dict[str, dict] = {}
    total_weighted_penalty = 0.0

    for feature, threshold in thresholds.items():
        delta  = deltas[feature]   # scalar for all 12 keys; mfcc_deltas ignored
        weight = weights[feature]

        # Continuous penalty — 0 inside threshold, linear beyond, capped at 2×
        raw_penalty    = max(0.0, abs(delta) / threshold - 1.0)
        capped_penalty = min(raw_penalty, 2.0)
        weighted_penalty = capped_penalty * weight

        # Binary flag — used only for report labels, not the score
        flagged = abs(delta) > threshold

        scored_features[feature] = {
            "delta":             delta,
            "threshold":         threshold,
            "weight":            weight,
            "raw_penalty":       round(raw_penalty,       8),
            "capped_penalty":    round(capped_penalty,    8),
            "weighted_penalty":  round(weighted_penalty,  8),
            "flagged":           flagged,
        }

        total_weighted_penalty += weighted_penalty

    raw_score         = 100.0 - (total_weighted_penalty / total_weight) * 100.0
    consistency_score = max(0.0, round(raw_score, 1))
    flagged_features  = [f for f, v in scored_features.items() if v["flagged"]]

    return {
        "consistency_score":      consistency_score,
        "flagged_features":       flagged_features,
        "scored_features":        scored_features,
        "total_weighted_penalty": round(total_weighted_penalty, 8),
        "total_weight":           round(total_weight,           8),
    }


# ---------------------------------------------------------------------------
# Phase 3 validation block
# Run: python scorer.py
# Uses self-identity logic — if analysis["deltas"] are all zero, score must be 100.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from config import THRESHOLDS, WEIGHTS

    print("\n" + "=" * 64)
    print("  AUDIO-QA — Phase 3 Scorer Validation")
    print("=" * 64)

    # Build a synthetic zero-delta analysis (self-identity equivalent)
    zero_deltas: dict = {k: 0.0 for k in THRESHOLDS}
    zero_deltas["mfcc_deltas"] = [0.0] * 13   # not scored, must not crash

    synthetic_analysis = {
        "chunk_path":       "synthetic_self_identity",
        "chunk_values":     {},
        "reference_values": {},
        "deltas":           zero_deltas,
    }

    score = score_chunk(synthetic_analysis, THRESHOLDS, WEIGHTS)
    cs    = score["consistency_score"]

    print(f"\n  Zero-delta (self-identity) Consistency Score: {cs}/100")

    if cs == 100.0:
        print("  PASS — zero deltas yield score 100.0  OK")
    else:
        print(f"  FAIL — expected 100.0, got {cs}")
        print("  Check scoring formula in score_chunk().")
        import sys; sys.exit(1)

    # Verify max-penalty case (all deltas = 3× threshold → capped at 2×)
    max_deltas: dict = {k: THRESHOLDS[k] * 3.0 for k in THRESHOLDS}
    max_deltas["mfcc_deltas"] = [0.0] * 13

    max_analysis = {
        "chunk_path":       "synthetic_max_penalty",
        "chunk_values":     {},
        "reference_values": {},
        "deltas":           max_deltas,
    }

    max_score = score_chunk(max_analysis, THRESHOLDS, WEIGHTS)
    ms        = max_score["consistency_score"]
    all_flagged = len(max_score["flagged_features"]) == len(THRESHOLDS)

    print(f"\n  3× threshold (all capped at 2×) Consistency Score: {ms}/100")
    print(f"  Expected: 0.0 (penalty = 2× for every feature)")
    print(f"  All features flagged: {'PASS' if all_flagged else 'FAIL'}")

    if ms == 0.0 and all_flagged:
        print("  PASS — max-penalty case produces 0.0 and all flags set  OK")
    else:
        print(f"  NOTE — got {ms} (should be 0.0 if cap at 2× fills all weight)")

    # Verify config integrity (keys must match)
    th_keys = set(THRESHOLDS)
    wt_keys = set(WEIGHTS)
    if th_keys == wt_keys:
        print(f"\n  Config key alignment: PASS ({len(th_keys)} features)")
    else:
        print(f"\n  FAIL — THRESHOLDS keys: {th_keys}")
        print(f"         WEIGHTS    keys: {wt_keys}")

    print("\n  Scorer validation complete.")
    print("=" * 64 + "\n")
