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
    "lufs": "LUFS",
    "rms": "RMS energy",
    "dynamic_range": "Dynamic range",
    "spectral_centroid": "Spectral centroid",
    "spectral_rolloff": "Spectral rolloff",
    "low_mid_energy": "Low-mid energy (200–500 Hz)",
    "presence_band": "Presence band (1k–4kHz)",
    "high_shelf": "High shelf (8kHz+)",
    "stereo_width": "Stereo width",
    "tempo": "Tempo",
    "zcr": "Zero crossing rate",
    "mfcc_distance": "MFCC distance",
}

_FEATURE_UNITS: dict[str, str] = {
    "lufs": "LUFS",
    "rms": "",
    "dynamic_range": "dB",
    "spectral_centroid": "Hz",
    "spectral_rolloff": "Hz",
    "low_mid_energy": "frac",
    "presence_band": "frac",
    "high_shelf": "frac",
    "stereo_width": "",
    "tempo": "BPM",
    "zcr": "",
    "mfcc_distance": "",
}

# printf-style format spec for scalar values and deltas
_FEATURE_FMT: dict[str, str] = {
    "lufs": ".2f",
    "rms": ".6f",
    "dynamic_range": ".2f",
    "spectral_centroid": ".1f",
    "spectral_rolloff": ".1f",
    "low_mid_energy": ".6f",
    "presence_band": ".6f",
    "high_shelf": ".6f",
    "stereo_width": ".6f",
    "tempo": ".1f",
    "zcr": ".6f",
    "mfcc_distance": ".4f",
}

# MFCC coefficient role labels — must match extractor._MFCC_LABELS (1-indexed)
_MFCC_ROLE_LABELS: list[str] = [
    "energy",  # 01
    "tonal char",  # 02
    "tonal char",  # 03
    "mid timbre",  # 04
    "mid timbre",  # 05
    "mid timbre",  # 06
    "mid timbre",  # 07
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
            if delta < 0
            else "Chunk is louder than reference — may clip or dominate assembly"
        )
    if feature == "low_mid_energy":
        return (
            "Low-mid buildup — possible muddiness (200–500 Hz)"
            if delta > 0
            else "Low-mid energy below reference — mix may sound thin in body range"
        )
    if feature == "stereo_width":
        return (
            "Stereo image narrower than reference — sounds more closed/mono"
            if delta < 0
            else "Stereo image wider than reference — spatial feel has broadened"
        )
    if feature == "spectral_centroid":
        return (
            "Mix darker than reference — tonal weight shifted down"
            if delta < 0
            else "Mix brighter than reference — possible harshness"
        )
    if feature == "tempo":
        return "Tempo drift — pacing inconsistency"
    if feature == "mfcc_distance":
        return "Timbre fingerprint mismatch — overall tonal character differs"
    if feature == "dynamic_range":
        return (
            "Over-compressed — dynamic range squashed vs reference"
            if delta < 0
            else "Dynamic range expanded — less compressed than reference"
        )
    if feature == "presence_band":
        return (
            "Vocal presence reduced — less cut-through in 1k–4kHz range"
            if delta < 0
            else "Presence band elevated — vocal forward or mid-range peaked"
        )
    if feature == "high_shelf":
        return (
            "Excessive high-frequency air or harshness above 8kHz"
            if delta > 0
            else "High shelf reduced — less air, possibly duller above 8kHz"
        )
    if feature == "zcr":
        return (
            "Elevated noise floor or distortion indicator"
            if delta > 0
            else "Zero crossing rate below reference — smoother signal"
        )
    if feature == "rms":
        return (
            "RMS energy below reference — chunk may sound quieter overall"
            if delta < 0
            else "RMS energy above reference — chunk louder than reference average"
        )
    if feature == "spectral_rolloff":
        return (
            "Spectral rolloff lower — high-frequency content reduced"
            if delta < 0
            else "Spectral rolloff higher — more high-frequency content than reference"
        )
    # Generic fallback for any feature not in the map
    direction = "above" if delta > 0 else "below"
    return (
        f"{_FEATURE_DISPLAY.get(feature, feature)} is {direction} reference threshold"
    )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt(feature: str, value: float) -> str:
    """Format a scalar value using the feature's display format."""
    return format(value, _FEATURE_FMT.get(feature, ".4f"))


