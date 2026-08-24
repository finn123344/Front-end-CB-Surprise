# Data

## `events.csv` — your scored archive (not committed)

Drop your timestamped scored events here as `data/events.csv`:

| column | type | notes |
|---|---|---|
| `timestamp` | ISO-8601, UTC | when the speech/presser started |
| `bank` | str | `FED`, `ECB`, `BOE`, `BOJ`, … (map to markets in `cb_surprise/config.py`) |
| `speaker` | str | stable identifier per person |
| `role` | str | `chair` / `president` / `governor_head` count as "chair"; anything else is "regional / other" |
| `event_type` | str | `presser`, `speech`, `testimony`, … (optional) |
| `score` | float | hawkishness score, hawkish = positive |

The surprise is computed *from* this file (score minus the speaker's own
trailing mean), so no surprise column is needed.

## `macro_releases.csv` — optional macro-release calendar

Events landing on a major-release day are flagged and reported separately.
US nonfarm payrolls is built in (first-Friday rule); add everything else here:

| column | type | notes |
|---|---|---|
| `date` | ISO-8601 date | release date |
| `release` | str | e.g. `US CPI`, `EA flash HICP` |

Sources: [bls.gov/schedule](https://www.bls.gov/schedule/news_release/cpi.htm)
and the Eurostat release calendar.

## `cache/` — market data (auto-created, not committed)

`run_study.py` downloads free daily 2y yields on first run and caches them here:

- **US2Y** — FRED series `DGS2` (keyless CSV endpoint)
- **EA2Y** — ECB Data Portal, euro-area AAA 2y spot yield (`YC` dataset, keyless)

Add more banks by writing a fetcher in `cb_surprise/market_data.py` and mapping
the bank to it in `MARKET_MAP`.
