# Leadership Pressure Radar methodology

## Purpose

The radar prioritises FTSE 100 companies for closer leadership-succession research. It does not predict that a CEO or Chair will leave office, and it is not a governance-quality rating.

Methodology `v0.6` separates scored signals from evidence overlays:

- role-specific tenure pressure
- qualifying significant dissent on management-sponsored resolutions in the existing Proxy Voting dataset
- official issuer profit-warning and material prospective profit-impact announcements
- officially announced active CEO and Chair succession processes

Profit-warning and succession evidence are visible but not scored. Share-price stress, activism, controversies, and broader news are not yet included.

## Universe and coverage

- The public FTSE 100 constituent table on Wikipedia is used as a reproducible 100-company roster snapshot.
- FTSE Russell remains the index authority; the public table is not presented as an official licensed index feed.
- All 100 companies have source-verified leadership records across `data/leadership_sources.json` and `data/leadership_sources_expansion.json`.
- The evidence cutoff for the current cohort is 8 August 2026.
- Six externally managed issuers without a company CEO are marked `Not applicable`; no CEO score is inferred for them.

## Score construction

Scores run from 0 to 100 and are built as tenure pressure plus a potential registered-dissent uplift.

### CEO

CEO tenure pressure increases across a ten-year reference horizon and is capped at 80 points. Ten years is an analytical reference, not a UK governance rule or formal tenure limit.

### Chair

Chair tenure pressure increases toward the UK Corporate Governance Code's nine-year independence and succession reference point and is capped at 80 points.

### Registered dissent uplift

Up to 20 points can be added for verified 20%+ dissent on management-sponsored resolutions captured by the existing tracker:

- 20% to 29.9% against: 4 points
- 30% to 49.9% against: 8 points
- 50% or more against: 15 points
- repeat qualifying resolutions add 3 points each, subject to the 20-point cap

Shareholder proposals and shareholder-requisitioned resolutions are excluded because votes against those proposals may align with management's recommendation.

Absence of a qualifying record is not evidence that a company had no dissent outside the tracker's narrow 2025 window.

## Profit-warning overlay

The initial overlay uses a 36-month lookback and includes only official issuer announcements that either:

- cut full-year earnings guidance; or
- quantify a material prospective adverse impact on profit.

Routine earnings misses, unquantified caution, and reductions to operating metrics without a clear profit implication are excluded. Each event records its announcement date, affected period, event type, severity, concise summary, principal drivers, and primary-source link.

The same review protocol was applied to all 100 companies for the 36 months to 8 August 2026. Fifteen high-confidence events were captured across 11 issuers. Review outcomes and source hubs are recorded in `data/profit_warning_reviews.json`.

For companies inside the reviewed subset, no warning badge means no qualifying event was captured under this protocol, not proof that no adverse announcement occurred. The overlay does not alter the 0-100 pressure score in methodology `v0.6`; any score contribution requires stronger calibration evidence first.

## Calibration audit

Calibration methodology `v0.4` records 56 source-backed transition outcomes alongside 188 current, right-censored role observations. The outcome census contains 50 completed CEO transitions and six eligible active CEO or Chair processes. One interim-Chair case remains excluded because the recorded incumbent began the role after the succession search was announced.

Completed cases are included only where an official issuer announcement or annual report identifies the incumbent, transition outcome and announcement timing. This is a purposive high-confidence cohort, not a complete census of FTSE 100 CEO changes. Where an issuer gives only a month for a role start, the first day is stored for calculation and the record is explicitly marked with month-level precision.

Every completed outcome has an explicit fixed 36-month review window ending on the official transition announcement. Twenty-four cases have complete warning reviews and 26 newly added cases remain partial pending archive backfill. Nine qualifying events have been identified from official issuer sources. Only the 24 complete cases enter aligned warning sensitivity metrics; partial coverage is never interpreted as zero events. Market sensitivity uses the trailing two-year dividend-adjusted company return less the FTSE 100 price-index return and also ends on the announcement date. Current comparisons use the evidence date.

Six source-backed historical dissent resolutions were captured. Four completed-transition windows now have complete resolution-level coverage for every AGM in scope, while the remaining windows stay partial. Dissent is therefore disclosed as contextual evidence and excluded from the aligned calibration score. Missing AGM history is never treated as zero dissent. The review ledger, event inclusion decisions and source links are stored in `data/calibration_historical_evidence.json`.

