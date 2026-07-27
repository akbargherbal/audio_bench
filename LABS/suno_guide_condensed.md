# Suno Prompt Engineering — Condensed Guide

---

## 1. The Core Mental Model: Gravity Wells

Suno does not read prompts like human instructions. Instead, it maps your words into a probabilistic style-mesh built from co-occurrence patterns in its training data. When you ask for "rap," the model automatically blends in elements like trap, heavy bass, hip-hop flows, and beats because those concepts frequently appeared together in the training set.

### Genre Clouds

These are tight clusters of styles that are practically inseparable due to high co-occurrence in training:

- **The Rap Cloud:** Rap, trap, bass, hip hop, beat (rap and trap share over 327 billion statistical connections).
- **The Orchestral Cloud:** Orchestral, epic, cinematic, dramatic, piano.
- **The Indie Cloud:** Indie, pop, acoustic, dreamy, psychedelic.
- **The Dark Electronic Cloud:** Dark, synth, electro, synthwave, futuristic.

### The Pop Gravity Well

Nearly every genre statistically drifts toward pop unless you actively push back. The model's learned connections to pop are massive:

- **Rock** carries 315 billion links to pop.
- **Funk** carries 116 billion links.
- **Emo** carries 12.2 billion links (connecting far more to pop and piano than to metal).

Without intentional countermeasures, an "industrial rock" or "emo metal" prompt will quietly drift toward synth-pop or pop ballads.

### Escaping a Gravity Well

1.  **Explicit Exclusion:** Name what you do not want in the negative prompt/exclude field (e.g., exclude "Pop, Trap").
2.  **Force Unusual Combinations:** Pair genres that rarely co-occur (e.g., _"orchestral phonk"_, _"math rock gospel"_) to push the model into territory where its defaults do not apply.
3.  **Strategic Contrast:** Emphasize elements that naturally repel unwanted associations without naming them directly.

**Practical Rule:** The more a prompt repeats or reinforces a strong genre word (even split across multiple fields), the harder it is to override with subtler instructions elsewhere. If a fix in one field doesn't change the output, check whether another field is silently reinforcing the problem through word choice.

---

## 2. Prompt Structure & Formatting

Suno was trained on structured, categorical music metadata. Avoid comma-separated lists or prose in the style prompt and format your instructions in a structured hierarchy.

### The Preferred Format (Colon + Quotes)

```text
genre: "indie folk rock, 2020s bedroom pop" vocal: "soft female alto, intimate delivery" instrumentation: "fingerpicked acoustic guitar, sparse piano" production: "lo-fi intimacy, tape warmth" mood: "melancholic, nostalgic"
```

On the desktop interface, hovering over the style panel will underline each parsed section as a unified block if it was recognized correctly.

### Formatting Rules That Override Word Choice

- **Periods Mark Instruction Boundaries:** Periods tell Suno to complete one instruction block before moving to the next. Without them, concepts blend together and weaken.
- **Use Conjunctions for Essential Elements; Use Commas for Optional Ones:** Suno treats comma-separated items as optional or skippable. Instructions connected by `and` or `with` and closed with a period are treated as essential.
  - _Weak/Skippable:_ `acoustic guitar, male vocals, reverb`
  - _Strong/Essential:_ `acoustic guitar with male vocals and reverb-heavy production.`

---

## 3. Weak Tags vs. Strong Tags

Not all tags carry equal weight.

- **Strong Tags** (_pop, rock, electronic_) dominate easily and will overpower other instructions if unchecked.
- **Weak Tags** (_grunge, math rock, swing_) have low connection counts and get overwhelmed unless heavily reinforced with extra descriptors and context.

When combining a weak tag with a strong tag, the strong one wins by default. To make a weak tag land, you must heavily reinforce its associated instrumentation and style while actively excluding the strong tag's characteristics.

---

## 4. Exclude Tags (Negative Prompting)

Exclusions are used to carve out unwanted sonic space and prevent genre-cloud bleed (e.g., excluding _"Electronic, Synthesizer, Drum Machine"_ to keep a track acoustic; excluding _"Oud, Qanun"_ to keep Arabic vocals from pulling in traditional Middle Eastern instrumentation).

- **What Exclusions Are Not For:** Do not use exclusions to block performance-quality problems like shouting, straining, or rushing. Suppressing a behavior doesn't teach the model what to do instead. Address quality problems in the **positive** prompt by naming the desired technical delivery.
- **Keep the List Lean:** Bloating the exclude field with near-duplicates (e.g., _"screamo, forced belting, vocal strain"_) dilutes the weight of the negative prompt. Consolidate entries and drop tags that are already resolved by a positive-prompt fix.

---

## 5. Structural Controls & MAX Mode

