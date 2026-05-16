Here are my assessments of the four engineering and measurement questions you have raised. I have all the necessary context from the provided files to address these.

---

### 1. MFCC Distance Threshold & Scoring Reliability

**Primary Finding**
The 7.0 threshold is a heuristic boundary, and single-point flag decisions around it are perceptually unreliable. The 99.4/100 score accurately reflects that a 7.28 distance is a mathematically trivial overshoot, not a catastrophic failure.

**Evidence Basis**

1. **The Scoring Formula:** As defined in `scorer.py`, the penalty is continuous: `max(0.0, abs(delta) / threshold - 1.0)`. A delta of 7.28 against a 7.0 threshold yields a raw penalty of just 0.04. Multiplied by the 1.5 weight, it barely dents the 100-point scale. The binary "Flag" is merely a UI label, while the score handles the actual severity.
2. **Conflation Risk:** MFCCs capture the overall spectral envelope. As noted in my core expertise, mean-MFCC distance conflates true timbral shifts (e.g., the vocalist changing) with arrangement shifts (e.g., a synth pad entering, or reverb tail extending).

**Confidence & Caveats**

- **High confidence** in the mathematical behavior of the script: the continuous scoring formula is working exactly as intended to prevent arbitrary cliff-edges at the threshold.
- **Limited confidence** in the perceptual meaning of the 7.28 value itself. Because MFCCs cannot isolate voice identity from mix bus changes, I cannot tell you if this 7.28 delta represents a new vocalist or simply a denser instrumental arrangement without listening to the chunk.

---

### 2. Crest Factor as a Dynamic Range Metric

**Primary Finding**
Crest factor is the wrong tool for measuring perceived dynamic range in vocal poetry. It misrepresents the perceptual phenomenon it is attempting to capture.

**Evidence Basis**
Crest factor (20·log10(peak/RMS)) is a waveform-domain measurement. It measures the distance between the highest transient spike and the average energy. In spoken word or vocal poetry, transient consonants (plosives like "P" and "B", or sibilance like "S" and "T") dictate the peak value. A track can have a massive crest factor simply because of an un-de-essed vocal or a loud plosive, even if the actual vocal delivery is dynamically flat and heavily compressed.

**Confidence & Caveats**

- **High confidence** based on the mathematical definition of crest factor versus psychoacoustic loudness principles.
- **Recommendation:** If you want to measure the perceived macro-dynamics (the musical difference between loud and soft phrases), Loudness Range (LRA) is the correct metric. LRA uses a statistical percentile spread of short-term LUFS blocks, effectively ignoring transient consonant spikes.

---

### 3. Presence Band as Fractional Power

**Primary Finding**
Yes, fractional framing introduces a direct conflation risk. A flagged drop in the presence band could absolutely be a bass-level shift in disguise.

**Evidence Basis**
By defining band energy as a "fraction of total spectral power" (as noted in the `README.md`), the metric divides the energy in the 1kHz–4kHz band by the total energy across all frequencies. If a chunk introduces heavy low-end energy (e.g., a bass instrument enters, or the AI generates proximity-effect rumble on the vocal), the total energy denominator increases. This mathematically shrinks the presence fraction, even if the absolute acoustic energy of the vocal in the 1kHz–4kHz range is identical to the reference.

**Confidence & Caveats**

- **High confidence** given the basic arithmetic of fractional normalization.
- **What this means for QA:** When you see a presence band flag, you must cross-reference it with the `low_mid_energy` and `spectral_rolloff` deltas. If the presence fraction drops while low-mid energy spikes, you are likely looking at a low-end buildup masking the vocal, not a recessed vocal.

---

### 4. LUFS Consistency vs. Streaming Normalization

**Primary Finding**
Chunk-to-chunk LUFS consistency is absolutely critical to score highest, _precisely because_ of how streaming normalization works.

**Evidence Basis**
Streaming platforms (Spotify, Apple Music, YouTube) apply a single, static gain offset to the _entire_ delivered file based on its overall integrated LUFS. They do not ride the fader or normalize section-by-section.

Because your pipeline is "Suno AI → Audacity Pipeline", you are assembling these chunks into a single master file. If Chunk A is −14 LUFS and Chunk B is −18 LUFS, assembling them creates a track with a jarring 4 dB volume drop in the middle. When Spotify normalizes that assembled track to −14 LUFS, it will apply the exact same gain change to the whole file—meaning that jarring 4 dB internal drop will be permanently baked in and broadcast to the listener.

**Confidence & Caveats**

- **High confidence** based on ITU-R BS.1770-4 standards and the documented delivery protocols of major streaming platforms. Normalization targets the master bus, not the arrangement blocks. Pre-assembly consistency is the only way to ensure a cohesive final master.
