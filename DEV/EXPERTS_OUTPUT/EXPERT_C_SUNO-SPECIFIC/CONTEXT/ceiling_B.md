# Audio QA: Ceiling Analysis — CHUNK_B.mp3

> ⚠ **PRODUCTION HYGIENE CHECK — NOT A STYLE TARGET**
> This report compares **CHUNK_B.mp3** against a commercial reference
> (`elisa_maktooba_leek.mp3`) to detect gross production failures only.
> These are **red flags**, not genre norms. Features excluded below
> are genre-specific and are intentionally not compared.

| | |
|---|---|
| **Chunk** | CHUNK_B.mp3 |
| **Commercial reference** | elisa_maktooba_leek.mp3 |
| **Features checked** | 9 of 12 |
| **Red flags raised** | 0 — No red flags raised. |

## Feature Comparison (Production Hygiene Features Only)

| Feature                     | Unit | Ceiling Ref |    Chunk |     Delta | Threshold | Flag |
| --------------------------- | ---- | ----------- | -------- | --------- | --------- | --- |
| LUFS                        | LUFS |       -7.39 |   -11.73 |     -4.35 |     ±8.00 | ✓ |
| RMS energy                  |      |    0.252726 | 0.170818 | -0.081907 | ±0.150000 | ✓ |
| Dynamic range               | dB   |       11.87 |    14.44 |     +2.57 |     ±8.00 | ✓ |
| Spectral centroid           | Hz   |      2534.4 |   3579.4 |   +1045.1 |   ±2500.0 | ✓ |
| Spectral rolloff            | Hz   |      5323.0 |   8189.2 |   +2866.2 |   ±4000.0 | ✓ |
| Low-mid energy (200–500 Hz) | frac |    0.335611 | 0.154577 | -0.181034 | ±0.250000 | ✓ |
| Presence band (1k–4kHz)     | frac |    0.206722 | 0.143900 | -0.062822 | ±0.250000 | ✓ |
| Zero crossing rate          |      |    0.056410 | 0.062001 | +0.005591 | ±0.150000 | ✓ |
| MFCC distance               |      |      0.0000 |   9.6983 |   +9.6983 |  ±20.0000 | ✓ |

*Not compared (genre-specific): High shelf (8kHz+), Stereo width, Tempo.*

## Red Flags

_No red flags raised — no gross production hygiene violations detected._
_All checked features are within the ceiling tolerance band._

## Ceiling Analysis Summary

> *Paste the block below directly into an LLM prompt.*

```
CEILING ANALYSIS — CHUNK_B.mp3
Commercial reference: elisa_maktooba_leek.mp3
Red flags raised: 0 of 9 features checked

No gross production hygiene violations detected. All checked features are within the ceiling tolerance band.

Features not compared (genre-specific): High shelf (8kHz+), Stereo width, Tempo

IMPORTANT: The commercial reference values are NOT style targets.
These are production hygiene floors only. Genre differences are intentional.

Subjective note from user: [paste what you hear here]
```
