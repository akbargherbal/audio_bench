"""
main.py — Phase 3 / 4: CLI Entry Point
Audio QA — Classical Arabic Poem → Suno AI → Audacity Pipeline

Phase 3 — Task 3.3 : Single reference + single chunk pipeline.
Phase 4 — Task 4.1 : Batch mode (--batch <folder>) extension.

Usage (single):
    python main.py --reference <ref.mp3>  --chunk <chunk.mp3>
    python main.py --reference <ref.mp3>  --chunk <chunk.mp3>  --output report.md
    python main.py --reference <ref.mp3>  --chunk <chunk.mp3>  --json

Usage (batch):
    python main.py --reference <ref.mp3>  --batch <folder/>
    python main.py --reference <ref.mp3>  --batch <folder/>  --json

Batch output:
    reports/<chunk_stem>_report.md   — one Markdown report per chunk
    reports/<chunk_stem>_report.json — if --json is set
    reports/summary.md               — ranked table, worst chunk first

Reference profile caching:
    On first run, reference_profile.json is written to the working directory.
    On subsequent runs (including batch), if --reference matches the cached
    source, extraction is skipped. In batch mode, the reference is extracted
    once and reused for all chunks — not once per chunk.

Stop conditions:
    Single mode : Consistency Score < 50 — recalibrate config.py (Phase 3 plan).
    Batch mode  : More than one file fails to process — prominent warning is
                  printed to stderr; batch completes and errors appear in
                  summary.md.
"""

import argparse
import json
import os
import sys

from profiler import build_reference_profile, load_reference_profile, analyze_chunk
from scorer   import score_chunk
from reporter import generate_report, generate_prompt_debug_report, generate_ceiling_report
from config   import THRESHOLDS, WEIGHTS, CEILING_THRESHOLDS

_PROFILE_CACHE = "reference_profile.json"
_REPORTS_DIR   = "reports"
_AUDIO_EXTS    = {".mp3", ".wav"}

# Feature display names for the batch summary table.
# Mirrors reporter._FEATURE_DISPLAY — defined here to avoid importing a private
# symbol from reporter.py.
_SUMMARY_NAMES: dict[str, str] = {
    "lufs":              "LUFS",
    "rms":               "RMS energy",
    "dynamic_range":     "Dynamic range",
    "spectral_centroid": "Spectral centroid",
    "spectral_rolloff":  "Spectral rolloff",
    "low_mid_energy":    "Low-mid energy",
    "presence_band":     "Presence band",
    "high_shelf":        "High shelf",
    "stereo_width":      "Stereo width",
    "tempo":             "Tempo",
    "zcr":               "Zero crossing rate",
    "mfcc_distance":     "MFCC distance",
}


# ---------------------------------------------------------------------------
# Reference profile caching  (unchanged from Phase 3)
# ---------------------------------------------------------------------------

def _load_or_build_reference(reference_path: str) -> dict:
    """
    Load reference profile from cache if it was built from the same file.
    Otherwise build (and cache) a fresh profile.

    Comparison is on absolute paths to avoid false misses from relative vs
    absolute path differences across runs.
    """
    abs_ref = os.path.abspath(reference_path)

    if os.path.isfile(_PROFILE_CACHE):
        try:
            cached        = load_reference_profile(_PROFILE_CACHE)
            cached_source = os.path.abspath(cached.get("_source", ""))
            if cached_source == abs_ref:
                print(f"  [MAIN] Cache hit — using existing {_PROFILE_CACHE}")
                return cached
            else:
                print(f"  [MAIN] Cache miss — cached source is a different file.")
                print(f"         Cached : {cached_source}")
                print(f"         Current: {abs_ref}")
                print(f"  [MAIN] Rebuilding reference profile...")
        except Exception as exc:
            print(f"  [MAIN] Could not read cache ({exc}) — rebuilding.", file=sys.stderr)

    return build_reference_profile(reference_path, save_path=_PROFILE_CACHE)


# ---------------------------------------------------------------------------
# Core pipeline — single chunk  (unchanged from Phase 3)
# ---------------------------------------------------------------------------

