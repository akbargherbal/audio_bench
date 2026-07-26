# tests/test_reporter.py
import pytest
from reporter import (
    _get_flag_label,
    _fmt,
    _fmt_delta,
    _fmt_delta_with_unit,
    generate_report,
    generate_ceiling_report,
    generate_style_compare_report,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "feature, delta, expected_fragment",
    [
        ("lufs", -1.0, "quieter"),
        ("lufs", +1.0, "louder"),
        ("low_mid_energy", +0.1, "muddiness"),
        ("low_mid_energy", -0.1, "thin"),
        ("stereo_width", -0.1, "narrower"),
        ("stereo_width", +0.1, "wider"),
        ("spectral_centroid", -100.0, "darker"),
        ("spectral_centroid", +100.0, "brighter"),
        ("mfcc_distance", +0.1, "timbre"),
        ("crest_factor_db", -1.0, "compressed"),
        ("crest_factor_db", +1.0, "transient"),
        ("presence_band", -0.1, "reduced"),
        ("presence_band", +0.1, "elevated"),
        ("high_shelf", +0.1, "harshness"),
        ("high_shelf", -0.1, "duller"),
        ("zcr", +0.1, "noise"),
        ("zcr", -0.1, "smoother"),
        ("rms", -0.1, "quieter"),
        ("rms", +0.1, "louder"),
        ("spectral_rolloff", -100.0, "reduced"),
        ("spectral_rolloff", +100.0, "more high-frequency"),
        ("tempo", 10.0, "drift"),  # generic fallback path
        ("phantom_feature", +1.0, "above"),  # unknown feature fallback
    ],
)
def test_get_flag_label(feature, delta, expected_fragment):
    label = _get_flag_label(feature, delta)
    assert expected_fragment.lower() in label.lower()


@pytest.mark.unit
def test_fmt_lufs_two_decimal_places():
    assert _fmt("lufs", -14.5) == "-14.50"


@pytest.mark.unit
def test_fmt_hz_one_decimal():
    assert _fmt("spectral_centroid", 2500.34) == "2500.3"


@pytest.mark.unit
def test_fmt_delta_positive_has_plus_sign():
    assert _fmt_delta("lufs", 1.5).startswith("+")


@pytest.mark.unit
def test_fmt_delta_negative_has_minus_sign():
    assert _fmt_delta("lufs", -1.5).startswith("-")


@pytest.mark.unit
def test_fmt_delta_zero_has_plus_sign():
    assert _fmt_delta("lufs", 0.0).startswith("+")


@pytest.mark.unit
def test_fmt_delta_with_unit_strips_empty_unit():
    assert _fmt_delta_with_unit("rms", 0.1) == "+0.100000"


@pytest.mark.unit
def test_fmt_delta_with_unit_appends_hz():
    assert _fmt_delta_with_unit("spectral_centroid", 50.0) == "+50.0 Hz"


@pytest.mark.unit
def test_generate_report_returns_string(zero_analysis, perfect_score):
    report = generate_report("chunk.wav", zero_analysis, perfect_score)
    assert isinstance(report, str)


@pytest.mark.unit
def test_generate_report_contains_chunk_name(zero_analysis, perfect_score):
    report = generate_report("TEST_CHUNK_XYZ.wav", zero_analysis, perfect_score)
    assert "TEST_CHUNK_XYZ.wav" in report


@pytest.mark.unit
def test_generate_report_contains_score(zero_analysis, perfect_score):
    report = generate_report("chunk.wav", zero_analysis, perfect_score)
    assert "100/100" in report or "100.0/100" in report


@pytest.mark.unit
def test_generate_report_has_feature_comparison_section(zero_analysis, perfect_score):
    report = generate_report("chunk.wav", zero_analysis, perfect_score)
    assert "## Feature Comparison" in report


@pytest.mark.unit
def test_generate_report_has_mfcc_detail_section(zero_analysis, perfect_score):
    report = generate_report("chunk.wav", zero_analysis, perfect_score)
    assert "## MFCC Detail" in report


@pytest.mark.unit
def test_generate_report_has_flagged_deviations_section(zero_analysis, perfect_score):
    report = generate_report("chunk.wav", zero_analysis, perfect_score)
    assert "## Flagged Deviations" in report


@pytest.mark.unit
def test_generate_report_has_diagnostic_summary_section(zero_analysis, perfect_score):
    report = generate_report("chunk.wav", zero_analysis, perfect_score)
    assert "## Diagnostic Summary" in report


@pytest.mark.unit
def test_generate_report_no_flags_shows_pass_text(zero_analysis, perfect_score):
    report = generate_report("chunk.wav", zero_analysis, perfect_score)
    assert "No deviations flagged" in report


