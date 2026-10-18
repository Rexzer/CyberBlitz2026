# Roam Logs — Forensics (500 pts)

> Ten images were recovered from somewhere in the Land of Dawn… a roamer always leaves a trail
> behind. Look beyond what can be seen and recover the hidden logs. The contents may not make
> much sense at first, but remember: **every route leaves a mark.** Follow each route carefully.
> Flag format: `CYBLTZ2026{WORD}`, uppercase, no spaces.

**Flag:** `CYBLTZ2026{LAYLAROAMS}`

This one matters beyond its own points — its answer is the entry point for
[Follow the Roam](../osint/follow-the-roam.md).

## The hidden logs

Ten visually identical 1280×591 JPEGs. "Look beyond what can be seen" is a metadata hint, and
`exiftool` pays out immediately — each file carries an EXIF **UserComment**:

```
img1 : Roam Log 01/10 // QAZXC     // Every route leaves a mark.
img2 : Log 02/10     // ZSEDCSD    // The order was not chosen by accident.
img3 : Log 03/10     // RGYGB      // Follow where the movement leads.
img4 : Log 04/10     // TGBNM      // The turns matter as much as the destination.
img5 : Log 05/10     // CFTGBFG    // A strange path can still have a familiar shape.
img6 : Log 06/10     // VFRTYHGFB  // Start from the beginning. Do not skip the bends.
img7 : Log 07/10     // WSXCVFRE   // Some patterns are easier seen than read.
img8 : Log 08/10     // BHUJMHJ    // What matters is what the route leaves behind.
img9 : Log 09/10     // XDRFTGB    // Nine routes. One destination.
img10: Log 10/10     // YTRFGHNBV  // Every journey has one final turn.
```

```bash
exiftool -UserComment -s -S img*.jpg
```

## Reading the routes

The strings aren't ciphertext — they're **paths traced on a QWERTY keyboard**. The hints say so
fairly loudly: *"every route leaves a mark"*, *"the turns matter"*, *"some patterns are easier
seen than read"*. Plot the keys and each log draws a **letter**.

Take log 01, `QAZXC`:

```
Q . . . . . . . . .        Q
 A . . . . . . . .    →    A
  Z X C . . . .            Z X C
```

Straight down the left column, then right along the bottom — an **L**.

Rendering all ten (one `#` per key, keyboard rows indented):

| # | Route | Shape | Letter |
|---|---|---|---|
| 01 | `QAZXC` | vertical stem, then bottom bar | **L** |
| 02 | `ZSEDCSD` | diagonal up, stem down, `S`→`D` crossbar | **A** |
| 03 | `RGYGB` | two diagonals meeting at `G`, stem to `B` | **Y** |
| 04 | `TGBNM` | vertical stem, then bottom bar | **L** |
| 05 | `CFTGBFG` | diagonal, stem, crossbar | **A** |
| 06 | `VFRTYHGFB` | left stem, top bar, middle bar, leg | **R** |
| 07 | `WSXCVFRE` | closed loop (`W→S→X→C→V→F→R→E`) | **O** |
| 08 | `BHUJMHJ` | diagonal, stem, crossbar | **A** |
| 09 | `XDRFTGB` | peak → valley → peak | **M** |
| 10 | `YTRFGHNBV` | top bar, down, middle bar, down, bottom bar | **S** |

Reading in log order: **L A Y L A R O A M S** → `LAYLAROAMS`.

The repeated `A`s at positions 2, 5 and 8 are a useful self-check — three different routes
(`ZSEDCSD`, `CFTGBFG`, `BHUJMHJ`) all draw the same diagonal-stem-crossbar shape in different
regions of the keyboard. If they didn't agree, the reading would be wrong.

## Script

[`tools/keyroute.py`](../../tools/keyroute.py) renders each route as ASCII so the letters can be
read directly rather than guessed:

```
=== Log 01 : QAZXC ===
 # . . . . . . . . .
  # . . . . . . . .
   # # # . . . .
```

## Verification

`LAYLAROAMS` reads naturally as "Layla roams", which fits the roamer theme — and it is a
plausible social handle, which is exactly what the follow-up challenge needs.

Submitting `CYBLTZ2026{LAYLAROAMS}` confirms it. (On CTFd, re-submitting to an already-solved
challenge returns *"Correct but you already solved this"* vs *"Incorrect…"* — a free way to
validate an intermediate value that feeds another challenge, with no scoring side effects.)