def run_single(
    reference_path: str,
    chunk_path:     str,
    output_json:    bool = False,
    prompt_debug:   bool = False,
) -> tuple[str, float]:
    """
    Full pipeline: profiler → scorer → reporter for one chunk.

    Args:
        reference_path: Path to the reference audio file.
        chunk_path:     Path to the chunk audio file.
        output_json:    If True, return a JSON string instead of Markdown.
        prompt_debug:   If True, use generate_prompt_debug_report() which
                        appends the 'Suno Prompt Implications' section.

    Returns:
        (report_str, consistency_score) — score is returned so main() can
        apply the Phase 3 stop condition check without re-parsing the report.
    """
    for path, label in [(reference_path, "Reference"), (chunk_path, "Chunk")]:
        if not os.path.isfile(path):
            print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    ref_profile = _load_or_build_reference(reference_path)
    analysis    = analyze_chunk(chunk_path, ref_profile)
    score       = score_chunk(analysis, THRESHOLDS, WEIGHTS)
    chunk_name  = os.path.basename(chunk_path)

    if output_json:
        report_str = json.dumps(
            {
                "chunk_name": chunk_name,
                "analysis": {
                    "chunk_path":       analysis["chunk_path"],
                    "chunk_values":     analysis["chunk_values"],
                    "reference_values": analysis["reference_values"],
                    "deltas":           analysis["deltas"],
                },
                "score": score,
            },
            indent=2,
        )
    elif prompt_debug:
        report_str = generate_prompt_debug_report(chunk_name, analysis, score)
    else:
        report_str = generate_report(chunk_name, analysis, score)

    return report_str, score["consistency_score"]


# ---------------------------------------------------------------------------
# Ceiling Analysis pipeline — Phase 6
# ---------------------------------------------------------------------------

def run_ceiling(
    ceiling_path: str,
    chunk_path:   str,
    output_json:  bool = False,
) -> str:
    """
    Phase 6 — Ceiling Analysis pipeline (FR-9).

    Does NOT share code paths with the reference-based QA pipeline.
    Calls extract_features() directly on both files, computes deltas
    for the 9 included features, checks against CEILING_THRESHOLDS,
    and delegates report generation to reporter.generate_ceiling_report().

    Features excluded from comparison (genre-specific):
        high_shelf, stereo_width, tempo

    Args:
        ceiling_path: Path to the commercial reference audio file.
        chunk_path:   Path to the chunk audio file to evaluate.
        output_json:  If True, return a JSON string instead of Markdown.

    Returns:
        str — Markdown ceiling report or JSON string.
    """
    import numpy as np
    from extractor import extract_features

    for path, label in [(ceiling_path, "Ceiling reference"), (chunk_path, "Chunk")]:
        if not os.path.isfile(path):
            print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    ceiling_name = os.path.basename(ceiling_path)
    chunk_name   = os.path.basename(chunk_path)

    print(
        f"  [CEILING] Extracting features from commercial reference: {ceiling_name}",
        file=sys.stderr,
    )
    ceiling_feats = extract_features(ceiling_path)

    print(
        f"  [CEILING] Extracting features from chunk: {chunk_name}",
        file=sys.stderr,
    )
    chunk_feats = extract_features(chunk_path)

    # Compute MFCC distance — derived metric, not a raw feature from extract_features()
    ceiling_mfccs = np.array(ceiling_feats["mfcc"])
    chunk_mfccs   = np.array(chunk_feats["mfcc"])
    mfcc_distance = float(np.mean(np.abs(chunk_mfccs - ceiling_mfccs)))

    # Compute deltas and red flags for included features only
    deltas:    dict[str, float] = {}
    red_flags: list[str]        = []

    for feature, threshold in CEILING_THRESHOLDS.items():
        if feature == "mfcc_distance":
            delta = mfcc_distance
        else:
            delta = chunk_feats[feature] - ceiling_feats[feature]
        deltas[feature] = round(delta, 8)
        if abs(delta) > threshold:
            red_flags.append(feature)

    if output_json:
        # Strip mfcc list from values — too verbose for JSON summary
        def _strip_mfcc(d: dict) -> dict:
            return {k: v for k, v in d.items() if k != "mfcc"}

        return json.dumps(
            {
                "mode":           "ceiling",
                "chunk_name":     chunk_name,
                "ceiling_name":   ceiling_name,
                "red_flags":      red_flags,
                "n_checked":      len(CEILING_THRESHOLDS),
                "n_flags":        len(red_flags),
                "deltas":         deltas,
                "chunk_values":   _strip_mfcc(chunk_feats),
                "ceiling_values": _strip_mfcc(ceiling_feats),
            },
            indent=2,
        )

    return generate_ceiling_report(
        chunk_name=chunk_name,
        ceiling_name=ceiling_name,
        chunk_feats=chunk_feats,
        ceiling_feats=ceiling_feats,
        deltas=deltas,
        red_flags=red_flags,
        ceiling_thresholds=CEILING_THRESHOLDS,
    )

