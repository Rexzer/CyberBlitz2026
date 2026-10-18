#!/usr/bin/env python3
"""Render keyboard-walk strings as ASCII so the letter they draw can be read.

CYBERBLITZ 2026 "Roam Logs": each EXIF UserComment held a key sequence that
traces a letter on a QWERTY keyboard. Extract them with:

    exiftool -UserComment -s -S img*.jpg

Usage: python3 keyroute.py QAZXC ZSEDCSD ...      (defaults to the Roam Logs set)
"""
import sys

ROWS = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
POS = {ch: (r, c) for r, row in enumerate(ROWS) for c, ch in enumerate(row)}

ROAM_LOGS = [
    ("01", "QAZXC"), ("02", "ZSEDCSD"), ("03", "RGYGB"), ("04", "TGBNM"),
    ("05", "CFTGBFG"), ("06", "VFRTYHGFB"), ("07", "WSXCVFRE"),
    ("08", "BHUJMHJ"), ("09", "XDRFTGB"), ("10", "YTRFGHNBV"),
]


def render(seq, label=""):
    marks = {POS[ch] for ch in seq.upper() if ch in POS}
    print(f"=== {label} {seq} ===")
    for r, row in enumerate(ROWS):
        line = " ".join("#" if (r, c) in marks else "." for c in range(len(row)))
        print(" " * r + " " + line)
    order = " -> ".join(ch for ch in seq.upper() if ch in POS)
    print(f"   order: {order}\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        for i, seq in enumerate(args, 1):
            render(seq, f"Log {i:02d} :")
    else:
        for num, seq in ROAM_LOGS:
            render(seq, f"Log {num} :")
        print("Reading the letters in log order spells the answer.")
