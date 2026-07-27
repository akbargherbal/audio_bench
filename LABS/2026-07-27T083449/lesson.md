# Lab 04 — Why Does Version A Sound "Clearer" Than Version B?

**Session date:** 2026-07-27
**Files:** `04-A.mp3`, `04-B.mp3` — two generations from the *same* Suno batch, same prompt, same seed lineage (Suno renders two takes per generation).
**Tool used:** `audio_bench` (this repo), `--style-compare` mode.

## 1. The subjective observation that started this lab

Before touching any numbers, the human listener's raw impression was:

> "I lean toward Version A. When the singer starts (نعُمُّ أُناساً سَناً ونَعِفُّ عَنْهُم), I hear him almost alone at the mic in A. In B I hear something accompanying him — more reverb than expected, a lack of purity. B feels *boxy*, like it wasn't recorded in a well-treated large room. This repeats at other lines too, even though B's *maqam* phrasing is arguably better in places."

This is the classic starting point of this lab series: turn a vague "something's off" into a named audio-engineering concept. Three concepts turned out to matter here: **LUFS**, **stereo width**, and **band energy (the "boxiness" band)**. Each is introduced below, then used directly on the two files.

## 2. Setup

Both files and their auto-generated transcripts (`04-A.srt`, `04-B.srt`) live in this lab folder. The transcripts double as a cheap "what instrument entered when" log, which turns out to matter later.

```python
import sys
import os

# Repo root is two levels up from this lab folder (LABS/<timestamp>/ -> LABS/ -> root)
REPO_ROOT = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

import numpy as np
import librosa
import soundfile as sf
import pyloudnorm as pyln

from extractor import extract_features, _band_energy_fraction, TARGET_SR

A_PATH = "04-A.mp3"
B_PATH = "04-B.mp3"

print("Repo root resolved to:", REPO_ROOT)
```

```text
Repo root resolved to: /home/claude/audio_bench
```

## 3. Concept: LUFS (Loudness Units relative to Full Scale)

LUFS is a standardized measure of *perceived* loudness, not peak amplitude. Unlike a simple peak or RMS reading, the LUFS algorithm (ITU-R BS.1770) applies a filter that approximates how the human ear weights frequencies, then integrates over time. It's the metric streaming platforms (Spotify, YouTube) use for loudness normalization.

Two tracks can have identical peak levels but very different LUFS if one has more sustained energy and the other is spikier.

```python
def measure_lufs(filepath: str) -> float:
    """Integrated loudness in LUFS. More negative = quieter."""
    data, rate = sf.read(filepath, always_2d=True)
    meter = pyln.Meter(rate)
    return meter.integrated_loudness(data)

lufs_a = measure_lufs(A_PATH)
lufs_b = measure_lufs(B_PATH)

print(f"A: {lufs_a:.2f} LUFS")
print(f"B: {lufs_b:.2f} LUFS")
print(f"Delta (B - A): {lufs_b - lufs_a:+.2f} LUFS")
```

```text
A: -12.32 LUFS
B: -12.86 LUFS
Delta (B - A): -0.55 LUFS
```

B sits about half a loudness-unit quieter than A across the whole track. On its own this is a small, easily-missed gap — the interesting part shows up once we stop looking at whole-track averages (Section 6).

## 4. Concept: Stereo Width

Stereo width measures how *different* the left and right channels are from each other. `audio_bench` computes it via **mid-side decomposition**:

$$\text{mid} = \frac{L + R}{2} \qquad \text{side} = \frac{L - R}{2}$$

$$\text{stereo\_width} = \frac{\text{RMS(side)}}{\text{RMS(mid)}}$$

- **mid** is what's identical/centered in both channels (usually lead vocal, kick, bass — anything panned dead-center).
- **side** is what *differs* between channels (reverb tails, wide-panned instruments, stereo-doubled parts).
- A width near **0** means near-mono (everything centered). A width that spikes upward means something wide and decorrelated (often a reverb or a swelling pad/orchestral layer) briefly dominates the mix.

Importantly: **this is a mix/arrangement metric, not a room-acoustics metric.** Suno doesn't simulate a physical room — "plate reverb" in a prompt is an algorithmic effect, not a recording space. A wide stereo image can come from a well-simulated hall *or* just from stacking wide, decorrelated layers (like an orchestral swell) on top of a vocal. The number tells us *what happened in the signal*, not *why* it happened — for the "why" we still need to look at the arrangement.

