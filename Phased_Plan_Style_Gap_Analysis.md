# AUDIO-QA — Phased Plan: Style Gap Analysis Mode
**Feature:** `--style-compare` — Neutral mix-character briefing against a commercial reference  
**Session authored:** Session 10  
**Status:** Ready for implementation

---

## 1. Executive Summary & Locked Decisions

### Current State vs Goal

**Current state:** The tool has four modes — QA, Batch, Prompt Debug, and Ceiling Analysis. Ceiling mode already extracts features from a commercial track and a Suno chunk but frames output as binary red flags with wide thresholds and mandatory hygiene disclaimers. It is not designed for mix-character awareness.

**Goal:** Add a fifth mode — `--style-compare` — that produces a neutral, directional, threshold-free side-by-side comparison between a commercial track and a Suno chunk. Output is a paste-ready Markdown briefing the user hands to Claude (or another LLM) with the question: *"What do these numbers tell me about the mix character differences?"* No score. No verdict. No red flags. No thresholds. Just the data, framed perceptually.

---

### Locked Decisions

| Decision | Resolution | Rationale |
|---|---|---|
| New mode vs extending ceiling mode | **New mode** (`--style-compare`) | Ceiling mode framing is deliberately cautious and must stay untouched. Mixing the two purposes in one function would compromise both. |
| Features included | **10 of 12**: `lufs`, `rms`, `dynamic_range`, `spectral_centroid`, `spectral_rolloff`, `low_mid_energy`, `presence_band`, `high_shelf`, `stereo_width`, `mfcc_distance` | These 10 map to mix feel and production character. |
| Features excluded | **`tempo`** (unreliable on poetry), **`zcr`** (noise/distortion indicator — technical, not mix feel) | Consistent with the project's established reasoning on tempo. ZCR adds noise not signal to a mix-character discussion. |
| No thresholds | No entries in `config.py` for this mode | Thresholds imply pass/fail. This mode has no pass/fail — it shows direction and magnitude only. |
| No scoring | No call to `scorer.py` | Same reason. `scorer.py` is untouched. |
| `--style-compare` is single-chunk only | `--batch` is incompatible; exits with error | Consistent with `--ceiling` precedent. Batch requires a reference profile and scoring logic. |
| `--json` flag is supported | JSON output path follows `run_ceiling()` pattern | Consistent with all other modes. |
| No changes to `extractor.py`, `profiler.py`, `scorer.py`, `config.py` | Zero-touch | All new code lives in `reporter.py` and `main.py` only. |
| Report framing | "STYLE GAP BRIEFING — NOT A QA VERDICT" | Distinct from ceiling's "PRODUCTION HYGIENE CHECK". No ⚠/✓ flag symbols — no threshold to flag against. Direction arrows (`↑`/`↓`/`≈`) used instead. |
| LLM paste block | Present as the final section of the report | Mirrors existing LLM summary block pattern. Pre-loads genre context and a suggested LLM prompt. |

---

## 2. Pre-Coding Checklist

The incoming LLM **must** complete all items before touching any file.

```
[ ] 1. Read Session_9_Handover.md — confirm project state and locked calibration values.
[ ] 2. Read README.md — confirm file map and known limitations.
[ ] 3. Read this plan in full before writing a single line.
[ ] 4. Confirm the following files are present and unmodified from Session 9:
        extractor.py, profiler.py, scorer.py, config.py, reporter.py, main.py
[ ] 5. Run existing validation suite to confirm no regressions at baseline:
        python scorer.py            → must print "PASS" for both cases
        python extractor.py data/audio/REF_01.mp3  → must print "VALIDATED"
[ ] 6. Confirm reporter.py ends at line 925 with generate_ceiling_report().
        The last function in that file is the anchor point for Phase 1 additions.
[ ] 7. Confirm main.py: run_ceiling() ends at line 265.
        The import block for reporter is at lines 42–46.
        The --ceiling argparse block is at lines 554–563.
        The ceiling dispatch block is at lines 618–653.
```

**Hard Gate:** Do not proceed to Phase 1 if any checklist item fails.

---

## 3. Phases

