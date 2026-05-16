"""
profiler.py — Phase 2: Reference Profiling & Chunk Delta
Audio QA — Classical Arabic Poem → Suno AI → Audacity Pipeline

Task 2.1 — build_reference_profile(filepath) -> dict
Task 2.2 — analyze_chunk(chunk_path, reference_profile) -> dict

Does NOT implement scoring or flagging — raw deltas only.
Does NOT modify extractor.py — calls it, does not refactor it.
"""

import json
import os
import numpy as np
from scipy.spatial.distance import cosine

from extractor import extract_features

# ---------------------------------------------------------------------------
# Task 2.1 — Reference Profile Builder
# ---------------------------------------------------------------------------


def build_reference_profile(
    filepath: str, save_path: str = "reference_profile.json"
) -> dict:
    """
    Extract features from the reference track and return the profile dict.

    Optionally serialises to `save_path` (default: reference_profile.json)
    so subsequent batch runs can skip re-extracting the reference.

    The profile dict is the direct output of extract_features() with one
    additional key:
        "_source": the filepath used to build the profile

    Args:
        filepath:  Path to the reference audio file (WAV or MP3)
        save_path: Where to write the JSON cache. Pass None to skip saving.

    Returns:
        dict — feature profile of the reference track
    """
    print(f"  [PROFILER] Building reference profile from: {filepath}")
    profile = extract_features(filepath)
    profile["_source"] = filepath

    if save_path is not None:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        print(f"  [PROFILER] Reference profile saved to: {save_path}")

    return profile


def load_reference_profile(json_path: str) -> dict:
    """
    Load a previously saved reference profile from JSON.
    Use this to skip re-extraction on subsequent batch runs.

    Args:
        json_path: Path to reference_profile.json

    Returns:
        dict — feature profile (same structure as build_reference_profile output)
    """
    with open(json_path, "r", encoding="utf-8") as f:
        profile = json.load(f)
    print(f"  [PROFILER] Reference profile loaded from: {json_path}")
    print(f"  [PROFILER] Original source: {profile.get('_source', 'unknown')}")
    return profile


# ---------------------------------------------------------------------------
# Task 2.2 — Chunk Analyser
# ---------------------------------------------------------------------------


def analyze_chunk(chunk_path: str, reference_profile: dict) -> dict:
    """
    Extract features from a chunk and compute per-feature deltas against the
    reference profile.

    MFCC handling (two representations, both always present):
        mfcc_distance  float  — mean(abs(chunk_mfccs - ref_mfccs))
                                 Used in the consistency score (Phase 3)
        mfcc_deltas    list   — 13 per-coefficient deltas (chunk - reference)
                                 Used in the MFCC detail table in the report

    Delta sign convention:
        positive delta = chunk value is HIGHER than reference
        negative delta = chunk value is LOWER than reference

    Args:
        chunk_path:        Path to the chunk audio file (WAV or MP3)
        reference_profile: Dict returned by build_reference_profile()

    Returns:
        dict with keys:
            chunk_path       str   — the input filepath
            chunk_values     dict  — raw feature values for this chunk
            reference_values dict  — raw feature values from the reference
            deltas           dict  — per-feature deltas (chunk - reference)
                                     includes mfcc_distance and mfcc_deltas

    Raises:
        ValueError if MFCC distance for a file compared against itself is
        non-zero (numerical stability check — see stop condition in plan).
    """
    print(f"  [PROFILER] Analysing chunk: {chunk_path}")
    chunk_feats = extract_features(chunk_path)

    # Build clean reference values dict (drop internal _source key)
    ref_values = {k: v for k, v in reference_profile.items() if not k.startswith("_")}

    # ------------------------------------------------------------------
    # Compute scalar deltas
    # All scalar features: delta = chunk_value - reference_value
    # ------------------------------------------------------------------
    scalar_keys = [
        "lufs",
        "rms",
        "dynamic_range",
        "spectral_centroid",
        "spectral_rolloff",
        "low_mid_energy",
        "presence_band",
        "high_shelf",
        "stereo_width",
        "tempo",
        "zcr",
    ]

    deltas = {}
    for key in scalar_keys:
        chunk_val = chunk_feats[key]
        ref_val = ref_values[key]
        deltas[key] = round(chunk_val - ref_val, 8)

    # ------------------------------------------------------------------
    # MFCC deltas — two representations
    # ------------------------------------------------------------------
    chunk_mfccs = np.array(chunk_feats["mfcc"])
    ref_mfccs = np.array(ref_values["mfcc"])

    mfcc_deltas = [round(float(d), 6) for d in (chunk_mfccs - ref_mfccs)]
    mfcc_distance = round(float(cosine(chunk_mfccs[1:], ref_mfccs[1:])), 6)

    deltas["mfcc_distance"] = mfcc_distance  # scalar — used in scoring
    deltas["mfcc_deltas"] = mfcc_deltas  # list of 13 — used in report

    # ------------------------------------------------------------------
    # Mono/stereo mismatch note
    # ------------------------------------------------------------------
    if chunk_feats["stereo_width"] == 0.0 and ref_values["stereo_width"] > 0.0:
        print(
            f"  [INFO] Chunk is mono, reference is stereo — "
            f"stereo_width delta = {deltas['stereo_width']:.6f} (chunk is mono)"
        )

    return {
        "chunk_path": chunk_path,
        "chunk_values": chunk_feats,
        "reference_values": ref_values,
        "deltas": deltas,
    }


