### Architectural Diagnosis: The Scalar Invariant

The existing codebase is built on a strict architectural invariant: **one audio file produces one flat dictionary of scalar values**. 
- `profiler.py` expects a 1:1 file-to-profile comparison.
- `scorer.py` expects `deltas[feature]` to be a single numeric type compatible with `abs()`.
- `config.py` enforces a strict bijection between `THRESHOLDS` and `WEIGHTS`.
- `reporter.py` expects to format single numbers for its Markdown tables.

Extensions A (UVR5 Stems) and B (Windowed Time-Series) fundamentally violate this invariant. Integrating them requires explicit routing of non-scalar and multi-file data around the existing scalar scoring path to prevent hard crashes and silent failures.

---

### Question 1: UVR5 Stem Separation & Profiler Calls

**Diagnosis:** `main.py` and `profiler.py` have no concept of sub-tracks. `analyze_chunk()` takes exactly one `chunk_path` and one `reference_profile`. 

**Answer:** Yes, the proposal requires three separate extraction passes. Furthermore, if the three-table structure is to include *deltas* (and thus scores) for the stems, **the reference track must also be pre-separated via UVR5**, yielding three reference profiles. If there is no per-stem reference, the stems can only be reported as raw values.

#### Integration Strategies & Trade-offs

| Strategy | Description | Trade-offs |
| :--- | :--- | :--- |
| **Option A: Full Stem QA** | UVR5 separates both Reference and Chunk. `analyze_chunk()` is called 3 times. | **Pros:** Full scoring and delta reporting for stems.<br>**Cons:** Triples extraction time; requires 3x reference caching logic; requires stem-specific `THRESHOLDS` in `config.py`. |
| **Option B: Raw Stem Reporting** | UVR5 separates Chunk only. `analyze_chunk()` runs on the Mix. `extract_features()` runs on stems. | **Pros:** No changes to `scorer.py` or `config.py`; backward compatible.<br>**Cons:** Stems get no consistency score, only raw values in the report. |

#### Implementation Sketch (Option A - Orchestration Layer in `main.py`)
UVR5 must be injected as a pre-processing hook *before* profiling.

```python
def run_single_with_stems(reference_path: str, chunk_path: str):
    # 1. Mandatory Pre-processing Hook
    ref_stems = uvr5_separate(reference_path) # Returns dict: {'mix': path, 'vocal': path, 'inst': path}
    chunk_stems = uvr5_separate(chunk_path)

    # 2. Build/Load 3 Reference Profiles
    ref_profiles = {
        stem: _load_or_build_reference(path) 
        for stem, path in ref_stems.items()
    }

    # 3. Analyze 3 Chunks
    analyses = {
        stem: analyze_chunk(path, ref_profiles[stem]) 
        for stem, path in chunk_stems.items()
    }
    
    # 4. Score and Report (Requires reporter update to handle 3 analyses)
    mix_score = score_chunk(analyses["mix"], THRESHOLDS, WEIGHTS)
    return generate_three_table_report(analyses, mix_score)
```

---

### Question 2: Windowed Time-Series & Scorer Compatibility

**Diagnosis:** `scorer.score_chunk()` executes `raw_penalty = max(0.0, abs(delta) / threshold - 1.0)`. 

**Answer:** Yes, `scorer.py` will immediately raise a `TypeError: bad operand type for abs(): 'list'` if windowed lists are placed in the `deltas` dictionary. The proposal must either explicitly exclude windowed features from the `deltas` dict, or compute a summary statistic (e.g., mean) to pass to the scorer.

**Silent Failure Flag:** If you simply compute `mean(HNR)` to satisfy the scorer's scalar contract, the pipeline will run, but the temporal variance data (the entire purpose of Extension B) will be silently dropped and unavailable to `reporter.py`.

#### Refactoring Plan (Preserving Scalar Path while adding Windowed Data)

1. **Modify `extractor.py` Schema:** Return a nested dictionary separating scalars from time-series data.
2. **Modify `profiler.py` Routing:** Compute scalar deltas for the scorer, but pass windowed data through untouched in a new key.
3. **Update `reporter.py`:** Read the new `windowed_values` key to generate the CSV or time-series plots.

#### Schema Design
```python
# extractor.py output contract
{
    "scalars": {
        "lufs": -14.2,
        "rms": 0.05,
        "mean_hnr": 12.4  # Aggregated for scorer
    },
    "windowed": {
        "hnr": [12.1, 12.5, 11.9, ...], # Bypasses scorer
        "pitch_confidence": [0.9, 0.8, 0.9, ...]
    }
}

# profiler.py output contract
{
    "chunk_path": "...",
    "deltas": { ... }, # ONLY scalars. Safe for scorer.py
    "windowed_chunk": { ... }, # Raw lists for reporter.py
    "windowed_ref": { ... }
}
```

---

### Question 3: Config Alignment & New Metrics

**Diagnosis:** `config.py` enforces `set(THRESHOLDS) == set(WEIGHTS)` at import time. Furthermore, `scorer.py` iterates over `THRESHOLDS.items()`, **not** `deltas.keys()`.

**Answer:** If the five new vocal-stem metrics (HNR, VAR, pitch_confidence, spectral_flatness, F0_range) are intended to affect the Consistency Score, they **must** have entries in both `THRESHOLDS` and `WEIGHTS`. Based on the proposal description, they are currently unanchored (no calibrated thresholds exist yet).

**Silent Failure Flag:** If a developer adds these 5 metrics to `extractor.py` and `profiler.py` but forgets to add them to `config.py`, the pipeline **will not crash**. Because `scorer.py` iterates over `THRESHOLDS`, it will simply ignore the new keys in `deltas`. The metrics will be silently excluded from the score.

#### Refactoring Plan (Safe Introduction of Unanchored Metrics)

To introduce these metrics without breaking the pipeline or skewing the score with uncalibrated data:

1. **Add to Extractor:** Implement the 5 metrics in `extractor.py` (returning scalar summaries if they are windowed).
2. **Add to Config with Zero Weight:** Add them to `config.py` with wide dummy thresholds and `0.0` weight. This satisfies the import invariant and prevents them from affecting the score while calibration occurs.

```python
# config.py
THRESHOLDS: dict[str, float] = {
    # ... existing 12 keys ...
    "mean_hnr": 999.0,             # Unanchored, wide threshold
    "pitch_confidence": 999.0,
    "spectral_flatness": 999.0,
    "f0_range": 999.0,
    "var": 999.0,
}

WEIGHTS: dict[str, float] = {
    # ... existing 12 keys ...
    "mean_hnr": 0.0,               # 0.0 weight = does not affect score
    "pitch_confidence": 0.0,
    "spectral_flatness": 0.0,
    "f0_range": 0.0,
    "var": 0.0,
}
```
3. **Calibrate:** Run a batch, observe the deltas in the report, and update `THRESHOLDS` and `WEIGHTS` with real heuristics in a subsequent PR.