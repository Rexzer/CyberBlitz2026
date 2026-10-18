# fraude-code — Reverse (500 pts)

> opus 6.7 make no mistakes

**Flag:** `CYBLTZ2026{please_bro_just_ten_more_subagents___please_just_five_million_dollars_more_in_tokens_bro}`

A stripped PIE ELF that presents itself as "Fraude Code v6.7 — an autonomous coding agent, by
ChudGPT". Running it in a pty, you get a prompt, a long fake "Cogitating… / Asking Grok… /
Committing ritual harakiri…" progress bar, and then:

```
! ! !  SAFEGUARD TRIGGERED  ! ! !
Your query violated our safeguards. Please try again later.
```

So some input passes and some doesn't. The challenge is three nested ELFs deep.

## Layer 1 — the dropper

`main` is ncurses chrome. The real logic is `fcn.000023f0`, which:

1. Computes `nbytes = 0x69300 - 0x42b0` — the span from the `.rsrc` section to the next section.
2. Decodes that blob with `fcn.00002379`.
3. `memfd_create("subagent")`, writes the decoded bytes, `fork`, and
   `execl("/proc/self/fd/N", "subagent", <your prompt>, NULL)`.
4. Returns 1 if the child exits 0.

The decoder is a rolling XOR keyed on a string that's sitting in plain sight:

```c
key = "FraudeCodeChudGPTv6.7_AgentKey!!"      // 32 bytes
out[i] = blob[i] ^ ((key[i % 32] + i) & 0xff)
```

Note the `+ i` — the key byte is offset by the index, so it's not a flat repeating XOR.

```python
blob = elf.read(0x42b0, 0x69300 - 0x42b0)
key  = b'FraudeCodeChudGPTv6.7_AgentKey!!'
out  = bytes(blob[i] ^ ((key[i % 32] + i) & 0xff) for i in range(len(blob)))
# -> ELF 64-bit LSB executable, not stripped
```

## Layer 2 — the subagent

Not stripped, so `main` reads easily:

- `argc != 2` → exit 1
- `strlen(argv[1]) != 0x64` → exit 1, so the answer is **exactly 100 characters**
- It then carves `.subsubagent` (`0x402010` … `0x463450`, i.e. `0x61440` bytes) into
  **25 equal slices** of `0x3E40` bytes — each one its own ELF
- For each slice `k`, it `memfd_create("subsubagent_%d")`, and passes
  **`argv[1][4k … 4k+4]`** — a 4-character chunk — to it
- All 25 must exit 0

So: 100 chars = 25 independent 4-character sub-problems. Nothing is checked globally, which
means each chunk can be cracked on its own.

## Layer 3 — the subsubagents

Each one reads its 4 bytes as a little-endian `uint32` and runs a fixed xorshift scramble,
then compares against a hardcoded constant:

```c
x = *(uint32_t*)argv[1];
for (c = 13; c > 1; c--) x ^= x >> c;
for (c = 25; c > 1; c--) x ^= x << c;
for (c =  7; c > 1; c--) x ^= x >> c;
if (x == 0xbe47d89f) return 0;      // constant differs per subsubagent
```

All 25 use the **same shift schedule** and differ only in the target constant — confirmed by
diffing the disassembly of `ss00`, `ss13` and `ss24`.

## Inverting it

Every operation is `x ^= x >> c` or `x ^= x << c`. Those are **linear over GF(2)** — no
addition, no carries. So the whole scramble is a 32×32 bit-matrix `M`, and recovering the input
is just solving `M·x = target`.

Build `M` by pushing the 32 basis vectors through the forward function, then Gaussian-eliminate:

```python
cols = [T(1 << i) for i in range(32)]          # column i = T(e_i)
A = [sum(((cols[i] >> b) & 1) << i for i in range(32)) for b in range(32)]
# then solve A·x = target over GF(2)
```

Brute force would have been 2³² per chunk × 25; the linear-algebra route is instant.

Recovering all 25 chunks and verifying each against its real binary (`rc == 0`):

```
ss00 0xbe47d89f -> b'CYBL' ✓    ss09 -> b'suba' ✓    ss18 -> b'_dol' ✓
ss01 0xf798986a -> b'TZ20' ✓    ss10 -> b'gent' ✓    ss19 -> b'lars' ✓
ss02 0xf1e86178 -> b'26{p' ✓    ss11 -> b's___' ✓    ss20 -> b'_mor' ✓
...                             ...                  ss24 -> b'bro}' ✓
```

Concatenated:

```
CYBLTZ2026{please_bro_just_ten_more_subagents___please_just_five_million_dollars_more_in_tokens_bro}
```

Exactly 100 characters, which is the length check from layer 2 — a nice self-confirmation.

Full script: [`tools/fraude_solve.py`](../../tools/fraude_solve.py)

## Notes

- The ncurses UI is entirely decorative. The "safeguard" message is just `exit != 0` from the
  subagent; the success screen simply echoes your prompt back as "your answer".
- Dumping the nested ELFs statically is far easier than trying to catch the `memfd` at runtime.