### Phase 1 — `reporter.py`: `generate_style_compare_report()`

**Risk level:** Low. This is a pure function with no side effects. It does not call any other module. It cannot break existing modes. It is the safest place to start and can be tested with synthetic data before any CLI wiring exists.

**Files touched:** `reporter.py` only.

---

#### Task 1.1 — Add module-level constants

**Location:** `reporter.py`, after `_CEILING_FEATURE_ORDER` list (after line 626). Insert before `_get_ceiling_flag_label()`.

**Add exactly:**

```python
# ---------------------------------------------------------------------------
# Style Gap Analysis — feature order and exclusion list
# Source: Phased_Plan_Style_Gap_Analysis.md, Phase 1
#
# Excluded features and rationale:
#   tempo — unreliable on Arabic poetry (librosa beat estimation artefact)
#   zcr   — noise/distortion indicator; not a mix-character metric
# ---------------------------------------------------------------------------

_STYLE_COMPARE_FEATURE_ORDER: list[str] = [
    "lufs",
    "rms",
    "dynamic_range",
    "spectral_centroid",
    "spectral_rolloff",
    "low_mid_energy",
    "presence_band",
    "high_shelf",
    "stereo_width",
    "mfcc_distance",
]

_STYLE_COMPARE_EXCLUDED_DISPLAY: list[str] = [
    "Tempo (unreliable on poetry — librosa artefact)",
    "Zero crossing rate (noise indicator, not mix character)",
]
```

**Minimum change rule:** Add exactly these two constants. Do not modify `_CEILING_FEATURE_ORDER`, `_CEILING_EXCLUDED_DISPLAY`, or any surrounding code.

**Verify:** `len(_STYLE_COMPARE_FEATURE_ORDER) == 10`. Count manually before proceeding.

---

#### Task 1.2 — Add `_get_style_compare_note()` helper

**Location:** `reporter.py`, immediately after the two constants added in Task 1.1.

**Purpose:** Returns a plain-English perceptual note for each feature and direction. Tone is neutral and descriptive — not "flag" language, not "hygiene" language. No parenthetical disclaimers. The LLM reading this block will reason about significance; this function only labels direction.

**Add exactly:**

```python
def _get_style_compare_note(feature: str, delta: float) -> str:
    """
    Plain-English perceptual note for a style gap feature delta.

    Tone: neutral and directional. No pass/fail, no hygiene framing.
    The LLM receiving this briefing will reason about significance.
    """
    if feature == "lufs":
        return (
            "Suno track is quieter — sits lower in perceived loudness"
            if delta < 0
            else "Suno track is louder — sits higher in perceived loudness"
        )
    if feature == "rms":
        return (
            "Suno track has less overall energy"
            if delta < 0
            else "Suno track has more overall energy"
        )
    if feature == "dynamic_range":
        return (
            "Suno track is more compressed — less dynamic headroom"
            if delta < 0
            else "Suno track is less compressed — more dynamic breathing room"
        )
    if feature == "spectral_centroid":
        return (
            "Suno track is darker — tonal weight sits lower in the spectrum"
            if delta < 0
            else "Suno track is brighter — tonal weight sits higher in the spectrum"
        )
    if feature == "spectral_rolloff":
        return (
            "Suno track rolls off earlier — less high-frequency content"
            if delta < 0
            else "Suno track rolls off later — more high-frequency content"
        )
    if feature == "low_mid_energy":
        return (
            "Suno track has more low-mid energy (200–500 Hz) — warmer or muddier body"
            if delta > 0
            else "Suno track has less low-mid energy — thinner body, less warmth"
        )
    if feature == "presence_band":
        return (
            "Suno track has less presence (1k–4kHz) — vocal sits further back in mix"
            if delta < 0
            else "Suno track has more presence (1k–4kHz) — vocal sits more forward in mix"
        )
    if feature == "high_shelf":
        return (
            "Suno track has more high-shelf energy (8kHz+) — more air or sheen"
            if delta > 0
            else "Suno track has less high-shelf energy (8kHz+) — less air, darker top end"
        )
    if feature == "stereo_width":
        return (
            "Suno track is narrower — more centred, less spatial spread"
            if delta < 0
            else "Suno track is wider — more spatial spread"
        )
    if feature == "mfcc_distance":
        return "Overall timbral character distance from commercial reference"
    # Generic fallback
    direction = "above" if delta > 0 else "below"
    return f"Suno track is {direction} commercial reference on this metric"
```

