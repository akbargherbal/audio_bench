This script assumes familiarity with the following fields:

════════════════════════════════════════
Field [A]: Audio Signal Processing (DSP)
════════════════════════════════════════

Documents this expert must review:

- extractor.py ← primary: every extraction decision lives here
- profiler.py ← MFCC distance formula is computed here, not
  in extractor.py; easy to miss
- FULL_qais_part_C_report.md ← the most extreme delta values in the
  batch; good stress-test for interrogating
  whether the numbers make physical sense

Skills required:

1. Understanding of librosa's frame-based feature pipeline — specifically
   that spectral_centroid, spectral_rolloff, and ZCR are computed
   per-frame then averaged across time, and what temporal information
   that averaging destroys.
2. Understanding of FFT-based band energy fractions using np.fft.rfft
   applied to the full signal (not a short-time windowed transform),
   and how this differs from a spectrogram-derived band estimate.
3. Understanding of pyloudnorm's integrated loudness requirements —
   the minimum file duration needed for a valid ITU-R BS.1770
   measurement, and what happens when that floor is violated.
4. Understanding of MFCC computation: the Mel filter bank, the 13-
   coefficient truncation, and what collapsing to a mean vector
   (mfcc_matrix.mean(axis=1)) conceals about temporal structure.
5. Understanding of librosa's beat.tempo() algorithm and its documented
   failure modes on non-rhythmic or sparse audio content.

Questions a domain expert must answer:

1. spectral_rolloff uses librosa's default roll_percent=0.85 (the
   frequency below which 85% of spectral energy falls). Is this
   percentile appropriate for comparing vocal-dominant Arabic music
   chunks, or does it produce an Hz value that is more sensitive to
   low-energy high-frequency noise than to actual tonal content?
2. The band energy fractions (low_mid, presence, high_shelf) run a
   single rfft over the entire signal, not a windowed STFT. For chunks
   of differing duration, does a global FFT accurately represent the
   spectral shape of the content, or does it weight longer silence/
   intro sections in a way that distorts the comparison?
3. MFCC distance is mean(abs(chunk_mfccs − ref_mfccs)) computed on
   13 mean-across-time coefficients. Coeff 01 (energy/C0) dominates
   magnitude. Is the mean-absolute-distance formula appropriately
   normalised across coefficients of vastly different scale, or is
   the distance figure effectively driven by C01 alone?
4. Stereo width is computed as mean(abs(L − R)). This is an amplitude
   difference, not a correlation-based width metric. Does this measure
   meaningfully capture "spatial consistency," or does it conflate a
   loud centre-panned element (which reduces L−R) with a narrow stereo
   image?

────────────────────────────────────────
Field [B]: Mastering & Perceptual Audio Engineering
────────────────────────────────────────

Documents this expert must review:

- config.py ← thresholds, weights, and calibration watch
  points are all here; this is the primary
  document for this field
- scorer.py ← the scoring formula implementation; must be
  read alongside config.py
- README.md ← "Calibration Notes" and "Scoring Formula"
  sections; "Known Limitations" for tempo
- FULL_qais_part_B_Edit_report.md ← a borderline MFCC flag at 7.28
  against a threshold of 7.0; useful for
  interrogating threshold sensitivity
- FULL_qais_part_C_report.md ← the outlier score (76.5/100);
  useful for interrogating whether the penalty
  weights produce a believable result

Skills required:

1. Understanding of integrated LUFS (ITU-R BS.1770-4) as a time-
   integrated measure, and how it differs from short-term or momentary
   loudness for the purpose of chunk-to-chunk matching.
2. Understanding of crest factor (peak/RMS in dB) as a dynamic range
   proxy, and how it differs from loudness-range (LRA) or DR-meter
   readings used in mastering practice.
3. Knowledge of perceptual frequency band weighting — what the
   200–500 Hz, 1k–4kHz, and 8kHz+ bands represent in a vocal-forward
   mix, and whether fractional spectral power in those bands is the
   right way to measure them.
4. Understanding of what a mean-MFCC distance represents perceptually
   — specifically whether it is a reliable proxy for "voice identity"
   or whether it conflates timbral change with arrangement change.

