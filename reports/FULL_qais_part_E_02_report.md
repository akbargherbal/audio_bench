# Audio QA Report — FULL_qais_part_E_02.wav

| | |
|---|---|
| **Consistency Score** | **100.0/100** |
| **Verdict** | PASS — within reference family |

## Feature Comparison

| Feature                     | Unit | Reference |    Chunk |     Delta | Flag |
| --------------------------- | ---- | --------- | -------- | --------- | --- |
| LUFS                        | LUFS |    -14.21 |   -12.84 |     +1.38 | ✓ |
| RMS energy                  |      |  0.133861 | 0.156266 | +0.022405 | ✓ |
| Dynamic range               | dB   |     12.66 |    15.12 |     +2.46 | ✓ |
| Spectral centroid           | Hz   |    3606.9 |   3668.2 |     +61.3 | ✓ |
| Spectral rolloff            | Hz   |    8469.4 |   8701.8 |    +232.4 | ✓ |
| Low-mid energy (200–500 Hz) | frac |  0.169654 | 0.156596 | -0.013058 | ✓ |
| Presence band (1k–4kHz)     | frac |  0.095893 | 0.100168 | +0.004275 | ✓ |
| High shelf (8kHz+)          | frac |  0.017991 | 0.016050 | -0.001941 | ✓ |
| Stereo width                |      |  0.085218 | 0.091319 | +0.006101 | ✓ |
| Tempo                       | BPM  |     165.4 |     82.7 |     -82.7 | ✓ |
| Zero crossing rate          |      |  0.059701 | 0.059053 | -0.000647 | ✓ |
| MFCC distance               |      |    0.0000 |   3.9044 |   +3.9044 | ✓ |

## MFCC Detail (13 Coefficients)

| Coeff | Reference  | Chunk      | Delta      | Role         |
| :---: | ---------: | ---------: | ---------: | :----------- |
| 01    |  -180.3466 |  -161.3806 |   +18.9660 | energy       |
| 02    |   111.8133 |   110.0618 |    -1.7515 | tonal char   |
| 03    |   -19.1641 |   -11.0125 |    +8.1515 | tonal char   |
| 04    |    57.3860 |    52.7004 |    -4.6857 | mid timbre   |
| 05    |    -3.9297 |    -3.1223 |    +0.8074 | mid timbre   |
| 06    |    41.8138 |    37.1022 |    -4.7116 | mid timbre   |
| 07    |   -23.0524 |   -21.8152 |    +1.2373 | mid timbre   |
| 08    |    15.6671 |    16.1661 |    +0.4990 | fine texture |
| 09    |     3.9542 |     2.6227 |    -1.3314 | fine texture |
| 10    |    -4.5757 |     0.3132 |    +4.8889 | fine texture |
| 11    |    -1.7582 |    -3.1751 |    -1.4169 | fine texture |
| 12    |     4.8644 |     6.8832 |    +2.0188 | fine texture |
| 13    |     4.1602 |     4.4511 |    +0.2909 | fine texture |

## Flagged Deviations

_No deviations flagged — all features are within reference thresholds._

## Diagnostic Summary

> *Paste the block below directly into an LLM prompt.*

```
DIAGNOSTIC SUMMARY — FULL_qais_part_E_02.wav
Consistency Score: 100.0/100
No issues flagged — chunk is within reference bounds on all metrics.

Subjective note from user: [paste what you hear here]
```
