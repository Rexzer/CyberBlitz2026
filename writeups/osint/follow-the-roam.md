# Follow the Roam — OSINT (419 pts, 16 solves)

> A roamer never stays in one place for long. The value recovered in Roam Logs is not the end
> of the trail, it is your lead. Search for where that name appears online and follow the traces
> it leaves behind. **Two fragments** of the final flag are hidden across different forms of
> media. **One was captured in a moment. The other was caught in motion.**

**Flag:** `CYBLITZ2026{T1GrE4l_P4qU1t0}`

> ⚠️ **Prefix warning.** This flag uses **`CYBLITZ`** (extra `I`), unlike every other flag in
> the event. `CYBLTZ2026{T1GrE4l_P4qU1t0}` is **rejected**. What looks like a typo in the
> challenge text is the accepted answer — verified by submitting both.

**Credit:** team effort. A teammate found fragment 1 and worked out that the payload sits at an
ultimate cast; I traced the OSINT chain, rebuilt the cooldown index, and located the exact
2-frame insert. The honest failure analysis is in [LESSONS.md](../../LESSONS.md).

## 1. The lead

[Roam Logs](../forensics/roam-logs.md) yields `LAYLAROAMS`. "Search for where that name appears
online" — but search engines return **nothing** for a persona created days before the event.
A null search result does not mean the account doesn't exist; probe platforms directly.

```
youtube.com/@laylaroams    200  "LaylaRoams - YouTube"     ✓
instagram.com/laylaroams   200  13 posts                   ✓
x / tiktok / twitch / kick / rumble / medium / tumblr      ✗
```

`sherlock` reported 9 platforms; **only 2 were real**. Everything else (CGTrader, Rajce,
BabyRu, TikTok, Twitch…) was a false positive. Verify each hit properly — e.g. Twitch's GraphQL
`user(login:...)` returns `null`, TikTok's mobile page says "Couldn't find this account".

The YouTube channel's About links to `instagram.com/laylaroams`, confirming both belong to the
same persona. Channel banner: *"LAYLAROAMS — MATCH ARCHIVE // ROAM LOGS"*.

## 2. Fragment 1 — "captured in a moment" (Instagram)

13 posts titled **Match Archive #01–#13**, each a Mobile Legends skin screenshot with a
narrative caption about a corrupted match archive. Post **#07** is the payload:

> Something strange turned up while recovering this one.
> Most of the match record was intact, but a small piece of information appeared between the
> damaged sections…
> **Recovered Fragment 1/2:**
> **`CYBLITZ2026{T1GrE4l_`**
> Looks like only half of it survived. The remaining data could not be recovered from the image
> itself. **A picture can only tell half the story. The rest was caught in motion.**

`T1GrE4l` = **Tigreal**, a Mobile Legends tank/roamer. The other captions are flavour, but they
consistently push you to video — #09 *"a single frame does not tell you very much"*, #10
*"things make more sense when you can watch what happened before and after"*, #12 *"images
preserve moments… movement is one of them [they were never meant to preserve]"*.

## 3. Fragment 2 — "caught in motion" (YouTube)

Three gameplay videos, no shorts/playlists/community posts, two unrelated comments:

| id | title | description | len |
|---|---|---|---|
| `Zp1bE9KRSqc` | Layla gameplay but the audio is just me weeping in a dark room | "nothing to see here, just me forgetting the audio" | 841s |
| `2QlgH98RMys` | **Layla but I can't aim** | **"Damn I keep whiffing my ult"** | 1252s |
| `LDxBaUtOoIM` | minotaur but constantly being carried | "nothing to see here, just me being bad at minotaur" | 904s |

**This is the crux of the challenge, and it is a reading-comprehension problem, not a technical
one.** Combine the two authored hints:

- caption: *"the rest was caught in motion"*
- description: *"Damn I keep **whiffing my ult**"*

→ **look at the moments Layla casts her ultimate**, in `2QlgH98RMys`.

That turns 1,252 seconds into three short windows. Without it you are scanning 75,061 frames
for something that exists in two of them.

### Indexing the ult casts from the HUD

Layla's ultimate is the **top button** of the skill arc (centre ≈ `(1630, 617)` at 1920×1080) —
identifiable because it shows the longest cooldown. Crop just the cooldown digits once per
second and OCR with a digit whitelist:

```bash
ffmpeg -i hd_2QlgH98RMys.mp4 \
  -vf "fps=1,crop=104:84:1578:575,scale=iw*4:ih*4,format=gray,eq=contrast=1.6" u_%05d.png
ls u_*.png > l.txt
tesseract l.txt out --psm 7 -c tessedit_char_whitelist=0123456789
```

A cast = the cooldown appearing / jumping up. This surfaced a cast at **t≈282s (4:41)** with the
countdown `37,36,34,33,32,31,30,27…`.

Caveat worth recording: at `t=618.000` the button read **empty** and at `618.17` it read **27** —
the ult fired at ≈`618.1`, *between* two 1 fps samples. Sampling can straddle the very event
you're indexing; widen to ±5s around any candidate rather than trusting the exact second.

### Finding the insert

The payload is **white text visible for exactly 2 frames** — `t = 618.100` and `618.117`
(1/30 s at 60 fps), lower-right of the screen over the attack button, during the 3rd ult cast.

**OCR never read it.** Full-resolution OCR of every frame in the window read `Recall`, `Regen`,
`Flicker`, `SHUT DOWN` and player names perfectly, but never the flag — thin white glyphs over
a bright, busy VFX background. Even tightly cropped and upscaled 3× across four PSM modes the
best output was `PRU toy` / `RAG 1 tO}`.

What worked was **looking**:

```bash
ffmpeg -ss 617.0 -t 3.0 -i hd_2QlgH98RMys.mp4 -vf "fps=60,scale=480:-1" l_%04d.png
ls l_*.png | split -l 30 - chunk_
for c in chunk_*; do montage $(cat $c) -tile 6x5 -geometry +3+3 -label '%f' sheet.png; done
```

180 frames across 6 contact sheets; the text is plainly legible in sheet 3, row 2, tiles 1–2.
Re-extracting those two frames and cropping `crop=470:140:1440:790` gives a clean read:

```
P4qU1t0}
```

`P4qU1t0` = **Paquito**, another Mobile Legends hero — pairing with Tigreal from fragment 1.

## 4. Assemble

```
CYBLITZ2026{T1GrE4l_  +  P4qU1t0}   =   CYBLITZ2026{T1GrE4l_P4qU1t0}
```

## Takeaways

1. **The authored text is the solution.** Both hints needed were written in plain English in the
   caption and the video description. The description reads like a throwaway joke; it is the key.
2. **Narrow, then go exhaustive.** 450 well-chosen frames beat 16,000 badly-chosen ones.
3. **OCR is not vision.** A pipeline that cannot fall back to a human (or model) *looking* at
   frames will miss stylised text over busy backgrounds.
4. **Pull 1080p, not 720p** — the lower bitrate smears small text further.
5. **Verify both plausible flag prefixes** before concluding a correct answer is wrong.
