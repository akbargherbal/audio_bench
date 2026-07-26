# tests/conftest.py
import sys
import os

# Insert src directory into path so tests can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import numpy as np
import pytest
import tempfile

try:
    import soundfile as sf
except ImportError:
    sf = None

TARGET_SR = 44100

@pytest.fixture(scope="session")
def tmp_audio_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d

@pytest.fixture(scope="session")
def mono_sine_wav(tmp_audio_dir):
    """3-second 440 Hz sine wave, mono, float32. Minimal valid audio."""
    sr = TARGET_SR
    t = np.linspace(0, 3.0, int(sr * 3.0), endpoint=False)
    y = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    path = os.path.join(tmp_audio_dir, "mono_sine.wav")
    if sf is not None:
        sf.write(path, y, sr)
    return path

@pytest.fixture(scope="session")
def stereo_sine_wav(tmp_audio_dir):
    """3-second 440 Hz sine wave, stereo (L/R differ slightly for width > 0)."""
    sr = TARGET_SR
    t = np.linspace(0, 3.0, int(sr * 3.0), endpoint=False)
    L = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    R = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    y = np.stack([L, R], axis=-1)
    path = os.path.join(tmp_audio_dir, "stereo_sine.wav")
    if sf is not None:
        sf.write(path, y, sr)
    return path

@pytest.fixture(scope="session")
def silent_wav(tmp_audio_dir):
    """2-second silence — edge case for RMS=0 and crest_factor_db=0."""
    sr = TARGET_SR
    y = np.zeros(int(sr * 2.0), dtype=np.float32)
    path = os.path.join(tmp_audio_dir, "silent.wav")
    if sf is not None:
        sf.write(path, y, sr)
    return path

SCALAR_KEYS = [
    "lufs", "rms", "crest_factor_db", "spectral_centroid", "spectral_rolloff",
    "low_mid_energy", "presence_band", "high_shelf", "stereo_width", "tempo", "zcr",
]

def make_analysis(delta_overrides: dict = None) -> dict:
    """
    Return a minimal analysis dict with zero deltas for all features.
    Override specific deltas via delta_overrides, e.g.:
        make_analysis({"lufs": -5.0, "mfcc_distance": 0.15})
    """
    deltas = {k: 0.0 for k in SCALAR_KEYS}
    deltas["mfcc_distance"] = 0.0
    deltas["mfcc_deltas"] = [0.0] * 13
    if delta_overrides:
        deltas.update(delta_overrides)

    ref_vals = {k: 0.0 for k in SCALAR_KEYS}
    ref_vals["mfcc"] = [0.0] * 13
    chunk_vals = {k: ref_vals[k] + deltas.get(k, 0.0) for k in SCALAR_KEYS}
    chunk_vals["mfcc"] = [d + r for d, r in zip(deltas.get("mfcc_deltas", [0.0]*13), ref_vals["mfcc"])]

    return {
        "chunk_path": "fake_chunk.wav",
        "chunk_values": chunk_vals,
        "reference_values": ref_vals,
        "deltas": deltas,
    }

@pytest.fixture
def zero_analysis():
    return make_analysis()

@pytest.fixture
def make_analysis_fn():
    return make_analysis

def make_score(score_overrides: dict = None) -> dict:
    """Minimal score dict matching scorer.score_chunk() output."""
    from config import THRESHOLDS, WEIGHTS
    scored_features = {}
    for feat, thresh in THRESHOLDS.items():
        scored_features[feat] = {
            "delta": 0.0,
            "threshold": thresh,
            "weight": WEIGHTS[feat],
            "raw_penalty": 0.0,
            "capped_penalty": 0.0,
            "weighted_penalty": 0.0,
            "flagged": False,
            "disabled": thresh <= 0.0,
        }
    base = {
        "consistency_score": 100.0,
        "flagged_features": [],
        "scored_features": scored_features,
        "total_weighted_penalty": 0.0,
        "total_weight": sum(w for f, w in WEIGHTS.items() if THRESHOLDS[f] > 0.0),
    }
    if score_overrides:
        base.update(score_overrides)
    return base

@pytest.fixture
def perfect_score():
    return make_score()

@pytest.fixture
def make_score_fn():
    return make_score