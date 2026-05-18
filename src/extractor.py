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
# BUG-TQ-04 fix — pin all loads to a single sample rate so that MFCC
# filterbanks and FFT frequency resolution are directly comparable across
# all files in a project.  If you change this value, delete
# reference_profile.json first — the cache records the rate used.
# ---------------------------------------------------------------------------
TARGET_SR: int = 44100


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


def _band_absolute_power(
    y_mono: np.ndarray, sr: int, f_low: float, f_high: float
) -> float:
    """
    Absolute spectral power (sum of squared FFT magnitudes) in [f_low, f_high) Hz.

    Unlike _band_energy_fraction(), this does NOT normalise by total power.
    This is intentional: VAR (Vocal-to-Accompaniment Ratio) requires absolute
    power so that a quiet vocal and a loud instrumental produce a ratio that
    reflects the true acoustic balance, not a normalised fraction of each
    stem's own energy.

    Used exclusively for VAR computation in extract_vocal_stem_features().
    Do NOT use for the mix-level band metrics (low_mid_energy, presence_band,
    high_shelf) — those correctly use _band_energy_fraction().

    Returns 0.0 if no FFT bins fall in the band (degenerate / silent input).
    """
    fft = np.fft.rfft(y_mono)
    magnitudes_sq = np.abs(fft) ** 2

    freqs = np.fft.rfftfreq(len(y_mono), d=1.0 / sr)
    mask = (freqs >= f_low) & (freqs < f_high)
    if not np.any(mask):
        return 0.0

    return float(np.sum(magnitudes_sq[mask]))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_features(filepath: str) -> dict:
    """
    Load one audio file (WAV or MP3) and return a flat dict of all 12 features.

    Keys returned:
        lufs              float  — integrated loudness in LUFS (negative)
        rms               float  — global waveform RMS energy
        crest_factor_db   float  — crest factor in dB (20·log10(peak/RMS))
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
    y, sr = librosa.load(filepath, mono=False, sr=TARGET_SR)  # TQ-04: pinned

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
    # RMS energy — global waveform RMS (BUG-TQ-02 fix)
    # Was: librosa.feature.rms().mean() — frame-based, quiet frames
    #       weighted equally regardless of amplitude.
    # Now: np.sqrt(np.mean(y**2)) — each sample weighted by amplitude
    #       squared; standard signal RMS definition.
    # The same value is reused for crest factor below (BUG-TQ-02 fix —
    # previously a second, separate rms_raw was computed for that purpose).
    # ------------------------------------------------------------------
    rms = float(np.sqrt(np.mean(y_mono**2)))

    # ------------------------------------------------------------------
    # Crest factor in dB — peak / RMS  (BUG-TQ-01 fix: was misnamed
    # "dynamic_range"; crest factor and dynamic range are different metrics)
    # ------------------------------------------------------------------
    peak = float(np.max(np.abs(y_mono)))
    if rms > 0.0:
        crest_factor_db = float(20.0 * np.log10(peak / rms))
    else:
        crest_factor_db = 0.0
        print("  [WARN] RMS is zero — crest_factor_db set to 0.0. Check input file.")

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
        "crest_factor_db": crest_factor_db,
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


def extract_vocal_stem_features(vocal_filepath: str, inst_filepath: str) -> dict:
    """
    Extract 5 vocal-stem-specific metrics from a separated vocal stem and its
    corresponding instrumental stem.

    This function is called ONLY when --stems is active (single-chunk mode).
    It is completely separate from extract_features() and must never be merged
    into it. Results are passed directly to reporter.py as a standalone
    stem_data dict — they never enter scorer.py or profiler.py.

    Args:
        vocal_filepath: Path to the UVR5-separated vocal stem WAV.
        inst_filepath:  Path to the UVR5-separated instrumental stem WAV.

    Returns a flat dict with these keys:
        hnr                      float  — Harmonics-to-Noise Ratio in dB (via parselmouth)
        var_db                   float  — Vocal-to-Accompaniment Ratio in dB (presence band)
                                          Positive = vocal louder; negative = instrumental louder.
        pitch_confidence_voiced  float  — Mean voiced_prob restricted to voiced frames only.
                                          Low value = genuine pitch ambiguity during phonation.
        pitch_stability_f0_var   float  — Variance of F0 (Hz) across voiced frames only.
                                          High value = melodic drift or unstable pitch.
        spectral_flatness_vocal  float  — Mean spectral flatness of the vocal stem [0, 1].
                                          0 = tonal (pure tone); 1 = noise-like.

    WATCH POINTS (from EXPERTS_SYNTHESIS.md):
        - HNR: unreliable if BS-Roformer bleed is present on dense low-mid content.
          Always cross-reference with var_db. If var_db is negative at the same
          moment HNR drops, the HNR reading is likely a bleed artefact.
        - pitch_confidence_voiced and pitch_stability_f0_var: both are masked to
          voiced frames (voiced_flag == True) to avoid falsely penalising Arabic
          consonants (ع, ح, خ, ق) which are correctly unvoiced.
        - var_db uses _band_absolute_power() (not _band_energy_fraction()) so that
          acoustic balance is preserved across stems of differing loudness.
    """
    import parselmouth  # guarded import — only needed for --stems runs

    VAR_F_LOW = 1000.0   # presence band: 1 kHz
    VAR_F_HIGH = 4000.0  # presence band: 4 kHz

    # ------------------------------------------------------------------
    # Load both stems
    # ------------------------------------------------------------------
    y_voc, sr_voc = librosa.load(vocal_filepath, mono=True, sr=TARGET_SR)  # TQ-04
    y_inst, sr_inst = librosa.load(inst_filepath, mono=True, sr=TARGET_SR)  # TQ-04

    # ------------------------------------------------------------------
    # HNR — Harmonics-to-Noise Ratio via parselmouth (Praat engine)
    # parselmouth requires a WAV; UVR5 outputs WAV by default.
    # HNR is computed on the vocal stem only.
    # ------------------------------------------------------------------
    snd = parselmouth.Sound(vocal_filepath)
    harmonicity = snd.to_harmonicity()
    hnr_values = harmonicity.values[harmonicity.values != -200.0]  # -200 = unvoiced sentinel
    hnr = float(np.mean(hnr_values)) if len(hnr_values) > 0 else 0.0

    # ------------------------------------------------------------------
    # VAR — Vocal-to-Accompaniment Ratio in dB (presence band 1k–4kHz)
    # Uses absolute power (not fractional) so acoustic balance is preserved.
    # ------------------------------------------------------------------
    voc_abs = _band_absolute_power(y_voc, sr_voc, VAR_F_LOW, VAR_F_HIGH)
    inst_abs = _band_absolute_power(y_inst, sr_inst, VAR_F_LOW, VAR_F_HIGH)

    if voc_abs > 0.0 and inst_abs > 0.0:
        var_db = float(10.0 * np.log10(voc_abs / inst_abs))
    elif voc_abs > 0.0:
        var_db = float("inf")   # vocal only — degenerate case
    elif inst_abs > 0.0:
        var_db = float("-inf")  # instrumental only — degenerate case
    else:
        var_db = 0.0            # both silent

    # ------------------------------------------------------------------
    # Pitch tracking — librosa.pyin on vocal stem
    # Returns: f0 (Hz, NaN when unvoiced), voiced_flag (bool), voiced_prob [0,1]
    # Both pitch statistics are masked to voiced frames to avoid penalising
    # correctly-unvoiced Arabic consonants.
    # ------------------------------------------------------------------
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y_voc,
        sr=sr_voc,
        fmin=librosa.note_to_hz("C2"),   # ~65 Hz — covers bass-baritone range
        fmax=librosa.note_to_hz("C6"),   # ~1047 Hz — ceiling for this voice type
    )

    voiced_mask = voiced_flag.astype(bool)

    # Pitch confidence: mean voiced_prob restricted to voiced frames only
    if np.any(voiced_mask):
        pitch_confidence_voiced = float(np.mean(voiced_prob[voiced_mask]))
    else:
        pitch_confidence_voiced = 0.0

    # Pitch stability: variance of F0 across voiced frames only
    voiced_f0 = f0[voiced_mask]
    voiced_f0_clean = voiced_f0[~np.isnan(voiced_f0)]
    if len(voiced_f0_clean) > 1:
        pitch_stability_f0_var = float(np.var(voiced_f0_clean))
    else:
        pitch_stability_f0_var = 0.0

    # ------------------------------------------------------------------
    # Spectral flatness — vocal stem
    # Values near 0 = tonal / harmonic; near 1 = noise-like / breathy
    # ------------------------------------------------------------------
    spectral_flatness_vocal = float(
        librosa.feature.spectral_flatness(y=y_voc).mean()
    )

    return {
        "hnr": hnr,
        "var_db": var_db,
        "pitch_confidence_voiced": pitch_confidence_voiced,
        "pitch_stability_f0_var": pitch_stability_f0_var,
        "spectral_flatness_vocal": spectral_flatness_vocal,
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
        "crest_factor_db",
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
        "rms": "global waveform RMS",
        "crest_factor_db": "dB  (20·log10(peak/RMS))",
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