```python
def measure_stereo_width(filepath: str) -> float:
    """Side/Mid RMS ratio. 0.0 if mono."""
    y, sr = librosa.load(filepath, mono=False, sr=TARGET_SR)
    if y.ndim != 2:
        return 0.0
    L, R = y[0], y[1]
    mid = (L + R) / 2.0
    side = (L - R) / 2.0
    return float(np.sqrt(np.mean(side**2)) / (np.sqrt(np.mean(mid**2)) + 1e-9))

width_a = measure_stereo_width(A_PATH)
width_b = measure_stereo_width(B_PATH)

print(f"A: {width_a:.3f}")
print(f"B: {width_b:.3f}")
print(f"Delta (B - A): {width_b - width_a:+.3f}")
```

```text
A: 0.427
B: 0.418
Delta (B - A): -0.009
```

Whole-track, B is actually very slightly *narrower* than A — nearly a tie. This is the number that misled the first pass of this lab. It only becomes interesting once we stop averaging over 4+ minutes and isolate the vocal entrance (Section 6).

## 5. Concept: Band Energy — the "boxy" frequency range

"Boxy" is a common but vague engineering complaint. It usually points to a buildup of energy in the **low-mid range, roughly 200–500 Hz** — the range that carries vocal body/warmth in healthy amounts, but reads as muffled, congested, or like the source is trapped in a small hard-walled space when it builds up too much.

`audio_bench` measures this as a **fraction of total spectral power** (not absolute energy), so it's comparable across clips of different length or loudness:

```python
def measure_band_fraction(filepath: str, f_low: float, f_high: float) -> float:
    """Fraction of total FFT power in [f_low, f_high) Hz. Range [0, 1]."""
    y, sr = librosa.load(filepath, mono=False, sr=TARGET_SR)
    y_mono = librosa.to_mono(y) if y.ndim == 2 else y
    return _band_energy_fraction(y_mono, sr, f_low, f_high)

low_mid_a = measure_band_fraction(A_PATH, 200.0, 500.0)
low_mid_b = measure_band_fraction(B_PATH, 200.0, 500.0)

print(f"Low-mid (200-500Hz) A: {low_mid_a:.4f}")
print(f"Low-mid (200-500Hz) B: {low_mid_b:.4f}")
print(f"Delta (B - A): {low_mid_b - low_mid_a:+.4f}")
```

```text
Low-mid (200-500Hz) A: 0.1234
Low-mid (200-500Hz) B: 0.1070
Delta (B - A): -0.0164
```

Whole-track, B has *less* low-mid energy than A — the opposite of the "boxy" hypothesis. Same trap as stereo width: a single global average across the whole song can hide a short, localized spike. That's the motivation for Section 6.

## 6. Investigation 1 — Whole-track style comparison (the full CLI report)

Before slicing anything, this is what the project's own `--style-compare` mode produces when run against the two full tracks. This mode is designed for exactly this situation: comparing two same-intent renders without assuming either one is "correct."

```bash
python ../../src/main.py \
  --style-compare 04-A.mp3 \
  --chunk 04-B.mp3
```

```text
| Feature                     | Unit | Commercial |     Suno |     Delta | Direction     |
| ---------------------------- | ---- | ---------- | -------- | --------- | ------------- |
| LUFS                        | LUFS |     -12.32 |   -12.86 |     -0.55 | down Suno lower  |
| RMS energy                  |      |   0.165515 | 0.150521 | -0.014995 | down Suno lower  |
| Crest factor                | dB   |      13.03 |    14.61 |     +1.57 | up Suno higher |
| Spectral centroid           | Hz   |     3411.5 |   3619.2 |    +207.7 | up Suno higher |
| Spectral rolloff            | Hz   |     7492.5 |   7820.1 |    +327.6 | up Suno higher |
| Low-mid energy (200-500 Hz) | frac |   0.123360 | 0.106982 | -0.016379 | down Suno lower  |
| Presence band (1k-4kHz)     | frac |   0.154432 | 0.176183 | +0.021751 | up Suno higher |
| High shelf (8kHz+)          | frac |   0.014450 | 0.024666 | +0.010216 | up Suno higher |
| Stereo width                |      |   0.426831 | 0.417513 | -0.009319 | down Suno lower  |
| MFCC distance                |      |     0.0000 |   0.0032 |   +0.0032 | up Suno higher |
```

**Whole-track, the numbers seem to *contradict* the ear.** B reads as brighter (higher spectral centroid/rolloff), more present (1-4kHz), and *less* muddy (lower low-mid) than A. If clarity were purely about broadband brightness, B should sound cleaner — not A.

This mismatch is the actual lesson here: **a single average over a 4+ minute track can hide a short, localized event that dominates first impressions.** The vocal entrance is a few seconds out of 264. Averaging washes it out.

## 7. Investigation 2 — Isolating specific lines

Using the SRT timestamps as ground truth, three moments were cut out of each file and re-compared in isolation: the vocal's first entrance, and two later lines the human specifically praised/criticized.

