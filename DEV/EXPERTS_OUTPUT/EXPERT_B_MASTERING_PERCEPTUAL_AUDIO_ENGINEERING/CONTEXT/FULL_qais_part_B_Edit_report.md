# Audio QA Report — FULL_qais_part_B_Edit.wav

| | |
|---|---|
| **Consistency Score** | **99.4/100** |
| **Verdict** | PASS — within reference family |

## Feature Comparison

| Feature                     | Unit | Reference |    Chunk |     Delta | Flag |
| --------------------------- | ---- | --------- | -------- | --------- | --- |
| LUFS                        | LUFS |    -14.21 |   -11.74 |     +2.47 | ✓ |
| RMS energy                  |      |  0.133887 | 0.170777 | +0.036890 | ✓ |
| Dynamic range               | dB   |     12.70 |    14.59 |     +1.89 | ✓ |
| Spectral centroid           | Hz   |    3578.4 |   3629.6 |     +51.2 | ✓ |
| Spectral rolloff            | Hz   |    8433.8 |   8273.3 |    -160.5 | ✓ |
| Low-mid energy (200–500 Hz) | frac |  0.169636 | 0.154682 | -0.014954 | ✓ |
| Presence band (1k–4kHz)     | frac |  0.095966 | 0.143785 | +0.047820 | ✓ |
| High shelf (8kHz+)          | frac |  0.018186 | 0.016578 | -0.001608 | ✓ |
| Stereo width                |      |  0.085289 | 0.104212 | +0.018924 | ✓ |
| Tempo                       | BPM  |     112.5 |     84.0 |     -28.5 | ✓ |
| Zero crossing rate          |      |  0.059882 | 0.061867 | +0.001985 | ✓ |
| MFCC distance               |      |    0.0000 |   7.2826 |   +7.2826 | ⚠ |

## MFCC Detail (13 Coefficients)

| Coeff | Reference  | Chunk      | Delta      | Role         |
| :---: | ---------: | ---------: | ---------: | :----------- |
| 01    |  -180.6576 |  -146.0202 |   +34.6374 | energy       |
| 02    |   112.6220 |   107.9092 |    -4.7128 | tonal char   |
| 03    |   -19.8035 |   -22.5417 |    -2.7382 | tonal char   |
| 04    |    58.0204 |    51.1365 |    -6.8839 | mid timbre   |
| 05    |    -4.6828 |     0.2586 |    +4.9414 | mid timbre   |
| 06    |    42.3066 |    38.1029 |    -4.2037 | mid timbre   |
| 07    |   -23.4139 |   -16.1551 |    +7.2588 | mid timbre   |
| 08    |    15.7395 |    10.6190 |    -5.1205 | fine texture |
| 09    |     4.1003 |     5.3659 |    +1.2656 | fine texture |
| 10    |    -4.9099 |    -0.1640 |    +4.7460 | fine texture |
| 11    |    -1.2732 |    -7.6426 |    -6.3694 | fine texture |
| 12    |     4.2648 |    10.6716 |    +6.4069 | fine texture |
| 13    |     4.9427 |    -0.4465 |    -5.3893 | fine texture |

## Flagged Deviations

- **MFCC distance** `+7.2826` — Timbre fingerprint mismatch — overall tonal character differs

## Diagnostic Summary

> *Paste the block below directly into an LLM prompt.*

```
DIAGNOSTIC SUMMARY — FULL_qais_part_B_Edit.wav
Consistency Score: 99.4/100
Flagged issues:
  - Timbre fingerprint mismatch — overall tonal character differs  (delta: +7.2826)

Subjective note from user: [paste what you hear here]
```
