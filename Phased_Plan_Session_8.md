# AUDIO-QA — Session 8 Phased Plan
## Expert Remediation: Two Bug Fixes + Validation

**Prepared:** 2026-05-16
**Authority documents:** `EXECUTIVE_SUMMARY.md`, `EXPERT_A_ANSWERS.md`, `EXPERT_B_ANSWERS.md`, `EXPERT_C_ANSWERS.md`
**Baseline:** All Phase 1–6 deliverables complete and validated. No regressions permitted.

---

## 1. Executive Summary & Locked Decisions

### Current State vs. Goal

| | |
|---|---|
| **Current state** | Two measurement bugs exist in `extractor.py` and `profiler.py`. MFCC distance is a loudness proxy, not a timbre metric. Stereo width is an absolute amplitude difference, not an amplitude-normalised spatial metric. All batch scores from previous sessions are corrupted by these two bugs. |
| **Goal (this session)** | Fix both bugs with minimum-change surgical edits. Re-run the full batch. Regenerate `summary.md`. Add a documentation note to `README.md`. The project must remain in a fully runnable state after every phase. |

### Locked Decisions (not open for debate)

| Decision | Resolution | Source |
|---|---|---|
| MFCC fix location | `profiler.py::analyze_chunk()` and `main.py::run_ceiling()` — NOT `extractor.py` | Code audit: extraction is correct; distance formula is the bug |
| MFCC fix formula | `cosine(chunk_mfccs[1:], ref_mfccs[1:])` — drop C0, cosine distance on C1–C12 | Expert A + Executive Summary |
| `mfcc_deltas` (13-element list) | Leave untouched in both bugs — it is display-only, not used in scoring | Code audit: `scorer.py` only reads `mfcc_distance` scalar |
| Stereo width fix location | `extractor.py::extract_features()` — stereo branch only | Expert A + code audit |
| Stereo width fix formula | Side/Mid RMS ratio with `1e-9` epsilon | Expert A |
| Mono branch | `stereo_width = 0.0` (mono branch in `extractor.py`) — do NOT touch | Existing validated behaviour |
| `stereo_width` threshold value | Do NOT change `±0.15` in `config.py` yet — add watch point comment only; recalibrate after batch re-run | Executive Summary: "document and defer" |
| `scorer.py` | No changes — reads `mfcc_distance` as an opaque scalar; formula is metric-agnostic | Code audit |
| `reporter.py` MFCC table | All 13 coefficients remain in the display table; add one footnote line only | Code audit: C0 shown for transparency; distance formula change needs labelling |
| Crest factor → LRA | Backlog. Do not implement, do not scaffold | Executive Summary |
| Ceiling threshold validation | Backlog. Do not implement, do not scaffold | Executive Summary |
| Median reference profile | Workflow-only; no code changes; out of scope for this session | Executive Summary |

---

## 2. Pre-coding Checklist & Hard Gate

Run every command below before touching any source file. All must pass.

**Step A — Verify scipy is available**
```bash
python -c "from scipy.spatial.distance import cosine; print('scipy OK')"
```
Expected output: `scipy OK`
If it fails: `pip install scipy` — do not proceed without it.

**Step B — Verify all source files are present**
```bash
ls src/extractor.py src/profiler.py src/main.py src/config.py src/scorer.py src/reporter.py
```
Expected: all six listed without error.

**Step C — Run baseline self-identity check (establish pre-fix baseline)**
```bash
cd src
python profiler.py data/audio/REF_01.mp3 data/audio/REF_01.mp3
```
Expected: `Self-identity: MFCC distance = 0.00000000  OK` and `Phase 2 PASSED`.
Record the pre-fix `mfcc_distance` output from a real chunk for comparison after fixes.

**Step D — Delete the reference profile cache**
```bash
rm -f src/reference_profile.json
```
The cache stores stereo_width computed with the old formula. It must be regenerated after the Bug 2 fix to avoid a stale cached value corrupting all downstream scores.

> **HARD GATE:** Do not proceed to Phase 1 if any step above fails or cannot be resolved.

---

## 3. Phase 1 — Fix Bug 1: MFCC Distance

**Files changed:** `profiler.py`, `main.py`
**Files NOT changed:** `extractor.py`, `config.py`, `scorer.py`, `reporter.py`
**Effort:** ~10 minutes
**Risk:** Medium — highest-weighted feature (1.5); self-identity stop condition depends on this formula

### Task 1.1 — Add scipy import to `profiler.py`

**File:** `src/profiler.py`
**Location:** Top of file, imports block (after `import numpy as np`, currently line ~6)

Add exactly one line:
```python
from scipy.spatial.distance import cosine
```

Do not touch any other import. Do not reorder imports.

### Task 1.2 — Replace MFCC distance formula in `profiler.py::analyze_chunk()`

