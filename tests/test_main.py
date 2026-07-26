# tests/test_main.py
import pytest
import sys
import os
import json
import shutil
from main import (
    _build_qa_record,
    _build_ceiling_record,
    _build_style_record,
    _load_or_build_reference,
    run_single,
    run_ceiling,
    run_style_compare,
    run_batch,
    main as main_func,
)
from extractor import TARGET_SR


@pytest.mark.unit
def test_build_qa_record_has_required_keys(zero_analysis, perfect_score):
    record = _build_qa_record("chunk.wav", "ref.mp3", zero_analysis, perfect_score)
    for key in (
        "mode",
        "chunk_name",
        "reference_name",
        "consistency_score",
        "flagged_count",
        "flagged_features",
        "features",
        "mfcc",
    ):
        assert key in record
    assert record["mode"] == "qa"


@pytest.mark.unit
def test_build_ceiling_record_mode_is_ceiling():
    record = _build_ceiling_record("chunk.wav", "ceiling.mp3", {}, {}, {}, [])
    assert record["mode"] == "ceiling"


@pytest.mark.unit
def test_build_style_record_mode_is_style_compare():
    record = _build_style_record("chunk.wav", "style.mp3", {}, {}, {})
    assert record["mode"] == "style_compare"


@pytest.mark.integration
def test_cache_hit_skips_rebuild(mono_sine_wav, tmp_path, monkeypatch):
    """A valid cache with matching source and TARGET_SR must not trigger rebuild."""
    cache_file = tmp_path / "reference_profile.json"
    fake_profile = {
        "_source": os.path.abspath(mono_sine_wav),
        "_sr": TARGET_SR,
        "lufs": -14.0,
        "rms": 0.05,
        "crest_factor_db": 3.0,
        "spectral_centroid": 1000.0,
        "spectral_rolloff": 2000.0,
        "low_mid_energy": 0.1,
        "presence_band": 0.2,
        "high_shelf": 0.02,
        "stereo_width": 0.0,
        "tempo": 120.0,
        "zcr": 0.05,
        "mfcc": [0.0] * 13,
    }

    # Write fake cache to disk
    cache_file.write_text(json.dumps(fake_profile))

    # Patch the cache filepath inside main.py
    import main as main_mod

    monkeypatch.setattr(main_mod, "_PROFILE_CACHE", str(cache_file))

    build_called = False

    def mock_build(filepath, save_path=None):
        nonlocal build_called
        build_called = True
        return fake_profile

    monkeypatch.setattr("main.build_reference_profile", mock_build)

    profile = _load_or_build_reference(mono_sine_wav)
    assert build_called is False
    assert profile["_source"] == os.path.abspath(mono_sine_wav)


@pytest.mark.integration
def test_cache_miss_on_sr_mismatch(mono_sine_wav, tmp_path, monkeypatch):
    """If cached SR != TARGET_SR, profile must be rebuilt."""
    cache_file = tmp_path / "reference_profile.json"
    stale_profile = {
        "_source": os.path.abspath(mono_sine_wav),
        "_sr": 22050,  # Wrong SR
        "lufs": -14.0,
        "mfcc": [0.0] * 13,
    }
    cache_file.write_text(json.dumps(stale_profile))

    import main as main_mod

    monkeypatch.setattr(main_mod, "_PROFILE_CACHE", str(cache_file))

    build_called = False

    def mock_build(filepath, save_path=None):
        nonlocal build_called
        build_called = True
        return {
            "_source": os.path.abspath(mono_sine_wav),
            "_sr": TARGET_SR,
            "lufs": -14.0,
            "mfcc": [0.0] * 13,
        }

    monkeypatch.setattr("main.build_reference_profile", mock_build)

    profile = _load_or_build_reference(mono_sine_wav)
    assert build_called is True
    assert profile["_sr"] == TARGET_SR


@pytest.mark.unit
def test_mutual_exclusion_reference_and_ceiling(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--reference",
            "ref.mp3",
            "--ceiling",
            "ceiling.mp3",
            "--chunk",
            "chunk.mp3",
        ],
    )
    with pytest.raises(SystemExit):
        main_func()


@pytest.mark.unit
def test_no_mode_flag_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py"])
    with pytest.raises(SystemExit):
        main_func()


@pytest.mark.unit
def test_stems_with_batch_exits(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["main.py", "--reference", "ref.mp3", "--batch", ".", "--stems"]
    )
    with pytest.raises(SystemExit):
        main_func()


