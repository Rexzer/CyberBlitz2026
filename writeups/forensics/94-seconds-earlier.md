# 94 Seconds Earlier — Forensics (310 pts)

> The lobby controller and security desk logged the same 94-second outage with disagreeing
> clocks. Reconcile the incident and submit its incident reference as `CYBLTZ2026{ }`.

**Flag:** `CYBLTZ2026{d47e29ac836f10b2}`

Three sources, two clocks. The answer is the `incident_ref` of the one row that matches **after**
you apply the clock offset — the decoys are the rows that match if you forget to.

## The handout

```
sensor_window.csv     controller clock: (controller_ms, zone, event)
incident_report.jpg   two sticky notes on a monitor
lobby_events.sqlite   incidents(id, zone, start_ms, duration_ms, severity, incident_ref)  -- 400 rows
```

## The reconciliation facts are in the photo

`incident_report.jpg` is a desk photo with two Post-its:

- **Yellow:** *"Lobby controller clock is **FAST**. **17342 ms** ahead of our desk DB. Facilities
  told. Still not fixed."*
- **Green:** *"Outage **drill Wed**: log it as **sev 5**."*

So: `desk_start = controller_start − 17342`, and the incident we want is **severity 5**,
**duration 94000 ms**.

## Find the outage in the controller log

The CSV records `lux-loss` → `lux-restored` pairs. Two zones show exactly a 94-second outage:

```
lobby-east : loss 1782902542342  restored 1782902636342   = 94000 ms
lobby-west : loss 1782902543342  restored 1782902637342   = 94000 ms
```

## Apply the offset and match the DB

```
lobby-east : 1782902542342 − 17342 = 1782902525000
lobby-west : 1782902543342 − 17342 = 1782902526000
```

```sql
SELECT * FROM incidents
WHERE duration_ms=94000 AND severity=5
  AND start_ms IN (1782902525000, 1782902526000);
```

Only **lobby-east** has an exact hit:

```
id=7319  zone=lobby-east  start_ms=1782902525000  duration_ms=94000  severity=5
incident_ref = d47e29ac836f10b2
```

`lobby-west @ 1782902526000` has no matching row, so it falls away.

## The decoys

The table also contains rows whose `start_ms` equals the **raw controller time** (no offset
applied) — e.g. `id=7326 lobby-east @1782902542342` and `id=7415 lobby-west @1782902543342`,
both sev 5 / 94000. They're traps for anyone who skips the 17342 ms correction.

```
CYBLTZ2026{d47e29ac836f10b2}
```

**Takeaway:** when two systems log "the same event" with different clocks, the only safe join is
on a corrected timestamp plus independent attributes (zone, duration, severity). Rows that match
on the *uncorrected* value are exactly the bait.