**File:** `src/profiler.py`
**Function:** `analyze_chunk()`
**Exact target line** (currently reads):
```python
mfcc_distance = round(float(np.mean(np.abs(chunk_mfccs - ref_mfccs))), 6)
```

Replace with exactly:
```python
mfcc_distance = round(float(cosine(chunk_mfccs[1:], ref_mfccs[1:])), 6)
```

**Dangerous zone — DO NOT TOUCH:**
- The line immediately above: `mfcc_deltas = [round(float(d), 6) for d in (chunk_mfccs - ref_mfccs)]`
  — this uses all 13 coefficients intentionally; it is for the report display table, not the score.
- The `chunk_mfccs` and `ref_mfccs` array assignments immediately above the delta block.
- Anything outside the MFCC delta block.

**Invariant that must hold:** `mfcc_deltas` still contains 13 elements after this change.

### Task 1.3 — Fix ceiling MFCC distance in `main.py::run_ceiling()`

**File:** `src/main.py`
**Function:** `run_ceiling()`
**Location:** The function already contains `import numpy as np` at its top (local import, line ~184). Add the scipy import directly below it:
```python
from scipy.spatial.distance import cosine
```

**Exact target line** (currently reads, around line 210):
```python
mfcc_distance = float(np.mean(np.abs(chunk_mfccs - ceiling_mfccs)))
```

Replace with exactly:
```python
mfcc_distance = float(cosine(chunk_mfccs[1:], ceiling_mfccs[1:]))
```

Do not touch any other line in `run_ceiling()`.

### Phase 1 Success Criteria

| Check | Command | Expected result |
|---|---|---|
| Self-identity passes | `python profiler.py data/audio/REF_01.mp3 data/audio/REF_01.mp3` | `MFCC distance = 0.00000000  OK` and `Phase 2 PASSED` |
| No import error | `python -c "from profiler import analyze_chunk"` | No output / no error |
| Scorer still passes | `python scorer.py` | `PASS — zero deltas yield score 100.0` |

### Phase 1 Stop Condition

> **STOP** if `mfcc_distance` for reference vs itself is non-zero after the fix. `cosine(v, v)` must equal `0.0` for identical vectors. If it does not, the scipy installation is broken or the slice `[1:]` is producing empty arrays. Halt and investigate — do not proceed to Phase 2.

### Phase 1 Rollback

Revert the two changed lines in `profiler.py` and `main.py` to their original formulas. The original `np.mean(np.abs(...))` is always recoverable.

---

## 4. Phase 2 — Fix Bug 2: Stereo Width

**Files changed:** `extractor.py`, `config.py`
**Files NOT changed:** `profiler.py`, `main.py`, `scorer.py`, `reporter.py`
**Effort:** ~10 minutes
**Risk:** Low — formula is self-contained; mono branch is separate and untouched

### Task 2.1 — Replace stereo width formula in `extractor.py::extract_features()`

**File:** `src/extractor.py`
**Function:** `extract_features()`
**Location:** Stereo branch (inside `if is_stereo:` block)

**Exact target line** (currently reads):
```python
stereo_width = float(np.mean(np.abs(L - R)))
```

Replace with exactly:
```python
mid  = (L + R) / 2.0
side = (L - R) / 2.0
stereo_width = float(np.sqrt(np.mean(side**2)) / (np.sqrt(np.mean(mid**2)) + 1e-9))
```

**Dangerous zone — DO NOT TOUCH:**
- The line immediately above: `L, R = y[0], y[1]` — must remain exactly as-is.
- The `else:` branch for mono files — `stereo_width = 0.0` and its INFO log — must remain exactly as-is.
- Nothing else in `extract_features()` is touched.

**Invariant that must hold:** For a mono file, `stereo_width` must still return `0.0`. The mono branch is a separate `else:` block and is not affected by this change, but verify it after the edit.

### Task 2.2 — Add calibration watch point to `config.py`

**File:** `src/config.py`
**Location:** The `CALIBRATION WATCH POINTS` comment block, immediately after the existing watch-point entries (after the `mfcc_distance` entry, before the closing `# ---` line).

Add exactly these lines to the comment block:
```python
#   stereo_width ±0.15 — RECALIBRATION REQUIRED after Session 8 fix.
#                         Previous metric: mean(abs(L - R)) — absolute amplitude, not normalised.
#                         New metric: Side/Mid RMS ratio — scale approximately [0.0, 1.0+].
#                         ±0.15 was calibrated against the old metric and is no longer valid.
#                         Run full batch after fix, observe actual S/M ratio deltas,
#                         and reset this threshold before treating stereo scores as authoritative.
```

Do NOT change the value `0.15`. Do NOT touch `WEIGHTS`, `CEILING_THRESHOLDS`, or any other entry.

### Phase 2 Success Criteria

