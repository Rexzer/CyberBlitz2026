#!/usr/bin/env python3
"""Find brief on-screen inserts in video (1-3 frames) and make them viewable.

Built after CYBERBLITZ 2026 "Follow the Roam", where the payload existed for 2
frames out of 75,061 and OCR could not read it at any resolution.

Two things this encodes:
  * detect  -- a LOCAL block transient (differs from both neighbours while the
               neighbours agree). Frame-average metrics cannot see a small overlay.
  * look    -- contact sheets, because OCR is not vision. Stylised text over a
               busy background is legible to an eye and invisible to tesseract.

Detectors RANK, they do not decide: in action footage, VFX and damage numbers
will outrank the real insert. Narrow the window from the challenge's own hints
first, then run this.

Usage:
    python3 vidflash.py detect video.mp4 613 11          # scan 613s for 11s
    python3 vidflash.py sheets video.mp4 617 3 /out/dir  # contact sheets to look at
"""
import os
import subprocess
import sys

import cv2
import numpy as np


def detect(video, start, dur, block=48, agree=25.0, top=15):
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)
    frames, times = [], []
    while len(frames) < int(dur * fps) + 2:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        h, w = g.shape
        gh, gw = h // block, w // block
        frames.append(g[:gh * block, :gw * block]
                      .reshape(gh, block, gw, block).mean(axis=(1, 3)))
        times.append(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0)
    cap.release()
    print(f"frames={len(frames)} fps={fps:.2f}")

    out = []
    # single-frame and 2-frame inserts: pair (b,c) alike, both unlike a and d
    for i in range(1, len(frames) - 2):
        a, b, c, d = frames[i - 1], frames[i], frames[i + 1], frames[i + 2]
        single = np.minimum(np.abs(b - a), np.abs(b - c)) - np.abs(c - a)
        pair = np.where((np.abs(b - c) < agree) & (np.abs(d - a) < agree),
                        np.minimum(np.abs(b - a), np.abs(c - d)), 0.0)
        out.append((float(max(single.max(), pair.max())), times[i], i))
    out.sort(reverse=True)
    print("score    t(s)       idx")
    for s, t, i in out[:top]:
        print(f"{s:7.2f}  {t:9.3f}  {i}")
    return out


def sheets(video, start, dur, outdir, fps=60, tile=480, per=30):
    """Extract every frame in the window and montage into readable sheets."""
    os.makedirs(outdir, exist_ok=True)
    tmp = os.path.join(outdir, "_frames")
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur),
                    "-i", video, "-vf", f"fps={fps},scale={tile}:-1",
                    os.path.join(tmp, "f_%05d.png")], check=True)
    files = sorted(os.listdir(tmp))
    print(f"{len(files)} frames -> sheets of {per}")
    for n, i in enumerate(range(0, len(files), per), 1):
        chunk = [os.path.join(tmp, f) for f in files[i:i + per]]
        sheet = os.path.join(outdir, f"sheet_{n}.png")
        subprocess.run(["montage", *chunk, "-tile", "6x", "-geometry", "+3+3",
                        "-background", "black", "-label", "%f", sheet], check=True)
        t0 = start + i / fps
        print(f"  {sheet}  (t={t0:.2f}s)")
    print("\nNow LOOK at the sheets. Keep tiles >= 320px or text will not be legible.")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    mode, video, start, dur = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
    if mode == "detect":
        detect(video, start, dur)
    elif mode == "sheets":
        sheets(video, start, dur, sys.argv[5] if len(sys.argv) > 5 else "sheets")
    else:
        print(__doc__)
