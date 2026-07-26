# tests/test_config.py
import pytest
import os
from config import THRESHOLDS, WEIGHTS, CEILING_THRESHOLDS


@pytest.mark.unit
def test_thresholds_and_weights_have_same_keys():
    assert set(THRESHOLDS) == set(WEIGHTS)


@pytest.mark.unit
def test_all_thresholds_are_non_negative():
    for feat, thresh in THRESHOLDS.items():
        assert thresh >= 0.0, f"Threshold for {feat} is negative: {thresh}"


@pytest.mark.unit
def test_all_weights_are_non_negative():
    for feat, weight in WEIGHTS.items():
        assert weight >= 0.0, f"Weight for {feat} is negative: {weight}"


@pytest.mark.unit
def test_stereo_width_threshold_is_zero():
    assert THRESHOLDS["stereo_width"] == 0.0


@pytest.mark.unit
def test_tempo_weight_is_zero():
    assert WEIGHTS["tempo"] == 0.0


@pytest.mark.unit
def test_tempo_threshold_is_large():
    assert THRESHOLDS["tempo"] >= 999.0


@pytest.mark.unit
def test_mfcc_distance_threshold_is_sane():
    # Cosine distance range is [0, 2], so the threshold must be within this range
    assert 0.0 < THRESHOLDS["mfcc_distance"] <= 2.0


@pytest.mark.unit
def test_ceiling_thresholds_is_non_empty_dict():
    assert isinstance(CEILING_THRESHOLDS, dict)
    assert len(CEILING_THRESHOLDS) > 0


@pytest.mark.unit
def test_ceiling_thresholds_all_positive():
    for feat, thresh in CEILING_THRESHOLDS.items():
        assert (
            thresh > 0.0
        ), f"Ceiling threshold for {feat} must be positive, got {thresh}"


@pytest.mark.unit
def test_ceiling_excludes_stereo_width():
    assert "stereo_width" not in CEILING_THRESHOLDS


@pytest.mark.unit
def test_ceiling_excludes_tempo():
    assert "tempo" not in CEILING_THRESHOLDS


@pytest.mark.unit
def test_ceiling_excludes_high_shelf():
    assert "high_shelf" not in CEILING_THRESHOLDS


@pytest.mark.unit
def test_integrity_check_fires_on_extra_threshold_key():
    bad_thresholds = {**THRESHOLDS, "phantom_feature": 1.0}
    missing = set(bad_thresholds) - set(WEIGHTS)
    assert missing == {"phantom_feature"}


@pytest.mark.unit
def test_integrity_check_fires_on_extra_weight_key():
    bad_weights = {**WEIGHTS, "phantom_feature": 1.0}
    missing = set(bad_weights) - set(THRESHOLDS)
    assert missing == {"phantom_feature"}


@pytest.mark.unit
def test_integrity_check_fires_on_mismatched_keys():
    """
    Directly execute config.py with in-memory modifications to trigger
    the ValueError branches (lines 115 and 120 of config.py).
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "src", "config.py")
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Mismatch Scenario 1: Key in THRESHOLDS but missing in WEIGHTS
    modified_content_1 = content.replace(
        "THRESHOLDS: dict[str, float] = {",
        'THRESHOLDS: dict[str, float] = {\n    "phantom_feature": 1.0,',
    )
    with pytest.raises(ValueError) as excinfo:
        exec(modified_content_1, {})
    assert "keys in THRESHOLDS but missing from WEIGHTS" in str(excinfo.value)

    # Mismatch Scenario 2: Key in WEIGHTS but missing in THRESHOLDS
    modified_content_2 = content.replace(
        "WEIGHTS: dict[str, float] = {",
        'WEIGHTS: dict[str, float] = {\n    "phantom_feature": 1.0,',
    )
    with pytest.raises(ValueError) as excinfo:
        exec(modified_content_2, {})
    assert "keys in WEIGHTS but missing from THRESHOLDS" in str(excinfo.value)