**Minimum change rule:** Add exactly this function. Do not modify any existing function.

---

#### Task 1.3 — Add `generate_style_compare_report()`

**Location:** `reporter.py`, after `generate_ceiling_report()` (after line 924, the final `return` statement of that function). This is the last addition to `reporter.py`.

**Add exactly:**

```python
def generate_style_compare_report(
    chunk_name: str,
    style_name: str,
    chunk_feats: dict,
    style_feats: dict,
    deltas: dict,
) -> str:
    """
    Style Gap Analysis — neutral mix-character briefing report.

    Compares a Suno chunk against a commercial reference on 10 mix-relevant
    features. Produces no score, no verdict, no pass/fail flags. Output is
    a paste-ready Markdown briefing for LLM-assisted mix-character reasoning.

    Report sections (all always present):
        1. Header          — framing note, file names, feature count
        2. Feature table   — Commercial / Suno / Delta / Direction for 10 features
        3. Perceptual notes — plain-English directional description per feature
        4. LLM briefing block — paste-ready block with genre context and suggested prompt

    Args:
        chunk_name:   Chunk filename (display).
        style_name:   Commercial reference filename (display).
        chunk_feats:  Raw dict from extract_features() for the Suno chunk.
        style_feats:  Raw dict from extract_features() for the commercial track.
        deltas:       {feature: delta} for included features.
                      mfcc_distance must be pre-computed and present.

    Returns:
        str — complete Markdown style gap briefing.
    """
    n_features = len(_STYLE_COMPARE_FEATURE_ORDER)

    # ------------------------------------------------------------------
    # Section 1 — Header
    # ------------------------------------------------------------------
    header = "\n".join(
        [
            f"# Audio QA: Style Gap Briefing — {chunk_name}",
            "",
            "> **STYLE GAP BRIEFING — NOT A QA VERDICT**",
            f"> This report compares the mix character of **{chunk_name}** (Suno)",
            f"> against **{style_name}** (commercial reference).",
            "> No score. No pass/fail. No thresholds.",
            "> These are directional observations for mix-character awareness.",
            "> Paste the briefing block at the end into an LLM for interpretation.",
            "",
            "| | |",
            "|---|---|",
            f"| **Suno chunk** | {chunk_name} |",
            f"| **Commercial reference** | {style_name} |",
            f"| **Features compared** | {n_features} of 12 |",
            f"| **Features excluded** | tempo, zero crossing rate |",
            "",
        ]
    )

    # ------------------------------------------------------------------
    # Section 2 — Feature comparison table
    # ------------------------------------------------------------------
    rows: list[tuple] = []
    for key in _STYLE_COMPARE_FEATURE_ORDER:
        display = _FEATURE_DISPLAY[key]
        unit = _FEATURE_UNITS[key]
        delta = deltas[key]
        fmt = _FEATURE_FMT.get(key, ".4f")

        if key == "mfcc_distance":
            ref_str = format(0.0, fmt)
            chunk_str = format(delta, fmt)
        else:
            ref_str = format(style_feats[key], fmt)
            chunk_str = format(chunk_feats[key], fmt)

        sign = "+" if delta >= 0 else ""
        delta_str = f"{sign}{format(delta, fmt)}"

        # Direction arrow — neutral, no threshold required
        if abs(delta) < 1e-6:
            direction = "≈"
        elif delta > 0:
            direction = "↑ Suno higher"
        else:
            direction = "↓ Suno lower"

        rows.append((display, unit, ref_str, chunk_str, delta_str, direction))

    hdr = ("Feature", "Unit", "Commercial", "Suno", "Delta", "Direction")
    widths = [max(len(hdr[i]), max(len(r[i]) for r in rows)) for i in range(len(hdr))]

    def _row(*cells):
        return (
            f"| {cells[0]:<{widths[0]}} "
            f"| {cells[1]:<{widths[1]}} "
            f"| {cells[2]:>{widths[2]}} "
            f"| {cells[3]:>{widths[3]}} "
            f"| {cells[4]:>{widths[4]}} "
            f"| {cells[5]:<{widths[5]}} |"
        )

    sep = (
        f"| {'-'*widths[0]} "
        f"| {'-'*widths[1]} "
        f"| {'-'*widths[2]:>{widths[2]}} "
        f"| {'-'*widths[3]:>{widths[3]}} "
        f"| {'-'*widths[4]:>{widths[4]}} "
        f"| {'-'*widths[5]} |"
    )

    excluded_note = (
        f"*Not compared: {'; '.join(_STYLE_COMPARE_EXCLUDED_DISPLAY)}.*"
    )

    table_lines = ["## Feature Comparison", ""]
    table_lines += [_row(*hdr), sep]
    for r in rows:
        table_lines.append(_row(*r))
    table_lines += ["", excluded_note, ""]
    feature_table = "\n".join(table_lines)

    # ------------------------------------------------------------------
    # Section 3 — Perceptual notes
    # ------------------------------------------------------------------
    note_lines = ["## Perceptual Notes", ""]
    for key in _STYLE_COMPARE_FEATURE_ORDER:
        delta = deltas[key]
        display = _FEATURE_DISPLAY[key]
        unit = _FEATURE_UNITS.get(key, "")
        fmt = _FEATURE_FMT.get(key, ".4f")
        sign = "+" if delta >= 0 else ""
        d_str = f"{sign}{format(delta, fmt)}"
        d_with_unit = f"{d_str} {unit}".strip()
        note = _get_style_compare_note(key, delta)
        note_lines.append(f"- **{display}** `{d_with_unit}` — {note}")
    note_lines.append("")
    perceptual_notes = "\n".join(note_lines)

    # ------------------------------------------------------------------
    # Section 4 — LLM paste-ready briefing block
    # ------------------------------------------------------------------
    inner: list[str] = [
        f"STYLE GAP BRIEFING — {chunk_name} vs {style_name}",
        "",
        "Context:",
        f"  Suno track : {chunk_name}",
        f"              Classical Arabic Fusha vocal, deep Basso-Baritone,",
        f"              minimalist rock accompaniment. Generated with Suno AI.",
        f"  Commercial : {style_name}",
        f"              Used as a mix-character reference only.",
        f"              Genre differences are expected and intentional.",
        "",
        "Feature deltas (positive = Suno track higher than commercial):",
    ]

    for key in _STYLE_COMPARE_FEATURE_ORDER:
        delta = deltas[key]
        display = _FEATURE_DISPLAY[key]
        unit = _FEATURE_UNITS.get(key, "")
        fmt = _FEATURE_FMT.get(key, ".4f")
        sign = "+" if delta >= 0 else ""
        d_str = f"{sign}{format(delta, fmt)}"
        d_with_unit = f"{d_str} {unit}".strip()
        note = _get_style_compare_note(key, delta)
        inner.append(f"  {display:<30} {d_with_unit:<14} ({note})")

    inner += [
        "",
        "Features not compared: tempo (unreliable on poetry), zero crossing rate",
        "",
        "Question for LLM:",
        "  Based on these mix-character deltas, what do you notice about how",
        "  the Suno track differs from the commercial reference in terms of",
        "  general feel, mix balance, and production texture?",
        "  Focus on mix character only — not vocal performance or genre differences.",
        "",
        "Subjective note from user: [paste what you hear here]",
    ]

    summary_lines = [
        "## Style Gap Briefing Block",
        "",
        "> *Paste the block below directly into an LLM prompt.*",
        "",
        "```",
    ]
    summary_lines.extend(inner)
    summary_lines += ["```", ""]
    briefing_block = "\n".join(summary_lines)

    return "\n".join([header, feature_table, perceptual_notes, briefing_block])