@pytest.mark.unit
def test_generate_report_flagged_feature_shown(make_analysis_fn, make_score_fn):
    from config import THRESHOLDS, WEIGHTS

    analysis = make_analysis_fn({"lufs": THRESHOLDS["lufs"] * 2.0})
    scored_features = {}
    for feat, thresh in THRESHOLDS.items():
        is_lufs = feat == "lufs"
        scored_features[feat] = {
            "delta": analysis["deltas"][feat],
            "threshold": thresh,
            "weight": WEIGHTS[feat],
            "raw_penalty": 1.0 if is_lufs else 0.0,
            "capped_penalty": 1.0 if is_lufs else 0.0,
            "weighted_penalty": WEIGHTS[feat] if is_lufs else 0.0,
            "flagged": is_lufs,
            "disabled": thresh <= 0.0,
        }
    score = make_score_fn(
        {
            "consistency_score": 90.0,
            "flagged_features": ["lufs"],
            "scored_features": scored_features,
        }
    )
    report = generate_report("chunk.wav", analysis, score)
    assert "LUFS" in report
    assert (
        "Chunk is louder than reference" in report
        or "Chunk is quieter than reference" in report
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "score_val, expected",
    [
        (100.0, "PASS"),
        (85.0, "PASS"),
        (84.0, "REVIEW"),
        (65.0, "REVIEW"),
        (64.0, "CAUTION"),
        (50.0, "CAUTION"),
        (49.0, "FAIL"),
        (0.0, "FAIL"),
    ],
)
def test_verdict_band(score_val, expected, zero_analysis, make_score_fn):
    score = make_score_fn({"consistency_score": score_val})
    report = generate_report("test_chunk.wav", zero_analysis, score)
    assert expected in report


@pytest.mark.unit
def test_generate_ceiling_report_returns_string():
    from config import CEILING_THRESHOLDS

    chunk_feats = {k: 0.0 for k in CEILING_THRESHOLDS}
    chunk_feats["mfcc"] = [0.0] * 13
    ceiling_feats = {k: 0.0 for k in CEILING_THRESHOLDS}
    ceiling_feats["mfcc"] = [0.0] * 13
    deltas = {k: 0.0 for k in CEILING_THRESHOLDS}
    deltas["mfcc_distance"] = 0.0

    report = generate_ceiling_report(
        "chunk.wav",
        "ceiling.mp3",
        chunk_feats,
        ceiling_feats,
        deltas,
        [],
        CEILING_THRESHOLDS,
    )
    assert isinstance(report, str)
    assert "Ceiling Analysis" in report


@pytest.mark.unit
def test_generate_ceiling_report_contains_no_violations_text_when_clean():
    from config import CEILING_THRESHOLDS

    chunk_feats = {k: 0.0 for k in CEILING_THRESHOLDS}
    chunk_feats["mfcc"] = [0.0] * 13
    ceiling_feats = {k: 0.0 for k in CEILING_THRESHOLDS}
    ceiling_feats["mfcc"] = [0.0] * 13
    deltas = {k: 0.0 for k in CEILING_THRESHOLDS}
    deltas["mfcc_distance"] = 0.0

    report = generate_ceiling_report(
        "chunk.wav",
        "ceiling.mp3",
        chunk_feats,
        ceiling_feats,
        deltas,
        [],
        CEILING_THRESHOLDS,
    )
    assert "No red flags raised" in report


@pytest.mark.unit
def test_generate_ceiling_report_contains_flag_name_when_flagged():
    from config import CEILING_THRESHOLDS

    chunk_feats = {k: 0.0 for k in CEILING_THRESHOLDS}
    chunk_feats["mfcc"] = [0.0] * 13
    ceiling_feats = {k: 0.0 for k in CEILING_THRESHOLDS}
    ceiling_feats["mfcc"] = [0.0] * 13
    deltas = {k: 0.0 for k in CEILING_THRESHOLDS}
    deltas["lufs"] = 10.0
    deltas["mfcc_distance"] = 0.0

    report = generate_ceiling_report(
        "chunk.wav",
        "ceiling.mp3",
        chunk_feats,
        ceiling_feats,
        deltas,
        ["lufs"],
        CEILING_THRESHOLDS,
    )
    assert "LUFS" in report


@pytest.mark.unit
def test_generate_style_compare_report_returns_string():
    chunk_feats = {
        "lufs": -14.0,
        "rms": 0.1,
        "crest_factor_db": 10.0,
        "spectral_centroid": 1500.0,
        "spectral_rolloff": 3000.0,
        "low_mid_energy": 0.2,
        "presence_band": 0.3,
        "high_shelf": 0.05,
        "stereo_width": 0.1,
        "mfcc": [0.0] * 13,
    }
    style_feats = {
        "lufs": -14.0,
        "rms": 0.1,
        "crest_factor_db": 10.0,
        "spectral_centroid": 1500.0,
        "spectral_rolloff": 3000.0,
        "low_mid_energy": 0.2,
        "presence_band": 0.3,
        "high_shelf": 0.05,
        "stereo_width": 0.1,
        "mfcc": [0.0] * 13,
    }
    deltas = {
        "lufs": 0.0,
        "rms": 0.0,
        "crest_factor_db": 0.0,
        "spectral_centroid": 0.0,
        "spectral_rolloff": 0.0,
        "low_mid_energy": 0.0,
        "presence_band": 0.0,
        "high_shelf": 0.0,
        "stereo_width": 0.0,
        "mfcc_distance": 0.0,
    }

    report = generate_style_compare_report(
        "chunk.wav", "style.mp3", chunk_feats, style_feats, deltas
    )
    assert isinstance(report, str)
    assert "Style Gap Briefing" in report


