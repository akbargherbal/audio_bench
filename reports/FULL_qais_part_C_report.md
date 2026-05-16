# Audio QA Report — FULL_qais_part_C.wav

| | |
|---|---|
| **Consistency Score** | **78.1/100** |
| **Verdict** | REVIEW — minor deviations present |

## Feature Comparison

| Feature                     | Unit | Reference |    Chunk |     Delta | Flag |
| --------------------------- | ---- | --------- | -------- | --------- | --- |
| LUFS                        | LUFS |    -14.21 |   -15.50 |     -1.28 | ✓ |
| RMS energy                  |      |  0.133861 | 0.113678 | -0.020183 | ✓ |
| Dynamic range               | dB   |     12.66 |    13.29 |     +0.63 | ✓ |
| Spectral centroid           | Hz   |    3606.9 |   4640.1 |   +1033.2 | ⚠ |
| Spectral rolloff            | Hz   |    8469.4 |  10886.8 |   +2417.4 | ⚠ |
| Low-mid energy (200–500 Hz) | frac |  0.169654 | 0.157764 | -0.011890 | ✓ |
| Presence band (1k–4kHz)     | frac |  0.095893 | 0.085645 | -0.010248 | ✓ |
| High shelf (8kHz+)          | frac |  0.017991 | 0.027268 | +0.009277 | ✓ |
| Stereo width                |      |  0.085218 | 0.076810 | -0.008408 | ✓ |
| Tempo                       | BPM  |     165.4 |    165.4 |      +0.0 | ✓ |
| Zero crossing rate          |      |  0.059701 | 0.074188 | +0.014488 | ✓ |
| MFCC distance               |      |    0.0000 |   7.9660 |   +7.9660 | ⚠ |

## MFCC Detail (13 Coefficients)

| Coeff | Reference  | Chunk      | Delta      | Role         |
| :---: | ---------: | ---------: | ---------: | :----------- |
| 01    |  -180.3466 |  -180.1799 |    +0.1667 | energy       |
| 02    |   111.8133 |    94.6284 |   -17.1849 | tonal char   |
| 03    |   -19.1641 |    -2.5939 |   +16.5702 | tonal char   |
| 04    |    57.3860 |    50.2523 |    -7.1337 | mid timbre   |
| 05    |    -3.9297 |     0.0435 |    +3.9731 | mid timbre   |
| 06    |    41.8138 |    39.5822 |    -2.2316 | mid timbre   |
| 07    |   -23.0524 |   -23.9095 |    -0.8571 | mid timbre   |
| 08    |    15.6671 |    24.6761 |    +9.0090 | fine texture |
| 09    |     3.9542 |    -4.3445 |    -8.2987 | fine texture |
| 10    |    -4.5757 |     9.8932 |   +14.4689 | fine texture |
| 11    |    -1.7582 |   -10.2135 |    -8.4553 | fine texture |
| 12    |     4.8644 |    15.6678 |   +10.8034 | fine texture |
| 13    |     4.1602 |    -0.2449 |    -4.4051 | fine texture |

## Flagged Deviations

- **Spectral centroid** `+1033.2 Hz` — Mix brighter than reference — possible harshness
- **Spectral rolloff** `+2417.4 Hz` — Spectral rolloff higher — more high-frequency content than reference
- **MFCC distance** `+7.9660` — Timbre fingerprint mismatch — overall tonal character differs

## Diagnostic Summary

> *Paste the block below directly into an LLM prompt.*

```
DIAGNOSTIC SUMMARY — FULL_qais_part_C.wav
Consistency Score: 78.1/100
Flagged issues:
  - Mix brighter than reference — possible harshness  (delta: +1033.2 Hz)
  - Spectral rolloff higher — more high-frequency content than reference  (delta: +2417.4 Hz)
  - Timbre fingerprint mismatch — overall tonal character differs  (delta: +7.9660)

Subjective note from user: [paste what you hear here]
```
