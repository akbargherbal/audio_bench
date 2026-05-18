# Audio Analysis Script — Extension Proposal
## Enabling Human-LLM Collaboration for Mix Debugging

**Status:** Proposal — for review and prioritization
**Scope:** Extension of the existing style gap analysis script
**Audience:** Developer (self) and LLM collaborator

---

## Problem Statement

The current script produces a mix-level style gap table comparing a Suno-generated track against a commercial reference. This table has proven useful — an LLM can read it and form hypotheses about mix character differences. However, the current output has two structural limitations:

**1. It operates only on the full mix.**
Every metric is computed over the stereo output as rendered. If the vocal is unclear, the numbers can only say "the mix is thin in the presence band." They cannot say whether the problem originates in the vocal performance, the mix balance between voice and instruments, or both. The fix for each is different — and conflating them wastes prompt iterations.

**2. It is time-averaged.**
Each metric is a single number across the full duration. A single swallowed consonant at 0:43, a rushed hemistich at 1:12, or a pitch drift across a melismatic run are invisible to aggregate analysis. The LLM receives a blurred average rather than a located event.

These two limitations define the scope of what needs to be built.

---

## Proposed Extensions

### Extension A — Stem-Level Analysis (High Priority)

**What it requires:**
Run UVR5 (BS Roformer model) on the input track before any analysis to separate:
- `vocal_stem.wav` — isolated singing voice
- `instrumental_stem.wav` — everything else

Then run the full metric suite on all three: full mix, vocal stem, and instrumental stem.

**What this unlocks for the LLM:**
The LLM receives three parallel tables. Cross-referencing them allows precise localization. Example:

| Metric | Full Mix | Vocal Stem | Instrumental Stem |
|---|---|---|---|
| Presence band (1k–4kHz) | 0.167 | 0.091 | 0.241 |

This pattern tells the LLM: the instrumental is 2.6× louder than the vocal in the exact frequency range where vocal intelligibility lives. The vocal is being masked, not absent. The fix is a mix balance intervention, not a performance intervention.

Without stem separation, the full-mix number alone (0.167) produces only a vague hypothesis.

**New metrics to add on the vocal stem specifically:**

| Metric | Library | What it tells the LLM |
|---|---|---|
| Harmonic-to-Noise Ratio (HNR) | `parselmouth` (Praat bindings) | Closest numerical proxy to "the vocals don't sound clear." Low HNR = noise, breathiness, or distortion mixed into the voice. |
| Vocal-to-Accompaniment Ratio (VAR) in presence band | computed from stems | How many dB the vocal leads (or loses to) the instrumental at 1k–4kHz. Negative = vocal is buried. |
| Pitch confidence (mean + std dev) | `librosa.pyin` | Low mean confidence = pitch instability. High std dev = erratic. Relevant to melismatic runs drifting. |
| Spectral flatness of vocal stem | `librosa.feature.spectral_flatness` | A focused tonal voice has low flatness. High flatness = the voice is drifting toward noise. Relevant to heavy Arabic consonants being swallowed. |
| Fundamental frequency range (F0 min/max/range) | `librosa.pyin` | Captures how wide the singer's pitch register is across the track. Useful for verifying baritone vs tenor range. |

---

### Extension B — Time-Series / Windowed Analysis (Medium Priority)

**What it requires:**
Re-run a subset of metrics in a sliding window (suggested: 2-second windows, 1-second hop) across the vocal stem. Output a time-indexed CSV, not a single summary number.

**Target metrics for windowed analysis:**
- HNR per window
- Pitch confidence per window
- RMS energy per window (vocal stem)
- Spectral flatness per window

**What this unlocks for the LLM:**
The LLM can be given the CSV and asked: *"Flag any window where HNR drops below X or pitch confidence drops below Y."* This converts a vague "the vocals feel unclear" into a list of timestamps. The user can then jump to those exact moments in Audacity and confirm aurally.

This is the closest the script can get to a stack trace — locating the event, not just measuring the average state.

**Output format:** A CSV with columns `[time_start, time_end, HNR, pitch_confidence, rms_vocal, spectral_flatness]`. Flagged rows (below threshold) marked in a boolean column. A summary of flagged windows included in the main briefing table.

---

### Extension C — Reference Normalization Layer (Low Priority, High Value Later)

**What it requires:**
Store a small library of reference track metric profiles (commercial tracks the user has approved as "this is what good sounds like"). When running analysis on a new Suno track, select the closest reference by genre/mood and compute deltas against it automatically.

**Why it matters:**
The current script requires the user to manually select a reference each time. As the library of Suno tracks grows, having a reference profile library means the LLM always receives a delta against a relevant baseline, not a genre-mismatched one.

**Implementation note:** A JSON file mapping reference track names to their precomputed metric profiles is sufficient. No database needed.

---

## Output Format Requirements

The briefing document fed to the LLM must follow these conventions for maximum interpretive value:

1. **Three-table structure:** Full mix | Vocal stem | Instrumental stem. Always all three when stems are available.
2. **Delta column:** Always express Suno track relative to reference. Positive = Suno higher. Negative = Suno lower. Direction arrow.
3. **Plain-language annotation:** One sentence per metric explaining what the delta means perceptually. The LLM reads this as grounding before forming hypotheses.
4. **Flagged windows section:** If windowed analysis was run, include a summary: "N windows flagged below HNR threshold of X, concentrated between [time range]."
5. **Metadata block:** Track name, reference name, stem separation model used, date, Suno version, prompt hash or reference ID.

---

## What the Numbers Cannot Tell the LLM — Hard Limits

These are outside the scope of any planned extension and require listening judgment:

- **Arabic pronunciation fidelity** — whether Fusha consonants (ق, ع) were correctly articulated, whether dialect contamination occurred, whether tanween was swallowed. No open-source metric captures this for classical Arabic.
- **Maqam adherence** — pitch class histograms can indicate scale usage but cannot confirm maqam fidelity or whether microtonal intervals landed correctly.
- **Inter-chunk coherence** — whether chunk 2 sounds like the same singer as chunk 1. Metrics measure each track in isolation.
- **Reverb character** — the script can measure reverb energy but not whether the space sounds like a cold digital hall vs a warm room.
- **Felt emotional authenticity** — whether the rubato feels human, whether a melismatic run lands with weight. These are the user's ears, not the script's domain.

The LLM's role is to convert the numbers into hypotheses and targeted prompt interventions. The user's ears confirm or reject those hypotheses. This division of labor is the correct operating model.

---

## Recommended Implementation Order

1. **Stem separation pre-processing** — prerequisite for everything else. UVR5 CLI or Python API. Output: `vocal_stem.wav`, `instrumental_stem.wav`.
2. **HNR via parselmouth** — single highest-value new metric. Add to vocal stem analysis immediately.
3. **VAR computation** — trivial once stems exist. Ratio of RMS in presence band: vocal vs instrumental.
4. **Pitch confidence (pyin)** — add to vocal stem. `librosa.pyin` is already available if librosa is in the environment.
5. **Windowed HNR + pitch confidence** — add after the above are stable. Output to CSV.
6. **Reference library** — defer until the user has 5+ approved reference tracks profiled.

---

## Summary

The current script established that quantitative audio features can serve as a shared language between user and LLM. The extensions proposed here deepen that language in two directions: *specificity* (stem-level rather than mix-level) and *precision* (time-located rather than time-averaged). The result is a briefing document that allows the LLM to form hypotheses with enough resolution to point at a specific intervention — mix balance, vocal clarity, pitch stability — rather than returning a generic "the mix is thin."

The user's ears remain the ground truth. The script is a translation layer.
