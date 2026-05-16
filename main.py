"""
main.py — Phase 3: CLI Entry Point
Audio QA — Classical Arabic Poem → Suno AI → Audacity Pipeline

Task 3.3 — Wire profiler → scorer → reporter for single reference + single chunk.

Usage:
    python main.py --reference <ref.mp3>  --chunk <chunk.mp3>
    python main.py --reference <ref.mp3>  --chunk <chunk.mp3>  --output report.md
    python main.py --reference <ref.mp3>  --chunk <chunk.mp3>  --json

Reference profile caching:
    On first run, reference_profile.json is written to the working directory.
    On subsequent runs, if --reference matches the cached source, extraction
    is skipped — the cached profile is loaded instead. This matters in batch
    use (Phase 4) where re-extracting the reference for every chunk is wasteful.

Stop condition (Phase 3, per plan):
    If Consistency Score < 50 for a chunk that sounds correct to the user's ear,
    a warning is printed to stderr. Recalibrate config.py before Phase 4.

Phase 4 (batch mode) will extend this file. Do not add batch logic here.
"""

import argparse
import json
import os
import sys

from profiler import build_reference_profile, load_reference_profile, analyze_chunk
from scorer   import score_chunk
from reporter import generate_report
from config   import THRESHOLDS, WEIGHTS

_PROFILE_CACHE = "reference_profile.json"

# ---------------------------------------------------------------------------
# Reference profile caching
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
# Core pipeline
# ---------------------------------------------------------------------------

def run_single(
    reference_path: str,
    chunk_path:     str,
    output_json:    bool = False,
) -> tuple[str, float]:
    """
    Full pipeline: profiler → scorer → reporter for one chunk.

    Args:
        reference_path: Path to the reference audio file.
        chunk_path:     Path to the chunk audio file.
        output_json:    If True, return a JSON string instead of Markdown.

    Returns:
        (report_str, consistency_score) — score is returned so main() can
        apply the Phase 3 stop condition check without re-parsing the report.
    """
    # Input validation
    for path, label in [(reference_path, "Reference"), (chunk_path, "Chunk")]:
        if not os.path.isfile(path):
            print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    # Step 1 — Reference profile (cached or fresh)
    ref_profile = _load_or_build_reference(reference_path)

    # Step 2 — Chunk analysis (deltas against reference)
    analysis = analyze_chunk(chunk_path, ref_profile)

    # Step 3 — Consistency score
    score = score_chunk(analysis, THRESHOLDS, WEIGHTS)

    # Step 4 — Report
    chunk_name = os.path.basename(chunk_path)

    if output_json:
        # JSON mode — emit full analysis + score dict.
        # Keeps mfcc_deltas as a plain list; mfcc in values as a plain list.
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

    return report_str, score["consistency_score"]


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
  # Basic run — Markdown report to stdout
  python main.py --reference happy_accident.mp3 --chunk chunk_01.mp3

  # Save report to file
  python main.py --reference happy_accident.mp3 --chunk chunk_01.mp3 --output reports/chunk_01_report.md

  # JSON output for downstream processing
  python main.py --reference happy_accident.mp3 --chunk chunk_01.mp3 --json
""",
    )

    parser.add_argument(
        "--reference", required=True,
        help="Reference audio file (WAV or MP3) — your 'Happy Accident' track.",
    )
    parser.add_argument(
        "--chunk", required=True,
        help="Chunk audio file to analyse (WAV or MP3).",
    )
    parser.add_argument(
        "--output", default=None, metavar="FILE",
        help="Write report to FILE instead of stdout. Parent directory must exist.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON (analysis + score) instead of Markdown report.",
    )

    args = parser.parse_args()

    print(f"\n{'='*64}", file=sys.stderr)
    print(f"  AUDIO-QA — Single Chunk Analysis", file=sys.stderr)
    print(f"  Reference : {args.reference}", file=sys.stderr)
    print(f"  Chunk     : {args.chunk}", file=sys.stderr)
    print(f"{'='*64}\n", file=sys.stderr)

    report, consistency_score = run_single(
        reference_path=args.reference,
        chunk_path=args.chunk,
        output_json=args.json,
    )

    # -----------------------------------------------------------------------
    # Phase 3 stop condition check (plan Section 3, Task 3.3)
    # If score < 50 for a chunk that SOUNDS correct: thresholds need
    # recalibration. Print prominent warning to stderr — does NOT suppress
    # the report, so the user can still read what fired.
    # -----------------------------------------------------------------------
    if consistency_score < 50:
        print("", file=sys.stderr)
        print("  ⚠  STOP CONDITION — Consistency Score is below 50", file=sys.stderr)
        print(f"     Score: {consistency_score}/100", file=sys.stderr)
        print("     If this chunk sounds correct to your ear:", file=sys.stderr)
        print("     → recalibrate THRESHOLDS in config.py before Phase 4.", file=sys.stderr)
        print("     → do not treat this score as authoritative.", file=sys.stderr)
        print("", file=sys.stderr)
    elif consistency_score < 65:
        print(f"\n  ℹ  Note: Score {consistency_score}/100 — review flagged features "
              f"before assembly.\n", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Output — file or stdout
    # -----------------------------------------------------------------------
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"  [MAIN] Report written to: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
