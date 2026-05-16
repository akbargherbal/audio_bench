# Session 1 Handover — AUDIO-QA
**Date:** 2026-05-15
**Session type:** Phase 0 — Problem definition + Client Brief (complete)

---

## 1. What We Did

- Read user profile (`BULLET_PROFILE.md`), Arabic poem workflow (`arabic_workflow.md`), and prior SonicLens session analysis (`session_analysis.md`) to establish full project context
- Identified and named the core problem: **inter-chunk spectral/loudness inconsistency** across Suno-generated poem chunks, discovered too late (during or after Audacity assembly)
- Established two distinct use cases: **pre-assembly chunk QA** and **Suno prompt debugging**
- Defined the reference track: user's Happy Accident MP3 (not a commercial track — genre mismatch makes commercial tracks invalid as references)
- Resolved a scope question: vocal voice-type classification (Baritone/Tenor) was considered and **rejected** — unreliable without clean stem separation, and not the core problem. Production quality metrics are the priority
- Resolved format question: MP3 reference is acceptable — Suno export compression is uniform and will not skew comparative analysis
- Produced `audio_qa_brief.md` — full client brief with functional requirements

---

## 2. Artefacts Produced

| File | Role |
|---|---|
| `audio_qa_brief.md` | Complete client brief — problem definition, two use cases, FR-1 through FR-8, feature extraction table, output modes, technical constraints, definition of done |

---

## 3. Key Decisions

| Decision | Rationale |
|---|---|
| Happy Accident MP3 as reference | Only valid same-genre reference available |
| No vocal classification | Unreliable without stem separation; adds complexity without reliable payoff |
| MP3 input acceptable | Suno compression artifacts are uniform; won't skew comparative metrics |
| librosa + pyloudnorm as core libraries | Standard, well-supported, Colab-compatible |
| No GUI — CLI only | Consistent with user's tooling philosophy; avoids bloat |
| LLM-ready summary block (FR-6) | Critical bridge between script output and LLM-assisted diagnosis |

---

## 4. Current Project State

| Artefact | State |
|---|---|
| `audio_qa_brief.md` | ✅ Complete — ready to inform phased plan next session |
| Python script(s) | ❌ Does not exist — Phase 1+ deliverable |

Active phase: **Phase 0 complete ✅ — ready to proceed to Phased Plan + coding next session.**

---

## 5. Next Session Work Items

1. User to share a sample Phased Plan document (their standard template) before any coding begins
2. Incoming LLM reads `audio_qa_brief.md` and the sample Phased Plan
3. Produce a Phased Plan for this project based on the brief
4. Get user sign-off on the Phased Plan
5. Begin Phase 1 coding only after sign-off

**Do not begin coding before the Phased Plan is agreed. The brief is the input to the plan, not to the code directly.**

---

## 6. Known Issues / Watch Points

- **Demucs stem separation** — mentioned as a possibility for future vocal isolation analysis; not in current brief scope. If user later wants vocal-specific metrics, Demucs + `librosa.pyin` is the path, but reliability ceiling must be re-communicated clearly
- **Suno MP3 quality** — user is on free account; export quality may vary if Suno changes their encoding. Brief assumes consistent MP3 quality across all chunks from the same project
- **Threshold calibration (FR-4)** — deviation thresholds for the Consistency Score are configurable but not yet defined. These will need a calibration pass once the script runs against real chunks; initial values will be heuristic
- **FR-8 Prompt Implications mapping** — the mapping from measured deviations to Suno prompt causes requires a curated lookup table; this is a design decision to be made during the Phased Plan session, not assumed in code

---

## Session Handover Protocol

> **This section is the standing protocol for all future sessions. Do not remove it from the phased plan or from any handover document — always include it as a standard format.**

At the end of every session — whether a full phase is complete or not — produce a `Session_N_Handover.md` file before closing. The file must fit on one page and cover:

1. **What we did** — tasks completed, files changed, key decisions made
2. **Artefacts produced** — table of new/modified files and their role
3. **Key numbers** — inference call counts, OOM events, track counts processed, scored, failed
4. **Current project state** — which phase is active, what is the last confirmed working state of each script
5. **Next session work items** — ordered list, first command to run
6. **Known issues / watch points** — anything fragile, deferred, or asymmetric

**Rules:**

- One page. If it runs longer, cut prose, not coverage. Do not count this protocol block toward the page limit — always include it in full.
- Produce the handover even if the session ended early or a phase was abandoned mid-way — document what was attempted and what state the codebase is in.
- The handover replaces memory. Write it as if handing off to someone who has never seen the project — but who has access to the `audio_qa_brief.md`.
- File naming: `Session_N_Handover.md` where N increments per session, not per phase. Multiple sessions may cover the same phase.
- Keep all handover files in the project root alongside the source files.
- The incoming LLM for the next session must read the latest `Session_N_Handover.md` and the `audio_qa_brief.md` before doing anything else. If neither is attached, ask for them explicitly before proceeding.
- **Next session must also receive a sample Phased Plan document from the user before producing the project phased plan.**