def _collect_audio_files(folder: str) -> list[str]:
    """
    Return a sorted list of absolute paths for all .mp3 / .wav files in folder.
    Sorting is alphabetical so run order is deterministic and matches typical
    chunk naming conventions (chunk_01, chunk_02, …).
    Subdirectories are ignored — flat scan only.
    """
    return sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and os.path.splitext(f)[1].lower() in _AUDIO_EXTS
    )


def _write_summary(results: list[dict]) -> None:
    """
    Write reports/summary.md.

    Layout:
        Ranked table — successful chunks sorted by Consistency Score ascending
                       (worst first).
        Error table  — appended below the ranked table if any chunk failed.

    Each result dict must contain:
        chunk_name  str         — filename
        score       float|None  — None when processing failed
        flagged     list[str]   — feature keys that were flagged (may be empty)
        error       str|None    — error message if failed, else None
    """
    successes = sorted(
        [r for r in results if r["error"] is None],
        key=lambda r: r["score"],
    )
    errors = [r for r in results if r["error"] is not None]

    lines: list[str] = [
        "# Audio QA — Batch Summary",
        "",
        "_Sorted by Consistency Score — worst first._",
        "",
        "| Rank | Chunk | Consistency Score | Flagged Features |",
        "|:----:|:------|------------------:|:-----------------|",
    ]

    for rank, r in enumerate(successes, start=1):
        flagged_display = (
            ", ".join(_SUMMARY_NAMES.get(f, f) for f in r["flagged"])
            if r["flagged"] else "—"
        )
        lines.append(
            f"| {rank} "
            f"| {r['chunk_name']} "
            f"| {int(r['score'])}/100 "
            f"| {flagged_display} |"
        )

    if errors:
        lines += [
            "",
            "### Processing Errors",
            "",
            "| Chunk | Error |",
            "|:------|:------|",
        ]
        for r in errors:
            err_msg   = r["error"]
            err_short = err_msg[:120] + "…" if len(err_msg) > 120 else err_msg
            lines.append(f"| {r['chunk_name']} | `{err_short}` |")

    lines.append("")

    summary_path = os.path.join(_REPORTS_DIR, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"  [BATCH] Summary written to: {summary_path}", file=sys.stderr)


