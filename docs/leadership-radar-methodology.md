# Leadership Pressure Radar methodology

## Purpose

The radar prioritises FTSE 100 companies for closer leadership-succession research. It does not predict that a CEO or Chair will leave office, and it is not a governance-quality rating.

Methodology `v0.3` separates scored signals from evidence overlays:

- role-specific tenure pressure
- qualifying significant dissent on management-sponsored resolutions in the existing Proxy Voting dataset
- official issuer profit-warning and material prospective profit-impact announcements
- officially announced active CEO and Chair succession processes

Profit-warning and succession evidence are visible but not scored. Share-price stress, activism, controversies, and broader news are not yet included.

## Universe and coverage

- The public FTSE 100 constituent table on Wikipedia is used as a reproducible 100-company roster snapshot.
- FTSE Russell remains the index authority; the public table is not presented as an official licensed index feed.
- Twenty-five companies have source-verified CEO and Chair appointment records in `data/leadership_sources.json`.
- The evidence cutoff for the current cohort is 6 August 2026.
- The other constituents are retained in the interface as visibly `Unrated` research candidates.
- No leadership names, dates, or scores are inferred for unresearched companies.

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

The same review protocol was applied to all 25 companies in the verified cohort for the 36 months to 8 August 2026. Four high-confidence events were captured across Rentokil Initial, Marks & Spencer, Kingfisher, and Computacenter. Review outcomes and source hubs are recorded in `data/profit_warning_reviews.json`.

A company without a warning badge means no qualifying event was captured under this protocol, not proof that no adverse announcement occurred. The overlay does not alter the 0-100 pressure score in methodology `v0.3`; any score contribution requires calibration and outcome testing first.

## Active succession overlay

An active succession case requires an official issuer announcement that an incumbent CEO or Chair will leave, that a search is underway, or that a named successor has not yet taken office. Informal speculation, general succession-planning language, and completed appointments are excluded.

All 25 rated companies were reviewed to 8 August 2026. The current release captures one active process: Kingfisher's internal and external CEO search following Thierry Garnier's announced resignation. The exact incumbent, status, dates, named successor where available, and primary-source link are stored in `data/succession_sources.json`.

Succession status is displayed as live evidence and does not alter the pressure score. Absence means no qualifying official announcement was captured by the evidence date, not proof that a board is not planning succession privately.

## Pressure bands

- `Lower`: 0-24
- `Watch`: 25-49
- `Elevated`: 50-69
- `Acute`: 70-100
- `Unrated`: leadership evidence has not yet been researched

## Validation

The build fails if it finds:

- a roster other than exactly 100 constituents
- duplicate constituent or curated tickers
- a rated role without a primary source URL
- a score outside 0-100
- a duplicate or malformed profit-warning event ID
- a warning ticker outside the current roster
- an unsupported event type or severity
- an invalid, future, or out-of-window event date
- missing source evidence or an impossible percentage change
- warning reviews that do not exactly cover the verified cohort
- warning-review outcomes that do not reconcile to captured events
- succession reviews that do not exactly cover the verified cohort
- an invalid succession status, date, source, role, or incumbent mismatch

The generated file records validation status, methodology version, source mode, generation time, evidence date, and limitations.

## Refresh model

`npm run data` refreshes the public constituent snapshot, rebuilds the Proxy Voting dataset, recalculates radar scores, and runs as part of the weekly GitHub Actions workflow.

Leadership appointments, profit-warning events, and succession cases remain editorially approved because issuer disclosures vary and a false automated match would be more damaging than a visible evidence gap. The weekly monitor discovers candidate issuer links, but never publishes them as analytical evidence automatically.