Questions a domain expert must answer:

1. The scoring formula assigns mfcc_distance a weight of 1.5 (the
   highest, tied with LUFS) and a threshold of 7.0. In the sample
   output, FULL_qais_part_B_Edit scores 99.4/100 despite an MFCC
   distance of 7.28 — just over threshold. Is this distance value
   perceptually meaningful on this scale, or is the 7.0 threshold
   arbitrary enough that single-point flag decisions around it are
   unreliable?
2. Dynamic range is crest factor: 20·log10(peak/RMS). A spoken-word
   recording with loud transient consonants will have a very different
   crest factor than a music track with comparable perceived dynamics.
   Is crest factor the correct dynamic range metric for a vocal poetry
   track, or does it misrepresent the perceptual phenomenon it is
   supposed to capture?
3. Presence band is measured as a fraction of total spectral power.
   If a chunk has more low-frequency energy than the reference, the
   presence_band fraction drops even if the absolute vocal energy is
   identical. Does this fractional framing mean the metric can flag a
   presence-band deviation that is actually a bass-level shift in
   disguise?
4. LUFS carries the highest perceptual weight (1.5), but most
   streaming platforms apply loudness normalisation at delivery
   (−14 LUFS on Spotify, −16 on Apple Music). For a track that will
   be normalised before release, is chunk-to-chunk LUFS consistency
   genuinely the most perceptually critical dimension to score highest?

────────────────────────────────────────
Field [C]: AI-Generated Music Pipeline (Suno-Specific)
────────────────────────────────────────

Documents this expert must review:

- README.md ← "Known Limitations" and "What the Script
  Does NOT Do" sections define the pipeline
  assumptions explicitly; start here
- summary.md ← the full batch ranked by score; shows which
  chunks deviate and by how much — the pattern
  across all 6 chunks is the evidence base
- FULL_qais_part_C_report.md ← the 76.5/100 outlier; the centroid
  and rolloff shifts here are the primary
  example of a deviation this tool cannot
  classify as failure vs variation
- ceiling_B.md ← the ceiling analysis output; shows what the
  tool considers a "hygiene floor" and what
  it explicitly excludes as genre-specific
- config.py ← CEILING_THRESHOLDS dict; the expert needs
  to see the actual threshold values to assess
  whether they are calibrated for Suno's
  variance range

Skills required:

1. Understanding of how Suno generates audio in discrete segments and
   what spectral artifacts typically appear at generation boundaries
   versus within a continuous generation.
2. Understanding of how Suno's style and prompt conditioning affects
   spectral consistency across multiple generations from the same
   seed — and how much variance is normal versus anomalous.
3. Knowledge of what "reference consistency" means when the reference
   is itself an AI output, not a human recording, and what assumptions
   that transfers onto every score the tool produces.

Questions a domain expert must answer:

1. The entire scoring system is anchored to REF_01.mp3 — a single
   Suno-generated chunk chosen as the reference. If REF_01 is itself
   a statistical outlier in the batch (e.g., an atypically bright or
   loud generation), every chunk is penalised relative to a flawed
   baseline. Is there any way to validate that REF_01 is
   representative, or is reference selection entirely trust-based by
   design?
2. FULL_qais_part_C scores 76.5/100 with a spectral centroid shift of
   +1061.7 Hz and rolloff of +2453 Hz. In Suno's generation behaviour,
   does a shift of this magnitude indicate a generation failure (wrong
   instrumentation, mode collapse), or is it within the normal range
   of stylistic variation that the same prompt can produce across
   seeds? The tool cannot distinguish these cases — should it be
   expected to?
3. The ceiling analysis excludes high_shelf, stereo_width, and tempo
   as "genre-specific" and compares only 9 features against one
   commercial Arabic pop track. Suno's output varies spectrally even
   with identical prompts. Has the ±4000 Hz rolloff ceiling threshold
   been validated against enough Suno-generated outputs to distinguish
   genuine production failures from normal generation variance, or is
   it still a first-pass heuristic?
