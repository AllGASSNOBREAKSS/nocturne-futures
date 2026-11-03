# Macro calendar sample

`sample_events.json` is an explicitly labelled **public-schedule sample**, not a
live economic calendar. Consensus, actual, prior and revision fields are null.
Do not treat these records as point-in-time consensus data.

Production ingestion must use an authorized provider, preserve publication and
availability timestamps, and respect licensing. The `CalendarStore` accepts
JSONL records matching `nocturne.macro.calendar.EconomicEvent`.
