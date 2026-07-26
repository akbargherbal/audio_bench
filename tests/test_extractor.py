# tests/test_extractor.py
import pytest
import numpy as np
import importlib.util
import subprocess
import sys
import os
from extractor import _band_energy_fraction, _band_absolute_power, TARGET_SR


@pytest.mark.unit
class TestBandEnergyFraction:
    def test_returns_zero_for_silent_signal(self):
        y = np.zeros(44100)
        result = _band_energy_fraction(y, 44100, 200.0, 500.0)
        assert result == 0.0

    def test_returns_zero_when_no_bins_in_range(self):
        # 1 Hz sine wave, band is 200-500 Hz -> almost zero energy in band
        t = np.arange(44100) / 44100.0
        y = np.sin(2 * np.pi * 1.0 * t)
        result = _band_energy_fraction(y, 44100, 200.0, 500.0)
        assert result == 0.0 or result < 1e-5

    def test_returns_zero_no_bins_out_of_bounds(self):
        # No bins in high out-of-bounds band (above Nyquist)
        y = np.ones(100)
        result = _band_energy_fraction(y, 1000, 10000.0, 20000.0)
        assert result == 0.0

    def test_pure_tone_in_band_has_high_fraction(self):
        # 440 Hz is within the 200-500 Hz band
        t = np.arange(44100) / 44100.0
        y = np.sin(2 * np.pi * 440.0 * t)
        result = _band_energy_fraction(y, 44100, 200.0, 500.0)
        assert result > 0.9

    def test_pure_tone_outside_band_has_low_fraction(self):
        # 10,000 Hz is far outside the 200-500 Hz band
        t = np.arange(44100) / 44100.0
        y = np.sin(2 * np.pi * 10000.0 * t)
        result = _band_energy_fraction(y, 44100, 200.0, 500.0)
        assert result < 0.05

    def test_result_is_in_zero_to_one(self):
        y = np.random.randn(44100).astype(np.float32)
        result = _band_energy_fraction(y, 44100, 200.0, 500.0)
        assert 0.0 <= result <= 1.0


@pytest.mark.unit
class TestBandAbsolutePower:
    def test_returns_zero_for_silent_signal(self):
        y = np.zeros(44100)
        assert _band_absolute_power(y, 44100, 200.0, 500.0) == 0.0

    def test_returns_zero_no_bins_out_of_bounds(self):
        # No bins in high out-of-bounds band
        y = np.ones(100)
        result = _band_absolute_power(y, 1000, 10000.0, 20000.0)
        assert result == 0.0

    def test_positive_value_for_signal_in_band(self):
        t = np.arange(44100) / 44100.0
        y = np.sin(2 * np.pi * 440.0 * t)
        result = _band_absolute_power(y, 44100, 200.0, 500.0)
        assert result > 0.0

    def test_not_normalised(self):
        # Double the amplitude -> absolute power should increase, unlike the fraction
        t = np.arange(44100) / 44100.0
        y = np.sin(2 * np.pi * 440.0 * t)
        p1 = _band_absolute_power(y, 44100, 200.0, 500.0)
        p2 = _band_absolute_power(y * 2.0, 44100, 200.0, 500.0)
        assert p2 > p1


