# Same Kopi, Different Cup — Crypto (230 pts)

> A kopitiam terminal reused something across encrypted receipts. Recover the midnight order
> from the known order and its matching receipt.

**Flag:** `CYBLTZ2026{54m3_571ck_n3w_r3c31pT}`

Keystream reuse — the terminal XORs every receipt with the **same** keystream, so one known
plaintext/ciphertext pair recovers the key for all of them.

## The handout

```
known_order.txt:  ORDER|table=07|drink=kopi-o-kosong|status=paid|     (47 bytes)

receipts.txt:
  known    = dce0ba2436ebedcb7eb6fddfd0ddd7e4c991b9b36ac2fc7e3fc8b981edc1696efdd5821210f6eddf6fe7e883898ed7
  morning  = dce0ba2436ebedcb7eb6fddfd0d9d7e4c991b9b36addf6667b86aadff2cf6e74e08f8e000df3e5
  noon     = dce0ba2436ebedcb7eb6fddfd1dbd7e4c991b9b36ac4fa623999a5d8e7da6f72aec4910800eb
  midnight = d0ebbc2d30cdab9a2eece3d7d48798df8ecfe6bb3cf6fd3d21baa49fe59d2b71c7cf
```

The `known` ciphertext is exactly the length of `known_order.txt`, and `known`, `morning`,
`noon` share a long common prefix — the signature of a fixed keystream XOR'd against plaintexts
that share the `ORDER|table=0…` header.

## Recover the keystream, decrypt midnight

```
keystream = known_ct XOR known_pt
midnight  = midnight_ct XOR keystream[:len(midnight_ct)]
```

```python
pt  = open('known_order.txt','rb').read().rstrip(b'\n')
ct  = {k: bytes.fromhex(v) for k,v in
       (l.split('=',1) for l in open('receipts.txt') if '=' in l)}
ks  = bytes(a^b for a,b in zip(ct['known'], pt))
dec = lambda c: bytes(x^k for x,k in zip(c, ks))
for n in ('morning','noon','midnight'):
    print(n, dec(ct[n]))
```
```
morning  b'ORDER|table=03|drink=teh-c|status=paid|'
noon     b'ORDER|table=11|drink=milo|status=void|'
midnight b'CYBLTZ2026{54m3_571ck_n3w_r3c31pT}'
```

The midnight "order" is the flag — *same stick, new receipt*.

**Takeaway:** a shared keystream (reused OTP / stream-cipher nonce / fixed XOR key) is broken
the moment you have one plaintext of equal-or-greater length. Never reuse keystream across
messages.
