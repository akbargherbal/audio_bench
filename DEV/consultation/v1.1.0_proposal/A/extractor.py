"""
extractor.py — Phase 1: Feature Extraction
Audio QA — Classical Arabic Poem → Suno AI → Audacity Pipeline

Task 1.1 — extract_features(filepath) -> dict
Task 1.2 — __main__ validation block

Extracts all 12 features from a single WAV or MP3 file.
No comparison logic, no scoring, no reporting — extraction only.

REVISION NOTE (Phase 1 finding):
  Band energies (low_mid_energy, presence_band, high_shelf) are expressed
  as a fraction of total spectral power in [0, 1]. Raw FFT power scales with
  signal length squared, making absolute values incomparable across chunks of
  different duration. Fractional energy is length-independent, scale-independent,
  and aligns with the ±0.10 / ±0.05 thresholds defined in config.py.
"""

import warnings
import numpy as np
import librosa
import soundfile as sf
import pyloudnorm as pyln

warnings.filterwarnings("ignore")  # suppress librosa / numba routine noise


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _band_energy_fraction(
    y_mono: np.ndarray, sr: int, f_low: float, f_high: float
) -> float:
    """
    Fraction of total spectral power in the frequency band [f_low, f_high) Hz.

    Returns a value in [0, 1]:
        0.0 = no energy at all in this band
        1.0 = all energy concentrated in this band (degenerate case)

    Using fractional energy rather than absolute power makes the metric:
      - Independent of signal length (FFT magnitude scales with N)
      - Independent of overall loudness (already captured by LUFS/RMS)
      - Directly interpretable: "X% of the mix energy lives in this band"
      - Comparable across chunks of different duration

    Returns 0.0 if no FFT bins fall in the band or total power is zero.
    """
    fft = np.fft.rfft(y_mono)
    magnitudes_sq = np.abs(fft) ** 2

    total_power = float(np.sum(magnitudes_sq))
    if total_power == 0.0:
        return 0.0

    freqs = np.fft.rfftfreq(len(y_mono), d=1.0 / sr)
    mask = (freqs >= f_low) & (freqs < f_high)
    if not np.any(mask):
        return 0.0

    band_power = float(np.sum(magnitudes_sq[mask]))
    return band_power / total_power


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_features(filepath: str) -> dict:
    """
    Load one audio file (WAV or MP3) and return a flat dict of all 12 features.

    Keys returned:
        lufs              float  — integrated loudness in LUFS (negative)
        rms               float  — mean RMS energy
        dynamic_range     float  — crest factor in dB (peak / RMS)
        spectral_centroid float  — brightness in Hz
        spectral_rolloff  float  — high-frequency rolloff in Hz
        low_mid_energy    float  — fraction of total power in 200–500 Hz  [0,1]
        presence_band     float  — fraction of total power in 1k–4kHz     [0,1]
        high_shelf        float  — fraction of total power above 8kHz     [0,1]
        stereo_width      float  — mean absolute L-R difference (0.0 if mono)
        tempo             float  — estimated BPM (unreliable on poetry)
        mfcc              list   — 13 floats, mean MFCC coefficients across time
        zcr               float  — mean zero-crossing rate

    Does NOT raise on implausible tempo — logs and continues.
    DOES raise on pyloudnorm errors (file too short, bad sample rate).
    """

    # ------------------------------------------------------------------
    # Load — librosa float32, shape (2, N) stereo or (N,) mono
    # sr=None preserves the file's native sample rate
    # ------------------------------------------------------------------
    y, sr = librosa.load(filepath, mono=False, sr=None)

    is_stereo = y.ndim == 2
    if is_stereo:
        y_mono = librosa.to_mono(y)
        L, R = y[0], y[1]
        mid = (L + R) / 2.0
        side = (L - R) / 2.0
        stereo_width = float(
            np.sqrt(np.mean(side**2)) / (np.sqrt(np.mean(mid**2)) + 1e-9)
        )
    else:
        y_mono = y
        stereo_width = 0.0
        print(
            f"  [INFO] {filepath} is mono — stereo_width fixed at 0.0 (known limitation)"
        )

    # ------------------------------------------------------------------
    # LUFS — pyloudnorm requires float64, shape (N,) or (N, 2)
    # soundfile delivers both natively; loaded separately for LUFS only
    # ------------------------------------------------------------------
    sf_data, sf_rate = sf.read(filepath, always_2d=True)
    meter = pyln.Meter(sf_rate)
    lufs = float(meter.integrated_loudness(sf_data))

    # ------------------------------------------------------------------
    # RMS energy
    # ------------------------------------------------------------------
    rms = float(librosa.feature.rms(y=y_mono).mean())

    # ------------------------------------------------------------------
    # Dynamic range — crest factor in dB (peak / RMS)
    # ------------------------------------------------------------------
    peak = float(np.max(np.abs(y_mono)))
    rms_raw = float(np.sqrt(np.mean(y_mono**2)))
    if rms_raw > 0.0:
        dynamic_range = float(20.0 * np.log10(peak / rms_raw))
    else:
        dynamic_range = 0.0
        print("  [WARN] RMS is zero — dynamic_range set to 0.0. Check input file.")

    # ------------------------------------------------------------------
    # Spectral centroid and rolloff
    # ------------------------------------------------------------------
    spectral_centroid = float(librosa.feature.spectral_centroid(y=y_mono, sr=sr).mean())
    spectral_rolloff = float(librosa.feature.spectral_rolloff(y=y_mono, sr=sr).mean())

    # ------------------------------------------------------------------
    # Band energies — fraction of total spectral power [0, 1]
    # Nyquist = sr / 2; high_shelf upper bound capped there
    # ------------------------------------------------------------------
    low_mid_energy = _band_energy_fraction(y_mono, sr, 200.0, 500.0)
    presence_band = _band_energy_fraction(y_mono, sr, 1000.0, 4000.0)
    high_shelf = _band_energy_fraction(y_mono, sr, 8000.0, sr / 2.0)

    # ------------------------------------------------------------------
    # Tempo — unreliable on non-rhythmic Arabic poetry; log, never error
    # ------------------------------------------------------------------
    try:
        tempo = float(librosa.beat.tempo(y=y_mono, sr=sr)[0])
    except Exception as exc:
        tempo = 0.0
        print(f"  [WARN] Tempo estimation failed ({exc}) — tempo set to 0.0")

    # ------------------------------------------------------------------
    # MFCCs — 13 coefficients, mean across time frames
    # ------------------------------------------------------------------
    mfcc_matrix = librosa.feature.mfcc(y=y_mono, sr=sr, n_mfcc=13)
    mfcc_list = [float(v) for v in mfcc_matrix.mean(axis=1)]

    # ------------------------------------------------------------------
    # Zero crossing rate
    # ------------------------------------------------------------------
    zcr = float(librosa.feature.zero_crossing_rate(y_mono).mean())

    return {
        "lufs": lufs,
        "rms": rms,
        "dynamic_range": dynamic_range,
        "spectral_centroid": spectral_centroid,
        "spectral_rolloff": spectral_rolloff,
        "low_mid_energy": low_mid_energy,
        "presence_band": presence_band,
        "high_shelf": high_shelf,
        "stereo_width": stereo_width,
        "tempo": tempo,
        "mfcc": mfcc_list,
        "zcr": zcr,
    }