@pytest.mark.integration
class TestExtractFeatures:
    def test_returns_all_12_keys(self, mono_sine_wav):
        from extractor import extract_features

        feats = extract_features(mono_sine_wav)
        required = {
            "lufs",
            "rms",
            "crest_factor_db",
            "spectral_centroid",
            "spectral_rolloff",
            "low_mid_energy",
            "presence_band",
            "high_shelf",
            "stereo_width",
            "tempo",
            "mfcc",
            "zcr",
        }
        assert required.issubset(set(feats.keys()))

    def test_lufs_is_negative(self, mono_sine_wav):
        from extractor import extract_features

        feats = extract_features(mono_sine_wav)
        assert feats["lufs"] < 0.0

    def test_band_energies_in_unit_interval(self, mono_sine_wav):
        from extractor import extract_features

        feats = extract_features(mono_sine_wav)
        for key in ("low_mid_energy", "presence_band", "high_shelf"):
            assert 0.0 <= feats[key] <= 1.0, f"{key} is out of bounds: {feats[key]}"

    def test_mfcc_has_13_coefficients(self, mono_sine_wav):
        from extractor import extract_features

        feats = extract_features(mono_sine_wav)
        assert len(feats["mfcc"]) == 13

    def test_mono_stereo_width_is_zero(self, mono_sine_wav):
        from extractor import extract_features

        feats = extract_features(mono_sine_wav)
        assert feats["stereo_width"] == 0.0

    def test_stereo_stereo_width_is_positive(self, stereo_sine_wav):
        from extractor import extract_features

        feats = extract_features(stereo_sine_wav)
        assert feats["stereo_width"] > 0.0

    def test_rms_is_positive_for_sine(self, mono_sine_wav):
        from extractor import extract_features

        feats = extract_features(mono_sine_wav)
        assert feats["rms"] > 0.0

    def test_crest_factor_db_is_non_negative(self, mono_sine_wav):
        from extractor import extract_features

        feats = extract_features(mono_sine_wav)
        assert feats["crest_factor_db"] >= 0.0

    def test_determinism_same_file_same_result(self, mono_sine_wav):
        from extractor import extract_features

        f1 = extract_features(mono_sine_wav)
        f2 = extract_features(mono_sine_wav)
        for key in ("lufs", "rms", "spectral_centroid", "zcr"):
            assert f1[key] == f2[key]

    # --- BUG-TQ-02 regression: RMS must be global waveform RMS ---
    def test_rms_is_global_waveform_rms(self, mono_sine_wav):
        import librosa
        from extractor import extract_features

        y, sr = librosa.load(mono_sine_wav, mono=True, sr=TARGET_SR)
        expected_rms = float(np.sqrt(np.mean(y**2)))
        feats = extract_features(mono_sine_wav)
        assert abs(feats["rms"] - expected_rms) < 1e-5

    # --- BUG-TQ-01 regression: crest_factor_db must be peak/RMS in dB ---
    def test_crest_factor_db_formula(self, mono_sine_wav):
        import librosa
        from extractor import extract_features

        y, sr = librosa.load(mono_sine_wav, mono=True, sr=TARGET_SR)
        rms = float(np.sqrt(np.mean(y**2)))
        peak = float(np.max(np.abs(y)))
        expected_cf = 20.0 * np.log10(peak / rms)
        feats = extract_features(mono_sine_wav)
        assert abs(feats["crest_factor_db"] - expected_cf) < 1e-2

    # --- BUG-TQ-04 regression: sample rate must be pinned ---
    def test_target_sr_constant(self):
        assert TARGET_SR == 44100

    # --- Silent file edge case ---
    def test_silent_file_crest_factor_is_zero(self, silent_wav):
        from extractor import extract_features

        feats = extract_features(silent_wav)
        assert feats["crest_factor_db"] == 0.0

    # --- Tempo estimation fail path monkeypatch ---
    def test_extract_features_tempo_exception(self, monkeypatch, mono_sine_wav):
        from extractor import extract_features
        import librosa.beat

        def mock_tempo(*args, **kwargs):
            raise RuntimeError("Injected tempo failure")

        monkeypatch.setattr(librosa.beat, "tempo", mock_tempo)

        feats = extract_features(mono_sine_wav)
        assert feats["tempo"] == 0.0


@pytest.mark.skipif(
    importlib.util.find_spec("parselmouth") is None,
    reason="parselmouth is not installed",
)
@pytest.mark.integration
def test_extract_vocal_stem_features_runs_without_crashing(mono_sine_wav):
    from extractor import extract_vocal_stem_features

    feats = extract_vocal_stem_features(mono_sine_wav, mono_sine_wav)
    required = {
        "hnr",
        "var_db",
        "pitch_confidence_voiced",
        "pitch_stability_f0_var",
        "spectral_flatness_vocal",
    }
    assert required.issubset(set(feats.keys()))


@pytest.mark.skipif(
    importlib.util.find_spec("parselmouth") is None,
    reason="parselmouth is not installed",
)
@pytest.mark.integration
def test_extract_vocal_stem_features_degenerate_cases(mono_sine_wav, silent_wav):
    from extractor import extract_vocal_stem_features

    # Case 1: Vocal active, Instrumental silent
    res1 = extract_vocal_stem_features(mono_sine_wav, silent_wav)
    assert res1["var_db"] == float("inf")

    # Case 2: Vocal silent, Instrumental active
    res2 = extract_vocal_stem_features(silent_wav, mono_sine_wav)
    assert res2["var_db"] == float("-inf")

    # Case 3: Both silent (covers no voiced frames, pitch stability else path)
    res3 = extract_vocal_stem_features(silent_wav, silent_wav)
    assert res3["var_db"] == 0.0
    assert res3["pitch_confidence_voiced"] == 0.0
    assert res3["pitch_stability_f0_var"] == 0.0


@pytest.mark.integration
def test_extractor_main_execution(mono_sine_wav):
    """Run extractor.py as a script to verify main print diagnostics and cover lines 373-452."""
    extractor_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "extractor.py"
    )
    result = subprocess.run(
        [sys.executable, extractor_path, mono_sine_wav],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "AUDIO-QA — Feature Extraction Validation" in result.stdout
    assert "VALIDATED -- proceed to Phase 2" in result.stdout