@pytest.mark.slow
def test_run_single_returns_report_and_score(mono_sine_wav, tmp_path, monkeypatch):
    import main as main_mod

    cache_file = tmp_path / "reference_profile.json"
    monkeypatch.setattr(main_mod, "_PROFILE_CACHE", str(cache_file))

    report, score = run_single(
        reference_path=mono_sine_wav,
        chunk_path=mono_sine_wav,
    )
    assert isinstance(report, str)
    assert score == 100.0


@pytest.mark.slow
def test_run_single_stop_condition_score_below_50(
    mono_sine_wav, tmp_path, monkeypatch, capsys
):
    """
    Phase 3 plan stop condition: if score < 50, warning prints to stderr.
    """
    from config import THRESHOLDS, WEIGHTS
    import main as main_mod

    cache_file = tmp_path / "reference_profile.json"
    monkeypatch.setattr(main_mod, "_PROFILE_CACHE", str(cache_file))

    # Construct a valid, fully-populated scored_features mapping
    # to prevent KeyErrors in generate_report() table builder
    mocked_scored_features = {
        key: {
            "delta": 0.0,
            "threshold": THRESHOLDS[key],
            "weight": WEIGHTS[key],
            "raw_penalty": 0.0,
            "capped_penalty": 0.0,
            "weighted_penalty": 0.0,
            "flagged": key == "lufs",
            "disabled": THRESHOLDS[key] <= 0.0,
        }
        for key in THRESHOLDS
    }

    monkeypatch.setattr(
        "main.score_chunk",
        lambda *a, **kw: {
            "consistency_score": 0.0,
            "flagged_features": ["lufs"],
            "scored_features": mocked_scored_features,
            "total_weighted_penalty": 20.0,
            "total_weight": 10.0,
        },
    )

    report, score = run_single(mono_sine_wav, mono_sine_wav)
    assert score < 50.0


@pytest.mark.slow
def test_run_ceiling_end_to_end(mono_sine_wav, tmp_path):
    """Verify ceiling analysis workflow execution."""
    save_path = tmp_path / "ceiling_results.json"
    report = run_ceiling(mono_sine_wav, mono_sine_wav, save_json_path=str(save_path))
    assert isinstance(report, str)
    assert "Ceiling Analysis" in report
    assert os.path.exists(save_path)
    with open(save_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["mode"] == "ceiling"


@pytest.mark.slow
def test_run_style_compare_end_to_end(mono_sine_wav, tmp_path):
    """Verify style gap comparison workflow execution."""
    save_path = tmp_path / "style_results.json"
    report = run_style_compare(
        mono_sine_wav, mono_sine_wav, save_json_path=str(save_path)
    )
    assert isinstance(report, str)
    assert "Style Gap" in report
    assert os.path.exists(save_path)
    with open(save_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["mode"] == "style_compare"


@pytest.mark.slow
def test_run_batch_end_to_end(mono_sine_wav, tmp_path, monkeypatch):
    """Verify batch processing mode and directory search logic."""
    import main as main_mod

    cache_file = tmp_path / "reference_profile.json"
    monkeypatch.setattr(main_mod, "_PROFILE_CACHE", str(cache_file))

    batch_dir = tmp_path / "batch_wavs"
    batch_dir.mkdir()
    shutil.copy(mono_sine_wav, batch_dir / "chunk_a.wav")

    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(main_mod, "_REPORTS_DIR", str(reports_dir))

    save_path = reports_dir / "batch_results.json"
    run_batch(mono_sine_wav, str(batch_dir), save_json_path=str(save_path))

    assert os.path.exists(reports_dir / "summary.md")
    assert os.path.exists(reports_dir / "chunk_a_report.md")
    assert os.path.exists(save_path)
    with open(save_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["mode"] == "qa_batch"


@pytest.mark.slow
def test_main_cli_scenarios(mono_sine_wav, tmp_path, monkeypatch):
    """Exercise standard single-file and batch execution flows using main()'s CLI argument parser."""
    import main as main_mod

    cache_file = tmp_path / "reference_profile.json"
    monkeypatch.setattr(main_mod, "_PROFILE_CACHE", str(cache_file))

    # Single QA
    monkeypatch.setattr(
        sys, "argv", ["main.py", "--reference", mono_sine_wav, "--chunk", mono_sine_wav]
    )
    main_func()

    # Ceiling Mode
    monkeypatch.setattr(
        sys, "argv", ["main.py", "--ceiling", mono_sine_wav, "--chunk", mono_sine_wav]
    )
    main_func()

    # Style Gap Mode
    monkeypatch.setattr(
        sys,
        "argv",
        ["main.py", "--style-compare", mono_sine_wav, "--chunk", mono_sine_wav],
    )
    main_func()
