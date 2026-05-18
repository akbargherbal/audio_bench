# Session 14 Handover — AUDIO-QA

**Date:** 2026-05-18
**Session type:** Execution — Audio QA Extension (Option B)

---

## 1. What We Did

- Recovered session state after an unexpected crash.
- **Completed Phase 1 (Core DSP & Stem Extraction):** Added `_band_absolute_power()` helper and `extract_vocal_stem_features()` to `src/extractor.py`. Implemented HNR, VAR (dB), Pitch Confidence, Pitch Stability, and Spectral Flatness metrics with strict masking for voiced frames.
- **Completed Phase 2 (Pipeline Integration):** Added `_separate_stems()` UVR5 hook to `src/main.py`. Added the `--stems` CLI flag with strict mutual exclusion validation against `--batch`, `--ceiling`, and `--style-compare`. Wired `run_single()` to extract stem features and pass the isolated `stem_data` dict forward.

---

## 2. Artefacts Produced

| File                     | Description                                         | State      |
| :----------------------- | :-------------------------------------------------- | :--------- |
| `src/extractor.py`       | Added stem-specific DSP extraction functions        | ✅ Updated |
| `src/main.py`            | Added UVR5 separation hook and `--stems` CLI wiring | ✅ Updated |
| `Session_14_Handover.md` | This file                                           | ✅ Done    |

---

## 3. Key Decisions Locked This Session

| Decision                 | Resolution                                                                                                                                                                                          |
| :----------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Data Isolation**       | `stem_data` is passed as a completely separate keyword argument to the reporter. It strictly bypasses `scorer.py` and `analysis["deltas"]`, ensuring the core mix-level pipeline remains untouched. |
| **CLI Mutual Exclusion** | The `--stems` flag triggers an immediate `sys.exit(1)` if combined with `--batch`, `--ceiling`, or `--style-compare`.                                                                               |

---

## 4. Current Project State

| Phase                               | Status         |
| :---------------------------------- | :------------- |
| Phase 1: Core DSP & Stem Extraction | ✅ Complete    |
| Phase 2: Pipeline Integration       | ✅ Complete    |
| Phase 3: Reporter Updates           | 🔄 Not started |

---

## 5. Next Session Work Items

**Primary:** Complete Phase 3 (Reporter Updates) and run end-to-end verification.

1. **Pre-requisite:** User must provide `src/reporter.py` at session start.
2. **Phase 3, Task 3.1:** In `src/reporter.py`, add `_section_stem_table(stem_data: dict) -> str` to render the 3-column raw values table.
3. **Phase 3, Task 3.2:** Update `generate_report` and `generate_prompt_debug_report` signatures to accept `stem_data: dict = None` and append the table before the LLM summary block.
4. **Verification:** Run `python main.py --reference REF.mp3 --chunk CHUNK.mp3 --stems` to verify the observable proofs defined in the plan.

---

## 6. Known Issues / Watch Points

- **Temporary TypeError:** Running `main.py --stems` right now will raise a `TypeError` because `reporter.py` does not yet accept the `stem_data` argument passed by `main.py`. This is expected and will be resolved immediately in Phase 3.
- **UVR5 Model Download:** The first time `--stems` is run successfully, `audio-separator` will download the BS-Roformer model. This may take a moment depending on network speed.

---

> ### Session Handover Protocol
>
> This section is the standing protocol for all future sessions. Do not remove it from any handover document — always include it in full.
>
> At the end of every session, produce a `Session_N_Handover.md` file before closing. The file must fit on one page and cover: (1) What we did, (2) Artefacts produced, (3) Key decisions locked, (4) Current project state, (5) Next session work items, (6) Known issues / watch points.
>
> Rules: One page. Cut prose, not coverage. Do not count this protocol block toward the page limit — always include it in full. Produce the handover even if the session ended early or a phase was abandoned mid-way. The handover replaces memory — write it as if handing off to someone who has the plan and spec but has never seen the session conversation. File naming: `Session_N_Handover.md` where N increments per session. The incoming session must read the latest handover plus the current plan and spec before doing anything else. If none are attached, ask for them explicitly before proceeding. Keep all handover files alongside the project source files.