```

**Minimum change rule:** Add exactly this function after `generate_ceiling_report()`. Do not modify `generate_ceiling_report()` or any code above it.

---

#### Phase 1 — Success Criteria

```
[ ] reporter.py imports cleanly: python -c "import reporter; print('OK')"
[ ] generate_style_compare_report is callable:
        python -c "from reporter import generate_style_compare_report; print('OK')"
[ ] Smoke test with synthetic data (run in src/ directory):
        python - <<'EOF'
        from reporter import generate_style_compare_report
        fake_feats = {
            "lufs": -14.0, "rms": 0.1, "dynamic_range": 12.0,
            "spectral_centroid": 2000.0, "spectral_rolloff": 4000.0,
            "low_mid_energy": 0.12, "presence_band": 0.20,
            "high_shelf": 0.05, "stereo_width": 0.40, "mfcc_distance": 0.0,
            "tempo": 100.0, "zcr": 0.05, "mfcc": [0.0]*13,
        }
        fake_deltas = {
            "lufs": -2.5, "rms": -0.03, "dynamic_range": 3.0,
            "spectral_centroid": -800.0, "spectral_rolloff": -1500.0,
            "low_mid_energy": 0.04, "presence_band": -0.06,
            "high_shelf": 0.01, "stereo_width": -0.10, "mfcc_distance": 0.12,
        }
        report = generate_style_compare_report(
            "CHUNK_C.wav", "elisa.mp3", fake_feats, fake_feats, fake_deltas
        )
        assert "STYLE GAP BRIEFING" in report
        assert "Feature Comparison" in report
        assert "Perceptual Notes" in report
        assert "Style Gap Briefing Block" in report
        assert len(report.splitlines()) > 40
        print("SMOKE TEST PASSED")
        EOF
