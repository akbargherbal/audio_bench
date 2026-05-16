"""
reporter.py — Phase 3: Markdown Report Generator
Audio QA — Classical Arabic Poem → Suno AI → Audacity Pipeline

Task 3.2 — generate_report(chunk_name, analysis, score) -> str

Produces a structured Markdown report in this order (all sections mandatory):
  1. Header          — chunk filename + Consistency Score
  2. Feature table   — Reference / Chunk / Delta / Flag for all 12 scored features
  3. MFCC detail     — 13-coefficient breakdown with role labels, always present
  4. Flagged devs    — plain-English label per flagged feature, with delta context
  5. LLM summary     — FR-6 paste-ready diagnostic block

Does NOT modify extractor.py, profiler.py, scorer.py, or config.py.

NOTE on mfcc_distance in the feature table:
    mfcc_distance is a derived scalar (not raw from extract_features).
    The conceptual baseline is 0.0 (perfect match).
    Table shows: Reference = 0.0000 | Chunk = distance | Delta = distance
"""

# ---------------------------------------------------------------------------
# Static lookup tables
# ---------------------------------------------------------------------------

# Display order: scalar features first, mfcc_distance last
# Must match the 12 keys in config.THRESHOLDS
_SCORE_KEYS: list[str] = [
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
    "mfcc_distance",
]

_FEATURE_DISPLAY: dict[str, str] = {
    "lufs":              "LUFS",
    "rms":               "RMS energy",
    "dynamic_range":     "Dynamic range",
    "spectral_centroid": "Spectral centroid",
    "spectral_rolloff":  "Spectral rolloff",
    "low_mid_energy":    "Low-mid energy (200–500 Hz)",
    "presence_band":     "Presence band (1k–4kHz)",
    "high_shelf":        "High shelf (8kHz+)",
    "stereo_width":      "Stereo width",
    "tempo":             "Tempo",
    "zcr":               "Zero crossing rate",
    "mfcc_distance":     "MFCC distance",
}

_FEATURE_UNITS: dict[str, str] = {
    "lufs":              "LUFS",
    "rms":               "",
    "dynamic_range":     "dB",
    "spectral_centroid": "Hz",
    "spectral_rolloff":  "Hz",
    "low_mid_energy":    "frac",
    "presence_band":     "frac",
    "high_shelf":        "frac",
    "stereo_width":      "",
    "tempo":             "BPM",
    "zcr":               "",
    "mfcc_distance":     "",
}

# printf-style format spec for scalar values and deltas
_FEATURE_FMT: dict[str, str] = {
    "lufs":              ".2f",
    "rms":               ".6f",
    "dynamic_range":     ".2f",
    "spectral_centroid": ".1f",
    "spectral_rolloff":  ".1f",
    "low_mid_energy":    ".6f",
    "presence_band":     ".6f",
    "high_shelf":        ".6f",
    "stereo_width":      ".6f",
    "tempo":             ".1f",
    "zcr":               ".6f",
    "mfcc_distance":     ".4f",
}

# MFCC coefficient role labels — must match extractor._MFCC_LABELS (1-indexed)
_MFCC_ROLE_LABELS: list[str] = [
    "energy",        # 01
    "tonal char",    # 02
    "tonal char",    # 03
    "mid timbre",    # 04
    "mid timbre",    # 05
    "mid timbre",    # 06
    "mid timbre",    # 07
    "fine texture",  # 08
    "fine texture",  # 09
    "fine texture",  # 10
    "fine texture",  # 11
    "fine texture",  # 12
    "fine texture",  # 13
]


# ---------------------------------------------------------------------------
# Flag label map — directional where the plan specifies direction
# Source: AUDIO_QA_Phased_Plan.md, Phase 3, Task 3.2
# ---------------------------------------------------------------------------

