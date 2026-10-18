# CYBERBLITZ 2026 — CTF Writeups

Writeups for challenges from **CYBERBLITZ 2026** (`ctf.cyberh4ts.com`), a Mobile-Legends-themed
CTF. Flag format is `CYBLTZ2026{...}` — with one documented exception noted below.

Published after the event ended.

## Solved

| # | Challenge | Category | Flag |
|---|---|---|---|
| 9 | [Roam Logs](writeups/forensics/roam-logs.md) | Forensics | `CYBLTZ2026{LAYLAROAMS}` |
| 13 | [ragebait](writeups/misc/ragebait.md) | Misc | `CYBLTZ2026{n0t_go04_3nou6h_m4t3}` |
| 22 | [Prims](writeups/pwn/prims.md) | Pwn | `CYBLTZ2026{c10aafab...4b768d}` |
| 24 | [Eight Registers, No Compiler](writeups/rev/eight-registers.md) | Reverse | `CYBLTZ2026{31gh7_r3G5_0n3_v01c3}` |
| 25 | [fraude-code](writeups/rev/fraude-code.md) | Reverse | `CYBLTZ2026{please_bro_just_ten_more_subagents___...}` |
| 26 | [Infinite GPA Hack](writeups/rev/infinite-gpa-hack.md) | Reverse | `CYBLTZ2026{inf1n1t3_gp4_gl1tch}` |
| 41 | [Follow the Roam](writeups/osint/follow-the-roam.md) | OSINT | `CYBLITZ2026{T1GrE4l_P4qU1t0}` ⚠️ |

⚠️ **Follow the Roam uses the `CYBLITZ` prefix** (extra `I`), unlike every other flag in the
event. `CYBLTZ2026{T1GrE4l_P4qU1t0}` is rejected by the scoreboard. This looked like an author
typo in the challenge text but is in fact the accepted flag.

## Not solved (analysis notes published anyway)

| # | Challenge | Category | How far it got |
|---|---|---|---|
| 23 | [ROP2Impress](writeups/pwn/rop2impress.md) | Pwn | Full exploitation path derived, not weaponised |
| 17 | [Whack-a-Mole](writeups/misc/whack-a-mole.md) | Misc | Protocol + forensic tooling built, detection unreliable |
| 48 | Heap Karaoke 2AM | Pwn | Released late; not attempted |

These are included because the dead ends are often more instructive than the wins — see
especially the [lessons learned](LESSONS.md) writeup on how a 2-frame video insert defeated
~16,000 frames of OCR.

## Repository layout

```
writeups/
  forensics/   roam-logs.md
  misc/        ragebait.md  whack-a-mole.md
  osint/       follow-the-roam.md
  pwn/         prims.md  rop2impress.md
  rev/         eight-registers.md  fraude-code.md  infinite-gpa-hack.md
tools/         reusable scripts produced while solving
LESSONS.md     post-mortem: what worked, what didn't, and why
```

## Attribution

This was a team event and several challenges were solved in parallel by teammates. To be
straight about provenance:

- **First solves by me:** Prims (#22), Eight Registers (#24).
- **Independently derived, teammate also solved:** fraude-code (#25), ragebait (#13),
  Roam Logs (#9) — the Roam Logs decode was re-derived from scratch because its output is the
  input to Follow the Roam.
- **Collaborative:** Follow the Roam (#41). A teammate found fragment 1 and identified that the
  payload sits at an ultimate cast; I traced the OSINT chain and located the exact 2-frame
  insert. Credited in detail in that writeup.

Tooling: Kali VM driven through the HexStrike MCP toolkit, plus `pwntools`, `ffmpeg`,
`tesseract`, `OpenCV`, and `transformers`/`peft` for the LoRA challenge.
