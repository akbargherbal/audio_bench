Here are the technical evaluations of the four specific mechanisms in your pipeline.

---

### 1. Spectral Rolloff Percentile (0.85)

## Answer

A `roll_percent` of 0.85 is **inappropriate** for measuring high-frequency content in vocal-dominant Arabic music. Because vocal energy is heavily concentrated in the fundamental frequency and lower formants (typically below 2–3 kHz), the 85th percentile of spectral energy is reached very early in the spectrum.

Rather than being sensitive to high-frequency noise, 0.85 is actually _blind_ to it. It acts as a tracker of the lower-mid energy balance. If your goal is to measure the upper boundary of the spectrum (e.g., "air," sibilance, or high-frequency harshness), 0.85 will completely miss it.

## Supporting Facts

- Librosa's `spectral_rolloff` defaults to 0.85.
- Human vocals and traditional acoustic instruments exhibit a steep spectral tilt (roughly $1/f$ energy distribution).
- 85% of the total spectral energy in such signals is almost entirely dictated by the fundamental (F0) and the first two formants (F1, F2).

## Confidence

High — Follows directly from the spectral tilt of human speech/vocals and the mathematical definition of the spectral rolloff threshold.

## Key Nuances

If you increase the percentile to 0.95 or 0.99 to accurately capture the high-frequency boundary, the metric _will_ become highly sensitive to low-energy high-frequency noise (like tape hiss or breath). You must choose: track the formants (0.85) or track the noise/air floor (0.95+).

## Implementation Note

```python
# To capture actual high-frequency rolloff:
spectral_rolloff = float(librosa.feature.spectral_rolloff(y=y_mono, sr=sr, roll_percent=0.95).mean())
```

---

### 2. Global FFT vs. STFT for Band Energy

## Answer

A global `rfft` on the full signal **does not** accurately represent the spectral shape of the content across chunks of differing durations. It heavily distorts the comparison.

Because the FFT integrates over the entire duration, a chunk with a longer silent intro (or more pauses between vocal phrases) will accumulate more noise floor energy, diluting the fractional energy of the active bands. Furthermore, a full-signal FFT assumes signal stationarity. Music and vocals are highly non-stationary; a global FFT smears transient broadband energy (like consonants or percussion) across the entire time domain, masking the actual spectral balance of the active audio.

## Supporting Facts

- `_band_energy_fraction` uses `np.fft.rfft` on the full `y_mono` array.
- The audio is non-stationary (vocals/music).
- Fractional energy normalizes for total power, but it does not normalize for the _temporal distribution_ of active vs. inactive time.

## Confidence

High — Follows directly from the Fourier transform's integration over time and the fundamental non-stationarity of audio signals.

## Key Nuances

If chunks are perfectly time-aligned and have identical active-to-inactive ratios, the global FFT fraction might be comparable. For arbitrary chunks, it fails silently, producing plausible but mathematically misleading fractions.

## Implementation Note

```python
# Hardened alternative: STFT-based active frame averaging
S = np.abs(librosa.stft(y_mono))**2
# Optional: gate out frames below an RMS threshold here
total_power_per_frame = S.sum(axis=0)
# Compute band power per frame, then average the fractions
```

---

### 3. MFCC Distance Normalization

## Answer

The mean-absolute-distance formula is **fundamentally flawed** as implemented. It is entirely dominated by the first coefficient (C0), meaning your "timbre distance" is effectively just a redundant loudness/gain difference metric.

C0 represents the overall log-energy of the frame. As shown in your report, C0 has a vastly larger magnitude (e.g., -180) compared to higher-order coefficients (e.g., ±5). Because the formula `mean(abs(chunk - ref))` applies no variance standardization or weighting, a simple volume difference between the chunk and the reference will cause a massive spike in `mfcc_distance`, even if the actual timbral fingerprint (C1–C12) is identical.

## Supporting Facts

- `mfcc_distance` is computed as `np.mean(np.abs(chunk_mfccs - ref_mfccs))`.
- The provided report shows C01 is ~ -180 while C13 is ~ 4.
- No standardization, z-scoring, or coefficient dropping is applied before the mean.
- `mfcc.mean(axis=1)` is used, which already destroys all temporal dynamics (a separate but critical failure mode for sequence comparison).

## Confidence

High — Follows directly from the provided code, the report's numerical evidence, and the mathematical definition of unweighted Mean Absolute Error on unscaled vectors.

## Key Nuances

Even if C0 is dropped, C1 (spectral tilt) typically has a much larger variance than C12. Proper timbral distance requires Mahalanobis distance, cosine distance, or at least variance standardization across the dataset.

## Implementation Note

```python
# Drop C0 (energy) and compute Cosine Distance for scale-invariant timbre comparison
from scipy.spatial.distance import cosine
# chunk_mfccs and ref_mfccs should be slices [1:]
timbre_distance = cosine(chunk_mfccs[1:], ref_mfccs[1:])
```

---

### 4. Stereo Width via Amplitude Difference

## Answer

`mean(abs(L - R))` **does not** meaningfully capture spatial consistency. It conflates spatial width with overall signal amplitude.

This formula effectively measures the absolute energy of the Side channel. If a chunk is simply mastered louder than the reference, `abs(L - R)` will increase, falsely implying a wider stereo image. A loud, narrowly panned element will yield the exact same value as a quiet, hard-panned element. A true spatial width metric must be amplitude-normalized.

## Supporting Facts

- The code computes `np.mean(np.abs(L - R))`.
- This is an absolute amplitude difference, not normalized by the Mid channel `(L + R)` or the total RMS energy.

## Confidence

High — Follows directly from the mathematical definition of the implemented metric and the principles of Mid/Side spatial processing.

## Key Nuances

This metric will correctly identify a purely mono file (value = 0.0), but for any stereo file, the delta between chunk and reference is hopelessly polluted by their relative LUFS/RMS differences.

## Implementation Note

```python
# Hardened alternative: Side-to-Mid energy ratio (amplitude normalized)
mid = (L + R) / 2.0
side = (L - R) / 2.0
# Add epsilon to avoid division by zero
stereo_width = float(np.sqrt(np.mean(side**2)) / (np.sqrt(np.mean(mid**2)) + 1e-9))
```