[ ] Verify existing functions still importable:
        python -c "from reporter import generate_report, generate_prompt_debug_report, generate_ceiling_report; print('OK')"
```

**Stop condition:** If any check fails, do not proceed to Phase 2. Fix before moving on.

---

### Phase 2 — `main.py`: `run_style_compare()` + CLI wiring

**Risk level:** Medium. Touches the argparse dispatch block that routes all existing modes. The mutual exclusion validation (lines 602–616) must be expanded carefully — a mistake here silently breaks all modes.

**Files touched:** `main.py` only.

---

#### Task 2.1 — Expand the reporter import

**Location:** `main.py`, lines 42–46.

**Current:**
```python
from reporter import (
    generate_report,
    generate_prompt_debug_report,
    generate_ceiling_report,
)
```

**Replace with:**
```python
from reporter import (
    generate_report,
    generate_prompt_debug_report,
    generate_ceiling_report,
    generate_style_compare_report,
)
```

**Minimum change rule:** Add exactly one line (`generate_style_compare_report,`). Do not reorder or reformat the import block.

---

#### Task 2.2 — Add `run_style_compare()`

**Location:** `main.py`, after `run_ceiling()` ends at line 265, before `_collect_audio_files()` at line 268.

**Add exactly:**

```python
# ---------------------------------------------------------------------------
# Style Gap Analysis pipeline — Phase 7 (Style Gap)
# ---------------------------------------------------------------------------


