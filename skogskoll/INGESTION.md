# Ingestion and alert safety

The pure ingestion core is in `src/observation-core.mjs`; run tests with:

```sh
node --test skogskoll/tests/*.test.mjs
```

## Invariants
- Identity is `source + source_id`; never deduplicate solely by geometry or parcel name.
- Missing source IDs are rejected and counted; never invent random IDs.
- An unchanged record is a touch, not a new alert.
- Changed attributes or geometry should update the stored record and create an auditable change event later; they are not automatically a new-application alert.
- Initial baseline import must not alert on historical records. Alerting stays disabled until baseline is explicitly established.
- A failed or incomplete poll must never mark unseen records inactive. Reconciliation may only follow a complete successful scan.
- Preserve `Inkomdatum` as a source value until live metadata confirms its type and meaning.
- This pure core is database-agnostic. Supabase persistence and transactional alert-outbox handling are a later layer; no email or push notifications are sent here.