def _fmt_delta(feature: str, delta: float) -> str:
    """Format a delta with explicit +/- sign."""
    fmt = _FEATURE_FMT.get(feature, ".4f")
    sign = "+" if delta >= 0 else ""
    return f"{sign}{format(delta, fmt)}"


def _fmt_delta_with_unit(feature: str, delta: float) -> str:
    """Delta formatted with unit suffix — used in LLM summary block."""
    unit = _FEATURE_UNITS.get(feature, "")
    d = _fmt_delta(feature, delta)
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

    return "\n".join(
        [
            f"# Audio QA Report — {chunk_name}",
            "",
            f"| | |",
            f"|---|---|",
            f"| **Consistency Score** | **{consistency_score}/100** |",
            f"| **Verdict** | {verdict} |",
            "",
        ]
    )


def _section_feature_table(analysis: dict, score: dict) -> str:
    chunk_vals = analysis["chunk_values"]
    ref_vals = analysis["reference_values"]
    deltas = analysis["deltas"]
    scored = score["scored_features"]

    # Build rows — mfcc_distance handled specially (baseline = 0.0)
    rows: list[tuple] = []
    for key in _SCORE_KEYS:
        display = _FEATURE_DISPLAY[key]
        unit = _FEATURE_UNITS[key]
        is_flagged = scored[key]["flagged"]

        if key == "mfcc_distance":
            ref_v = 0.0
            chunk_v = deltas["mfcc_distance"]
            delta = deltas["mfcc_distance"]
        else:
            ref_v = ref_vals[key]
            chunk_v = chunk_vals[key]
            delta = deltas[key]

        rows.append(
            (
                display,
                unit,
                _fmt(key, ref_v),
                _fmt(key, chunk_v),
                _fmt_delta(key, delta),
                "⚠" if is_flagged else "✓",
            )
        )

    # Dynamic column widths — ensures alignment regardless of value length
    hdr = ("Feature", "Unit", "Reference", "Chunk", "Delta", "Flag")
    widths = [max(len(hdr[i]), max(len(r[i]) for r in rows)) for i in range(len(hdr))]

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
    ref_mfccs = analysis["reference_values"]["mfcc"]
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
    lines.append(
        "*Note: `MFCC distance` (scored feature) uses cosine distance on C02–C13 only. "
        "C01 (energy) is shown above for reference but is excluded from the distance calculation "
        "to prevent loudness differences from dominating the timbre metric.*"
    )
    lines.append("")
    return "\n".join(lines)


def _section_flagged_deviations(analysis: dict, score: dict) -> str:
    flagged = score["flagged_features"]
    deltas = analysis["deltas"]

    lines = ["## Flagged Deviations", ""]

    if not flagged:
        lines += [
            "_No deviations flagged — all features are within reference thresholds._",
            "",
        ]
        return "\n".join(lines)

    for feature in flagged:
        delta = deltas[feature]
        label = _get_flag_label(feature, delta)
        delta_ctx = _fmt_delta_with_unit(feature, delta)
        display = _FEATURE_DISPLAY[feature]
        lines.append(f"- **{display}** `{delta_ctx}` — {label}")

    lines.append("")
    return "\n".join(lines)


def _section_llm_summary(chunk_name: str, analysis: dict, score: dict) -> str:
    """
    FR-6 mandatory block — paste this directly into an LLM prompt.
    Always present, even when Consistency Score = 100.
    """
    consistency_score = score["consistency_score"]
    flagged = score["flagged_features"]
    deltas = analysis["deltas"]

    # Build inner content of the fenced block
    inner: list[str] = [
        f"DIAGNOSTIC SUMMARY — {chunk_name}",
        f"Consistency Score: {consistency_score}/100",
    ]

    if flagged:
        inner.append("Flagged issues:")
        for feature in flagged:
            delta = deltas[feature]
            label = _get_flag_label(feature, delta)
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
# Phase 5 — Prompt implications section
# Source: AUDIO_QA_Phased_Plan.md, Phase 5, prompt implication map v1
# ---------------------------------------------------------------------------

