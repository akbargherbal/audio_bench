# Phased Plan: Audio QA Extension — Option B (Raw Stem Reporting)

## 1. Executive Summary & Locked Decisions

**Current State:** The pipeline successfully extracts 12 mix-level features, scores them against a reference, and generates a Markdown report. It has no concept of stems.
**Goal:** Introduce an optional `--stems` flag for single-chunk runs that separates the chunk via UVR5, extracts 5 new vocal-specific metrics, and appends a raw three-column (Mix | Vocal | Inst) table to the report.

**Locked Decisions:**
| Decision | Resolution |
| :--- | :--- |
| **Architecture** | Option B (Raw Stem Reporting). Stem data bypasses `scorer.py` entirely. |
| **Config Safety** | `config.py` will **not** be modified. Stem metrics do not need `999.0/0.0` entries because they never enter the scorer. |
| **Batch Mode** | `--stems` is strictly disabled in `--batch` mode. Attempting to combine them will trigger an explicit CLI error. |
| **Extraction Contract** | `extract_features()` remains untouched. New metrics go into a separate `extract_vocal_stem_features()` function. |

---

## 2. Pre-Coding Checklists & Baseline Assumptions

**Environment Baselines:**
Before writing code, the environment must have the new dependencies installed:
```bash
pip install \"audio-separator[cpu]\" praat-parselmouth
```
*(Note: `audio-separator` is the standard Python wrapper for UVR5/BS-Roformer).*

**Assumption Checks:**
- `src/extractor.py` contains `_band_energy_fraction`.
- `src/main.py` contains `run_single` and `run_batch`.
- `src/reporter.py` contains `generate_report` and `generate_prompt_debug_report`.

**Hard Gates:**
- 🛑 **DO NOT PROCEED** to Phase 1 if `import parselmouth` or `from audio_separator.separator import Separator` fail in the Python REPL.

---

## 3. Risk-First, Strictly Ordered Phasing

### Phase 1: Core DSP & Stem Extraction (Highest Risk)
*Isolating the new math and dependencies before touching the pipeline.*

*   **Task 1.1: Absolute Power Helper.** In `src/extractor.py`, add `_band_absolute_power(y_mono, sr, f_low, f_high) -> float` directly below `_band_energy_fraction`.
    *   *Constraint:* Do not modify `_band_energy_fraction`.
*   **Task 1.2: Vocal Stem Extractor.** In `src/extractor.py`, add `extract_vocal_stem_features(filepath, inst_filepath) -> dict`.
    *   *Implementation:* Must compute HNR (via `parselmouth`), VAR (using Task 1.1), Pitch Confidence (masked by `voiced_flag`), Pitch Stability (F0 variance), and Spectral Flatness.
    *   *Constraint:* Do not modify the existing `extract_features()` function.

### Phase 2: Pipeline Integration (Medium Risk)
*Wiring the UVR5 hook and CLI.*

*   **Task 2.1: UVR5 Hook.** In `src/main.py`, add `_separate_stems(chunk_path) -> tuple[str, str]` using `audio-separator`.
*   **Task 2.2: CLI Updates.** In `src/main.py` `main()`, add the `--stems` boolean flag. Add validation to explicitly `sys.exit(1)` if `--stems` is used with `--batch`, `--ceiling`, or `--style-compare`.
*   **Task 2.3: Pipeline Wiring.** In `src/main.py` `run_single()`, accept `use_stems: bool`. If True, call `_separate_stems`, then run `extract_features` on both stems, and `extract_vocal_stem_features` on the vocal stem. Pass this new `stem_data` dict to the reporter.

### Phase 3: Reporter Updates (Low Risk)
*Rendering the new data.*

*   **Task 3.1: Stem Table Builder.** In `src/reporter.py`, add `_section_stem_table(stem_data: dict) -> str`. It must render a 3-column table (Mix | Vocal | Instrumental) with raw values only (no deltas, no flags).
*   **Task 3.2: Report Wiring.** Update `generate_report` and `generate_prompt_debug_report` to accept an optional `stem_data: dict = None` argument. If present, append the output of `_section_stem_table` just before the LLM Summary block.

---

## 4. Hyper-Specific Task Definitions & Dangerous Zones

*   **Dangerous Zone (`scorer.py`):** The scorer expects a flat dict of scalars. Stem data must be kept in a completely separate dictionary (`stem_data`) that is passed directly from `main.py` to `reporter.py`. It must **never** be merged into `analysis["deltas"]`.
*   **Minimum Change Rule:** When updating `main.py`'s `run_single`, do not refactor the existing `analyze_chunk` or `score_chunk` calls. Simply append the stem logic below them.

---

## 5. Verifiable Success Criteria

*   **Observable Proof 1 (CLI):** Running `python main.py --batch ./WAV/ --stems` immediately prints an error and exits.
*   **Observable Proof 2 (Execution):** Running `python main.py --reference REF.mp3 --chunk CHUNK.mp3 --stems` creates `_Vocals.wav` and `_Instrumental.wav` in the chunk's directory.
*   **Observable Proof 3 (Output):** The resulting Markdown report contains a new `## Stem Analysis` section with a table showing HNR, VAR, and Pitch metrics.
*   **Negative Check:** The `Consistency Score` and `Flagged Deviations` sections remain exactly identical whether `--stems` is used or not.

---

## 6. Stop Conditions & Rollback Plans

**Explicit Stop Conditions:**
1.  **STOP** if `audio-separator` throws an Out Of Memory (OOM) error or fails to download the BS-Roformer model.
2.  **STOP** if `scorer.py` throws a `TypeError` or `KeyError` during a `--stems` run (indicates stem data leaked into the scoring pipeline).
3.  **STOP** if `parselmouth` fails to read the temporary WAV files generated by UVR5.

**Rollback Plan:**
If Phase 1 or 2 fails fundamentally, run `git restore src/extractor.py src/main.py src/reporter.py` to revert to the audited mix-only state.

---

## 7. Strict Scope Boundaries

**In Scope:**
- UVR5 separation for single chunks.
- 5 new vocal-specific metrics.
- Raw 3-column reporting.

**Out of Scope (DO NOT IMPLEMENT):**
- Option A (Scoring stems or calculating deltas for stems).
- Extension B (Windowed/Time-series analysis).
- Extension C (Reference library).
- Modifying `config.py` or `scorer.py`.
- Running UVR5 on the reference track.

---

## 8. Session Handover Protocol

At the end of this and all future sessions, the assistant will generate a `Session_N_Handover.md` file containing:
1. What We Did
2. Artefacts Produced
3. Key Decisions Locked
4. Current Project State (Phase status)
5. Next Session Work Items
6. Known Issues / Watch Points
7. The standing Session Handover Protocol block.

