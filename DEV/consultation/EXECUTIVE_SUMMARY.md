# Executive Summary — AUDIO-QA Pipeline: Next Steps

**Prepared from:** Expert A (DSP), Expert B (Mastering), Expert C (Suno-Specific), codebase review, and project profile.

---

## Overall Verdict

The pipeline's architecture is sound and its core purpose — directing the ear before Audacity assembly — is being served. The Part C outlier (76.5/100) is almost certainly a real catch, not a false positive; a +1,061 Hz centroid shift and +2,453 Hz rolloff shift exceed normal Suno seed variance for a tightly conditioned prompt. The tool is doing its job.

However, two of the twelve extracted features contain measurement bugs serious enough to corrupt your highest-weighted metric. These need to be fixed before you trust the numbers. Everything else falls into "document and defer" or "accept the known limitation."

---

## The Two Bugs You Fix Now

Both are in `extractor.py`. Both are 2-line changes. Both have exact replacement code supplied by Expert A.

**Bug 1 — MFCC distance is measuring loudness, not timbre.** C0 (the energy coefficient) is on a scale of approximately −180, while C1–C12 sit in a ±5–20 range. The unweighted mean-absolute-distance formula is therefore almost entirely a function of the volume difference between the chunk and the reference — not timbral identity. This is your highest-weighted feature (1.5, tied with LUFS). Fix: drop C0, replace with cosine distance on C1–C12.

```python
from scipy.spatial.distance import cosine
timbre_distance = cosine(chunk_mfccs[1:], ref_mfccs[1:])
```

**Bug 2 — Stereo width is not amplitude-normalised.** `mean(abs(L − R))` is the absolute energy of the side channel. A chunk that is simply louder than the reference will report a wider stereo image regardless of actual spatial characteristics. Fix: replace with the Side-to-Mid energy ratio.

```python
mid  = (L + R) / 2.0
side = (L - R) / 2.0
stereo_width = float(np.sqrt(np.mean(side**2)) / (np.sqrt(np.mean(mid**2)) + 1e-9))
```

After these two changes, re-run the full batch and regenerate `summary.md`. Scores will shift — the MFCC flags in particular may look very different.

---

## The One Workflow Change You Make Before Next Batch

**Your reference selection has no validation mechanism.** Expert C's finding is unambiguous: the codebase explicitly documents a single-seed, unvalidated reference architecture. If `REF_01.mp3` happens to be an atypically bright or loud generation, every score in every batch will be penalising normal outputs. This is the highest-risk structural assumption in the system, and it requires no code changes to address.

Before the next production run: generate 5–8 chunks from the same prompt and seed parameters, run them through `extractor.py`, compute the median for each feature manually, and write that as your `reference_profile.json`. One-time effort, permanently removes the single-seed fragility.

---

## What You Accept and Document

**LUFS weighting (1.5) is correct.** Expert B confirmed this directly: streaming normalisation is applied as a single static gain offset to the assembled master, not section-by-section. A 4 dB LUFS gap between adjacent chunks survives delivery and is audible. Keep the weight.

**Crest factor is the wrong dynamic range metric for vocal poetry** (Expert B). LRA would be more perceptually accurate. However, replacing it requires non-trivial implementation work, and the current metric at least flags gross dynamic inconsistencies. Add it to the backlog; don't act now.

**Global FFT band energy has a non-stationarity problem** (Expert A). For variable-duration chunks with differing silence ratios, it can produce misleading spectral fractions. The fractional normalization your code already implements partially addresses this, but doesn't solve the active-vs-inactive time problem. The cross-reference rule Expert B gives is practical in the meantime: when a presence band flag fires, check whether `low_mid_energy` also spiked in the same chunk. If yes, it's likely a low-end masking artifact, not a genuinely recessed vocal.

**Spectral rolloff at 0.85 tracks formants, not high-frequency content** (Expert A). It is doing what it is doing — acting as a formant tracker, not an air/sibilance detector. This is a labelling and interpretation problem, not a bug. Adjust your mental model of what the metric reports; don't change the percentile unless you specifically want to detect high-frequency noise artefacts.

**All ceiling thresholds are uncalibrated v1 heuristics.** Expert C confirmed this directly from `config.py`'s own documentation ("calibration pass is MANDATORY"). The ceiling analysis is a directional tool, not a production gate, until you run it against a labelled corpus of known-good and known-failed Suno outputs.

---

## Prioritised Action List

| Priority | Action                                                  | Effort      | File                          |
| -------- | ------------------------------------------------------- | ----------- | ----------------------------- |
| 1        | Fix MFCC: drop C0, cosine distance                      | ~5 min      | `extractor.py`, `profiler.py` |
| 2        | Fix stereo width: Side/Mid ratio                        | ~5 min      | `extractor.py`                |
| 3        | Re-run batch, regenerate summary                        | ~10 min     | —                             |
| 4        | Build median reference profile from 5–8 seeds           | 1 session   | workflow only                 |
| 5        | Add cross-reference rule to report interpretation notes | ~15 min     | `README.md`                   |
| Backlog  | Replace crest factor with LRA                           | significant | `extractor.py`, `config.py`   |
| Backlog  | Validate ceiling thresholds against labelled corpus     | significant | —                             |

The Part C chunk still needs your ear. The score is telling you something diverged; only listening resolves whether it is a generative failure or a valid musical evolution.
