#!/usr/bin/env python3
"""CYBERBLITZ 2026 "fraude-code" — unwrap 3 nested ELFs and invert 25 GF(2) scrambles.

  layer 1  dropper : XOR-decodes .rsrc -> "subagent" ELF (memfd_create + execl)
  layer 2  subagent: needs argv[1] of exactly 100 chars; splits it into 25 x 4-char
                     chunks and hands each to an embedded "subsubagent_N"
  layer 3  each    : x = u32le(chunk); xorshift scramble; compare to a constant

The scramble is linear over GF(2) (only ^ and shifts), so each chunk is recovered
by solving M*x = target with a 32x32 bit-matrix instead of brute force.

Usage: python3 fraude_solve.py            (expects ./fraude in cwd)
"""
import os
import struct
import subprocess
import sys

from pwn import ELF

KEY = b"FraudeCodeChudGPTv6.7_AgentKey!!"
RSRC_START, RSRC_END = 0x42B0, 0x69300      # .rsrc .. next section
SUBSUB_START, SUBSUB_END, N_SUB = 0x402010, 0x463450, 25
MASK = 0xFFFFFFFF

# cmp eax, <imm> from each subsubagent (objdump)
TARGETS = [
    0xBE47D89F, 0xF798986A, 0xF1E86178, 0xBA9027FF, 0x3E049143,
    0xC58A9898, 0x66BC9CBF, 0x4105C2D1, 0xFF96ABFE, 0x99C7A826,
    0x3D74CB8F, 0xD24B120E, 0x10D4C1F8, 0x886CC758, 0x59050329,
    0x1207D1A0, 0x2E31733F, 0x136263DC, 0x7A2445AE, 0x1F376FF5,
    0xAFFEFC1F, 0x63021FAA, 0x9233A901, 0xFD3BA97A, 0x7C464E45,
]


def unwrap(path="fraude"):
    """layer 1 -> subagent.bin ; layer 2 -> ss/ss00..ss24.bin"""
    elf = ELF(path, checksec=False)
    blob = elf.read(RSRC_START, RSRC_END - RSRC_START)
    sub = bytes(blob[i] ^ ((KEY[i % 32] + i) & 0xFF) for i in range(len(blob)))
    assert sub[:4] == b"\x7fELF", "layer-1 decode failed"
    open("subagent.bin", "wb").write(sub)

    sa = ELF("subagent.bin", checksec=False)
    size = (SUBSUB_END - SUBSUB_START) // N_SUB
    data = sa.read(SUBSUB_START, size * N_SUB)
    os.makedirs("ss", exist_ok=True)
    for i in range(N_SUB):
        p = f"ss/ss{i:02d}.bin"
        open(p, "wb").write(data[i * size:(i + 1) * size])
        os.chmod(p, 0o755)
    print(f"unwrapped: subagent.bin + {N_SUB} subsubagents")


def T(x):
    """forward scramble, identical in all 25 subsubagents"""
    for c in range(13, 1, -1):
        x = (x ^ (x >> c)) & MASK
    for c in range(25, 1, -1):
        x = (x ^ (x << c)) & MASK
    for c in range(7, 1, -1):
        x = (x ^ (x >> c)) & MASK
    return x


def solve_gf2(target):
    """invert T by Gaussian elimination over GF(2)"""
    cols = [T(1 << i) for i in range(32)]
    rows = [[sum(((cols[i] >> b) & 1) << i for i in range(32)), (target >> b) & 1]
            for b in range(32)]
    piv, r = [-1] * 32, 0
    for col in range(32):
        sel = next((rr for rr in range(r, 32) if (rows[rr][0] >> col) & 1), None)
        if sel is None:
            continue
        rows[r], rows[sel] = rows[sel], rows[r]
        for rr in range(32):
            if rr != r and ((rows[rr][0] >> col) & 1):
                rows[rr][0] ^= rows[r][0]
                rows[rr][1] ^= rows[r][1]
        piv[col] = r
        r += 1
    return sum(1 << col for col in range(32) if piv[col] != -1 and rows[piv[col]][1])


def main():
    if not os.path.exists("ss/ss00.bin"):
        unwrap(sys.argv[1] if len(sys.argv) > 1 else "fraude")

    flag = b""
    for i, target in enumerate(TARGETS):
        x = solve_gf2(target)
        assert T(x) == target, f"inversion failed for chunk {i}"
        chunk = struct.pack("<I", x)
        rc = subprocess.run([f"./ss/ss{i:02d}.bin", chunk],
                            capture_output=True).returncode
        print(f"ss{i:02d} {target:#010x} -> {chunk!r}  verify_rc={rc}")
        flag += chunk

    print(f"\nFLAG ({len(flag)} chars): {flag.decode()}")


if __name__ == "__main__":
    main()