# ---------------------------------------------------------------------------
# Phase 2 validation block
# Run: python profiler.py ./data/audio/REF_01.mp3 ./data/audio/CHUNK_01.mp3
#
# Critical stop condition:
#   If mfcc_distance for reference vs itself is non-zero -> STOP.
#   This indicates a numerical stability or normalisation bug.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python profiler.py <reference.mp3> <chunk.mp3>")
        print(
            "  Tip: pass the reference as both arguments to run the self-identity check."
        )
        sys.exit(1)

    ref_path = sys.argv[1]
    chunk_path = sys.argv[2]

    print(f"\n{'='*64}")
    print(f"  AUDIO-QA — Phase 2 Validation")
    print(f"{'='*64}")

    # Step 1 — Build reference profile
    print(f"\n[1/3] Building reference profile...")
    ref_profile = build_reference_profile(ref_path)

    # Step 2 — STOP CONDITION: reference vs itself must produce zero deltas
    print(f"\n[2/3] Self-identity check (reference vs itself)...")
    self_analysis = analyze_chunk(ref_path, ref_profile)

    self_deltas = self_analysis["deltas"]
    mfcc_self_dist = self_deltas["mfcc_distance"]

    scalar_self_failures = {
        k: v
        for k, v in self_deltas.items()
        if k not in ("mfcc_distance", "mfcc_deltas") and abs(v) > 1e-9
    }

    if mfcc_self_dist > 1e-9:
        print(f"\n  STOP CONDITION MET")
        print(f"  MFCC distance for reference vs itself = {mfcc_self_dist}")
        print(f"  Expected: 0.0")
        print(f"  This is a numerical stability or normalisation bug.")
        print(f"  Do NOT proceed to Phase 3. Investigate extractor.py.")
        sys.exit(1)

    if scalar_self_failures:
        print(
            f"  [WARN] Non-zero scalar deltas on self-comparison (may be float noise):"
        )
        for k, v in scalar_self_failures.items():
            print(f"    {k}: {v}")
    else:
        print(f"  Self-identity: all scalar deltas = 0.0  OK")

    print(f"  Self-identity: MFCC distance = {mfcc_self_dist:.8f}  OK")

    # Step 3 — Analyse actual chunk
    print(f"\n[3/3] Analysing chunk: {chunk_path}")
    analysis = analyze_chunk(chunk_path, ref_profile)

    d = analysis["deltas"]
    cv = analysis["chunk_values"]
    rv = analysis["reference_values"]

    scalar_keys = [
        "lufs",
        "rms",
        "dynamic_range",
        "spectral_centroid",
        "spectral_rolloff",
        "low_mid_energy",
        "presence_band",
        "high_shelf",
        "stereo_width",
        "tempo",
        "zcr",
    ]

    print(f"\n  {'Feature':<22} {'Reference':>14} {'Chunk':>14} {'Delta':>14}")
    print(f"  {'-'*22}   {'-'*14}   {'-'*14}   {'-'*14}")
    for key in scalar_keys:
        sign = "+" if d[key] >= 0 else ""
        print(f"  {key:<22} {rv[key]:>14.6f} {cv[key]:>14.6f} {sign}{d[key]:>13.6f}")

    print(f"  {'mfcc_distance':<22} {'':>14} {'':>14} {d['mfcc_distance']:>14.6f}")

    print(f"\n  MFCC per-coefficient deltas (chunk - reference):")
    print(f"  {'Coeff':<8} {'Reference':>12} {'Chunk':>12} {'Delta':>12}")
    print(f"  {'-'*8}   {'-'*12}   {'-'*12}   {'-'*12}")
    for i, (ref_v, chunk_v, delta_v) in enumerate(
        zip(rv["mfcc"], cv["mfcc"], d["mfcc_deltas"]), start=1
    ):
        sign = "+" if delta_v >= 0 else ""
        print(f"  [{i:02d}]    {ref_v:>12.4f} {chunk_v:>12.4f} {sign}{delta_v:>11.4f}")

    print(f"\n{'='*64}")
    print(f"  Phase 2 checks:")

    lufs_neg_delta = d["lufs"] < 0
    print(
        f"  Negative LUFS delta = chunk quieter than ref : "
        f"{'yes' if lufs_neg_delta else 'no (chunk is louder)'}"
    )
    print(f"  MFCC distance (overall timbre drift)        : {d['mfcc_distance']:.4f}")
    print(f"  Stereo width delta                          : {d['stereo_width']:+.6f}")
    print(f"\n  Phase 2 PASSED -- delta table looks correct.")
    print(f"  Proceed to Phase 3 (scorer.py + reporter.py + config.py).")
    print(f"{'='*64}\n")
