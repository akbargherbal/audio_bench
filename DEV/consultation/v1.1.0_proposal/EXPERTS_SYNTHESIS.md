## Expert Synthesis — Session 12

**All 13 files now in hand.** Complete inventory confirmed at the bottom.

---

### Structure of This Synthesis

The two experts addressed different layers. Expert A invalidated or corrected three metric implementations. Expert B confirmed three architectural crash/failure points and provided safe resolution strategies. Below I map each finding to a concrete decision or action, then produce a corrected implementation order.

---

### Expert A Findings — DSP Corrections

**Finding A1 — HNR is unreliable when stem bleed is present (confirmed, not dismissible)**

Expert A's diagnosis is unambiguous: BS-Roformer bleed on dense low-mid content will depress HNR by the same mechanism as genuine vocal breathiness — the autocorrelation algorithm cannot distinguish aperiodic leaked energy from aperiodic glottal noise. The failure is _silent_ — the number looks plausible but means something else.

The corrective intervention is not a code fix; it is a **reporting constraint**: HNR must always be cross-referenced against VAR in the same window. If VAR is negative (instrumental louder than vocal in the presence band) at the same moment HNR drops, the HNR reading is likely an artefact of bleed. The LLM briefing block must carry this caveat explicitly — it cannot treat HNR in isolation.

_Consequence for implementation:_ HNR and VAR must be computed together and reported together. They cannot be added to the output as independent metrics.

---

**Finding A2 — Pitch confidence conflates pitch quality with phonation density (corrected implementation required)**

The proposal's framing ("low mean = pitch instability, high std dev = erratic") is incorrect as stated. Expert A confirms: if `voiced_prob` is averaged across all frames including unvoiced consonants, the statistic measures the _proportion of voiced frames_, not pitch quality. For Classical Arabic specifically, the high density of pharyngeals and uvular fricatives (ع, ح, خ, ق) will systematically drag the mean down and spike the std dev — not because pitch is erratic, but because Arabic has correct, dense consonant distribution.

The corrected implementation requires two separate statistics:

1. **Pitch tracking confidence** — mean and std dev of `voiced_prob` restricted to frames where `voiced_flag == True`. Low confidence during voiced frames = genuine pitch ambiguity.
2. **Pitch stability** — variance or derivative of the `f0` array, again only during voiced frames. This is what detects melodic drift, not `voiced_prob` at all.

_Consequence for implementation:_ `librosa.pyin` returns all three arrays (`f0`, `voiced_flag`, `voiced_prob`). The implementation must use `voiced_flag` as a mask on both statistics. The proposal's original formulation must be discarded.

---

**Finding A3 — VAR from fractional energies is mathematically invalid (new helper function required)**

Expert A's proof is definitive. `_band_energy_fraction()` normalises by each stem's own total power — a whisper with 80% of its energy in the presence band and a roaring instrumental with 20% in the same band would produce a ratio of 4:1 favouring the vocal, while acoustically the vocal is completely buried.

The required fix is a new helper function — Expert A names it `_band_absolute_power()` — that computes absolute power (or absolute RMS) in the band without the `/ total_power` division. VAR is then:

```
VAR_dB = 10 * np.log10(absolute_vocal_band_power / absolute_inst_band_power)
```

This function sits alongside `_band_energy_fraction()` in `extractor.py` and is only called for VAR computation. The existing fractional functions are correct for their use cases and must not be changed.

---

### Expert B Findings — Architectural Corrections

**Finding B1 — Three-signal pipeline requires an explicit architecture decision**

Expert B confirms: `profiler.analyze_chunk()` has no concept of sub-tracks, and the reference profile cache (`reference_profile.json`) only covers the mix. Running stem analysis with delta columns requires UVR5 separation of the reference track too — which means three reference profiles (mix, vocal, instrumental) and three separate `analyze_chunk()` calls per run.

Expert B presents two clean options:

| Option                     | UVR5 on reference? | Stems get delta column? | Changes to scorer/config?        | Complexity |
| -------------------------- | ------------------ | ----------------------- | -------------------------------- | ---------- |
| **A — Full Stem QA**       | Yes                | Yes                     | Yes — new stem thresholds needed | High       |
| **B — Raw Stem Reporting** | No                 | No                      | None                             | Low        |

**This is a design decision that must be made before any code is written for Extension A.** Neither option is wrong — Option B is a significant scope reduction but it is backward-compatible and can be shipped much faster. Option A is the "correct" implementation but requires stem-specific threshold calibration that doesn't exist yet and would require real audio runs before it could be made authoritative.

My read: **Option B is the correct starting point.** The three-table structure gives the LLM the cross-referencing capability described in the proposal (the presence-band example: 0.167 mix / 0.091 vocal / 0.241 instrumental) without requiring threshold calibration for stems that hasn't been done. Option A can be layered on later once stem raw values have been observed across several real runs.

---

**Finding B2 — Windowed metrics will crash the scorer (hard crash, not silent)**

