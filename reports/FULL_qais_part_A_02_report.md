# Audio QA Report — FULL_qais_part_A_02.wav

| | |
|---|---|
| **Consistency Score** | **98.9/100** |
| **Verdict** | PASS — within reference family |

## Feature Comparison

| Feature                     | Unit | Reference |    Chunk |     Delta | Flag |
| --------------------------- | ---- | --------- | -------- | --------- | --- |
| LUFS                        | LUFS |    -14.21 |   -14.22 |     -0.01 | ✓ |
| RMS energy                  |      |  0.133861 | 0.135585 | +0.001725 | ✓ |
| Dynamic range               | dB   |     12.66 |    13.14 |     +0.49 | ✓ |
| Spectral centroid           | Hz   |    3606.9 |   4108.3 |    +501.4 | ⚠ |
| Spectral rolloff            | Hz   |    8469.4 |   9611.6 |   +1142.2 | ⚠ |
| Low-mid energy (200–500 Hz) | frac |  0.169654 | 0.147387 | -0.022267 | ✓ |
| Presence band (1k–4kHz)     | frac |  0.095893 | 0.120858 | +0.024965 | ✓ |
| High shelf (8kHz+)          | frac |  0.017991 | 0.019518 | +0.001527 | ✓ |
| Stereo width                |      |  0.085218 | 0.072700 | -0.012518 | ✓ |
| Tempo                       | BPM  |     165.4 |     84.0 |     -81.5 | ✓ |
| Zero crossing rate          |      |  0.059701 | 0.066494 | +0.006794 | ✓ |
| MFCC distance               |      |    0.0000 |   6.6775 |   +6.6775 | ✓ |

## MFCC Detail (13 Coefficients)

| Coeff | Reference  | Chunk      | Delta      | Role         |
| :---: | ---------: | ---------: | ---------: | :----------- |
| 01    |  -180.3466 |  -163.4395 |   +16.9071 | energy       |
| 02    |   111.8133 |   104.2805 |    -7.5328 | tonal char   |
| 03    |   -19.1641 |   -14.4734 |    +4.6907 | tonal char   |
| 04    |    57.3860 |    50.1117 |    -7.2743 | mid timbre   |
| 05    |    -3.9297 |    -3.3800 |    +0.5497 | mid timbre   |
| 06    |    41.8138 |    39.9053 |    -1.9085 | mid timbre   |
| 07    |   -23.0524 |   -24.1905 |    -1.1381 | mid timbre   |
| 08    |    15.6671 |    23.5662 |    +7.8991 | fine texture |
| 09    |     3.9542 |     1.1416 |    -2.8126 | fine texture |
| 10    |    -4.5757 |     6.4647 |   +11.0404 | fine texture |
| 11    |    -1.7582 |   -11.9318 |   -10.1736 | fine texture |
| 12    |     4.8644 |    15.8999 |   +11.0355 | fine texture |
| 13    |     4.1602 |     0.3144 |    -3.8457 | fine texture |

## Flagged Deviations

- **Spectral centroid** `+501.4 Hz` — Mix brighter than reference — possible harshness
- **Spectral rolloff** `+1142.2 Hz` — Spectral rolloff higher — more high-frequency content than reference

## Diagnostic Summary

> *Paste the block below directly into an LLM prompt.*

```
DIAGNOSTIC SUMMARY — FULL_qais_part_A_02.wav
Consistency Score: 98.9/100
Flagged issues:
  - Mix brighter than reference — possible harshness  (delta: +501.4 Hz)
  - Spectral rolloff higher — more high-frequency content than reference  (delta: +1142.2 Hz)

Subjective note from user: [paste what you hear here]
```
