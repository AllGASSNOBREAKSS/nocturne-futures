# Nocturne

**An overnight futures outlook engine for ES, NQ, GC and SI that publishes a dated call, then grades itself.**

Most market tools show you a chart and a narrative. Nocturne writes the call down before the session — bias, probability-weighted close, expected range, five levels, three scenarios — commits it as a timestamped JSON artifact, and scores it against the official settlement the next day. The archive of calls, including the misses, is the product.

---

## The first call

**Published:** 2026-10-27 20:55 ET · **Session:** 2026-10-28 · **Engine:** v0.1.0

| Instrument | Bias | Conf. | Predicted close | Expected range | 1σ close |
|---|---|---:|---|---|---|
| **ES** · E-mini S&P 500 | Neutral-bearish | 55% | 7,745–7,755 | 7,700–7,800 | ±65–85 |
| **NQ** · E-mini Nasdaq-100 | Neutral-bearish | 55% | 29,750–29,820 | 29,300–30,050 | ±380–450 |
| **GC** · Gold | Bearish | 58% | 4,050–4,065 | 3,990–4,100 | ±40–50 |
| **SI** · Silver | Bearish | 60% | 54.10–54.25 | 52.70–55.30 | ±0.95–1.20 |

### What happened

| Instrument | Prior | Predicted | Actual | Error | Dir | Band | Range |
|---|---:|---|---:|---:|:--:|:--:|:--:|
| **ES** | 7,758.25 | 7,745–7,755 | **7,783.25** | +33.25 (+0.43%) | ❌ | ❌ | ⚠️ |
| **NQ** | 29,812.00 | 29,750–29,820 | **29,979.50** | +194.50 (+0.65%) | ❌ | ❌ | ⚠️ |
| **GC** | 4,074.60 | 4,050–4,065 | **4,051.60** | −5.90 (−0.15%) | ✅ | ✅ | ✅ |
| **SI** | 54.293 | 54.10–54.25 | **53.457** | −0.72 (−1.33%) | ✅ | ❌ | ✅ |

**Direction 50% · close band 25% · range 50% full (100% touched) · mean absolute close error 0.64%.**

The FOMC held at 3.75%–4.00% on a 10–2 vote. Equities read *"the accumulation of more information"* as patience and rallied through R1 and R2; the 10-year rose to 5.045% and metals settled lower. Gold was the clean hit — the 4,084 resistance capped the high at 4,097, the 4,035 support held within 2 points, and the settlement landed inside the band. ES and NQ were wrong on direction: both made their low in the first fifteen minutes and peaked at 14:35–14:40 ET.

The full postmortem, including the three design defects this exposed, is in [`docs/lessons-2026-10-28.md`](docs/lessons-2026-10-28.md).

---

## How it works

```text
Yahoo Finance · US Treasury · Federal Reserve · ForexFactory · Nasdaq
                              │
                              ▼
                 ts/src  (fetch + zod schema validation)
                              │  data/raw/*.json
                              ▼
              data/snapshots/<call_id>/call.json   ← immutable, dated
                              │
                              ▼
     python src/nocturne  (stats → levels → scenarios → score → report)
                              │
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
  <call_id>_call.md     <session>_scorecard.md   <call_id>_dashboard.html
  <call_id>_levels.png  <session>_scorecard.png
```

**Python** does the analytics, scoring and charts (pandas, numpy, matplotlib).
**TypeScript** does ingestion and schema validation (Node 24, zod, tsx).
The contract between them is plain JSON, validated on both sides.

### Why two languages

- Python is the right tool for the statistics, the 15-year study, and matplotlib.
- TypeScript is the right tool for a typed ingestion pipeline and a future web dashboard.
- JSON keeps the call artifact readable, diffable, and independent of either runtime.

---

## Repo layout