def run_batch(reference_path: str, batch_folder: str, output_json: bool = False) -> None:
    """
    Batch pipeline: process all .mp3 / .wav files in batch_folder.

    The reference profile is loaded once and reused for every chunk — extraction
    happens at most once per batch run (or is served from cache).

    For each chunk:
        Runs profiler.analyze_chunk → scorer.score_chunk → reporter.generate_report
        Writes the report to reports/<chunk_stem>_report.md  (or .json if --json)

    After all chunks:
        Writes reports/summary.md sorted worst-first.

    Stop condition (plan Phase 4):
        If more than one file fails, a prominent warning is printed to stderr.
        The batch always completes — errors surface in summary.md.

    Args:
        reference_path: Path to the reference audio file (WAV or MP3).
        batch_folder:   Path to folder containing chunk audio files.
        output_json:    If True, write .json reports instead of .md.
    """
    # -- Validate inputs -----------------------------------------------------
    if not os.path.isfile(reference_path):
        print(f"ERROR: Reference file not found: {reference_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(batch_folder):
        print(f"ERROR: Batch folder not found: {batch_folder}", file=sys.stderr)
        sys.exit(1)

    audio_files = _collect_audio_files(batch_folder)

    if not audio_files:
        print(
            f"ERROR: No .mp3 or .wav files found in: {batch_folder}",
            file=sys.stderr,
        )
        sys.exit(1)

    # -- Setup ---------------------------------------------------------------
    os.makedirs(_REPORTS_DIR, exist_ok=True)
    report_ext = ".json" if output_json else ".md"

    print(f"\n{'='*64}", file=sys.stderr)
    print(f"  AUDIO-QA — Batch Mode", file=sys.stderr)
    print(f"  Reference : {reference_path}", file=sys.stderr)
    print(f"  Folder    : {batch_folder}", file=sys.stderr)
    print(f"  Chunks    : {len(audio_files)} file(s) found", file=sys.stderr)
    print(f"  Output    : {_REPORTS_DIR}/", file=sys.stderr)
    print(f"{'='*64}\n", file=sys.stderr)

    # -- Load reference ONCE (cache-aware) -----------------------------------
    ref_profile = _load_or_build_reference(reference_path)

    # -- Process each chunk --------------------------------------------------
    results: list[dict] = []
    error_count = 0

    for i, chunk_path in enumerate(audio_files, start=1):
        chunk_name      = os.path.basename(chunk_path)
        chunk_stem      = os.path.splitext(chunk_name)[0]
        report_filename = f"{chunk_stem}_report{report_ext}"
        report_path     = os.path.join(_REPORTS_DIR, report_filename)

        print(f"  [BATCH] ({i}/{len(audio_files)}) {chunk_name}", file=sys.stderr)

        try:
            analysis = analyze_chunk(chunk_path, ref_profile)
            score    = score_chunk(analysis, THRESHOLDS, WEIGHTS)

            if output_json:
                report_str = json.dumps(
                    {
                        "chunk_name": chunk_name,
                        "analysis": {
                            "chunk_path":       analysis["chunk_path"],
                            "chunk_values":     analysis["chunk_values"],
                            "reference_values": analysis["reference_values"],
                            "deltas":           analysis["deltas"],
                        },
                        "score": score,
                    },
                    indent=2,
                )
            else:
                report_str = generate_report(chunk_name, analysis, score)

            with open(report_path, "w", encoding="utf-8") as fh:
                fh.write(report_str)

            consistency_score = score["consistency_score"]
            flagged           = score["flagged_features"]
            flag_display      = (
                ", ".join(_SUMMARY_NAMES.get(f, f) for f in flagged) or "none"
            )

            print(
                f"           Score: {consistency_score}/100  "
                f"Flagged: {flag_display}",
                file=sys.stderr,
            )
            if consistency_score < 50:
                print(
                    f"           ⚠  Score below 50 — review this chunk carefully.",
                    file=sys.stderr,
                )

            results.append({
                "chunk_name": chunk_name,
                "score":      consistency_score,
                "flagged":    flagged,
                "error":      None,
            })

        except Exception as exc:
            error_count += 1
            error_msg = str(exc)
            print(f"           ERROR — {error_msg}", file=sys.stderr)
            results.append({
                "chunk_name": chunk_name,
                "score":      None,
                "flagged":    [],
                "error":      error_msg,
            })

    # -- Stop condition (plan Phase 4) ---------------------------------------
    if error_count > 1:
        print("", file=sys.stderr)
        print(
            f"  ⚠  STOP CONDITION — {error_count} files failed to process.",
            file=sys.stderr,
        )
        print(
            "     This exceeds the plan's tolerance of 1 failure.",
            file=sys.stderr,
        )
        print(
            "     Review errors above and in summary.md before treating "
            "these results as authoritative.",
            file=sys.stderr,
        )
        print("", file=sys.stderr)

    # -- Summary -------------------------------------------------------------
    _write_summary(results)

    processed = len(audio_files) - error_count
    print(
        f"\n  [BATCH] Done — {processed}/{len(audio_files)} chunk(s) processed "
        f"successfully.\n",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="audio-qa",
        description="Pre-assembly chunk consistency check against a reference track.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single chunk — Markdown report to stdout
  python main.py --reference happy_accident.mp3 --chunk chunk_01.mp3

  # Single chunk — save report to file
  python main.py --reference happy_accident.mp3 --chunk chunk_01.mp3 --output reports/chunk_01_report.md

  # Single chunk — JSON output
  python main.py --reference happy_accident.mp3 --chunk chunk_01.mp3 --json

  # Prompt debug mode
  python main.py --reference happy_accident.mp3 --chunk new_gen.mp3 --mode prompt-debug

  # Batch mode — process entire folder, Markdown reports
  python main.py --reference happy_accident.mp3 --batch ./chunks/

  # Batch mode — JSON reports
  python main.py --reference happy_accident.mp3 --batch ./chunks/ --json

  # Ceiling analysis — production hygiene red-flag check (Phase 6)
  python main.py --ceiling elisa_maktooba_leek.mp3 --chunk chunk_01.mp3
""",
    )

    parser.add_argument(
        "--reference", required=False, default=None,
        help=(
            "Reference audio file (WAV or MP3) — your 'Happy Accident' track. "
            "Required for all modes except --ceiling."
        ),
    )
    parser.add_argument(
        "--ceiling", default=None, metavar="FILE",
        help=(
            "Commercial reference track for production hygiene check (Phase 6). "
            "Mutually exclusive with --reference and --batch. "
            "Use with --chunk only."
        ),
    )

    # --chunk and --batch are mutually exclusive; exactly one is required.
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--chunk",
        metavar="FILE",
        help="Single chunk audio file to analyse (WAV or MP3).",
    )
    mode_group.add_argument(
        "--batch",
        metavar="FOLDER",
        help="Folder of .mp3/.wav chunk files to analyse in batch mode.",
    )

    parser.add_argument(
        "--output", default=None, metavar="FILE",
        help="[Single mode only] Write report to FILE instead of stdout.",
    )
    parser.add_argument(
        "--mode", default="qa", choices=["qa", "prompt-debug"],
        help=(
            "[Single mode only] 'qa' = standard QA report (default). "
            "'prompt-debug' = QA report + Suno Prompt Implications section. "
            "Ignored when --ceiling is set."
        ),
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of Markdown.",
    )

    args = parser.parse_args()

    # -- Validate --reference / --ceiling mutual exclusion -------------------
    has_reference = args.reference is not None
    has_ceiling   = args.ceiling   is not None

    if has_reference and has_ceiling:
        parser.error("--reference and --ceiling are mutually exclusive. Use one or the other.")

    if not has_reference and not has_ceiling:
        parser.error(
            "One of --reference or --ceiling is required.\n"
            "  Standard QA / batch : --reference <file>\n"
            "  Ceiling analysis    : --ceiling <commercial_track>"
        )

    # -- Ceiling mode (Phase 6) ----------------------------------------------
    if has_ceiling:
        if args.batch:
            print(
                "  [MAIN] ERROR: --ceiling is not supported in batch mode. "
                "Ceiling analysis runs on a single chunk only.\n"
                "  Use: python main.py --ceiling <track.mp3> --chunk <chunk.mp3>",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.mode != "qa":
            print(
                f"  [MAIN] Note: --mode {args.mode} is ignored in ceiling mode.",
                file=sys.stderr,
            )

        print(f"\n{'='*64}", file=sys.stderr)
        print(f"  AUDIO-QA — Ceiling Analysis (Phase 6)", file=sys.stderr)
        print(f"  Ceiling ref : {args.ceiling}", file=sys.stderr)
        print(f"  Chunk       : {args.chunk}", file=sys.stderr)
        print(
            f"  Framing     : production hygiene only — NOT a style match",
            file=sys.stderr,
        )
        print(f"{'='*64}\n", file=sys.stderr)

        report = run_ceiling(args.ceiling, args.chunk, args.json)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(report)
            print(f"  [MAIN] Ceiling report written to: {args.output}", file=sys.stderr)
        else:
            print(report)
        return

    # -- Batch mode ----------------------------------------------------------
    if args.batch:
        if args.output:
            print(
                "  [MAIN] Note: --output is ignored in batch mode. "
                "Reports are written automatically to reports/.",
                file=sys.stderr,
            )
        if args.mode == "prompt-debug":
            print(
                "  [MAIN] Note: --mode prompt-debug is not supported in batch mode. "
                "Run single-chunk mode for prompt debugging.",
                file=sys.stderr,
            )
        run_batch(args.reference, args.batch, args.json)
        return

    # -- Single mode (Phase 3 / 5 logic) ------------------------------------
    is_prompt_debug = args.mode == "prompt-debug"
    mode_label      = "Prompt Debug" if is_prompt_debug else "Single Chunk Analysis"

    print(f"\n{'='*64}", file=sys.stderr)
    print(f"  AUDIO-QA — {mode_label}", file=sys.stderr)
    print(f"  Reference : {args.reference}", file=sys.stderr)
    print(f"  Chunk     : {args.chunk}", file=sys.stderr)
    if is_prompt_debug:
        print(f"  Mode      : prompt-debug (Suno Prompt Implications enabled)", file=sys.stderr)
    print(f"{'='*64}\n", file=sys.stderr)

    report, consistency_score = run_single(
        reference_path=args.reference,
        chunk_path=args.chunk,
        output_json=args.json,
        prompt_debug=is_prompt_debug,
    )

    # Phase 3 stop condition (plan Section 3, Task 3.3)
    if consistency_score < 50:
        print("", file=sys.stderr)
        print("  ⚠  STOP CONDITION — Consistency Score is below 50", file=sys.stderr)
        print(f"     Score: {consistency_score}/100", file=sys.stderr)
        print("     If this chunk sounds correct to your ear:", file=sys.stderr)
        print("     → recalibrate THRESHOLDS in config.py before Phase 4.", file=sys.stderr)
        print("     → do not treat this score as authoritative.", file=sys.stderr)
        print("", file=sys.stderr)
    elif consistency_score < 65:
        print(
            f"\n  ℹ  Note: Score {consistency_score}/100 — review flagged features "
            f"before assembly.\n",
            file=sys.stderr,
        )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"  [MAIN] Report written to: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
