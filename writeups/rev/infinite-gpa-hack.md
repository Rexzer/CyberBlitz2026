# Infinite GPA Hack — Reverse (500 pts)

> WE MAKING IT OUT THE PROVOST'S LIST WITH THIS ONE 🔥🔥🔥🔥

**Flag:** `CYBLTZ2026{inf1n1t3_gp4_gl1tch}`

The easiest challenge in the set, and a good reminder to read files with a tool rather than
an eye.

`hack.py` is a jokey terminal app — pick a module, watch a spinner ("Cogitating…",
"Tung Tung Tung Sahuring"), get told your GPA is hacked. Reading it top-to-bottom it looks
harmless. But `file` flags it:

```
hack.py: Python script, Unicode text, UTF-8 text executable, with very long lines (592)
```

**592-character lines** in a script whose longest visible line is maybe 80. The payload is
padded far off-screen with whitespace so it never shows in a normal editor viewport:

```python
    loading_bar();                                            <~450 spaces>            exec(base64.b64decode(b"dHJ5OgogICAg...").decode())
```

Decoding the blob:

```python
try:
    if open("./flag.txt").read() == "CYBLTZ2026{inf1n1t3_gp4_gl1tch}":
        print("That's the correct flag!"); sys.exit(0)
except:
    pass
```

The flag is sitting in the comparison. No need to run anything.

```bash
$ grep -oE '[A-Za-z0-9+/=]{40,}' hack.py | base64 -d
```

**Takeaway:** when triaging a "source provided" challenge, check `file` output and line lengths
before reading. Horizontal scroll is a legitimate hiding place, and `cat` will not save you.