The audit tests two exploratory additions without changing production scores:

- a warning uplift of 6 points for a material event or 12 for any severe event, plus 3 for repeats and capped at 18
- a performance uplift of 8 points for relative underperformance of at least 20 percentage points or 15 points at 40 percentage points

Risk thresholds are derived only from the current-comparison cohort's 75th percentiles, so outcome observations do not influence the cutoffs used to assess them. The six-case evaluation sample established in v0.3 remains locked for comparability and the preceding 18 aligned cases remain the development cohort. In development, warning sensitivity improves capture from 27.8% to 38.9%. In the locked sample, tenure-only, warning and combined models all capture 16.7%. Market underperformance adds no lift. Because this sample has now been evaluated, it is no longer described as pristine unseen evidence.

The result does not support changing production weights. It suggests warnings may add retrospective separation in the development data, but that effect does not generalise in the small locked sample. The next evidential threshold is complete warning backfill for the 17 pending cases, broader complete AGM coverage beyond the first four cases, and a genuinely untouched future transition cohort before dissent or warning weights are promoted into production. Full records and summary statistics are published in `public/data/leadership-calibration.json`.

## Market-series quality

The market build validates all 100 company series and the FTSE 100 benchmark. Isolated approximately 100x switches between pounds and pence are aligned to the preceding observation before returns are calculated. Each correction is counted, and the build fails if an extreme discontinuity remains. This does not smooth ordinary market movements.

## Active succession overlay

An active succession case requires an official issuer announcement that an incumbent CEO or Chair will leave, that a search is underway, or that a named successor has not yet taken office. Informal speculation, general succession-planning language, and completed appointments are excluded.

All 100 companies were reviewed to 8 August 2026. The current release captures seven active processes: CEO transitions at Babcock International, Barratt Redrow, British Land, and Kingfisher, plus Chair processes at British American Tobacco, Burberry, and JD Sports. The exact incumbent, status, dates, named successor where available, and primary-source link are stored in `data/succession_sources.json`.

Succession status is displayed as live evidence and does not alter the pressure score. Absence means no qualifying official announcement was captured by the evidence date, not proof that a board is not planning succession privately.

## Pressure bands

- `Lower`: 0-24
- `Watch`: 25-49
- `Elevated`: 50-69
- `Acute`: 70-100
- `Unrated`: leadership evidence has not yet been researched
- `Not applicable`: the externally managed listed issuer has no company CEO

## Validation

The build fails if it finds:

- a roster other than exactly 100 constituents
- duplicate constituent or curated tickers
- a rated role without a primary source URL
- leadership evidence that does not exactly match the current 100-company roster
- a future appointment date, non-HTTPS source, or unsourced not-applicable designation
- a score outside 0-100
- a duplicate or malformed profit-warning event ID
- a warning ticker outside the current roster
- an unsupported event type or severity
- an invalid, future, or out-of-window event date
- missing source evidence or an impossible percentage change
- warning reviews containing tickers outside the verified cohort
- warning-review outcomes that do not reconcile to captured events
- succession reviews that do not exactly cover the verified cohort
- an invalid succession status, date, source, role, or incumbent mismatch
- duplicate, future-dated, unsourced, or chronologically impossible calibration outcomes
- missing or duplicate historical evidence reviews and review windows not aligned to exactly 36 months
- historical warning or dissent events outside their outcome window, attached to the wrong issuer, or lacking an HTTPS primary source
- unsupported warning classifications, non-management dissent, or impossible vote-against percentages
- duplicate or unsorted market observations and unresolved extreme scale discontinuities

The generated file records validation status, methodology version, source mode, generation time, evidence date, and limitations.

## Refresh model

`npm run data` refreshes the public constituent snapshot, rebuilds Proxy Voting, recalculates radar scores, refreshes market-performance series for all 100 companies, and runs as part of the weekly GitHub Actions workflow.

Leadership appointments, profit-warning events, and succession cases remain editorially approved because issuer disclosures vary and a false automated match would be more damaging than a visible evidence gap. The weekly monitor discovers candidate issuer links, but never publishes them as analytical evidence automatically. Historical calibration currently has 33 complete warning windows and four complete AGM windows across 50 completed transitions; partial histories are not interpreted as zero events.
