# Lessons Learned

Post-mortem notes. The failures taught more than the solves, and the numbers are specific
enough to be worth recording.

## 1. A 2-frame insert defeats sampled scanning — the maths

In [Follow the Roam](writeups/osint/follow-the-roam.md), the payload was on screen for **2
frames out of 75,061** (0.033 s, **0.0027%** of the video).

| Approach | Frames examined | Coverage | P(catching a 2-frame flash) |
|---|---|---|---|
| 1 fps OCR | 1,252 | 1.7% | **3%** |
| 3 fps OCR | 3,756 | 5.0% | **10%** |
| Hint-narrowed, full rate | **450** | 0.6% | **~100%** |

The winning approach examined **fewer frames** than the losing one. Coverage is the wrong
metric; *targeting* is the metric.

**Rule: narrow first, then go exhaustive. Never widen the sample rate and hope.**

A corollary on honesty: after a sampled scan you may only say *"not found in X% of frames"* —
never *"it isn't there."*

## 2. The hint was in plain English and I treated it as a joke

Two authored strings were all that was needed:

- Instagram caption: *"the rest was caught in motion"*
- Video description: *"Damn I keep whiffing my ult"*

Together: look at the ultimate casts. That reduces 1,252 seconds to three 5-second windows.
I read both, classified the description as flavour text, and went off to build computer-vision
pipelines instead.

**Rule: before writing any code, list every authored string — title, description, filename,
caption, comment — and for each write down "what does this tell me to look AT?"** Exhaust that
list first.

## 3. Global metrics cannot detect local events

I built transient detectors on **frame-average** luma difference (`ffmpeg signalstats` YDIF).
A small text overlay moves a whole-frame average by almost nothing, so it never crossed
threshold — it was flat at the exact moment the flag appeared.

Block-wise local differencing is the right shape of detector, but in a VFX-heavy game it still
produced ~500 candidates per minute (damage numbers, spell effects). **Detectors rank; they do
not decide.** They are worthless without the narrowing from §2.

## 4. OCR is not vision

This is the big one. At the correct timestamp, at 1080p, full-resolution `tesseract` read
`Recall`, `Regen`, `Flicker`, `SHUT DOWN` and player names flawlessly — and **never** read the
flag. Cropped tightly and upscaled 3× across four PSM modes, the best output was `PRU toy` and
`RAG 1 tO}`. The text was thin white glyphs over a bright, busy background.

It was found by **montaging the window into contact sheets and looking at them.**

Any media-forensics pipeline needs a path for a human (or model) to actually view frames. If
your only reader is OCR, stylised text over busy backgrounds is invisible to you.

## 5. Tooling gap: no way to see

For most of this event the Kali VM had **no file bridge to the host**, and the sandbox blocked
serving files over HTTP. Viewing an image meant base64-chunking it through command output —
slow, token-expensive, and error-prone.

That single gap cost two challenges:
- **Whack-a-Mole** — a purely visual task reduced to reasoning over numeric heatmaps.
- **Follow the Roam** — frames could not be eyeballed, so OCR was the only reader.

**Fix:** a VMware Shared Folder (`open-vm-tools` + `vmhgfs-fuse`) mapping a host directory to
`/mnt/hgfs/ctfshare`, with an `/etc/fstab` entry so it survives reboot. Zero network impact —
it uses the hypervisor's host-guest channel, not the NIC. After enabling it, the same frame
that defeated every OCR pass was legible instantly.

## 6. Smaller things worth keeping

- **`tesseract <listfile> <out>`** processes a file list in one process — roughly 10× faster
  than spawning tesseract per frame. Essential above ~100 frames.
- **Pull 1080p, not 720p.** Lower bitrate smears small text; the challenge may be unreadable at
  720p and readable at 1080p.
- **Two clocks.** An in-game timer is not video position (here the offset was ~70 s). Calibrate
  before trusting a quoted timestamp.
- **Sampling can straddle the event you're indexing.** The ult fired at 618.1; the 1 fps sample
  at 618.0 showed the button idle. Always widen to ±5 s around a candidate.
- **Check team solves first.** On a team CTF, two challenges were re-solved from scratch that
  teammates had already finished. One API call would have prevented it.
- **CTFd free verification.** Re-submitting to an already-solved challenge returns *"Correct
  but you already solved this"* vs *"Incorrect…"* — a zero-cost oracle for validating an
  intermediate value (used to confirm `LAYLAROAMS`) or an ambiguous flag prefix.
- **Verify both plausible prefixes.** `CYBLITZ2026{…}` was correct and `CYBLTZ2026{…}` rejected
  for exactly one challenge in the event.
- **Linear algebra beats brute force.** In fraude-code, 25 × 2³² of brute force became 25
  instant GF(2) matrix solves once the scramble was recognised as linear.
- **When you know the output format, optimise the input for it.** In ragebait, hill-climbing a
  trigger against `CE(model → "CYBLTZ2026{")` found a 2-word trigger in ~2,300 forward passes;
  generate-and-check would never have found it.