@pytest.mark.unit
def test_generate_style_report_no_score_or_verdict():
    chunk_feats = {
        "lufs": -14.0,
        "rms": 0.1,
        "crest_factor_db": 10.0,
        "spectral_centroid": 1500.0,
        "spectral_rolloff": 3000.0,
        "low_mid_energy": 0.2,
        "presence_band": 0.3,
        "high_shelf": 0.05,
        "stereo_width": 0.1,
        "mfcc": [0.0] * 13,
    }
    style_feats = {
        "lufs": -14.0,
        "rms": 0.1,
        "crest_factor_db": 10.0,
        "spectral_centroid": 1500.0,
        "spectral_rolloff": 3000.0,
        "low_mid_energy": 0.2,
        "presence_band": 0.3,
        "high_shelf": 0.05,
        "stereo_width": 0.1,
        "mfcc": [0.0] * 13,
    }
    deltas = {
        "lufs": 0.0,
        "rms": 0.0,
        "crest_factor_db": 0.0,
        "spectral_centroid": 0.0,
        "spectral_rolloff": 0.0,
        "low_mid_energy": 0.0,
        "presence_band": 0.0,
        "high_shelf": 0.0,
        "stereo_width": 0.0,
        "mfcc_distance": 0.0,
    }

    report = generate_style_compare_report(
        "chunk.wav", "style.mp3", chunk_feats, style_feats, deltas
    )
    assert "Consistency Score" not in report
    assert "PASS" not in report


@pytest.mark.unit
def test_generate_style_report_has_all_required_sections():
    chunk_feats = {
        "lufs": -14.0,
        "rms": 0.1,
        "crest_factor_db": 10.0,
        "spectral_centroid": 1500.0,
        "spectral_rolloff": 3000.0,
        "low_mid_energy": 0.2,
        "presence_band": 0.3,
        "high_shelf": 0.05,
        "stereo_width": 0.1,
        "mfcc": [0.0] * 13,
    }
    style_feats = {
        "lufs": -14.0,
        "rms": 0.1,
        "crest_factor_db": 10.0,
        "spectral_centroid": 1500.0,
        "spectral_rolloff": 3000.0,
        "low_mid_energy": 0.2,
        "presence_band": 0.3,
        "high_shelf": 0.05,
        "stereo_width": 0.1,
        "mfcc": [0.0] * 13,
    }
    deltas = {
        "lufs": 0.0,
        "rms": 0.0,
        "crest_factor_db": 0.0,
        "spectral_centroid": 0.0,
        "spectral_rolloff": 0.0,
        "low_mid_energy": 0.0,
        "presence_band": 0.0,
        "high_shelf": 0.0,
        "stereo_width": 0.0,
        "mfcc_distance": 0.0,
    }

    report = generate_style_compare_report(
        "chunk.wav", "style.mp3", chunk_feats, style_feats, deltas
    )
    assert "## Feature Comparison" in report
    assert "## Perceptual Notes" in report
    assert "## Style Gap Briefing Block" in report


@pytest.mark.unit
def test_generate_style_report_direction_arrows():
    chunk_feats = {
        "lufs": -12.0,
        "rms": 0.1,
        "crest_factor_db": 10.0,
        "spectral_centroid": 1500.0,
        "spectral_rolloff": 3000.0,
        "low_mid_energy": 0.2,
        "presence_band": 0.3,
        "high_shelf": 0.05,
        "stereo_width": 0.1,
        "mfcc": [0.0] * 13,
    }
    style_feats = {
        "lufs": -14.0,
        "rms": 0.1,
        "crest_factor_db": 10.0,
        "spectral_centroid": 1500.0,
        "spectral_rolloff": 3000.0,
        "low_mid_energy": 0.2,
        "presence_band": 0.3,
        "high_shelf": 0.05,
        "stereo_width": 0.1,
        "mfcc": [0.0] * 13,
    }
    deltas = {
        "lufs": 2.0,
        "rms": 0.0,
        "crest_factor_db": 0.0,
        "spectral_centroid": 0.0,
        "spectral_rolloff": 0.0,
        "low_mid_energy": 0.0,
        "presence_band": 0.0,
        "high_shelf": 0.0,
        "stereo_width": 0.0,
        "mfcc_distance": 0.0,
    }

    report = generate_style_compare_report(
        "chunk.wav", "style.mp3", chunk_feats, style_feats, deltas
    )
    assert "↑ Suno higher" in report