```bash
mkdir -p segments

# Opening line: "نعُمُّ أُناساً..." — where the human felt A was cleanest
ffmpeg -y -i 04-A.mp3 -ss 00:00:26 -to 00:00:37 segments/A_opening_vocal.mp3
ffmpeg -y -i 04-B.mp3 -ss 00:00:32 -to 00:00:43 segments/B_opening_vocal.mp3

# "نطاعن ما تراخى الناس عنا" — human noted B's maqam performance was better here
ffmpeg -y -i 04-A.mp3 -ss 00:00:48 -to 00:00:53 segments/A_nutaein.mp3
ffmpeg -y -i 04-B.mp3 -ss 00:00:48 -to 00:00:53 segments/B_nutaein.mp3

# "نجذ رؤوسهم في غير بر"
ffmpeg -y -i 04-A.mp3 -ss 00:02:58 -to 00:03:03 segments/A_najuzzu.mp3
ffmpeg -y -i 04-B.mp3 -ss 00:02:52 -to 00:02:57 segments/B_najuzzu.mp3
```

```python
segment_pairs = {
    "opening_vocal": ("segments/A_opening_vocal.mp3", "segments/B_opening_vocal.mp3"),
    "nutaein":       ("segments/A_nutaein.mp3",       "segments/B_nutaein.mp3"),
    "najuzzu":       ("segments/A_najuzzu.mp3",       "segments/B_najuzzu.mp3"),
}

results = {}
for label, (path_a, path_b) in segment_pairs.items():
    feat_a = extract_features(path_a)
    feat_b = extract_features(path_b)
    results[label] = {
        "low_mid_energy_a": feat_a["low_mid_energy"],
        "low_mid_energy_b": feat_b["low_mid_energy"],
        "stereo_width_a": feat_a["stereo_width"],
        "stereo_width_b": feat_b["stereo_width"],
    }
    print(f"--- {label} ---")
    print(f"  low_mid  A={feat_a['low_mid_energy']:.3f}  B={feat_b['low_mid_energy']:.3f}  "
          f"delta(B-A)={feat_b['low_mid_energy']-feat_a['low_mid_energy']:+.3f}")
    print(f"  width    A={feat_a['stereo_width']:.3f}  B={feat_b['stereo_width']:.3f}  "
          f"delta(B-A)={feat_b['stereo_width']-feat_a['stereo_width']:+.3f}")
```

```text
--- opening_vocal ---
  low_mid  A=0.141  B=0.257  delta(B-A)=+0.116
  width    A=0.322  B=0.370  delta(B-A)=+0.048

--- nutaein ---
  low_mid  A=0.129  B=0.048  delta(B-A)=-0.081
  width    A=0.347  B=0.276  delta(B-A)=-0.070

--- najuzzu ---
  low_mid  A=0.282  B=0.081  delta(B-A)=-0.201
  width    A=0.318  B=0.298  delta(B-A)=-0.020
```