# Maps flagged feature key → (condition_fn, implication_str)
# condition_fn receives delta and returns True when the implication applies.
# Multiple entries per feature are allowed (high vs low cases).
_PROMPT_IMPLICATIONS: list[tuple] = [
    # feature key         condition               implication text
    (
        "low_mid_energy",
        lambda d: d > 0,
        "Prompt may lack explicit vocal-forward or mix clarity instruction",
    ),
    (
        "lufs",
        lambda d: d < 0,
        "Suno generated a quieter, more restrained performance — check energy/intensity descriptors",
    ),
    (
        "lufs",
        lambda d: d >= 0,
        "Suno generated a louder, more intense performance — check for words like 'powerful', 'full'",
    ),
    (
        "stereo_width",
        lambda d: d < 0,
        "Prompt may be producing a more intimate/close recording — check spatial descriptors",
    ),
    (
        "spectral_centroid",
        lambda d: d < 0,
        "Mix is darker than reference — prompt may lack brightness or air descriptors",
    ),
    (
        "spectral_centroid",
        lambda d: d > 0,
        "Mix is brighter than reference — check for descriptors pushing high-frequency energy (e.g. 'crisp', 'bright', 'airy'); consider softening or removing them",
    ),
    (
        "spectral_rolloff",
        lambda d: d > 0,
        "More high-frequency content than reference — prompt may be over-specifying brightness or air; check descriptors like 'crisp', 'bright', 'open'",
    ),
    (
        "spectral_rolloff",
        lambda d: d < 0,
        "Less high-frequency content than reference — mix is rolling off earlier than reference; prompt may lack air or presence descriptors",
    ),
    (
        "presence_band",
        lambda d: d < 0,
        "Vocal is less forward — consider adding 'vocal-forward', 'clear vocals', 'intimate'",
    ),
    (
        "presence_band",
        lambda d: d > 0,
        "Vocal presence is elevated above reference — mid-range may be peaked; check for descriptors like 'forward', 'present', 'in-your-face'",
    ),
    (
        "mfcc_distance",
        lambda d: True,
        "Overall timbre has drifted — check whether reference audio was attached to this generation",
    ),
    (
        "tempo",
        lambda d: True,
        "Pacing has changed — Suno may have interpreted rhythm cues differently",
    ),
]


