# Eight Registers, No Compiler — Reverse (500 pts)

> A compiler vanished, leaving an eight-register interpreter and a courier program.
> Handout: `hello.vm`, `math.vm`, `courier.vm`.
> `hello.vm` output: `HI` — `math.vm` final registers: `r0=250 r1=11 r2=5 r3=14`

**Flag:** `CYBLTZ2026{31gh7_r3G5_0n3_v01c3}`

The neat part of this challenge is that **no interpreter was supplied** — only two worked
examples. The whole task is deducing the ISA from input/output pairs.

## Format

```
$ xxd hello.vm
00000000: 4556 4d43 1700 4800 8a00 0000 1700 4900  EVMC..H.......I.
00000010: 8a00 0000 ff00 0000                      ........
```

4-byte magic `EVMC`, then fixed-width **4-byte instructions**. That alone makes `hello.vm`
five instructions long, which has to produce two characters and a halt.

## Deducing the opcodes

**From `hello.vm` → `HI`:**

```
17 00 48 00     0x48 = 'H'  →  17 R V = set reg[R] = V
8a 00 00 00                 →  8a R   = print reg[R] as a char
17 00 49 00     0x49 = 'I'
8a 00 00 00
ff 00 00 00                 →  ff     = halt
```

**From `math.vm` → `r0=250 r1=11 r2=5 r3=14`:**

```
17 00 fa 00     r0 = 250
17 01 0b 00     r1 = 11
39 02 00 01     r2 = f(r0, r1) = 5
52 03 02 01     r3 = g(r2, r1) = 14
ff 00 00 00
```

`r3 = 14` from `(5, 11)` is the giveaway: `5 ^ 11 = 14`, so **`0x52` is XOR**.

Then `r2 = 5` from `(250, 11)`. Not AND (10), OR (251), subtraction (239) or XOR (241) — but
`250 + 11 = 261 = 0x105`, and truncated to a byte that is **`0x05`**. So **`0x39` is ADD mod 256**.

| opcode | form | meaning |
|---|---|---|
| `0x17` | `17 R V 00` | `reg[R] = V` |
| `0x39` | `39 D A B` | `reg[D] = (reg[A] + reg[B]) & 0xff` |
| `0x52` | `52 D A B` | `reg[D] = reg[A] ^ reg[B]` |
| `0x8a` | `8a R 00 00` | `putchar(reg[R])` |
| `0xff` | `ff 00 00 00` | halt |

`courier.vm` uses only these five, which is a good sign the ISA is complete. Each output
character is built as `load, load, add, load, xor, print` — a trivial obfuscation so the flag
bytes never appear literally in the file.

## Interpreter

```python
def run(fn):
    d = open(fn, 'rb').read()
    assert d[:4] == b'EVMC'
    pc, reg, out = 4, [0]*8, bytearray()
    while pc + 4 <= len(d):
        op, a, b, c = d[pc:pc+4]; pc += 4
        if   op == 0x17: reg[a] = b
        elif op == 0x39: reg[a] = (reg[b] + reg[c]) & 0xff
        elif op == 0x52: reg[a] = reg[b] ^ reg[c]
        elif op == 0x8a: out.append(reg[a] & 0xff)
        elif op == 0xff: break
    return bytes(out)
```

Validate against the known sample before trusting it:

```
hello.vm   -> b'HI'                                        ✓ matches the brief
courier.vm -> b'CYBLTZ2026{31gh7_r3G5_0n3_v01c3}'
```

Full script: [`tools/evmc.py`](../../tools/evmc.py)