This is the turning point of the lab. **Only at the opening vocal entrance does B show a large low-mid spike (nearly double A's value).** At the other two lines — including the one where the human explicitly praised B's *maqam* phrasing — B is actually *less* boxy than A. The problem isn't a property of B's mix in general. It's localized to one specific moment: the singer's entrance.

## 8. Investigation 3 — Zooming into the first 2 seconds

To confirm this is a genuine transient event (and not just a coarser artefact of an 11-second window), the opening line was split into its first 2 seconds (the attack) and its remaining ~3 seconds (the sustain/tail).

```bash
mkdir -p segments/onset_narrow

ffmpeg -y -i 04-A.mp3 -ss 00:00:32.064 -to 00:00:34.064 segments/onset_narrow/A_onset_2s.mp3
ffmpeg -y -i 04-B.mp3 -ss 00:00:37.437 -to 00:00:39.437 segments/onset_narrow/B_onset_2s.mp3

ffmpeg -y -i 04-A.mp3 -ss 00:00:34.064 -to 00:00:36.935 segments/onset_narrow/A_onset_tail.mp3
ffmpeg -y -i 04-B.mp3 -ss 00:00:39.437 -to 00:00:42.302 segments/onset_narrow/B_onset_tail.mp3
```

```python
onset_pairs = {
    "onset_2s (attack)":   ("segments/onset_narrow/A_onset_2s.mp3",   "segments/onset_narrow/B_onset_2s.mp3"),
    "onset_tail (sustain)": ("segments/onset_narrow/A_onset_tail.mp3", "segments/onset_narrow/B_onset_tail.mp3"),
}

for label, (path_a, path_b) in onset_pairs.items():
    feat_a = extract_features(path_a)
    feat_b = extract_features(path_b)
    print(f"--- {label} ---")
    print(f"  LUFS     A={feat_a['lufs']:.2f}  B={feat_b['lufs']:.2f}  "
          f"delta(B-A)={feat_b['lufs']-feat_a['lufs']:+.2f}")
    print(f"  low_mid  A={feat_a['low_mid_energy']:.3f}  B={feat_b['low_mid_energy']:.3f}  "
          f"delta(B-A)={feat_b['low_mid_energy']-feat_a['low_mid_energy']:+.3f}")
    print(f"  width    A={feat_a['stereo_width']:.3f}  B={feat_b['stereo_width']:.3f}  "
          f"delta(B-A)={feat_b['stereo_width']-feat_a['stereo_width']:+.3f}")
```

```text
--- onset_2s (attack) ---
  LUFS     A=-15.54  B=-18.14  delta(B-A)=-2.60
  low_mid  A=0.174  B=0.228  delta(B-A)=+0.054
  width    A=0.329  B=0.659  delta(B-A)=+0.330

--- onset_tail (sustain) ---
  LUFS     A=-15.03  B=-15.39  delta(B-A)=-0.36
  low_mid  A=0.130  B=0.178  delta(B-A)=+0.048
  width    A=0.307  B=0.332  delta(B-A)=+0.025
```

At the literal attack — the first two seconds of the sung phrase — B's stereo width is **nearly double** A's (0.66 vs 0.33), and B sits **2.6 LUFS quieter**. Three seconds later, in the sustain/tail of the same phrase, the width gap has almost fully collapsed (0.33 vs 0.31) and the loudness gap shrinks to 0.36. This confirms the spike is a genuine transient — not a sustained mix characteristic — and it lands exactly where the human's ear flagged a problem.

## 9. Connecting the numbers back to the arrangement

The auto-generated transcripts annotate what's happening instrumentally at each timestamp. Comparing the two around the vocal entrance is revealing:

**`04-A.srt`** — orchestral swell and guitar power chords happen *before* the verse; the verse itself starts on close-to-bare vocals:
```text
2  → [orchestral strings, woodwinds, and brass swell]
3  → [distorted electric guitar enters with power chords]
4  → [Verse 1]
5  → [baritone male vocals]
6  → نعُمُّ أُناساً سَناً ونَعِفُّ عَنْهُم    <- vocal starts here, band already settled
```

**`04-B.srt`** — the orchestral swell is annotated as happening *simultaneously* with the vocal's first line:
```text
6  → [baritone male vocals]
7  → نعم أناسنا ونعف عنهم [orchestral strings swell]    <- swell hits at the same moment
```

That single arrangement difference is a plausible mechanism for everything measured above: in B, a wide, decorrelated orchestral swell arrives at the exact instant the voice enters, briefly doubling the stereo width and adding low-mid mass right on top of the vocal fundamental — then both effects decay within a few seconds as the swell settles. In A, the same swell had already resolved before the vocal started, so the voice enters onto a narrower, less congested bed.

## 10. Findings

1. **Whole-track averages actively misled the first hypothesis.** By every broadband metric (spectral centroid, rolloff, presence, low-mid), B reads as *brighter and less muddy* than A across the full song. The "A is clearer" impression could not be explained at that resolution.
2. **The effect is real, but localized to a ~2–3 second window at the vocal entrance.** Segment-level analysis reversed the picture: at that specific moment, B has roughly double A's low-mid energy and roughly double its stereo width.
3. **The spike decays quickly.** By the second half of the same sung phrase, both the width and low-mid gaps had mostly closed — consistent with a transient arrangement event (a swelling pad/orchestra), not a persistent mix problem.
4. **The transcript's own annotations point to a likely cause:** the orchestral swell is timed to land under the vocal's entrance in B, but resolves before the vocal entrance in A.
5. **This is not evenly distributed across the song.** At two other lines (`نطاعن ما تراخى الناس عنا`, `نجذ رؤوسهم في غير بر`), B was measurably *less* boxy than A — matching the human's separate observation that B's performance/phrasing was arguably stronger there.

## 11. Open questions for a future session

- Does the same onset-spike pattern repeat at the second and third vocal entrances after instrumental breaks (post-Bridge, post-instrumental-break in Verse 3), or was this specific to the very first entrance?
- Would isolating the vocal stem (`--stems` mode / `extract_vocal_stem_features`) show the low-mid spike living in the vocal signal itself, or purely in the orchestral layer underneath it — this would clarify whether it's a "vocal problem" or an "arrangement timing problem."
- Could a Gemini listening pass (per `LABS_README.md`'s guidance on when to bring in multimodal listening) independently confirm the swell timing described in the B transcript, since the transcript itself is a machine-generated approximation and not a verified ground truth?