def _get_flag_label(feature: str, delta: float) -> str:
    """
    Return the plain-English deviation label for a flagged feature.
    Labels are directional where the plan distinguishes high vs low.
    Unlisted directions fall through to a generic fallback.
    """
    if feature == "lufs":
        return (
            "Chunk is quieter than reference — energy/intensity mismatch"
            if delta < 0 else
            "Chunk is louder than reference — may clip or dominate assembly"
        )
    if feature == "low_mid_energy":
        return (
            "Low-mid buildup — possible muddiness (200–500 Hz)"
            if delta > 0 else
            "Low-mid energy below reference — mix may sound thin in body range"
        )
    if feature == "stereo_width":
        return (
            "Stereo image narrower than reference — sounds more closed/mono"
            if delta < 0 else
            "Stereo image wider than reference — spatial feel has broadened"
        )
    if feature == "spectral_centroid":
        return (
            "Mix darker than reference — tonal weight shifted down"
            if delta < 0 else
            "Mix brighter than reference — possible harshness"
        )
    if feature == "tempo":
        return "Tempo drift — pacing inconsistency"
    if feature == "mfcc_distance":
        return "Timbre fingerprint mismatch — overall tonal character differs"
    if feature == "dynamic_range":
        return (
            "Over-compressed — dynamic range squashed vs reference"
            if delta < 0 else
            "Dynamic range expanded — less compressed than reference"
        )
    if feature == "presence_band":
        return (
            "Vocal presence reduced — less cut-through in 1k–4kHz range"
            if delta < 0 else
            "Presence band elevated — vocal forward or mid-range peaked"
        )
    if feature == "high_shelf":
        return (
            "Excessive high-frequency air or harshness above 8kHz"
            if delta > 0 else
            "High shelf reduced — less air, possibly duller above 8kHz"
        )
    if feature == "zcr":
        return (
            "Elevated noise floor or distortion indicator"
            if delta > 0 else
            "Zero crossing rate below reference — smoother signal"
        )
    if feature == "rms":
        return (
            "RMS energy below reference — chunk may sound quieter overall"
            if delta < 0 else
            "RMS energy above reference — chunk louder than reference average"
        )
    if feature == "spectral_rolloff":
        return (
            "Spectral rolloff lower — high-frequency content reduced"
            if delta < 0 else
            "Spectral rolloff higher — more high-frequency content than reference"
        )
    # Generic fallback for any feature not in the map
    direction = "above" if delta > 0 else "below"
    return f"{_FEATURE_DISPLAY.get(feature, feature)} is {direction} reference threshold"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt(feature: str, value: float) -> str:
    """Format a scalar value using the feature's display format."""
    return format(value, _FEATURE_FMT.get(feature, ".4f"))


def _fmt_delta(feature: str, delta: float) -> str:
    """Format a delta with explicit +/- sign."""
    fmt  = _FEATURE_FMT.get(feature, ".4f")
    sign = "+" if delta >= 0 else ""
    return f"{sign}{format(delta, fmt)}"


def _fmt_delta_with_unit(feature: str, delta: float) -> str:
    """Delta formatted with unit suffix — used in LLM summary block."""
    unit = _FEATURE_UNITS.get(feature, "")
    d    = _fmt_delta(feature, delta)
    return f"{d} {unit}".strip()


# ---------------------------------------------------------------------------
# Report section builders
# ---------------------------------------------------------------------------

def _section_header(chunk_name: str, consistency_score: float) -> str:
    score_int = int(consistency_score)
    if score_int >= 85:
        verdict = "PASS — within reference family"
    elif score_int >= 65:
        verdict = "REVIEW — minor deviations present"
    elif score_int >= 50:
        verdict = "CAUTION — notable deviations, consider re-generation"
    else:
        verdict = "FAIL — significant drift from reference"

    return "\n".join([
        f"# Audio QA Report — {chunk_name}",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Consistency Score** | **{consistency_score}/100** |",
        f"| **Verdict** | {verdict} |",
        "",
    ])


def _section_feature_table(analysis: dict, score: dict) -> str:
    chunk_vals = analysis["chunk_values"]
    ref_vals   = analysis["reference_values"]
    deltas     = analysis["deltas"]
    scored     = score["scored_features"]

    # Build rows — mfcc_distance handled specially (baseline = 0.0)
    rows: list[tuple] = []
    for key in _SCORE_KEYS:
        display    = _FEATURE_DISPLAY[key]
        unit       = _FEATURE_UNITS[key]
        is_flagged = scored[key]["flagged"]

        if key == "mfcc_distance":
            ref_v   = 0.0
            chunk_v = deltas["mfcc_distance"]
            delta   = deltas["mfcc_distance"]
        else:
            ref_v   = ref_vals[key]
            chunk_v = chunk_vals[key]
            delta   = deltas[key]

        rows.append((
            display,
            unit,
            _fmt(key, ref_v),
            _fmt(key, chunk_v),
            _fmt_delta(key, delta),
            "⚠" if is_flagged else "✓",
        ))

    # Dynamic column widths — ensures alignment regardless of value length
    hdr = ("Feature", "Unit", "Reference", "Chunk", "Delta", "Flag")
    widths = [
        max(len(hdr[i]), max(len(r[i]) for r in rows))
        for i in range(len(hdr))
    ]

    def _row(*cells):
        return (
            f"| {cells[0]:<{widths[0]}} "
            f"| {cells[1]:<{widths[1]}} "
            f"| {cells[2]:>{widths[2]}} "
            f"| {cells[3]:>{widths[3]}} "
            f"| {cells[4]:>{widths[4]}} "
            f"| {cells[5]} |"
        )

    sep = (
        f"| {'-'*widths[0]} "
        f"| {'-'*widths[1]} "
        f"| {'-'*widths[2]:>{widths[2]}} "
        f"| {'-'*widths[3]:>{widths[3]}} "
        f"| {'-'*widths[4]:>{widths[4]}} "
        f"| --- |"
    )

    lines = ["## Feature Comparison", "", _row(*hdr), sep]
    for r in rows:
        lines.append(_row(*r))
    lines.append("")
    return "\n".join(lines)


