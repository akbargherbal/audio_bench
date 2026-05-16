# Audio QA Report — FULL_qais_part_G (Edit).wav

| | |
|---|---|
| **Consistency Score** | **100.0/100** |
| **Verdict** | PASS — within reference family |

## Feature Comparison

| Feature                     | Unit | Reference |    Chunk |     Delta | Flag |
| --------------------------- | ---- | --------- | -------- | --------- | --- |
| LUFS                        | LUFS |    -14.21 |   -13.32 |     +0.89 | ✓ |
| RMS energy                  |      |  0.133861 | 0.145964 | +0.012103 | ✓ |
| Dynamic range               | dB   |     12.66 |    14.37 |     +1.71 | ✓ |
| Spectral centroid           | Hz   |    3606.9 |   3971.7 |    +364.8 | ✓ |
| Spectral rolloff            | Hz   |    8469.4 |   9310.8 |    +841.4 | ✓ |
| Low-mid energy (200–500 Hz) | frac |  0.169654 | 0.191382 | +0.021728 | ✓ |
| Presence band (1k–4kHz)     | frac |  0.095893 | 0.090062 | -0.005832 | ✓ |
| High shelf (8kHz+)          | frac |  0.017991 | 0.022937 | +0.004946 | ✓ |
| Stereo width                |      |  0.085218 | 0.097614 | +0.012396 | ✓ |
| Tempo                       | BPM  |     165.4 |     84.0 |     -81.5 | ✓ |
| Zero crossing rate          |      |  0.059701 | 0.064434 | +0.004734 | ✓ |
| MFCC distance               |      |    0.0000 |   4.5505 |   +4.5505 | ✓ |

## MFCC Detail (13 Coefficients)

| Coeff | Reference  | Chunk      | Delta      | Role         |
| :---: | ---------: | ---------: | ---------: | :----------- |
| 01    |  -180.3466 |  -163.4288 |   +16.9178 | energy       |
| 02    |   111.8133 |   104.0148 |    -7.7985 | tonal char   |
| 03    |   -19.1641 |   -11.2720 |    +7.8920 | tonal char   |
| 04    |    57.3860 |    56.2124 |    -1.1736 | mid timbre   |
| 05    |    -3.9297 |    -6.4747 |    -2.5450 | mid timbre   |
| 06    |    41.8138 |    43.6496 |    +1.8359 | mid timbre   |
| 07    |   -23.0524 |   -23.4268 |    -0.3744 | mid timbre   |
| 08    |    15.6671 |    19.2226 |    +3.5555 | fine texture |
| 09    |     3.9542 |     4.2455 |    +0.2914 | fine texture |
| 10    |    -4.5757 |    -0.8345 |    +3.7411 | fine texture |
| 11    |    -1.7582 |    -7.8858 |    -6.1276 | fine texture |
| 12    |     4.8644 |     8.7106 |    +3.8463 | fine texture |
| 13    |     4.1602 |     1.1032 |    -3.0569 | fine texture |

## Flagged Deviations

_No deviations flagged — all features are within reference thresholds._

## Diagnostic Summary

> *Paste the block below directly into an LLM prompt.*

```
DIAGNOSTIC SUMMARY — FULL_qais_part_G (Edit).wav
Consistency Score: 100.0/100
No issues flagged — chunk is within reference bounds on all metrics.

Subjective note from user: [paste what you hear here]
```