def _section_prompt_implications(analysis: dict, score: dict) -> str:
    """
    Phase 5 — 'Suno Prompt Implications' section.

    Only rendered when at least one feature is flagged.
    When Consistency Score = 100 (no flags), replaced with a clean
    'No significant prompt issues flagged' note.

    Maps each flagged feature to a likely Suno prompt cause using
    _PROMPT_IMPLICATIONS (v1 map from AUDIO_QA_Phased_Plan.md, Phase 5).
    """
    flagged = score["flagged_features"]
    deltas = analysis["deltas"]

    lines = ["## Suno Prompt Implications", ""]

    if not flagged:
        lines += [
            "_No significant prompt issues flagged — chunk is within reference bounds "
            "on all metrics._",
            "",
        ]
        return "\n".join(lines)

    # Collect applicable implications — preserve plan order, deduplicate text
    seen: set[str] = set()
    implications: list[tuple[str, str]] = []  # (display_name, implication_text)

    for feature_key, condition_fn, implication_text in _PROMPT_IMPLICATIONS:
        if feature_key not in flagged:
            continue
        delta = deltas[feature_key]
        if not condition_fn(delta):
            continue
        if implication_text in seen:
            continue
        seen.add(implication_text)
        display = _FEATURE_DISPLAY.get(feature_key, feature_key)
        implications.append((display, implication_text))

    if not implications:
        # Flagged features exist but none matched the implication map
        # (e.g. rms, dynamic_range, high_shelf, zcr — not in map v1)
        lines += [
            "_Flagged features have no direct prompt implication in map v1. "
            "Review the Flagged Deviations section above for diagnostic detail._",
            "",
        ]
        return "\n".join(lines)

    lines.append(
        "> *These are diagnostic suggestions, not definitive causes. "
        "Use alongside your subjective notes.*"
    )
    lines.append("")

    for display, implication in implications:
        lines.append(f"- **{display}** — {implication}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase 3 (Stems) — Stem Analysis section
# Task 3.1: _section_stem_table(stem_data, chunk_values) -> str
#
# stem_data structure (assembled by main.run_single):
#   vocal_features  dict — extract_features() result for the vocal stem
#   inst_features   dict — extract_features() result for the instrumental stem
#   vocal_specific  dict — extract_vocal_stem_features() result (5 metrics)
#
# chunk_values is analysis["chunk_values"] — the mix-level chunk feature dict.
# It is passed by generate_report / generate_prompt_debug_report internally;
# callers do not need to supply it.
#
# Locked constraints:
#   - No deltas, no flags, no scoring — raw values only.
#   - stem_data never enters scored_features or analysis["deltas"].
#   - Section is appended BEFORE the LLM Summary block.
# ---------------------------------------------------------------------------

_STEM_SCALAR_KEYS: list[str] = [
    # All scored scalar features in display order; mfcc_distance excluded
    # (it is a derived metric, not a raw extract_features() output).
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

# Display metadata for the 5 vocal-specific metrics from extract_vocal_stem_features()
_STEM_METRIC_ORDER: list[str] = [
    "hnr",
    "var_db",
    "pitch_confidence_voiced",
    "pitch_stability_f0_var",
    "spectral_flatness_vocal",
]

_STEM_METRIC_DISPLAY: dict[str, str] = {
    "hnr":                     "HNR (Harmonics-to-Noise Ratio)",
    "var_db":                  "VAR (Vocal-to-Accomp. Ratio)",
    "pitch_confidence_voiced": "Pitch Confidence (voiced frames)",
    "pitch_stability_f0_var":  "Pitch Stability (F0 variance)",
    "spectral_flatness_vocal": "Spectral Flatness (vocal stem)",
}

_STEM_METRIC_UNITS: dict[str, str] = {
    "hnr":                     "dB",
    "var_db":                  "dB",
    "pitch_confidence_voiced": "",
    "pitch_stability_f0_var":  "Hz²",
    "spectral_flatness_vocal": "",
}

_STEM_METRIC_FMT: dict[str, str] = {
    "hnr":                     ".2f",
    "var_db":                  ".2f",
    "pitch_confidence_voiced": ".4f",
    "pitch_stability_f0_var":  ".2f",
    "spectral_flatness_vocal": ".6f",
}


def _section_stem_table(stem_data: dict, chunk_values: dict) -> str:
    """
    Task 3.1 — Raw stem analysis section.

    Renders two sub-tables:
      1. Mix-level features across all three sources (Mix chunk | Vocal stem | Inst stem).
         Uses the same 11 scalar features as the main QA table (mfcc_distance excluded —
         it is a derived metric not present in raw extract_features() output).
      2. Vocal-specific metrics (Vocal stem only — 5 metrics from extract_vocal_stem_features()).

    Args:
        stem_data:    Dict assembled by main.run_single() — keys:
                        vocal_features, inst_features, vocal_specific.
        chunk_values: analysis["chunk_values"] from the calling report function.
                      Provides the mix (unseparated chunk) column values.

    Returns:
        str — Markdown '## Stem Analysis' section. No deltas, no flags, no score impact.
    """
    vocal_feats = stem_data["vocal_features"]
    inst_feats  = stem_data["inst_features"]
    vocal_spec  = stem_data["vocal_specific"]

    # ------------------------------------------------------------------
    # Sub-table 1: Mix-level features — Mix | Vocal | Instrumental
    # ------------------------------------------------------------------
    mix_rows: list[tuple] = []
    for key in _STEM_SCALAR_KEYS:
        display  = _FEATURE_DISPLAY[key]
        unit     = _FEATURE_UNITS[key]
        fmt      = _FEATURE_FMT.get(key, ".4f")
        mix_v    = chunk_values.get(key, 0.0)
        voc_v    = vocal_feats.get(key, 0.0)
        inst_v   = inst_feats.get(key, 0.0)
        mix_rows.append((
            display,
            unit,
            format(mix_v,  fmt),
            format(voc_v,  fmt),
            format(inst_v, fmt),
        ))

    hdr1 = ("Feature", "Unit", "Mix", "Vocal", "Instrumental")
    widths1 = [
        max(len(hdr1[i]), max(len(r[i]) for r in mix_rows))
        for i in range(len(hdr1))
    ]

    def _row1(*cells):
        return (
            f"| {cells[0]:<{widths1[0]}} "
            f"| {cells[1]:<{widths1[1]}} "
            f"| {cells[2]:>{widths1[2]}} "
            f"| {cells[3]:>{widths1[3]}} "
            f"| {cells[4]:>{widths1[4]}} |"
        )

    sep1 = (
        f"| {'-'*widths1[0]} "
        f"| {'-'*widths1[1]} "
        f"| {'-'*widths1[2]:>{widths1[2]}} "
        f"| {'-'*widths1[3]:>{widths1[3]}} "
        f"| {'-'*widths1[4]:>{widths1[4]}} |"
    )

    lines: list[str] = [
        "## Stem Analysis",
        "",
        "> Raw values only — no scoring, no thresholds, no deltas.",
        "> Stem data bypasses the consistency scorer entirely.",
        "> The Consistency Score and Flagged Deviations above are unaffected by this section.",
        "",
        "### Mix-Level Features by Stem",
        "",
        _row1(*hdr1),
        sep1,
    ]
    for r in mix_rows:
        lines.append(_row1(*r))
    lines.append("")

    # ------------------------------------------------------------------
    # Sub-table 2: Vocal-specific metrics (Vocal stem only)
    # ------------------------------------------------------------------
    vocal_rows: list[tuple] = []
    for key in _STEM_METRIC_ORDER:
        display = _STEM_METRIC_DISPLAY[key]
        unit    = _STEM_METRIC_UNITS[key]
        fmt     = _STEM_METRIC_FMT[key]
        val     = vocal_spec.get(key, 0.0)
        # Guard against inf/-inf (VAR degenerate cases — silent stem)
        if val == float("inf"):
            val_str = "+inf"
        elif val == float("-inf"):
            val_str = "-inf"
        else:
            val_str = format(val, fmt)
        vocal_rows.append((display, unit, val_str))

    hdr2 = ("Metric", "Unit", "Vocal")
    widths2 = [
        max(len(hdr2[i]), max(len(r[i]) for r in vocal_rows))
        for i in range(len(hdr2))
    ]

    def _row2(*cells):
        return (
            f"| {cells[0]:<{widths2[0]}} "
            f"| {cells[1]:<{widths2[1]}} "
            f"| {cells[2]:>{widths2[2]}} |"
        )

    sep2 = (
        f"| {'-'*widths2[0]} "
        f"| {'-'*widths2[1]} "
        f"| {'-'*widths2[2]:>{widths2[2]}} |"
    )

    lines += [
        "### Vocal-Specific Metrics",
        "",
        _row2(*hdr2),
        sep2,
    ]
    for r in vocal_rows:
        lines.append(_row2(*r))

    lines += [
        "",
        (
            "*Interpretation guide — "
            "HNR: higher = cleaner vocal (less noise/bleed); "
            "VAR: positive = vocal louder than instrumental in 1k–4kHz presence band; "
            "Pitch Confidence: masked to voiced frames only (Arabic consonants excluded); "
            "Pitch Stability: lower variance = more consistent pitch; "
            "Spectral Flatness: near 0 = tonal/harmonic, near 1 = noise-like/breathy.*"
        ),
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_report(
    chunk_name: str,
    analysis: dict,
    score: dict,
    stem_data: dict = None,
) -> str:
    """
    Generate a full Markdown QA report for one chunk.

    Args:
        chunk_name: Display name for the chunk (typically os.path.basename of path).
        analysis:   Dict returned by profiler.analyze_chunk().
        score:      Dict returned by scorer.score_chunk().
        stem_data:  Optional dict assembled by main.run_single() when --stems is active.
                    Keys: vocal_features, inst_features, vocal_specific.
                    If present, a '## Stem Analysis' section is inserted immediately
                    before the LLM Summary block. If None, report is identical to the
                    pre-stems behaviour — no stem section, no other changes.

    Returns:
        str — complete Markdown report, ready to print or write to file.
              Standard sections are always present. Stem Analysis section is
              conditional on stem_data being supplied.
    """
    sections = [
        _section_header(chunk_name, score["consistency_score"]),
        _section_feature_table(analysis, score),
        _section_mfcc_detail(analysis),
        _section_flagged_deviations(analysis, score),
    ]
    if stem_data is not None:
        sections.append(_section_stem_table(stem_data, analysis["chunk_values"]))
    sections.append(_section_llm_summary(chunk_name, analysis, score))
    return "\n".join(sections)


def generate_prompt_debug_report(
    chunk_name: str,
    analysis: dict,
    score: dict,
    stem_data: dict = None,
) -> str:
    """
    Phase 5 — Prompt debug report.

    Identical to generate_report() with one additional section appended:
    'Suno Prompt Implications' — maps flagged deviations to likely Suno
    prompt causes using the v1 implication map from the plan.

    Args:
        chunk_name: Display name for the chunk (typically os.path.basename).
        analysis:   Dict returned by profiler.analyze_chunk().
        score:      Dict returned by scorer.score_chunk().
        stem_data:  Optional dict assembled by main.run_single() when --stems is active.
                    Keys: vocal_features, inst_features, vocal_specific.
                    If present, a '## Stem Analysis' section is inserted immediately
                    before the LLM Summary block. If None, report is identical to the
                    pre-stems behaviour.

    Returns:
        str — complete Markdown report with all standard sections
              plus the Suno Prompt Implications section at the end.
              Stem Analysis section is conditional on stem_data being supplied.
    """
    sections = [
        _section_header(chunk_name, score["consistency_score"]),
        _section_feature_table(analysis, score),
        _section_mfcc_detail(analysis),
        _section_flagged_deviations(analysis, score),
    ]
    if stem_data is not None:
        sections.append(_section_stem_table(stem_data, analysis["chunk_values"]))
    sections.append(_section_llm_summary(chunk_name, analysis, score))
    sections.append(_section_prompt_implications(analysis, score))
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Phase 6 — Ceiling Analysis Report (FR-9)
# ---------------------------------------------------------------------------

# Features excluded from ceiling comparison — genre-specific.
# Mirrors CEILING_THRESHOLDS exclusion list in config.py.
# Must stay in sync manually if config.py is ever revised.
_CEILING_EXCLUDED_DISPLAY: list[str] = [
    "High shelf (8kHz+)",
    "Stereo width",
    "Tempo",
]

# Display order for included ceiling features (matches CEILING_THRESHOLDS key order)
_CEILING_FEATURE_ORDER: list[str] = [
    "lufs",
    "rms",
    "dynamic_range",
    "spectral_centroid",
    "spectral_rolloff",
    "low_mid_energy",
    "presence_band",
    "zcr",
    "mfcc_distance",
]

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


def _get_ceiling_flag_label(feature: str, delta: float) -> str:
    """
    Plain-English red-flag label for ceiling analysis.

    Labels are framed as production hygiene failures, not style differences.
    Each label ends with a parenthetical hygiene reminder so that copy-pasted
    context is never misread as a genre-match failure.
    """
    if feature == "lufs":
        return (
            "Chunk is significantly quieter than commercial production norms — "
            "possible vocal burial. *(Hygiene flag, not a loudness target.)*"
            if delta < 0
            else "Chunk is significantly louder than commercial reference — "
            "possible clipping or overload. *(Hygiene flag, not a loudness target.)*"
        )
    if feature == "rms":
        return (
            "Chunk energy significantly below commercial reference — "
            "may sound weak or underproduced. *(Hygiene flag.)*"
            if delta < 0
            else "Chunk energy significantly above commercial reference. *(Hygiene flag.)*"
        )
    if feature == "dynamic_range":
        return (
            "Dynamic range severely squashed vs commercial reference — "
            "likely over-compressed. *(Hygiene flag.)*"
            if delta < 0
            else "Dynamic range severely expanded vs commercial reference — "
            "unusually uncompressed for production context. *(Hygiene flag.)*"
        )
    if feature == "spectral_centroid":
        return (
            "Mix extremely dark vs commercial reference — "
            "tonal balance may be a production issue. *(Hygiene flag.)*"
            if delta < 0
            else "Mix extremely bright vs commercial reference — "
            "possible harshness or production imbalance. *(Hygiene flag.)*"
        )
    if feature == "spectral_rolloff":
        return (
            "High-frequency content severely reduced vs commercial reference. "
            "*(Hygiene flag.)*"
            if delta < 0
            else "High-frequency content severely elevated vs commercial reference. "
            "*(Hygiene flag.)*"
        )
    if feature == "low_mid_energy":
        return (
            "Severe low-mid buildup vs commercial reference — "
            "possible muddiness (200–500 Hz). *(Hygiene flag.)*"
            if delta > 0
            else "Low-mid energy severely below commercial reference — "
            "mix may sound thin in the body range. *(Hygiene flag.)*"
        )
    if feature == "presence_band":
        return (
            "Vocal severely buried vs commercial reference — "
            "very low cut-through in 1k–4kHz range. *(Hygiene flag.)*"
            if delta < 0
            else "Vocal presence severely elevated vs commercial reference — "
            "strong mid-range peak. *(Hygiene flag.)*"
        )
    if feature == "zcr":
        return (
            "Significantly elevated noise or distortion vs commercial reference. "
            "*(Hygiene flag.)*"
            if delta > 0
            else "Zero crossing rate severely below commercial reference. *(Hygiene flag.)*"
        )
    if feature == "mfcc_distance":
        return (
            "Timbral character grossly different from commercial reference. "
            "*(Hygiene flag — large distance may reflect genre, not a defect.)*"
        )
    # Generic fallback
    direction = "above" if delta > 0 else "below"
    return (
        f"{_FEATURE_DISPLAY.get(feature, feature)} is grossly {direction} "
        f"commercial reference. *(Hygiene flag.)*"
    )


def generate_ceiling_report(
    chunk_name: str,
    ceiling_name: str,
    chunk_feats: dict,
    ceiling_feats: dict,
    deltas: dict,
    red_flags: list,
    ceiling_thresholds: dict,
) -> str:
    """
    Phase 6 — Ceiling analysis Markdown report.

    Compares chunk against a commercial reference on production hygiene
    features only. Does NOT share structure with generate_report() — this
    is a separate, explicitly framed report type.

    Report sections (all always present):
        1. Header — mandatory disclaimer, summary counts
        2. Feature comparison table — 9 included features + excluded note
        3. Red flags — plain-English hygiene labels (or clean message)
        4. Ceiling analysis summary — paste-ready LLM block

    Args:
        chunk_name:          Chunk filename (display).
        ceiling_name:        Commercial track filename (display).
        chunk_feats:         Raw dict from extract_features() for the chunk.
        ceiling_feats:       Raw dict from extract_features() for the ceiling track.
        deltas:              {feature: delta} for included features only.
                             mfcc_distance must be pre-computed and present.
        red_flags:           List of feature keys that exceeded ceiling thresholds.
        ceiling_thresholds:  CEILING_THRESHOLDS from config.py (for table display).

    Returns:
        str — complete Markdown ceiling report.
    """
    n_checked = len(_CEILING_FEATURE_ORDER)
    n_flags = len(red_flags)

    # ------------------------------------------------------------------
    # Section 1 — Header + mandatory disclaimer
    # ------------------------------------------------------------------
    flag_verdict = (
        "No red flags raised." if n_flags == 0 else f"{n_flags} red flag(s) raised."
    )

    header = "\n".join(
        [
            f"# Audio QA: Ceiling Analysis — {chunk_name}",
            "",
            "> ⚠ **PRODUCTION HYGIENE CHECK — NOT A STYLE TARGET**",
            f"> This report compares **{chunk_name}** against a commercial reference",
            f"> (`{ceiling_name}`) to detect gross production failures only.",
            "> These are **red flags**, not genre norms. Features excluded below",
            "> are genre-specific and are intentionally not compared.",
            "",
            "| | |",
            "|---|---|",
            f"| **Chunk** | {chunk_name} |",
            f"| **Commercial reference** | {ceiling_name} |",
            f"| **Features checked** | {n_checked} of 12 |",
            f"| **Red flags raised** | {n_flags} — {flag_verdict} |",
            "",
        ]
    )

    # ------------------------------------------------------------------
    # Section 2 — Feature comparison table
    # ------------------------------------------------------------------
    rows: list[tuple] = []
    for key in _CEILING_FEATURE_ORDER:
        display = _FEATURE_DISPLAY[key]
        unit = _FEATURE_UNITS[key]
        delta = deltas[key]
        threshold = ceiling_thresholds[key]
        is_flagged = key in red_flags

        fmt = _FEATURE_FMT.get(key, ".4f")

        if key == "mfcc_distance":
            ref_str = format(0.0, fmt)
            chunk_str = format(delta, fmt)
        else:
            ref_str = format(ceiling_feats[key], fmt)
            chunk_str = format(chunk_feats[key], fmt)

        sign = "+" if delta >= 0 else ""
        delta_str = f"{sign}{format(delta, fmt)}"
        thr_str = f"±{format(threshold, fmt)}"

        rows.append(
            (
                display,
                unit,
                ref_str,
                chunk_str,
                delta_str,
                thr_str,
                "⚠" if is_flagged else "✓",
            )
        )

    hdr = ("Feature", "Unit", "Ceiling Ref", "Chunk", "Delta", "Threshold", "Flag")
    widths = [max(len(hdr[i]), max(len(r[i]) for r in rows)) for i in range(len(hdr))]

    def _row(*cells):
        return (
            f"| {cells[0]:<{widths[0]}} "
            f"| {cells[1]:<{widths[1]}} "
            f"| {cells[2]:>{widths[2]}} "
            f"| {cells[3]:>{widths[3]}} "
            f"| {cells[4]:>{widths[4]}} "
            f"| {cells[5]:>{widths[5]}} "
            f"| {cells[6]} |"
        )

    sep = (
        f"| {'-'*widths[0]} "
        f"| {'-'*widths[1]} "
        f"| {'-'*widths[2]:>{widths[2]}} "
        f"| {'-'*widths[3]:>{widths[3]}} "
        f"| {'-'*widths[4]:>{widths[4]}} "
        f"| {'-'*widths[5]:>{widths[5]}} "
        f"| --- |"
    )

    excluded_note = (
        f"*Not compared (genre-specific): " f"{', '.join(_CEILING_EXCLUDED_DISPLAY)}.*"
    )

    table_lines = ["## Feature Comparison (Production Hygiene Features Only)", ""]
    table_lines += [_row(*hdr), sep]
    for r in rows:
        table_lines.append(_row(*r))
    table_lines += ["", excluded_note, ""]
    feature_table = "\n".join(table_lines)

    # ------------------------------------------------------------------
    # Section 3 — Red flags
    # ------------------------------------------------------------------
    flag_lines = ["## Red Flags", ""]
    if not red_flags:
        flag_lines += [
            "_No red flags raised — no gross production hygiene violations detected._",
            "_All checked features are within the ceiling tolerance band._",
            "",
        ]
    else:
        for feature in red_flags:
            delta = deltas[feature]
            label = _get_ceiling_flag_label(feature, delta)
            display = _FEATURE_DISPLAY[feature]
            unit = _FEATURE_UNITS.get(feature, "")
            sign = "+" if delta >= 0 else ""
            fmt = _FEATURE_FMT.get(feature, ".4f")
            d_str = f"{sign}{format(delta, fmt)}"
            d_with_unit = f"{d_str} {unit}".strip()
            flag_lines.append(f"- **{display}** `{d_with_unit}` — {label}")
        flag_lines.append("")
    red_flag_section = "\n".join(flag_lines)

    # ------------------------------------------------------------------
    # Section 4 — LLM-paste-ready summary block
    # ------------------------------------------------------------------
    inner: list[str] = [
        f"CEILING ANALYSIS — {chunk_name}",
        f"Commercial reference: {ceiling_name}",
        f"Red flags raised: {n_flags} of {n_checked} features checked",
        "",
    ]

    if red_flags:
        inner.append("Red flags:")
        for feature in red_flags:
            delta = deltas[feature]
            display = _FEATURE_DISPLAY[feature]
            unit = _FEATURE_UNITS.get(feature, "")
            sign = "+" if delta >= 0 else ""
            fmt = _FEATURE_FMT.get(feature, ".4f")
            d_str = f"{sign}{format(delta, fmt)}"
            d_with_unit = f"{d_str} {unit}".strip()
            label = _get_ceiling_flag_label(feature, delta)
            # Strip markdown bold/italics for plain-text block
            plain_label = label.replace("*(", "(").replace(")*", ")").replace("**", "")
            inner.append(f"  - {display} ({d_with_unit}): {plain_label}")
    else:
        inner.append(
            "No gross production hygiene violations detected. "
            "All checked features are within the ceiling tolerance band."
        )

    excluded_plain = ", ".join(_CEILING_EXCLUDED_DISPLAY)
    inner += [
        "",
        f"Features not compared (genre-specific): {excluded_plain}",
        "",
        "IMPORTANT: The commercial reference values are NOT style targets.",
        "These are production hygiene floors only. Genre differences are intentional.",
        "",
        "Subjective note from user: [paste what you hear here]",
    ]

    summary_lines = [
        "## Ceiling Analysis Summary",
        "",
        "> *Paste the block below directly into an LLM prompt.*",
        "",
        "```",
    ]
    summary_lines.extend(inner)
    summary_lines += ["```", ""]
    summary_section = "\n".join(summary_lines)

    return "\n".join([header, feature_table, red_flag_section, summary_section])


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
