# tests/test_scorer.py
import pytest
import sys
import os
import subprocess
from scorer import score_chunk
from config import THRESHOLDS, WEIGHTS


@pytest.mark.unit
def test_zero_delta_scores_100(zero_analysis):
    score = score_chunk(zero_analysis, THRESHOLDS, WEIGHTS)
    assert score["consistency_score"] == 100.0


@pytest.mark.unit
def test_score_is_float(zero_analysis):
    score = score_chunk(zero_analysis, THRESHOLDS, WEIGHTS)
    assert isinstance(score["consistency_score"], float)


@pytest.mark.unit
def test_score_range_is_0_to_100(make_analysis_fn):
    huge_deltas = {k: 10000.0 for k in THRESHOLDS}
    huge_deltas["mfcc_deltas"] = [10000.0] * 13
    analysis = make_analysis_fn(huge_deltas)
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)
    assert 0.0 <= score["consistency_score"] <= 100.0
    assert score["consistency_score"] == 0.0


@pytest.mark.unit
def test_three_times_threshold_scores_0(make_analysis_fn):
    # delta = 3 * threshold -> raw penalty = 2.0 -> capped to 2.0
    three_x_deltas = {}
    for feat, thresh in THRESHOLDS.items():
        if thresh > 0.0:
            three_x_deltas[feat] = thresh * 3.0
    three_x_analysis = make_analysis_fn(three_x_deltas)
    score = score_chunk(three_x_analysis, THRESHOLDS, WEIGHTS)
    assert score["consistency_score"] == 0.0


@pytest.mark.unit
def test_max_penalty_all_active_features_flagged(make_analysis_fn):
    three_x_deltas = {}
    for feat, thresh in THRESHOLDS.items():
        if thresh > 0.0:
            three_x_deltas[feat] = thresh * 3.0
    three_x_analysis = make_analysis_fn(three_x_deltas)
    score = score_chunk(three_x_analysis, THRESHOLDS, WEIGHTS)
    active_feats = [f for f in THRESHOLDS if THRESHOLDS[f] > 0.0]
    assert set(score["flagged_features"]) == set(active_feats)


@pytest.mark.unit
def test_score_decreases_as_delta_increases(make_analysis_fn):
    thresh = THRESHOLDS["lufs"]

    analysis1 = make_analysis_fn({"lufs": thresh * 1.5})
    score1 = score_chunk(analysis1, THRESHOLDS, WEIGHTS)["consistency_score"]

    analysis2 = make_analysis_fn({"lufs": thresh * 2.0})
    score2 = score_chunk(analysis2, THRESHOLDS, WEIGHTS)["consistency_score"]

    assert score2 < score1


@pytest.mark.unit
def test_at_exactly_threshold_no_penalty(make_analysis_fn):
    # Boundary is inclusive - penalty starts strictly ABOVE threshold
    analysis = make_analysis_fn({"lufs": THRESHOLDS["lufs"]})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)

    lufs_details = score["scored_features"]["lufs"]
    assert lufs_details["raw_penalty"] == 0.0
    assert lufs_details["flagged"] is False
    assert "lufs" not in score["flagged_features"]


@pytest.mark.unit
def test_just_above_threshold_small_penalty(make_analysis_fn):
    delta_val = THRESHOLDS["lufs"] * 1.01
    analysis = make_analysis_fn({"lufs": delta_val})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)

    lufs_details = score["scored_features"]["lufs"]
    assert lufs_details["raw_penalty"] > 0.0
    assert lufs_details["raw_penalty"] < 0.1
    assert lufs_details["flagged"] is True
    assert "lufs" in score["flagged_features"]


@pytest.mark.unit
def test_capped_penalty_at_two_times(make_analysis_fn):
    analysis = make_analysis_fn({"lufs": THRESHOLDS["lufs"] * 10.0})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)

    lufs_details = score["scored_features"]["lufs"]
    assert lufs_details["capped_penalty"] == 2.0


@pytest.mark.unit
def test_capped_penalty_not_exceeded(make_analysis_fn):
    analysis = make_analysis_fn({"lufs": THRESHOLDS["lufs"] * 1000.0})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)

    lufs_details = score["scored_features"]["lufs"]
    assert lufs_details["capped_penalty"] == 2.0


@pytest.mark.unit
def test_disabled_threshold_no_zero_division(make_analysis_fn):
    # BUG-TQ-05: threshold of 0.0 must not raise ZeroDivisionError
    analysis = make_analysis_fn({"stereo_width": 0.5})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)
    assert score["consistency_score"] == 100.0


@pytest.mark.unit
def test_disabled_feature_never_flagged(make_analysis_fn):
    analysis = make_analysis_fn({"stereo_width": 5.0})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)
    assert "stereo_width" not in score["flagged_features"]
    assert score["scored_features"]["stereo_width"]["flagged"] is False


@pytest.mark.unit
def test_disabled_feature_marked_in_scored_features(make_analysis_fn):
    analysis = make_analysis_fn({"stereo_width": 1.0})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)
    assert score["scored_features"]["stereo_width"]["disabled"] is True


@pytest.mark.unit
def test_disabled_feature_excluded_from_total_weight(zero_analysis):
    score = score_chunk(zero_analysis, THRESHOLDS, WEIGHTS)
    expected_weight = sum(WEIGHTS[f] for f in THRESHOLDS if THRESHOLDS[f] > 0.0)
    assert score["total_weight"] == expected_weight


@pytest.mark.unit
def test_zero_weight_feature_does_not_affect_score(make_analysis_fn):
    # tempo weight is 0.0
    analysis = make_analysis_fn({"tempo": 500.0})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)
    assert score["consistency_score"] == 100.0


@pytest.mark.unit
def test_no_flags_when_all_within_threshold(zero_analysis):
    score = score_chunk(zero_analysis, THRESHOLDS, WEIGHTS)
    assert score["flagged_features"] == []


@pytest.mark.unit
def test_single_feature_flagged_correctly(make_analysis_fn):
    analysis = make_analysis_fn({"lufs": THRESHOLDS["lufs"] * 1.5})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)
    assert score["flagged_features"] == ["lufs"]


@pytest.mark.unit
def test_flagged_features_list_is_subset_of_all_features(make_analysis_fn):
    analysis = make_analysis_fn({"lufs": 5.0, "rms": 0.2, "presence_band": -0.4})
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)
    assert set(score["flagged_features"]).issubset(set(THRESHOLDS.keys()))


@pytest.mark.unit
def test_mfcc_distance_is_scored_not_mfcc_deltas(zero_analysis):
    score = score_chunk(zero_analysis, THRESHOLDS, WEIGHTS)
    assert "mfcc_distance" in score["scored_features"]
    assert "mfcc_deltas" not in score["scored_features"]


@pytest.mark.unit
def test_total_weight_zero_returns_100(zero_analysis):
    zero_thresholds = {k: 0.0 for k in THRESHOLDS}
    zero_weights = {k: 0.0 for k in WEIGHTS}
    score = score_chunk(zero_analysis, zero_thresholds, zero_weights)
    assert score["consistency_score"] == 100.0


@pytest.mark.unit
def test_scorer_main_execution():
    """Execute the __main__ testing logic inside scorer.py to guarantee 100% coverage."""
    scorer_path = os.path.join(os.path.dirname(__file__), "..", "src", "scorer.py")
    result = subprocess.run(
        [sys.executable, scorer_path], capture_output=True, text=True, check=True
    )
    assert "AUDIO-QA — Phase 3 Scorer Validation" in result.stdout
    assert "Scorer validation complete" in result.stdout
