# Scorecard · 2026-10-28 session

**Call:** `2026-10-27` · published 2026-10-27T20:55:00-04:00  
**Scored:** 2026-10-28T16:00:00-04:00 · official settlement

**Verdict:** direction 50% · close band 25% · range 50% full (100% touched) · mean absolute close error 0.64%.

| Instrument | Prior | Predicted | Actual | Error | Dir | Band | Range | R1 break | S1 break | Bucket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **ES** | 7,758.25 | 7,745.00–7,755.00 | 7,783.25 | +33.25 (+0.43%) | ❌ | ❌ | ⚠️ partial | +46.50 | -38.25 | outside |
| **NQ** | 29,812.00 | 29,750.00–29,820.00 | 29,979.50 | +194.50 (+0.65%) | ❌ | ❌ | ⚠️ partial | +297.00 | -180.25 | outside |
| **GC** | 4,074.60 | 4,050.00–4,065.00 | 4,051.60 | -5.90 (-0.15%) | ✅ | ✅ | ✅ | +13.20 | -1.90 | outside |
| **SI** | 54.29 | 54.10–54.25 | 53.46 | -0.72 (-1.33%) | ✅ | ❌ | ✅ | -0.72 | +0.39 | Hawkish hold |

`R1 break` / `S1 break` are in points; positive means the session ran past that level. `Bucket` is the published scenario that contained the settlement; `outside` means the scenario bands left a gap.

## What happened

The FOMC held the target range at 3.75%–4.00% on a 10–2 vote. Equities rallied through resistance, the 10-year yield rose to 5.045%, and metals settled lower. ES +0.32%, NQ +0.56%, gold -0.56%, silver -1.54%.

> Inflation remains elevated. The accumulation of more information will help the Committee determine the policy stance appropriate to ensure a timely return of inflation to the Committee's 2 percent goal. The Committee will deliver price stability.

| Market | Close |
| --- | --- |
| S&P 500 cash | 7,743.98 |
| Nasdaq Composite | 26,549.85 |
| VIX | 16.91 |
| US 10Y | 5.045 |
| DXY | 102.19 |

## What worked, what did not

- Gold was the clean hit: the 4,084 resistance capped the high at 4,097, the 4,035 support held within 2 points, and the settlement landed inside the 4,050–4,065 band.
- Silver's direction and downside target were right — settled 53.46 against a 54.10–54.25 call, with the 53.00 support holding within 0.41 — but the close band was too high.
- ES and NQ were wrong on direction. Both opened near the prior close, made their low in the first 15 minutes (09:45 ET), then rallied through R1 and R2, peaking at 14:35–14:40 ET after the statement.
- The Fed held, but the phrase 'the accumulation of more information' was read as patience. Equities treated the hold as a relief signal even though two members voted to hike.
- The single-axis hawkish/dovish map was too coarse: a patient hold lifted equities while a higher long end (10Y 5.045%) pressured gold. The model needs a second axis for real yields.

## Calibration note

Direction 2/4, close band 1/4, range 2/4 full plus 2/4 partial, mean absolute close error 0.64%. Only one of four settlements landed inside a published scenario bucket, which is the clearest defect: the three named scenarios left gaps between 7,745–7,790 on ES and 29,700–30,200 on NQ. v0.2 should output a continuous distribution over price buckets, or five overlapping quantile buckets, instead of three narrow named bands.

---
*Scored on the official settlement: CME equity index futures at 16:00 ET, COMEX metals at 13:30 ET. The 16:00 ET mark for metals is shown below for transparency.*

| Instrument | 16:00 ET mark |
| --- | --- |
| ES | 7,784.50 |
| NQ | 29,990.75 |
| GC | 4,089.10 |
| SI | 54.39 |