#!/usr/bin/env python3
"""EVMC interpreter — CYBERBLITZ 2026 "Eight Registers, No Compiler".

ISA deduced from the two supplied samples (no interpreter was provided):
    0x17 R V .   reg[R] = V
    0x39 D A B   reg[D] = (reg[A] + reg[B]) & 0xff
    0x52 D A B   reg[D] = reg[A] ^ reg[B]
    0x8a R . .   putchar(reg[R])
    0xff . . .   halt

Usage: python3 evmc.py courier.vm [hello.vm ...]
"""
import sys


def run(path):
    data = open(path, "rb").read()
    if data[:4] != b"EVMC":
        raise ValueError(f"{path}: bad magic {data[:4]!r}")
    pc, reg, out = 4, [0] * 8, bytearray()
    while pc + 4 <= len(data):
        op, a, b, c = data[pc], data[pc + 1], data[pc + 2], data[pc + 3]
        pc += 4
        if op == 0x17:
            reg[a] = b
        elif op == 0x39:
            reg[a] = (reg[b] + reg[c]) & 0xFF
        elif op == 0x52:
            reg[a] = reg[b] ^ reg[c]
        elif op == 0x8A:
            out.append(reg[a] & 0xFF)
        elif op == 0xFF:
            break
        else:
            out += b"[?op%02x]" % op
    return bytes(out), reg


if __name__ == "__main__":
    for path in sys.argv[1:] or ["hello.vm", "math.vm", "courier.vm"]:
        try:
            out, reg = run(path)
        except (OSError, ValueError) as exc:
            print(f"{path}: {exc}")
            continue
        print(f"{path:<14} -> {out!r}")
        print(f"{'':<14}    regs: " + " ".join(f"r{i}={v}" for i, v in enumerate(reg[:4])))
