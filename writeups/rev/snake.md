# Snake — Reverse (280 pts)

> i actually wanted to make this a proper obfuscator but i got lazy

**Flag:** `CYBLTZ2026{s1mplyth000n}`

A `.pyc` whose **module** bytecode is deliberately malformed to break disassemblers and crash
the wrong interpreter, while the real logic is an `exec`'d, transformed base64 blob. Don't fight
the obfuscation — hook `exec` and let the program hand you the plaintext.

## Identify the version first

```
$ xxd snake.pyc | head -1
00000000: cb0d 0d0a ...
```

Magic `0d cb` = **3531** = **Python 3.12**. Loading it under 3.13/3.14 "works" for
`marshal.loads` but segfaults on execution and mis-renders in `dis` (bogus `CALL_KW`,
`SET_FUNCTION_ATTRIBUTE`, name indices out of range) — all of that is the anti-tamper. Get a
matching interpreter:

```bash
uv python install 3.12
```

## Visible constants

`marshal` still exposes the module's names and consts:

```
co_names: (base64, s, q, _0x5f3759df_0x7c2a4b8e, _0x8b7c6a5d_0x4e3d2c1b, exec, b64decode, encode, bytes, fromhex)
consts  : 'RsemjzJx...rxY967gL=M'   (828-char blob, ends in a mid-string '=')
          'da39a3ee5e6b4b0d3255bfef95601890afd80709'   (SHA-1 of the empty string)
```

The two `_0x...` functions (named after the fast-inverse-sqrt magic, `0x5f3759df`) do a
string permutation and a byte transform; both are hand-crafted to defeat `dis`. Reconstructing
them by hand is a trap.

## Hook `exec` instead of deobfuscating

The module ends in `exec(<decoded source>)`. Replace `exec` with a shim that **captures string
payloads and passes real code objects through** (so `import base64` still works), then run the
module under 3.12:

```python
import marshal, builtins
co = marshal.loads(open('snake.pyc','rb').read()[16:])
captured, real = [], builtins.exec
def shim(c, *a, **k):
    if isinstance(c, (str, bytes, bytearray)):
        captured.append(c); return None       # swallow the payload, don't run it
    return real(c, *a, **k)                    # let module-body code objects execute
builtins.exec = shim
real(co, {'__name__': '__main__'})
print(captured[0])
```

(Running it un-hooked under 3.12 segfaults, and hooking *all* `exec` breaks the `base64` import
— the `str/bytes`-only filter is the trick.)

## The payload is an RC4 checker

```python
k = b"opcodeopcodeopco"

def enc(key, data):                 # textbook RC4 KSA + PRGA
    S = list(range(256)); j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256; S[i], S[j] = S[j], S[i]
    i = j = 0; out = bytearray()
    for b in data:
        i = (i+1) % 256; j = (j+S[i]) % 256; S[i], S[j] = S[j], S[i]
        out.append(b ^ S[(S[i]+S[j]) % 256])
    return bytes(out)

a = input("flag > ")
if enc(k, a.encode()).hex() == "6b71030aee4b9241454b681386778f3a615b660d0d2f47f4":
    print("correct!")
```

## RC4 is symmetric — decrypt the target

```python
print(enc(b"opcodeopcodeopco",
          bytes.fromhex("6b71030aee4b9241454b681386778f3a615b660d0d2f47f4")).decode())
# CYBLTZ2026{s1mplyth000n}
```

**Takeaway:** against "lazy obfuscation" that ultimately `exec`s a string, don't reverse the
transform — instrument the sink. And always match the bytecode's Python version before
`marshal`/`dis`, or the tooling lies to you.
