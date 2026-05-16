## Question 1: Reference Validation

## Assessment

Reference selection in this pipeline is entirely trust-based by design. There is no automated mechanism within the provided codebase to validate whether `REF_01.mp3` is statistically representative of the prompt's intended output distribution. If the reference is an outlier, the entire scoring matrix will penalize normal generations.

## Facts This Depends On

- `README.md` documents a single-reference input architecture (`--reference <ref.mp3|wav>`).
- The reference profile is extracted once and cached to `reference_profile.json` without cross-validation against other seeds.
- The documentation explicitly states the tool "Does not replace the user's ear — it directs it," confirming reliance on human judgment for ground-truth selection.
- AI-origin references carry statistical patterns inherent to the generative model; a single generation is merely one sample from a wide variance distribution.

## Confidence

100% — The codebase documentation explicitly confirms the single-reference, unvalidated architecture.

## Caveats & Unknowns

This assessment assumes the user has not manually validated `REF_01.mp3` offline (e.g., by comparing it aurally or spectrally to a larger batch of generations) before designating it as the reference.

## Recommended Validation

Do not rely on a single Suno generation as a ground-truth reference for an automated quality gate. Generate 5–10 outputs from the same prompt, extract their features using `extractor.py`, and calculate the median for each feature. Construct a synthetic `reference_profile.json` using these medians to create a statistically stable baseline that resists single-seed anomalies.

---

## Question 2: Spectral Shift Magnitude & Tool Expectations

## Assessment

A spectral centroid shift of +1061.7 Hz and a rolloff shift of +2453.0 Hz strongly indicate a generative divergence, not normal stylistic variance for a stable prompt. In Suno, shifts of this magnitude typically signal a structural change: a shift in vocal register, the introduction of high-frequency instrumentation (e.g., cymbals, shakers), or a generative artifact (e.g., high-frequency smearing/hiss). The tool is a purely statistical comparator and cannot semantically distinguish between a valid musical arrangement change and a mode collapse. It should not be expected to do so.

## Facts This Depends On

- `FULL_qais_part_C_report.md` records a centroid delta of +1061.7 Hz and a rolloff delta of +2453.0 Hz.
- Suno's normal seed variance for a tightly conditioned prompt does not typically swing the spectral centroid by >1kHz unless the arrangement texture or vocal formant fundamentally changes.
- The pipeline relies on `librosa` for raw feature extraction, which measures acoustic energy distribution, not semantic musical intent.

## Confidence

90% — High confidence in Suno's spectral behavior boundaries, though the exact semantic cause of the shift requires aural verification.

## What Would Change This

Listening to `FULL_qais_part_C.wav`. Aural verification is required to determine if the +1061.7 Hz centroid shift is a generative failure (e.g., artifactual hiss/smearing) or a valid, prompt-compliant musical evolution (e.g., a chorus section introducing heavy cymbals).

---

## Question 3: Ceiling Threshold Validation

## Assessment

The ±4000 Hz rolloff ceiling threshold is strictly a first-pass heuristic. It has not been empirically validated against a corpus of Suno outputs to distinguish genuine production failures from normal generation variance. Furthermore, comparing AI-origin material to a human commercial master transfers assumptions about high-frequency spectral density that often do not hold for generative audio.

## Facts This Depends On

- `config.py` explicitly states: "All values are v1 heuristics. A calibration pass is MANDATORY after the first end-to-end run."
- `config.py` notes that ceiling thresholds are mathematically derived as "roughly 2–3× QA thresholds" rather than empirically derived from known Suno failure states.
- Suno's high-frequency generation (measured by rolloff and high-shelf) is inherently prone to variance and artifacting compared to acoustically grounded commercial masters.

## Confidence

100% — The codebase explicitly admits the thresholds are uncalibrated v1 heuristics.

## Caveats & Unknowns

Whether the user has performed the "MANDATORY" calibration pass offline since `config.py` was written.

## Recommended Validation

Before deploying the ceiling analysis as a production gate, run it against a dataset of at least 50 known "good" Suno generations and 50 known "failed" (muffled/harsh) generations. Plot the spectral rolloff distribution for both sets to empirically determine where the failure boundary actually lies for this specific AI model, rather than relying on a 3x multiplier of an uncalibrated QA threshold.
