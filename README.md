# Motion Crackers — launch video

A 20-second launch film for **Motion Crackers**, a curated gallery of AI-generated motion designs ("crackers") and the prompts that made them.

- `motion-crackers-launch.mp4`: final cut. 2560×1440 (2K), 60 fps, H.264, AAC 320 kb/s at 48 kHz.
- `video/`: the HyperFrames composition (`index.html`) plus fonts, vendored GSAP and the rendered score.
- `tools/score.py`: sequences, mixes and masters the score from recorded instrument samples.
- `tools/snap.mjs`: grabs still frames from the composition at given times, for review.

## Story (120 BPM, one bar = 2 s)

| Time | Picture | Sound |
|---|---|---|
| 0 – 2 s | A black dot morphs on each beat: circle, squircle, triangle, flower. Then it flies up and lands as the dot of the "i". | Log drums answer each shape. A muted-guitar pickup leads in. |
| 2 – 4 s | **Motion designs** grows out from the "i". | The groove starts: kick, snare, hats, bass, an Am9 guitar stab. |
| 4 – 6 s | **made by AI.** The letters "AI" glitch on 16th notes, then the full stop pops in. | Cross-sticks and muted guitar follow the glitch. A tom fill leads into the next bar. |
| 6 – 10 s | The full stop grows into a tile. The camera pulls back to show a wall of moving designs. The rows part for **All in one gallery.** | A D9 chord hit, then the groove continues. |
| 10 – 14 s | The camera dives into one tile until it fills the frame. Then one full-screen motion design per beat, each growing out of a dot. | Vibraphone chords over a steady pulse, with one marimba note per cut. |
| 14 – 16 s | The tile shrinks back into the full stop of **Each with its prompt.** | The groove comes back, then stops dead. |
| 16 – 20 s | The dot falls and cracks to become the placeholder mark. **Motion Crackers** glitches in letter by letter and resolves at 17.5 s. | Stuttered chops on every glitch step, then the final Am9 chord rings out. |

## Audio sources
All of the music comes from recorded, freely licensed sample libraries. No loops or pre-made music were used.
- Karoryfer **Swirly Drums**: snare, hi-hats, toms and splash.
- **Virtuosity Drums**: kick, cross-stick and rimshot.
- Karoryfer **Growlybass**: electric bass.
- Karoryfer **Emily Guitar**: clean and muted electric guitar.
- **VCSL**: log drums, shaker, vibraphone (soft mallets) and marimba.

The samples are not stored in this repo. To rebuild the score, clone the `sfzinstruments` repos and `sgossner/VCSL` into one folder, then run:

```
python3 tools/score.py <samples_dir> video/assets/audio/score.wav
```

## Render
```
cd video && npx hyperframes render . -o renders/draft.mp4 --fps 60 -q delivery
```
The delivered file is then remuxed with the 24-bit score encoded as 320 kb/s AAC.

Fonts: Inter Display (SIL OFL), Instrument Serif and JetBrains Mono. Instrument Serif and JetBrains Mono appear only in the glitch frames.
