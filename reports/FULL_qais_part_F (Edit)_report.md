# Audio QA Report — FULL_qais_part_F (Edit).wav

| | |
|---|---|
| **Consistency Score** | **99.4/100** |
| **Verdict** | PASS — within reference family |

## Feature Comparison

| Feature                     | Unit | Reference |    Chunk |     Delta | Flag |
| --------------------------- | ---- | --------- | -------- | --------- | --- |
| LUFS                        | LUFS |    -14.21 |   -12.96 |     +1.26 | ✓ |
| RMS energy                  |      |  0.133861 | 0.155294 | +0.021433 | ✓ |
| Dynamic range               | dB   |     12.66 |    13.82 |     +1.16 | ✓ |
| Spectral centroid           | Hz   |    3606.9 |   3203.8 |    -403.1 | ✓ |
| Spectral rolloff            | Hz   |    8469.4 |   7392.1 |   -1077.3 | ⚠ |
| Low-mid energy (200–500 Hz) | frac |  0.169654 | 0.175328 | +0.005675 | ✓ |
| Presence band (1k–4kHz)     | frac |  0.095893 | 0.122614 | +0.026721 | ✓ |
| High shelf (8kHz+)          | frac |  0.017991 | 0.009076 | -0.008915 | ✓ |
| Stereo width                |      |  0.085218 | 0.087396 | +0.002179 | ✓ |
| Tempo                       | BPM  |     165.4 |     84.0 |     -81.5 | ✓ |
| Zero crossing rate          |      |  0.059701 | 0.052858 | -0.006843 | ✓ |
| MFCC distance               |      |    0.0000 |   4.9136 |   +4.9136 | ✓ |

## MFCC Detail (13 Coefficients)

| Coeff | Reference  | Chunk      | Delta      | Role         |
| :---: | ---------: | ---------: | ---------: | :----------- |
| 01    |  -180.3466 |  -162.9011 |   +17.4456 | energy       |
| 02    |   111.8133 |   122.3282 |   +10.5149 | tonal char   |
| 03    |   -19.1641 |   -25.0637 |    -5.8997 | tonal char   |
| 04    |    57.3860 |    55.8196 |    -1.5664 | mid timbre   |
| 05    |    -3.9297 |    -5.8712 |    -1.9416 | mid timbre   |
| 06    |    41.8138 |    33.0025 |    -8.8113 | mid timbre   |
| 07    |   -23.0524 |   -18.4995 |    +4.5529 | mid timbre   |
| 08    |    15.6671 |    10.7268 |    -4.9402 | fine texture |
| 09    |     3.9542 |     7.4764 |    +3.5222 | fine texture |
| 10    |    -4.5757 |    -4.1976 |    +0.3781 | fine texture |
| 11    |    -1.7582 |    -3.7679 |    -2.0097 | fine texture |
| 12    |     4.8644 |     6.6318 |    +1.7675 | fine texture |
| 13    |     4.1602 |     4.6869 |    +0.5267 | fine texture |

## Flagged Deviations

- **Spectral rolloff** `-1077.3 Hz` — Spectral rolloff lower — high-frequency content reduced

## Diagnostic Summary

> *Paste the block below directly into an LLM prompt.*

```
DIAGNOSTIC SUMMARY — FULL_qais_part_F (Edit).wav
Consistency Score: 99.4/100
Flagged issues:
  - Spectral rolloff lower — high-frequency content reduced  (delta: -1077.3 Hz)

Subjective note from user: [paste what you hear here]
```