def run_style_compare(
    style_path: str,
    chunk_path: str,
    output_json: bool = False,
) -> str:
    """
    Style Gap Analysis pipeline.

    Extracts features from both files, computes deltas for the 10 included
    mix-character features, and delegates report generation to
    reporter.generate_style_compare_report().

    No scoring. No thresholds. No pass/fail.

    Features excluded from comparison:
        tempo — unreliable on Arabic poetry
        zcr   — noise/distortion indicator, not mix character

    Args:
        style_path:  Path to the commercial reference audio file.
        chunk_path:  Path to the Suno chunk audio file to compare.
        output_json: If True, return a JSON string instead of Markdown.

    Returns:
        str — Markdown style gap report or JSON string.
    """
    import numpy as np
    from scipy.spatial.distance import cosine
    from extractor import extract_features

    _STYLE_COMPARE_INCLUDED = {
        "lufs", "rms", "dynamic_range", "spectral_centroid", "spectral_rolloff",
        "low_mid_energy", "presence_band", "high_shelf", "stereo_width",
    }  # mfcc_distance handled separately; tempo and zcr excluded

    for path, label in [(style_path, "Style reference"), (chunk_path, "Chunk")]:
        if not os.path.isfile(path):
            print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    style_name = os.path.basename(style_path)
    chunk_name = os.path.basename(chunk_path)

    print(
        f"  [STYLE] Extracting features from commercial reference: {style_name}",
        file=sys.stderr,
    )
    style_feats = extract_features(style_path)

    print(
        f"  [STYLE] Extracting features from chunk: {chunk_name}",
        file=sys.stderr,
    )
    chunk_feats = extract_features(chunk_path)

    # Compute MFCC cosine distance (C02–C13 only, matches ceiling and QA pipeline)
    style_mfccs = np.array(style_feats["mfcc"])
    chunk_mfccs = np.array(chunk_feats["mfcc"])
    mfcc_distance = float(cosine(chunk_mfccs[1:], style_mfccs[1:]))

    # Compute deltas for included scalar features
    deltas: dict[str, float] = {}
    for feature in _STYLE_COMPARE_INCLUDED:
        deltas[feature] = round(chunk_feats[feature] - style_feats[feature], 8)
    deltas["mfcc_distance"] = round(mfcc_distance, 6)

    if output_json:
        def _strip_mfcc(d: dict) -> dict:
            return {k: v for k, v in d.items() if k != "mfcc"}

        return json.dumps(
            {
                "mode": "style_compare",
                "chunk_name": chunk_name,
                "style_name": style_name,
                "n_features_compared": 10,
                "deltas": deltas,
                "chunk_values": _strip_mfcc(chunk_feats),
                "style_values": _strip_mfcc(style_feats),
            },
            indent=2,
        )

    return generate_style_compare_report(
        chunk_name=chunk_name,
        style_name=style_name,
        chunk_feats=chunk_feats,
        style_feats=style_feats,
        deltas=deltas,
    )
```

**Minimum change rule:** Insert exactly this function. Do not modify `run_ceiling()` or `_collect_audio_files()`.

---

#### Task 2.3 — Add `--style-compare` argparse argument

**Location:** `main.py`, after the `--ceiling` argument block (after line 563, before the mutually exclusive group for `--chunk`/`--batch` at line 566).

**Add exactly:**

```python
    parser.add_argument(
        "--style-compare",
        default=None,
        metavar="FILE",
        dest="style_compare",
        help=(
            "Commercial reference track for style gap analysis. "
            "Produces a neutral mix-character briefing — no score, no thresholds. "
            "Mutually exclusive with --reference and --ceiling. "
            "Use with --chunk only."
        ),
    )
```

**Minimum change rule:** Add exactly this argument block. Do not modify the `--ceiling` or `--reference` argument blocks.

---

#### Task 2.4 — Expand the mutual exclusion validation block

**Location:** `main.py`, lines 600–616. The current block validates `--reference` / `--ceiling` mutual exclusion.

**Current block (lines 600–616):**
```python
    # -- Validate --reference / --ceiling mutual exclusion -------------------
    has_reference = args.reference is not None
    has_ceiling = args.ceiling is not None

    if has_reference and has_ceiling:
        parser.error(
            "--reference and --ceiling are mutually exclusive. Use one or the other."
        )

    if not has_reference and not has_ceiling:
        parser.error(
            "One of --reference or --ceiling is required.\n"
            "  Standard QA / batch : --reference <file>\n"
            "  Ceiling analysis    : --ceiling <commercial_track>"
        )
```

**Replace with:**
```python
    # -- Validate --reference / --ceiling / --style-compare mutual exclusion -
    has_reference = args.reference is not None
    has_ceiling = args.ceiling is not None
    has_style_compare = args.style_compare is not None

    active_modes = sum([has_reference, has_ceiling, has_style_compare])

    if active_modes > 1:
        parser.error(
            "--reference, --ceiling, and --style-compare are mutually exclusive. "
            "Use exactly one."
        )

    if active_modes == 0:
        parser.error(
            "One of the following is required:\n"
            "  Standard QA / batch  : --reference <file>\n"
            "  Ceiling analysis     : --ceiling <commercial_track>\n"
            "  Style gap briefing   : --style-compare <commercial_track>"
        )
