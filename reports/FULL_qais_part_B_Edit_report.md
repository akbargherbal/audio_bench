# Audio QA Report — FULL_qais_part_B_Edit.wav

| | |
|---|---|
| **Consistency Score** | **100.0/100** |
| **Verdict** | PASS — within reference family |

## Feature Comparison

| Feature                     | Unit | Reference |    Chunk |     Delta | Flag |
| --------------------------- | ---- | --------- | -------- | --------- | --- |
| LUFS                        | LUFS |    -14.21 |   -11.74 |     +2.48 | ✓ |
| RMS energy                  |      |  0.133861 | 0.170777 | +0.036916 | ✓ |
| Dynamic range               | dB   |     12.66 |    14.59 |     +1.93 | ✓ |
| Spectral centroid           | Hz   |    3606.9 |   3629.6 |     +22.7 | ✓ |
| Spectral rolloff            | Hz   |    8469.4 |   8273.3 |    -196.1 | ✓ |
| Low-mid energy (200–500 Hz) | frac |  0.169654 | 0.154682 | -0.014972 | ✓ |
| Presence band (1k–4kHz)     | frac |  0.095893 | 0.143785 | +0.047892 | ✓ |
| High shelf (8kHz+)          | frac |  0.017991 | 0.016578 | -0.001413 | ✓ |
| Stereo width                |      |  0.085218 | 0.104212 | +0.018994 | ✓ |
| Tempo                       | BPM  |     165.4 |     84.0 |     -81.5 | ✓ |
| Zero crossing rate          |      |  0.059701 | 0.061867 | +0.002166 | ✓ |
| MFCC distance               |      |    0.0000 |   6.9095 |   +6.9095 | ✓ |

## MFCC Detail (13 Coefficients)

| Coeff | Reference  | Chunk      | Delta      | Role         |
| :---: | ---------: | ---------: | ---------: | :----------- |
| 01    |  -180.3466 |  -146.0202 |   +34.3264 | energy       |
| 02    |   111.8133 |   107.9092 |    -3.9041 | tonal char   |
| 03    |   -19.1641 |   -22.5417 |    -3.3776 | tonal char   |
| 04    |    57.3860 |    51.1365 |    -6.2495 | mid timbre   |
| 05    |    -3.9297 |     0.2586 |    +4.1883 | mid timbre   |
| 06    |    41.8138 |    38.1029 |    -3.7109 | mid timbre   |
| 07    |   -23.0524 |   -16.1551 |    +6.8974 | mid timbre   |
| 08    |    15.6671 |    10.6190 |    -5.0481 | fine texture |
| 09    |     3.9542 |     5.3659 |    +1.4117 | fine texture |
| 10    |    -4.5757 |    -0.1640 |    +4.4117 | fine texture |
| 11    |    -1.7582 |    -7.6426 |    -5.8844 | fine texture |
| 12    |     4.8644 |    10.6716 |    +5.8073 | fine texture |
| 13    |     4.1602 |    -0.4465 |    -4.6067 | fine texture |

## Flagged Deviations

_No deviations flagged — all features are within reference thresholds._

## Diagnostic Summary

> *Paste the block below directly into an LLM prompt.*

```
DIAGNOSTIC SUMMARY — FULL_qais_part_B_Edit.wav
Consistency Score: 100.0/100
No issues flagged — chunk is within reference bounds on all metrics.

Subjective note from user: [paste what you hear here]
```