# ---------------------------------------------------------------------------
# Task 1.2 — Manual validation print block
# Run: python extractor.py ./data/audio/REF_01.mp3
# ---------------------------------------------------------------------------

_MFCC_LABELS = [
    "energy",  # 01
    "tonal char",  # 02
    "tonal char",  # 03
    "mid timbre",  # 04
    "mid timbre",  # 05
    "mid timbre",  # 06
    "mid timbre",  # 07
    "fine texture",  # 08
    "fine texture",  # 09
    "fine texture",  # 10
    "fine texture",  # 11
    "fine texture",  # 12
    "fine texture",  # 13
]

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extractor.py <audio_file.mp3|.wav>")
        sys.exit(1)

    fp = sys.argv[1]
    print(f"\n{'='*64}")
    print(f"  AUDIO-QA — Feature Extraction Validation")
    print(f"  File: {fp}")
    print(f"{'='*64}\n")

    feats = extract_features(fp)
    mfccs = feats.pop("mfcc")

    scalar_order = [
        "lufs",
        "rms",
        "dynamic_range",
        "spectral_centroid",
        "spectral_rolloff",
        "low_mid_energy",
        "presence_band",
        "high_shelf",
        "stereo_width",
        "tempo",
        "zcr",
    ]
    notes = {
        "lufs": "LUFS (must be negative)",
        "rms": "",
        "dynamic_range": "dB",
        "spectral_centroid": "Hz",
        "spectral_rolloff": "Hz",
        "low_mid_energy": "fraction of total power [0-1]",
        "presence_band": "fraction of total power [0-1]",
        "high_shelf": "fraction of total power [0-1]",
        "stereo_width": "0.0 = mono",
        "tempo": "BPM (unreliable on poetry)",
        "zcr": "",
    }

    print(f"  {'Feature':<22} {'Value':>14}   Note")
    print(f"  {'-'*22}   {'-'*14}   {'-'*30}")
    for key in scalar_order:
        print(f"  {key:<22} {feats[key]:>14.6f}   {notes[key]}")

    print(f"\n  mfcc  (13 coefficients)")
    print(f"  {'Coeff':<8} {'Value':>12}   Role")
    print(f"  {'-'*8}   {'-'*12}   {'-'*14}")
    for i, (v, label) in enumerate(zip(mfccs, _MFCC_LABELS), start=1):
        print(f"  [{i:02d}]    {v:>12.4f}   <- {label}")

    print(f"\n{'='*64}")
    print("  Validation checks:")
    ok_lufs = feats["lufs"] < 0
    ok_bands = all(
        0.0 <= feats[k] <= 1.0
        for k in ("low_mid_energy", "presence_band", "high_shelf")
    )
    ok_mfcc = len(mfccs) == 13
    ok_width = feats["stereo_width"] > 0

    print(f"  LUFS is negative float        : {'OK' if ok_lufs  else 'FAIL'}")
    print(
        f"  Band energies in [0, 1]       : {'OK' if ok_bands else 'FAIL -- normalization broken'}"
    )
    print(
        f"  MFCC count == 13              : {'OK' if ok_mfcc  else f'FAIL -- got {len(mfccs)}'}"
    )
    print(
        f"  Stereo width > 0              : {'OK' if ok_width else '-- mono file (width=0.0 expected)'}"
    )
    print(f"  Tempo (raw, may drift)        : {feats['tempo']:.1f} BPM")

    all_ok = ok_lufs and ok_bands and ok_mfcc
    print(
        f"\n  {'VALIDATED -- proceed to Phase 2' if all_ok else 'FAILED -- do not proceed'}"
    )
    print(f"{'='*64}\n")