| Check | Command | Expected result |
|---|---|---|
| Stereo file returns non-zero width | `python extractor.py data/audio/REF_01.mp3` | `stereo_width` is a positive float (not 0.0) |
| Mono file still returns 0.0 | Visual check of `is_stereo` branch after edit | `stereo_width = 0.0` line in `else:` block is unchanged |
| Extractor validation block passes | `python extractor.py data/audio/REF_01.mp3` | `VALIDATED -- proceed to Phase 2` |
| config.py imports cleanly | `python -c "from config import THRESHOLDS, WEIGHTS, CEILING_THRESHOLDS"` | No output / no error |

### Phase 2 Stop Condition

> **STOP** if `stereo_width` returns `0.0` for a stereo file (the two-channel WAV or MP3 files in `data/audio/`). This would indicate the formula change accidentally landed in the wrong branch. Halt, revert Task 2.1, and re-examine the branch structure.

### Phase 2 Rollback

Revert the three changed lines in `extractor.py` to the original `stereo_width = float(np.mean(np.abs(L - R)))`. Revert the config.py comment addition (comment-only, no functional risk).

---

## 5. Phase 3 — Reporter Note (Documentation)

**Files changed:** `reporter.py`
**Files NOT changed:** All others
**Effort:** ~5 minutes
**Risk:** Negligible — comment/note addition only; no logic changes

### Task 3.1 — Add C0 exclusion footnote to `_section_mfcc_detail()`

**File:** `src/reporter.py`
**Function:** `_section_mfcc_detail()` (lines 300–324)
**Location:** After the closing `lines.append("")` (line 323), before the `return` statement.

The MFCC detail table displays all 13 coefficients including C0 (labeled "energy"). After the Bug 1 fix, C0 is excluded from the distance calculation but remains visible in the table for transparency. Add one footnote line so the report reader is not confused:

Replace this block at the end of `_section_mfcc_detail()`:
```python
    lines.append("")
    return "\n".join(lines)
```

With:
```python
    lines.append("")
    lines.append(
        "*Note: `MFCC distance` (scored feature) uses cosine distance on C02–C13 only. "
        "C01 (energy) is shown above for reference but is excluded from the distance calculation "
        "to prevent loudness differences from dominating the timbre metric.*"
    )
    lines.append("")
    return "\n".join(lines)
```

Do not touch any other line in `_section_mfcc_detail()` or anywhere else in `reporter.py`.

### Phase 3 Success Criteria

| Check | Method | Expected result |
|---|---|---|
| Note appears in report | Run single-chunk mode; inspect MFCC Detail section | Footnote visible below the 13-row coefficient table |
| No other report section changed | Diff against previous report output | Only the MFCC Detail section differs |
| reporter.py imports cleanly | `python -c "from reporter import generate_report"` | No output / no error |

---

## 6. Phase 4 — Validation & Batch Re-run

**Files changed:** None (read-only validation run)
**Effort:** ~15 minutes

### Task 4.1 — Self-identity check (regression guard)

```bash
cd src
python profiler.py data/audio/REF_01.mp3 data/audio/REF_01.mp3
```

Expected: `MFCC distance = 0.00000000  OK` and `Phase 2 PASSED`. If this fails after Phases 1–3, do not continue — a regression was introduced.

### Task 4.2 — Run full batch against WAV folder

```bash
cd src
python main.py --reference data/audio/REF_01.mp3 --batch data/audio/WAV/
```

Expected:
- A new `reference_profile.json` is generated (cache was deleted in pre-coding Step D).
- One `_report.md` per chunk in `reports/`.
- `reports/summary.md` is regenerated with updated scores.
- At least one score differs from the pre-fix batch (confirms the fixes had effect).

### Task 4.3 — Spot-check the scores

Compare new `summary.md` scores against the pre-fix scores (from the existing `reports/summary.md` before overwrite, or from memory of the Session 7 results). Confirm:

- MFCC-flagged features in the old run (e.g. FULL_qais_part_B_Edit at 7.28 distance) now show a cosine-scale distance instead of a MAE-scale distance. The number will be very different.
- Part C (76.5/100 in the old run) may score differently — record the new score.
- Stereo width deltas across all chunks will shift; note whether any new stereo flags appear (expected, given threshold ±0.15 is still calibrated for the old metric).

### Task 4.4 — Run ceiling analysis (regression check for Bug 1 Task 1.3)

```bash
cd src
python main.py --ceiling data/audio/elisa_maktooba_leek.mp3 --chunk data/audio/CHUNK_B.mp3
```

Expected: Report generates cleanly. MFCC distance value in the ceiling report reflects the cosine scale (will differ from the value in `ceiling_B.md` from Session 7).

### Phase 4 Stop Condition

> **STOP** if the batch run produces zero changed scores compared to the previous run. This indicates `reference_profile.json` was not regenerated (stale cache served old stereo_width value). Delete the cache and re-run. If scores still do not change, the fixes were not saved to disk correctly.

