# Graph Report - /home/akbar/Jupyter_Notebooks/AntiGravity/audio_bench  (2026-07-26)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 281 nodes · 464 edges · 24 communities (14 shown, 10 thin omitted)
- Extraction: 68% EXTRACTED · 32% INFERRED · 0% AMBIGUOUS · INFERRED: 147 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8c2bb05b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- score_chunk
- _band_energy_fraction
- main.py
- reporter.py
- extract_features
- test_config.py
- generate_report
- conftest.py
- generate_style_compare_report
- generate_ceiling_report
- test_profiler.py
- _fmt_delta
- _fmt
- _fmt_delta_with_unit
- High shelf
- Low-mid energy
- MFCCs
- Presence band
- Spectral centroid
- Spectral rolloff
- Stereo width
- Tempo
- Zero crossing rate

## God Nodes (most connected - your core abstractions)
1. `generate_report()` - 31 edges
2. `score_chunk()` - 24 edges
3. `extract_features()` - 21 edges
4. `make_analysis_fn()` - 18 edges
5. `run_single()` - 15 edges
6. `TestExtractFeatures` - 15 edges
7. `run_batch()` - 12 edges
8. `generate_style_compare_report()` - 12 edges
9. `main.py` - 12 edges
10. `_band_energy_fraction()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `test_generate_report_contains_chunk_name()` --calls--> `generate_report()`  [INFERRED]
  tests/test_profiler.py → src/reporter.py
- `test_generate_report_contains_score()` --calls--> `generate_report()`  [INFERRED]
  tests/test_profiler.py → src/reporter.py
- `test_generate_report_has_diagnostic_summary_section()` --calls--> `generate_report()`  [INFERRED]
  tests/test_profiler.py → src/reporter.py
- `test_generate_report_has_feature_comparison_section()` --calls--> `generate_report()`  [INFERRED]
  tests/test_profiler.py → src/reporter.py
- `test_generate_report_has_flagged_deviations_section()` --calls--> `generate_report()`  [INFERRED]
  tests/test_profiler.py → src/reporter.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Mutually Exclusive CLI Modes** — readme_cli_reference, readme_cli_ceiling, readme_cli_style_compare [EXTRACTED 1.00]
- **QA Features Set** — readme_lufs, readme_rms, readme_crest_factor_db, readme_spectral_centroid, readme_spectral_rolloff, readme_low_mid_energy, readme_presence_band, readme_high_shelf, readme_stereo_width, readme_tempo, readme_mfcc, readme_zcr [EXTRACTED 1.00]
- **QA Pipeline Files** — readme_main_py, readme_config_py, readme_extractor_py, readme_profiler_py, readme_reporter_py, readme_scorer_py [EXTRACTED 1.00]

## Communities (24 total, 10 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.05
Nodes (51): _build_ceiling_record(), _build_qa_record(), _build_style_record(), _collect_audio_files(), _load_or_build_reference(), main(), main.py — Phase 3 / 4: CLI Entry Point Audio QA — Classical Arabic Poem → Suno A, Build a pandas-friendly record from a single QA pipeline run.      Features are (+43 more)

### Community 1 - "score_chunk"
Cohesion: 0.14
Nodes (27): config.py — Phase 3: Deviation Thresholds & Perceptual Weights Audio QA — Classi, scorer.py — Phase 3: Consistency Score & Deviation Flagging Audio QA — Classical, Score one chunk's analysis against the reference using configured     thresholds, score_chunk(), make_analysis_fn(), Execute the __main__ testing logic inside scorer.py to guarantee 100% coverage., test_at_exactly_threshold_no_penalty(), test_capped_penalty_at_two_times() (+19 more)

### Community 2 - "_band_energy_fraction"
Cohesion: 0.12
Nodes (14): ndarray, _band_absolute_power(), _band_energy_fraction(), extract_vocal_stem_features(), extractor.py — Phase 1: Feature Extraction Audio QA — Classical Arabic Poem → Su, Extract 5 vocal-stem-specific metrics from a separated vocal stem and its     co, Fraction of total spectral power in the frequency band [f_low, f_high) Hz., Absolute spectral power (sum of squared FFT magnitudes) in [f_low, f_high) Hz. (+6 more)

### Community 3 - "main.py"
Cohesion: 0.09
Nodes (22): --batch mode, --ceiling mode, Prompt Debug mode, --reference mode, --stems mode, --style-compare mode, config.py, Consistency Score (+14 more)

### Community 4 - "reporter.py"
Cohesion: 0.17
Nodes (17): generate_prompt_debug_report(), _get_flag_label(), reporter.py — Phase 3: Markdown Report Generator Audio QA — Classical Arabic Poe, Return the plain-English deviation label for a flagged feature.     Labels are d, FR-6 mandatory block — paste this directly into an LLM prompt.     Always presen, Phase 5 — 'Suno Prompt Implications' section.      Only rendered when at least o, Task 3.1 — Raw stem analysis section.      Renders two sub-tables:       1. Mix-, Phase 5 — Prompt debug report.      Identical to generate_report() with one addi (+9 more)

### Community 5 - "extract_features"
Cohesion: 0.21
Nodes (3): extract_features(), Load one audio file (WAV or MP3) and return a flat dict of all 12 features., TestExtractFeatures

### Community 7 - "generate_report"
Cohesion: 0.23
Nodes (15): generate_report(), Generate a full Markdown QA report for one chunk.      Args:         chunk_name:, make_score_fn(), test_generate_report_flagged_feature_shown(), test_verdict_band(), test_generate_report_contains_chunk_name(), test_generate_report_contains_score(), test_generate_report_flagged_feature_shown() (+7 more)

### Community 8 - "conftest.py"
Cohesion: 0.16
Nodes (12): make_analysis(), make_score(), mono_sine_wav(), perfect_score(), 3-second 440 Hz sine wave, mono, float32. Minimal valid audio., 3-second 440 Hz sine wave, stereo (L/R differ slightly for width > 0)., 2-second silence — edge case for RMS=0 and crest_factor_db=0., Return a minimal analysis dict with zero deltas for all features.     Override s (+4 more)

### Community 9 - "generate_style_compare_report"
Cohesion: 0.15
Nodes (13): generate_style_compare_report(), _get_style_compare_note(), Style Gap Analysis — neutral mix-character briefing report.      Compares a Suno, Plain-English perceptual note for a style gap feature delta.      Tone: neutral, test_generate_style_compare_report_returns_string(), test_generate_style_report_direction_arrows(), test_generate_style_report_has_all_required_sections(), test_generate_style_report_no_score_or_verdict() (+5 more)

### Community 10 - "generate_ceiling_report"
Cohesion: 0.18
Nodes (11): generate_ceiling_report(), _get_ceiling_flag_label(), Phase 6 — Ceiling analysis Markdown report.      Compares chunk against a commer, Plain-English red-flag label for ceiling analysis.      Labels are framed as pro, test_generate_ceiling_report_contains_flag_name_when_flagged(), test_generate_ceiling_report_contains_no_violations_text_when_clean(), test_generate_ceiling_report_returns_string(), test_get_ceiling_flag_label() (+3 more)

### Community 11 - "test_profiler.py"
Cohesion: 0.18
Nodes (10): Cover vocal stem raw detail sub-tables within report generator (lines 491-540)., test_generate_report_contains_chunk_name(), test_generate_report_contains_score(), test_generate_report_has_diagnostic_summary_section(), test_generate_report_has_feature_comparison_section(), test_generate_report_has_flagged_deviations_section(), test_generate_report_has_mfcc_detail_section(), test_generate_report_no_flags_shows_pass_text() (+2 more)

### Community 12 - "_fmt_delta"
Cohesion: 0.25
Nodes (8): _fmt_delta(), Format a delta with explicit +/- sign., test_fmt_delta_negative_has_minus_sign(), test_fmt_delta_positive_has_plus_sign(), test_fmt_delta_zero_has_plus_sign(), test_fmt_delta_negative_has_minus_sign(), test_fmt_delta_positive_has_plus_sign(), test_fmt_delta_zero_has_plus_sign()

### Community 13 - "_fmt"
Cohesion: 0.33
Nodes (6): _fmt(), Format a scalar value using the feature's display format., test_fmt_hz_one_decimal(), test_fmt_lufs_two_decimal_places(), test_fmt_hz_one_decimal(), test_fmt_lufs_two_decimal_places()

### Community 14 - "_fmt_delta_with_unit"
Cohesion: 0.33
Nodes (6): _fmt_delta_with_unit(), Delta formatted with unit suffix — used in LLM summary block., test_fmt_delta_with_unit_appends_hz(), test_fmt_delta_with_unit_strips_empty_unit(), test_fmt_delta_with_unit_appends_hz(), test_fmt_delta_with_unit_strips_empty_unit()

## Knowledge Gaps
- **26 isolated node(s):** `config.py`, `reporter.py`, `reference_profile.json`, `reports/`, `Consistency Score` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_single()` connect `main.py` to `score_chunk`, `_band_energy_fraction`, `reporter.py`, `extract_features`, `generate_report`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Why does `generate_report()` connect `generate_report` to `main.py`, `test_profiler.py`, `reporter.py`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `extract_features()` connect `extract_features` to `main.py`, `_band_energy_fraction`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `generate_report()` (e.g. with `run_batch()` and `run_single()`) actually correct?**
  _`generate_report()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `score_chunk()` (e.g. with `run_batch()` and `run_single()`) actually correct?**
  _`score_chunk()` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `extract_features()` (e.g. with `run_ceiling()` and `run_single()`) actually correct?**
  _`extract_features()` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `make_analysis_fn()` (e.g. with `make_analysis()` and `test_generate_report_flagged_feature_shown()`) actually correct?**
  _`make_analysis_fn()` has 17 INFERRED edges - model-reasoned connections that need verification._