Expert B confirms: `scorer.score_chunk()` calls `abs(delta)` on every value in `deltas`. A list in `deltas["hnr_windowed"]` raises `TypeError: bad operand type for abs(): 'list'` immediately. This is not a silent failure — it is a hard crash.

The resolution requires a **schema change in `extractor.py`'s output contract**: separate scalar and windowed data into distinct keys. Expert B's proposed schema is clean and correct:

```python
# extractor.py output (new contract for vocal stem only)
{
    "scalars": { "lufs": ..., "mean_hnr": 12.4, ... },
    "windowed": { "hnr": [...], "pitch_confidence": [...], ... }
}
```

The `deltas` dict in `profiler.py` must only ever receive scalars. Windowed data passes through a new key (`windowed_chunk`, `windowed_ref`) directly to `reporter.py`, bypassing the scorer entirely.

**This is the most architecturally invasive change in the entire proposal.** It is a breaking change to the existing data contract. It should be implemented as a parallel path for stem data only — the existing mix-level pipeline's flat dict remains unchanged, avoiding any risk to the working QA/batch/ceiling/style-gap modes.

---

**Finding B3 — Config alignment invariant requires new entries before scorer sees new metrics**

Expert B confirms the import-time invariant in `config.py`: `set(THRESHOLDS) == set(WEIGHTS)` is checked at import. Any new scalar metric that flows into the scorer must have entries in both dicts or the import raises `ValueError`.

The safe resolution is exact: add all 5 new metrics with `threshold: 999.0, weight: 0.0`. This satisfies the invariant, prevents any score impact while thresholds are uncalibrated, and makes the metrics visible in reports for observation. This is the same pattern already used for `tempo`.

Expert B also flags a **silent failure risk**: if the 5 new metrics are added to `extractor.py` but not to `config.py`, the scorer silently ignores them (it iterates over `THRESHOLDS`, not `deltas`). No crash — the metrics simply vanish from scoring. The `999.0 / 0.0` pattern is the correct guard against this.

---

### Corrected Implementation Order

Based on both experts combined, the proposal's recommended order needs adjustment:

| Step | Task                                                            | Notes                                                                                     |
| ---- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 0    | **Architecture decision: Option A or B for stem pipeline**      | Must be decided before writing any code                                                   |
| 1    | **`_band_absolute_power()` helper in `extractor.py`**           | Prerequisite for VAR — Expert A A3                                                        |
| 2    | **UVR5 stem separation hook in `main.py`**                      | New pre-processing layer; does not touch existing pipeline paths                          |
| 3    | **HNR via `parselmouth` on vocal stem**                         | Add as scalar summary (`mean_hnr`) for scorer; add to `config.py` with `999.0 / 0.0`      |
| 4    | **VAR computation** using `_band_absolute_power()`              | Expert A A3 correction                                                                    |
| 5    | **Pitch confidence (masked to `voiced_flag`)** — two statistics | Expert A A2 correction — both `pitch_confidence_voiced` and `pitch_stability_f0_variance` |
| 6    | **Spectral flatness of vocal stem**                             | Straightforward once stem exists                                                          |
| 7    | **F0 range (min/max/range)**                                    | Straightforward once pyin is running                                                      |
| 8    | **Config entries for all 5 new metrics**                        | `999.0 / 0.0` — do this in the same commit as step 3–7                                    |
| 9    | **Windowed schema change** (Extension B)                        | Only after scalar stem metrics are stable — breaking change, separate PR                  |
| 10   | **Reporter updates** for three-table output and windowed CSV    | Follows step 9                                                                            |
| 11   | **Reference library** (Extension C)                             | Defer until 5+ approved reference tracks exist                                            |

---

### One Open Decision for You

Before any code is written, the following must be decided:

> **Option A or Option B for the stem pipeline?**
>
> - **Option B (Raw Stem Reporting):** UVR5 separates the chunk only. Stems show raw feature values — no delta column, no score. The LLM gets the three-table cross-reference capability immediately, with no threshold calibration required. Fully backward-compatible.
> - **Option A (Full Stem QA):** UVR5 separates both reference and chunk. Stems get delta and score columns. Requires stem-specific threshold calibration that doesn't exist yet. Higher complexity, higher eventual value.

My recommendation is Option B first, with Option A as a planned future upgrade. But this is your call — it determines the scope of everything that follows.

---

### Complete File Inventory — Session 12

| File                                   | Status |
| -------------------------------------- | ------ |
| `Session_11_Handover.md`               | ✅     |
| `audio_qa_brief.md`                    | ✅     |
| `README.md`                            | ✅     |
| `audio_analysis_extension_proposal.md` | ✅     |
| `experts_data.json`                    | ✅     |
| `ANSWERS_EXPERT_A.md`                  | ✅     |
| `ANSWERS_EXPERT_B.md`                  | ✅     |
| `src/extractor.py`                     | ✅     |
| `src/profiler.py`                      | ✅     |
| `src/scorer.py`                        | ✅     |
| `src/config.py`                        | ✅     |
| `src/reporter.py`                      | ✅     |
| `src/main.py`                          | ✅     |

No files outstanding. Ready to proceed once the Option A/B decision is made.
