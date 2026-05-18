# Executive Summary: Audio QA Extension

## The Goal

Upgrade the script to provide **stem-level** and **time-located** data so the LLM can pinpoint exactly _where_ and _why_ a vocal track is failing (e.g., performance issue vs. mix balance issue), rather than just giving a mix-level average.

## The Reality Check (Expert Consensus)

The proposal is highly valuable but currently blocked by two major realities:

1. **DSP Math Errors:** The proposed ways to measure Vocal-to-Accompaniment Ratio (VAR) and Pitch Confidence are mathematically flawed and will feed the LLM hallucinated data. (We have the exact formulas to fix this).
2. **Architectural Incompatibility:** The current script is rigidly built for "1 file = 1 score." Introducing stems (3 files) and time-series data (lists instead of single numbers) will instantly crash the scorer unless we explicitly route around it.

## The Core Decision: Option A vs. Option B

To unblock development, you must choose how deeply to integrate the new stem data into the existing pipeline.

### Option A: Full Stem QA (High Effort, High Risk)

_How it works:_ UVR5 separates **both** the Reference track and the Suno Chunk. The script calculates deltas and scores for the full mix, the vocal stem, and the instrumental stem.

- **Pros:** Complete feature parity. Stems get red flags and a Consistency Score.
- **Cons:** Triples processing time. Requires massive architectural surgery.
- **The Dealbreaker:** We currently have **zero calibration data** for stem thresholds. If we build this today, the scores will be meaningless until you spend weeks manually calibrating the new metrics.

### Option B: Raw Stem Reporting (Low Effort, High ROI) — _Recommended_

_How it works:_ UVR5 separates **only** the Suno Chunk. The script scores the full mix exactly as it does today, but appends the raw stem values (HNR, VAR, Pitch Confidence) to the LLM briefing block without scoring them.

- **Pros:** Fast to implement. Zero risk of breaking the existing, working QA pipeline. Immediately gives the LLM the 3-table cross-reference data it needs to diagnose mix balance vs. vocal clarity.
- **Cons:** Stems do not get a Consistency Score or automated red flags (the LLM must interpret the raw numbers).

## Mandatory DSP Fixes (Required for either option)

Whichever path you choose, I will implement Expert A's mandatory corrections:

1. **VAR:** Build a new `_band_absolute_power()` helper to calculate true dB ratios, discarding the flawed fractional method.
2. **Pitch Confidence:** Mask the data using `voiced_flag` so Arabic consonants aren't falsely flagged as "erratic pitch."
3. **HNR:** Hardcode a warning into the LLM prompt that HNR drops must be cross-referenced with VAR to rule out instrumental bleed.

## Recommendation

**Proceed with Option B.**

Option B delivers 90% of the value to the LLM (the ability to cross-reference stems) with 10% of the architectural risk. More importantly, Option B acts as a **data-gathering phase**. By watching the raw stem numbers over your next few dozen generations, you will naturally learn what a "good" HNR or VAR looks like. Once you have that intuition, we can easily upgrade to Option A and lock in those thresholds.

**How would you like to proceed?** (Reply with "Option A" or "Option B", and I will generate the exact step-by-step implementation plan).