For acoustic, country, folk, singer-songwriter, or orchestral music, Suno's internal routing system can be biased toward higher fidelity and realism using specific bracketed parameters at the start of the style prompt.

### The MAX Mode Stack

Include this exact stack at the beginning of the style prompt for organic genres:

```text
[Is_MAX_MODE: MAX](MAX) [QUALITY: MAX](MAX) [REALISM: MAX](MAX) [REAL_INSTRUMENTS: MAX](MAX)
```

_Note: This stack has minimal effect on purely electronic, trap, or synthwave music, where physical realism is not part of the aesthetic._

### Skipping the Intro

To skip Suno's default instrumental intro and start singing immediately, use the `START_ON` parameters:

```text
[START_ON: TRUE] [START_ON: "[First few words of your lyrics]"]
```

### Duet Voice Controls

To establish clean vocal handoffs in a duet, guide the starting voices:

```text
[DUET_START_ON: TRUE] [MALE_START_ON: "[First words of male lyrics]"] [FEMALE_START_ON: "[First words of female lyrics]"]
```

---

## 6. Lyric Bleed & Formatting

Suno performs soft classification between _conditioning text_ (instructions) and _performable text_ (lyrics). Short poetic lines, brackets resembling stage directions, ALL CAPS phrases, quoted text, or rhythmic prose in the style prompt risk being sung as lyrics.

### Mitigations

- Keep your style prompt technical and dense to prevent it from scanning as singable lyrics.
- Always put content in the lyrics box. An empty lyrics box invites the model to pull performable text from your style prompt.
- Place `///*****///` at the very top of the lyrics box to force separation between metadata and performance text.

### Dynamic Lyrics Formatting

- **Vocal Intensity:** Match capitalization to delivery. Use standard sentence case for quiet passages and ALL CAPS for loud, belted, or intense lines:
  - _Calm:_ `My world's been left in sorrow for way too long.`
  - _Intense:_ `MY WORLD'S BEEN LEFT IN SORROW FOR WAY TOO LONG!`
- **Backing Vocals:** Place backing vocals or vocal echoes in parentheses: `(fading away...)` or `(RISE UP NOW!)`.
- **Separation:** Use a single blank line to separate section blocks.

---

## 7. Meta Tags (Section-Level Control)

Bracketed tags placed at the start of each lyrics section override the global style prompt for that specific section. For precise control, stack multiple instructions inside a single tag using the pipe (`|`) symbol.

```text
[Chorus | anthemic chorus | stacked harmonies | modern pop polish]
[guitar solo | 80s glam metal lead | heavy distortion | whammy bar bends]
```

### High-Yield Meta Tags

- **Vocal Arrangements:** `[raspy lead vocal]`, `[autotuned delivery]`, `[stacked harmonies]`, `[crowd-style vocals]`, `[spoken word verse]`.
- **Spatial & Reverb:** `[hall reverb]`, `[room reverb]`, `[plate reverb]`, `[spring reverb]`.
- **Dynamics & Energy:** `[high energy]`, `[building energy]`, `[explosive energy]`, `[breakdown]`, `[drop]`.
- **Technical Polish (For Intros/Outros):** `[high_fidelity]`, `[studio_mix]`, `[analog_warmth]`, `[crystal_clarity]`.

---

## 8. Realism Stack vs. Anti-Sawtooth Synthesis

### The Acoustic Realism Stack

"Realistic" is a weak descriptor that Suno often ignores. To achieve organic, authentic recordings, use specific, technical recording-engineer language:

- **Physical Space:** _small room acoustics, room tone (air, faint hiss), close mic presence, proximity effect, single-mic capture._
- **Performance Detail:** _natural timing drift, breath detail (inhales/exhales), pick noise, fret squeak, finger movement on strings._
- **Analog Character:** _tape saturation, analog warmth, slight wow and flutter, gentle preamp drive._
- **Spatial Dynamics:** _limited stereo, narrow mono image, realistic short-room reverb, consistent noise floor._

### The Anti-Sawtooth Synthesis Stack (Electronic & Hip-Hop)

Electronic genres do not benefit from realism tags. Instead, use specific synthesis and modulation terms to avoid Suno's loud, buzzy default sawtooth synths:

1.  **Describe the Synthesis Type, Not the Size:** Avoid terms like "big bass" or "heavy synth" (which trigger generic sawtooth waves). Request _"FM synthesis bass"_, _"wavetable movement"_, _"granular textures"_, or _"formant-driven bass"_.
2.  **Describe Motion:** Request _"evolving modulation"_, _"LFO-driven movement"_, or _"non-repeating harmonic motion"_.
3.  **Shape the Harmonics:** Request _"rounded harmonic profile"_, _"asymmetric waveforms"_, or _"band-limited synthesis"_.
4.  **Control the Frequencies and Stereo Field:** Saws rely on wide stereo panning and bright top ends. Request _"center-focused bass"_, _"mono-stable low end"_, _"controlled high end"_, and _"phase-coherent layers"_.