---

## 7. Phase 5 — README Documentation

**Files changed:** `README.md`
**Effort:** ~10 minutes

### Task 5.1 — Add cross-reference rule to Calibration Notes

**File:** `README.md`
**Location:** `## Calibration Notes` section, after the existing table of locked parameters.

Add one new subsection:

```markdown
### Presence Band Interpretation Rule

When a `presence_band` flag fires, cross-reference it with `low_mid_energy` in the same
chunk's report before treating it as a vocal recession:

- If `presence_band` drops **and** `low_mid_energy` spikes: the drop is likely caused by
  low-end energy inflating the total spectral power denominator, not by a genuinely recessed
  vocal. Check for bass buildup or proximity-effect rumble in this chunk.
- If `presence_band` drops **alone** (low-mid is within threshold): the vocal may genuinely
  have less 1k–4kHz cut-through. Consider re-generation or prompt adjustment.

Source: Expert B (Mastering), Session 8 consultation.
```

### Task 5.2 — Add stereo width recalibration note to Known Limitations

**File:** `README.md`
**Location:** `## Known Limitations` section, add a new bullet point.

```markdown
- **Stereo width threshold requires recalibration.** The `stereo_width` metric was corrected
  in Session 8 from an absolute amplitude formula to an amplitude-normalised Side/Mid RMS ratio.
  The threshold (±0.15 in `config.py`) was calibrated against the old formula and is no longer
  valid. Do not treat stereo width flags as authoritative until `THRESHOLDS["stereo_width"]`
  has been recalibrated against a batch run using the new metric.
```

Do not touch any other section of `README.md`.

### Phase 5 Success Criteria

Both additions are present in the file. No other section changed. Markdown renders cleanly (no broken table rows, no missing headers).

---

## 8. Strict Scope Boundaries

### In Scope — this session only

- Bug 1 fix: cosine distance on C1–C12 in `profiler.py` and `main.py`
- Bug 2 fix: Side/Mid RMS ratio in `extractor.py`
- `config.py` calibration watch point comment for `stereo_width`
- `reporter.py` C0 exclusion footnote in `_section_mfcc_detail()`
- Full batch re-run and `summary.md` regeneration
- `README.md` documentation additions (2 items)
- Session 8 Handover document

### Out of Scope — do not implement, do not scaffold

| Item | Reason |
|---|---|
| Crest factor → LRA replacement | Backlog; significant effort; Expert B confirmed current metric still catches gross failures |
| Ceiling threshold corpus validation | Backlog; requires 50+ labelled Suno outputs |
| Median reference profile from 5–8 seeds | Workflow-only; no code change; user does this manually before next production batch |
| STFT-based band energy (Expert A note) | Accepted limitation; fractional FFT with cross-reference rule is the interim mitigation |
| Spectral rolloff percentile change (0.85 → 0.95) | Accepted; labelling issue only; no recalibration planned this session |
| Any refactoring of `extractor.py`, `scorer.py`, `profiler.py` beyond the exact targets | Minimum-change rule — if it is not listed above, do not touch it |

---

## 9. Stop Conditions Summary

| Trigger | Action |
|---|---|
| Pre-coding checklist fails | Do not begin coding. Resolve the failure first. |
| `cosine(v, v) != 0.0` after Phase 1 | STOP. Scipy install or slice logic is broken. Rollback Phase 1. |
| `stereo_width == 0.0` for a stereo file after Phase 2 | STOP. Formula landed in wrong branch. Rollback Task 2.1. |
| Batch produces zero score changes vs pre-fix | STOP. Cache was not cleared. Delete `reference_profile.json` and re-run. |
| Any `import` error after any phase | STOP. A dependency or name error was introduced. Rollback last task. |
| `scorer.py` validation produces anything other than `PASS` | STOP. A regression reached the scoring layer. Rollback all changes. |

---

## 10. Session Handover Protocol

> This section is the standing protocol for all future sessions. Do not remove it from any handover document — always include it in full.
>
> At the end of every session, produce a `Session_N_Handover.md` file before closing. The file must fit on one page and cover: (1) What we did, (2) Artefacts produced, (3) Key decisions locked, (4) Current project state, (5) Next session work items, (6) Known issues / watch points.
>
> Rules: One page. Cut prose, not coverage. Do not count this protocol block toward the page limit — always include it in full. Produce the handover even if the session ended early or a phase was abandoned mid-way. The handover replaces memory — write it as if handing off to someone who has the plan and spec but has never seen the session conversation. File naming: `Session_N_Handover.md` where N increments per session. The incoming session must read the latest handover plus the current plan and spec before doing anything else. If none are attached, ask for them explicitly before proceeding. Keep all handover files alongside the project source files.
