# Audio QA Report — FULL_qais_part_C.wav

| | |
|---|---|
| **Consistency Score** | **76.5/100** |
| **Verdict** | REVIEW — minor deviations present |

## Feature Comparison

| Feature                     | Unit | Reference |    Chunk |     Delta | Flag |
| --------------------------- | ---- | --------- | -------- | --------- | --- |
| LUFS                        | LUFS |    -14.21 |   -15.50 |     -1.29 | ✓ |
| RMS energy                  |      |  0.133887 | 0.113678 | -0.020209 | ✓ |
| Dynamic range               | dB   |     12.70 |    13.29 |     +0.59 | ✓ |
| Spectral centroid           | Hz   |    3578.4 |   4640.1 |   +1061.7 | ⚠ |
| Spectral rolloff            | Hz   |    8433.8 |  10886.8 |   +2453.0 | ⚠ |
| Low-mid energy (200–500 Hz) | frac |  0.169636 | 0.157764 | -0.011872 | ✓ |
| Presence band (1k–4kHz)     | frac |  0.095966 | 0.085645 | -0.010320 | ✓ |
| High shelf (8kHz+)          | frac |  0.018186 | 0.027268 | +0.009082 | ✓ |
| Stereo width                |      |  0.085289 | 0.076810 | -0.008479 | ✓ |
| Tempo                       | BPM  |     112.5 |    165.4 |     +52.9 | ✓ |
| Zero crossing rate          |      |  0.059882 | 0.074188 | +0.014307 | ✓ |
| MFCC distance               |      |    0.0000 |   8.3931 |   +8.3931 | ⚠ |

## MFCC Detail (13 Coefficients)

| Coeff | Reference  | Chunk      | Delta      | Role         |
| :---: | ---------: | ---------: | ---------: | :----------- |
| 01    |  -180.6576 |  -180.1799 |    +0.4777 | energy       |
| 02    |   112.6220 |    94.6284 |   -17.9936 | tonal char   |
| 03    |   -19.8035 |    -2.5939 |   +17.2096 | tonal char   |
| 04    |    58.0204 |    50.2523 |    -7.7681 | mid timbre   |
| 05    |    -4.6828 |     0.0435 |    +4.7262 | mid timbre   |
| 06    |    42.3066 |    39.5822 |    -2.7244 | mid timbre   |
| 07    |   -23.4139 |   -23.9095 |    -0.4956 | mid timbre   |
| 08    |    15.7395 |    24.6761 |    +8.9366 | fine texture |
| 09    |     4.1003 |    -4.3445 |    -8.4448 | fine texture |
| 10    |    -4.9099 |     9.8932 |   +14.8032 | fine texture |
| 11    |    -1.2732 |   -10.2135 |    -8.9403 | fine texture |
| 12    |     4.2648 |    15.6678 |   +11.4030 | fine texture |
| 13    |     4.9427 |    -0.2449 |    -5.1876 | fine texture |

## Flagged Deviations

- **Spectral centroid** `+1061.7 Hz` — Mix brighter than reference — possible harshness
- **Spectral rolloff** `+2453.0 Hz` — Spectral rolloff higher — more high-frequency content than reference
- **MFCC distance** `+8.3931` — Timbre fingerprint mismatch — overall tonal character differs

## Diagnostic Summary

> *Paste the block below directly into an LLM prompt.*

```
DIAGNOSTIC SUMMARY — FULL_qais_part_C.wav
Consistency Score: 76.5/100
Flagged issues:
  - Mix brighter than reference — possible harshness  (delta: +1061.7 Hz)
  - Spectral rolloff higher — more high-frequency content than reference  (delta: +2453.0 Hz)
  - Timbre fingerprint mismatch — overall tonal character differs  (delta: +8.3931)

Subjective note from user: [paste what you hear here]
```