```text
nocturne-futures/
├── config/instruments.yaml          contract specs and tick values
├── data/
│   ├── snapshots/2026-10-27/call.json      the published call
│   ├── snapshots/2026-10-28/actual.json    the settlement used to score it
│   ├── studies/fomc_2024_2026.json         base rates used in the call
│   ├── studies/daily_15y/*.csv             15 years of daily bars
│   └── raw/history_1mo.json                chart history
├── docs/
│   ├── methodology.md
│   ├── data-sources.md
│   ├── lessons-2026-10-28.md
│   ├── ml-baseline.md
│   └── roadmap.md
├── reports/                         generated call, scorecard, charts, dashboard
├── scripts/
│   ├── run_study.py                 rebuild the 15-year base rates
│   └── train_baseline.py            walk-forward ML baseline
├── src/nocturne/                    Python package
│   ├── models.py                    typed Call / Instrument / Scenario
│   ├── stats.py                     ATR, realized vol, event stats
│   ├── levels.py                    level utilities
│   ├── scenarios.py                 expected close, bucket lookup
│   ├── score.py                     settlement scoring
│   ├── report.py                    markdown, matplotlib, HTML
│   └── cli.py                       `nocturne build|score|dashboard`
├── tests/                           12 tests, including the known scorecard
├── ts/                              TypeScript ingestion + validation
└── pyproject.toml
```

---

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m nocturne build --date 2026-10-27
```

That regenerates:

- `reports/2026-10-27_call.md`
- `reports/2026-10-27_levels.png`
- `reports/2026-10-28_scorecard.md`
- `reports/2026-10-28_scorecard.png`
- `reports/2026-10-27_dashboard.html`

TypeScript pipeline:

```bash
cd ts
npm install
npm run validate -- ../data/snapshots/2026-10-27/call.json
npm run fetch -- 2026-10-27        # writes data/raw/2026-10-27/*.json
```

Rebuild the 15-year study:

```bash
python scripts/run_study.py                 # from committed CSVs
python scripts/run_study.py --fetch         # refresh from Yahoo
```

---

## Method in one paragraph

ATR(14) sets the expected range. Twenty-day realized volatility sets the one-sigma close. Prior-session RTH highs and lows set R1/S1; the prior week's extremes and round numbers set R2/S2; VWAP is the pivot. Three scenarios — hawkish hold, dovish hold, hike — carry probabilities that sum to 1.0. The expected close is the probability-weighted midpoint. The bias label is a separate judgment about the modal outcome. Scoring uses the official settlement: 16:00 ET for CME equity index futures, 13:30 ET for COMEX metals. Full detail in [`docs/methodology.md`](docs/methodology.md).

---

## The honest part

This repo is not claiming a working edge.

- The first call got **2 of 4 directions** right and **1 of 4 close bands**.
- The scenario buckets left gaps: three of four settlements landed outside every named range. That is a design defect, fixed in v0.2.
- The walk-forward ML baseline does **not** beat the always-up base rate on ES, NQ or GC. On silver it is 0.3pp better, which is noise. See [`docs/ml-baseline.md`](docs/ml-baseline.md).

What the repo does have is a reproducible process: every input is dated, every call is committed before the session, every score is computed from the official settlement, and every miss is documented. That is the part worth building on.

---

## Roadmap

**v0.2** — five overlapping price buckets instead of three named ranges; a real-yield axis; options-implied moves; automated level selection; a running Brier/MAE table.

**v0.3** — event-aware ML on cross-asset and positioning features, validated with purged walk-forward and scored on calibration, not accuracy.

**v1.0** — paper-traded calls with slippage, risk sizing, and a public archive.

See [`docs/roadmap.md`](docs/roadmap.md).

---

## Disclaimer

Research artifact, not investment advice. Futures are leveraged; a 1-point ES move is $50 per contract, a 1-point NQ move is $20, a $1 gold move is $100, and a $0.01 silver move is $50. Data is from public sources and can be wrong. Do not trade off a single call.