_Example Anti-Saw Prompt:_

```text
genre: "dark synthwave" instrumentation: "FM and wavetable bass design with evolving modulation and non-repeating harmonic motion" style tags: "rounded harmonic profile, controlled high end, phase-coherent low end, clean punch."
```

---

## 9. Personas — Build a Dossier, Not a Label

A vague persona description like "female country singer" produces highly inconsistent vocals across generations. To anchor a vocal identity, build a four-layer dossier:

1.  **Demographics & Timbre:** Age, gender, voice type, fundamental character (_"Female contralto, androgynous"_).
2.  **Technical Delivery:** Phrasing, breath control, enunciation (_"monotone delivery, sharp enunciation, vocal fry"_).
3.  **Emotional Context:** The feeling behind the performance (_"emotionally numb, cold, detached"_).
4.  **Sonic Anchor:** Reference artists to provide a statistical target (_"reminiscent of Grimes with HEALTH-like atmosphere"_).

Combine this detailed persona in your style prompt with the explicit Vocal Gender UI parameter (Male or Female) to reinforce vocal consistency.

---

## 10. Advanced Production: Splicing, Covers, & Mastering Hacks

### Built-In Remastering via Lyrics Editing

The default "Remaster" button can be guided by editing your metadata. Go to **Song Details > Displayed Lyrics**, add high-fidelity master tags in brackets at the very top of your lyrics, save the changes, and then click **Remaster**.

```text
[high_fidelity | studio_mix | analog_warmth | crystal_clarity | punchy_dynamics]
```

### Cover-Based Remastering

To clean up a track's audio quality without altering its structure, use the **Cover** feature instead of Remaster:

1.  Keep the lyrics and structure exactly the same.
2.  In the style prompt, enter only the original genre and mastering descriptors. Remove all creative style adjectives to prevent the cover from drifting.
    - _Cover Prompt Example:_ `[Original Genre] with high fidelity recording and professional mastering. Instrumentation: Acoustic drums with realistic sound. Mastering: Clean, modern, professional sound.`

### Song-to-Song Transplanting (Frankenstein Splicing)

If you want a specific section (such as a bridge or solo) to feature completely different instrumentation or vocal styles:

1.  Generate the desired section as its own separate song using a unique prompt.
2.  Use an audio editor to extract that section and splice it into your main track.
3.  Upload the spliced track back into Suno and run it through the **Cover** tool with the following settings to smooth out the transitions:
    - **Weirdness:** 0
    - **Style Influence:** 100
    - **Audio Influence:** 100

---

## 11. Lyric-Writing Essentials

- **Metaphor Discipline:** Focus on one central metaphor and explore it deeply (e.g., exploring water from different angles—gentle rain, deep ocean, reflection). Switching between water, fire, and flying across different verses gives the listener no conceptual anchor.
- **Syllable Counts:** Keep lines between 6 to 10 syllables for standard tempos. Ensure lines in the same structural positions across different verses remain within $\pm$1–2 syllables of each other to avoid rushed or awkward vocal phrasing.
- **Red Flags:** Avoid generic AI adjective stacking (_"neon skies, electric hearts, endless dreams"_), erratic rhyme schemes with no pattern, or lines too wordy to be sung in one natural human breath.

---

## 12. Workflow & Community Observations

- **The Peak Performance Window:** Community observations suggest that generations completed during lower server traffic times—specifically between **3:00 AM and 4:30 AM local time**—frequently exhibit cleaner audio fidelity and better prompt adherence.
- **Thumbs Down vs. Reporting:** Giving a track a "Thumbs Down" only hides it from your view. To flag actual technical failures or glitches, use the **Report** function.
- **Visual Quality Association:** When batch-generating, generations with more visually detailed and aesthetically appealing default thumbnails often correlate with cleaner, higher-quality audio generations.

---

## Quick Debugging Checklist

When a prompt isn't landing:

1.  **Is a strong tag overpowering a weak one?** Reinforce the weak side with specific playing techniques and physical instruments; do not just type the genre name louder.
2.  **Are you reinforcing a gravity well?** Check adjacent fields (including the lyrics box) to ensure you are not repeating strong genre words that pull the track toward pop.
3.  **Is a quality problem sitting in your exclude list?** If the vocals sound strained, move "strain" out of exclusions and specify _"intimate, relaxed vocal delivery"_ in the positive prompt.
4.  **Are commas doing work that should be periods?** Ensure essential instructions are linked with `and` or `with` and closed with a period.
5.  **Is the exclude list bloated?** Consolidate near-duplicates to maximize the weight of your negative prompts.