def _section_mfcc_detail(analysis: dict) -> str:
    ref_mfccs   = analysis["reference_values"]["mfcc"]
    chunk_mfccs = analysis["chunk_values"]["mfcc"]
    mfcc_deltas = analysis["deltas"]["mfcc_deltas"]

    lines = [
        "## MFCC Detail (13 Coefficients)",
        "",
        "| Coeff | Reference  | Chunk      | Delta      | Role         |",
        "| :---: | ---------: | ---------: | ---------: | :----------- |",
    ]

    for i, (ref_v, chunk_v, delta_v, role) in enumerate(
        zip(ref_mfccs, chunk_mfccs, mfcc_deltas, _MFCC_ROLE_LABELS), start=1
    ):
        lines.append(
            f"| {i:02d}    "
            f"| {ref_v:>10.4f} "
            f"| {chunk_v:>10.4f} "
            f"| {delta_v:>+10.4f} "
            f"| {role:<12} |"
        )

    lines.append("")
    return "\n".join(lines)


def _section_flagged_deviations(analysis: dict, score: dict) -> str:
    flagged = score["flagged_features"]
    deltas  = analysis["deltas"]

    lines = ["## Flagged Deviations", ""]

    if not flagged:
        lines += [
            "_No deviations flagged — all features are within reference thresholds._",
            "",
        ]
        return "\n".join(lines)

    for feature in flagged:
        delta     = deltas[feature]
        label     = _get_flag_label(feature, delta)
        delta_ctx = _fmt_delta_with_unit(feature, delta)
        display   = _FEATURE_DISPLAY[feature]
        lines.append(f"- **{display}** `{delta_ctx}` — {label}")

    lines.append("")
    return "\n".join(lines)


def _section_llm_summary(chunk_name: str, analysis: dict, score: dict) -> str:
    """
    FR-6 mandatory block — paste this directly into an LLM prompt.
    Always present, even when Consistency Score = 100.
    """
    consistency_score = score["consistency_score"]
    flagged           = score["flagged_features"]
    deltas            = analysis["deltas"]

    # Build inner content of the fenced block
    inner: list[str] = [
        f"DIAGNOSTIC SUMMARY — {chunk_name}",
        f"Consistency Score: {consistency_score}/100",
    ]

    if flagged:
        inner.append("Flagged issues:")
        for feature in flagged:
            delta     = deltas[feature]
            label     = _get_flag_label(feature, delta)
            delta_ctx = _fmt_delta_with_unit(feature, delta)
            inner.append(f"  - {label}  (delta: {delta_ctx})")
    else:
        inner.append(
            "No issues flagged — chunk is within reference bounds on all metrics."
        )

    inner += [
        "",
        "Subjective note from user: [paste what you hear here]",
    ]

    lines = [
        "## Diagnostic Summary",
        "",
        "> *Paste the block below directly into an LLM prompt.*",
        "",
        "```",
    ]
    lines.extend(inner)
    lines += ["```", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(chunk_name: str, analysis: dict, score: dict) -> str:
    """
    Generate a full Markdown QA report for one chunk.

    Args:
        chunk_name: Display name for the chunk (typically os.path.basename of path).
        analysis:   Dict returned by profiler.analyze_chunk().
        score:      Dict returned by scorer.score_chunk().

    Returns:
        str — complete Markdown report, ready to print or write to file.
              All five sections are always present.
    """
    return "\n".join([
        _section_header(chunk_name, score["consistency_score"]),
        _section_feature_table(analysis, score),
        _section_mfcc_detail(analysis),
        _section_flagged_deviations(analysis, score),
        _section_llm_summary(chunk_name, analysis, score),
    ])