```

**Dangerous zone:** This block gates all mode dispatch. A mistake here breaks every existing mode. After replacing, verify that the three existing modes (QA, batch, ceiling) still parse correctly using the verification commands in the success criteria.

---

#### Task 2.5 — Add style-compare dispatch block

**Location:** `main.py`, after the ceiling dispatch block (after line 653, the `return` statement ending the ceiling block). Insert before the batch mode block.

**Add exactly:**

```python
    # -- Style Gap Analysis mode ---------------------------------------------
    if has_style_compare:
        if args.batch:
            print(
                "  [MAIN] ERROR: --style-compare is not supported in batch mode. "
                "Style gap analysis runs on a single chunk only.\n"
                "  Use: python main.py --style-compare <track.mp3> --chunk <chunk.mp3>",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.mode != "qa":
            print(
                f"  [MAIN] Note: --mode {args.mode} is ignored in style-compare mode.",
                file=sys.stderr,
            )

        print(f"\n{'='*64}", file=sys.stderr)
        print(f"  AUDIO-QA — Style Gap Analysis", file=sys.stderr)
        print(f"  Style ref : {args.style_compare}", file=sys.stderr)
        print(f"  Chunk     : {args.chunk}", file=sys.stderr)
        print(
            f"  Framing   : mix-character briefing only — NOT a QA verdict",
            file=sys.stderr,
        )
        print(f"{'='*64}\n", file=sys.stderr)

        report = run_style_compare(args.style_compare, args.chunk, args.json)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(report)
            print(
                f"  [MAIN] Style gap report written to: {args.output}",
                file=sys.stderr,
            )
        else:
            print(report)
        return
```

**Minimum change rule:** Insert exactly this block. Do not modify the ceiling dispatch block above it or the batch mode block below it.

---

#### Phase 2 — Success Criteria

```
[ ] Task 2.1: Import check
        python -c "from reporter import generate_style_compare_report; print('OK')"

[ ] Task 2.2: run_style_compare is importable
        python -c "from main import run_style_compare; print('OK')"

[ ] Task 2.3–2.5: Argparse smoke tests — all three flags parse without error
        python main.py --help
        Verify --style-compare appears in help output.

[ ] Regression — existing modes still parse (dry-run argparse only):
        python main.py --reference x.mp3 --chunk y.mp3 --help   → no error
        python main.py --ceiling x.mp3 --chunk y.mp3 --help     → no error

[ ] Mutual exclusion is enforced (expect parser errors, not crashes):
        python main.py --reference a.mp3 --ceiling b.mp3 --chunk c.mp3
        → must print "mutually exclusive" error

        python main.py --reference a.mp3 --style-compare b.mp3 --chunk c.mp3
        → must print "mutually exclusive" error

        python main.py --ceiling a.mp3 --style-compare b.mp3 --chunk c.mp3
        → must print "mutually exclusive" error

[ ] Batch rejection:
        python main.py --style-compare elisa_maktooba_leek.mp3 --batch data/audio/WAV/
        → must print "--style-compare is not supported in batch mode" and exit

[ ] End-to-end run against real files (run from src/):
        python main.py \
            --style-compare data/audio/elisa_maktooba_leek.mp3 \
            --chunk data/audio/WAV/FULL_qais_part_C.wav
        → Must produce Markdown output to stdout.
        → Output must contain all four section headers:
              "# Audio QA: Style Gap Briefing"
              "## Feature Comparison"
              "## Perceptual Notes"
              "## Style Gap Briefing Block"
        → Must NOT contain "Consistency Score", "PASS", "FAIL", "⚠", "✓"

[ ] JSON output works:
        python main.py \
            --style-compare data/audio/elisa_maktooba_leek.mp3 \
            --chunk data/audio/WAV/FULL_qais_part_C.wav \
            --json
        → Valid JSON. mode field = "style_compare". deltas has 10 keys.

[ ] File output works:
        python main.py \
            --style-compare data/audio/elisa_maktooba_leek.mp3 \
            --chunk data/audio/WAV/FULL_qais_part_C.wav \
            --output reports/style_gap_C.md
        → File created. Content matches stdout output above.

[ ] All existing modes still produce correct output (regression):
        python scorer.py         → PASS
        python main.py --reference data/audio/REF_01.mp3 --chunk data/audio/CHUNK_B.mp3
        → Markdown QA report, Consistency Score present, no crash
```

**Stop condition:** If the end-to-end run fails, or any regression check fails, halt and do not write `Session_10_Handover.md` as complete. Rollback by reverting `main.py` changes using git (`git checkout src/main.py`) and re-inspect.

---

## 4. Strict Scope Boundaries

### In Scope
- `reporter.py`: three additions (two constants, one helper, one public function)
- `main.py`: four additions (one import, one function, one argparse arg, one dispatch block) + one block replacement (mutual exclusion validation)

### Out of Scope — Do NOT implement, do NOT scaffold
- Any changes to `config.py` — no new threshold dict for this mode
- Any changes to `extractor.py`, `profiler.py`, `scorer.py`
- Batch support for `--style-compare`
- Any LLM API call from within the script
- A "style score" or numeric verdict in the output
- Auto-detection of genre context — genre note is hardcoded in the LLM block per the project's established workflow
- Any refactoring of existing functions, even if they look improvable
- README updates — document after confirming the feature works end-to-end

---

## 5. Rollback Plan

If Phase 2 leaves `main.py` in a broken state:

```bash
git checkout src/main.py
```

`reporter.py` additions are purely additive (new function, new constants) and do not affect existing code. Rolling back `main.py` is sufficient to restore all existing modes.

If `reporter.py` must also be rolled back:

```bash
git checkout src/reporter.py
```

---

## 6. README Update (Post-Implementation)

After all success criteria pass, add the following section to `README.md` under `## CLI Modes`, after the Ceiling Analysis section:

```markdown
### 5. Style Gap Analysis Mode

\`\`\`bash
python main.py --style-compare <commercial_track.mp3> --chunk <chunk.mp3>
python main.py --style-compare <commercial_track.mp3> --chunk <chunk.mp3> --output reports/style_gap.md
python main.py --style-compare <commercial_track.mp3> --chunk <chunk.mp3> --json
\`\`\`

**Purpose:** Neutral mix-character briefing. Compares 10 mix-relevant features between a Suno chunk and a commercial reference. No score, no thresholds, no pass/fail. Output is a paste-ready Markdown block for LLM-assisted mix-character reasoning.

**Features compared (10 of 12):** LUFS, RMS energy, Dynamic range, Spectral centroid, Spectral rolloff, Low-mid energy, Presence band, High shelf, Stereo width, MFCC distance.

**Explicitly excluded:** Tempo (unreliable on Arabic poetry), Zero crossing rate (noise indicator, not mix character).

**Report framing:** Every style gap report opens with "STYLE GAP BRIEFING — NOT A QA VERDICT." The commercial track values are not targets — they are mix-character context only. Genre differences are expected and intentional.

Single-chunk only — `--style-compare` with `--batch` errors explicitly.
```

Also update the **CLI Modes** table, the **File Map** section (no new files created by this mode), and the **What the Script Does NOT Do** section to add: *"Does not score Suno tracks against commercial production targets."*

---

## 7. Session Handover Protocol

> This section is the standing protocol for all future sessions. Do not remove it from any handover document — always include it in full.
>
> At the end of every session, produce a `Session_N_Handover.md` file before closing. The file must fit on one page and cover: (1) What we did, (2) Artefacts produced, (3) Key decisions locked, (4) Current project state, (5) Next session work items, (6) Known issues / watch points.
>
> Rules: One page. Cut prose, not coverage. Do not count this protocol block toward the page limit — always include it in full. Produce the handover even if the session ended early or a phase was abandoned mid-way. The handover replaces memory — write it as if handing off to someone who has the plan and spec but has never seen the session conversation. File naming: `Session_N_Handover.md` where N increments per session. The incoming session must read the latest handover plus the current plan and spec before doing anything else. If none are attached, ask for them explicitly before proceeding. Keep all handover files alongside the project source files.
