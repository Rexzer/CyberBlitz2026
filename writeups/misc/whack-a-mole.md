# Whack-a-Mole — Misc (482 pts, 9 solves) — **NOT SOLVED**

> Think you've got sharp eyes, or are you as blind as a mole?
> `http://45.77.247.35:22001`

Not solved. Publishing the protocol reversing and the scoring constraint, because the shape of
the challenge is the interesting part.

## What it is

A web game. From the intro screen:

> Something has been erased from each photo using an **AI eraser**. Your job is to figure out
> where it used to be. Most photos are divided into a grid… Choose the square that contains most
> of the edited area. Some photos may not have been edited at all.

So: **inpainting localisation**, 12 rounds.

## Protocol

`app.js` is unminified. Two endpoints:

```
GET  api/puzzles   -> { puzzles: [ {src, cols, rows, picks, mode?} ] }
POST api/submit    -> { picks: [[...], ...] }  ->  { score, total, pass, flag }
```

```json
[{"src":"img/97e6d562f2bc.jpg","cols":3,"rows":4,"picks":1},
 {"src":"img/62d9c65d5db3.jpg","cols":6,"rows":5,"picks":2},
 {"src":"img/c085484fe190.jpg","mode":"point","picks":1},
 ... 12 total]
```

- **grid mode** — answer is a cell index, row-major (`i = row*cols + col`)
- **point mode** — answer is normalised `[x, y]` click coordinates
- **"nothing erased"** — submit an empty list for that puzzle
- `picks` is how many cells/points that puzzle wants (1 or 2)

Images are plain static files, trivially scraped:

```bash
curl -s http://45.77.247.35:22001/api/puzzles | jq -r '.puzzles[].src' \
  | xargs -I{} curl -s -O http://45.77.247.35:22001/{}
```

## The constraint that makes it hard

Probing submit with all-empty picks reveals the grading:

```json
{"total": 12, "pass": 10}
```

**10 of 12 required, and a failing run returns no score** — only `total` and `pass`. There is no
per-round feedback and no partial signal, so you cannot iterate: it's one blind shot at ≥83%
accuracy on a perceptual task. Unlimited attempts are useless without a gradient.

## What I tried

Downloaded all 12 and built three detectors:

1. **ELA** (resave at q90, amplify the difference). Useless here — single-compression images,
   so the edited region doesn't stand out. Only legitimately high-detail objects (a price card)
   lit up.
2. **Local texture / high-frequency energy** (|g − 3×3 mean|, then local std). This is the one
   that works in principle: AI-inpainted regions are smoother than real photo texture. It
   clearly revealed an oval smooth blob in puzzle 4 (bougainvillea foliage) that is almost
   certainly the erase. But on flat scenes (sky, concrete, walls) natural smoothness dominates
   and the signal is swamped.
3. **Per-cell anomaly ranking** (median-absolute-deviation over brightness/std/saturation).
   Mostly surfaced naturally-dark or naturally-flat cells — false positives.

Confident reads: puzzle 0 (cell 1 — a smudge on the table with nothing casting it) and
puzzle 4 (cell 1). That's 2 of 12, well short of 10.

## Why I didn't get further

The honest answer is I could not **see** the images. The Kali VM had no file bridge to the host
at the time, and the sandbox blocked serving them over HTTP, so I was reduced to reasoning over
numeric heatmaps instead of looking at photographs — on a task that is fundamentally visual.
Building the forensics was the easy part; the missing capability was eyes.

That gap is now fixed (VMware shared folder → host-readable path), which would make a retry
materially different. See [LESSONS.md](../../LESSONS.md).

## If retrying

- Look at all 12 at full resolution first; human/model perception beats these detectors on
  inpainting artefacts.
- Use the texture map as a *second opinion*, not the primary signal.
- Watch for the logical tells rather than pixel statistics: a shadow with no object, a hand
  holding nothing, an interrupted railing, repeated texture.
- Remember some puzzles are genuinely unedited — "nothing erased" is a valid answer and you
  only need 10/12, so don't force a pick on a clean image.
