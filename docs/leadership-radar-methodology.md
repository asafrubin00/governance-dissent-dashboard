# Leadership Pressure Radar methodology

## Purpose

The radar prioritises FTSE 100 companies for closer leadership-succession research. It does not predict that a CEO or Chair will leave office, and it is not a governance-quality rating.

Methodology `v0.2` separates scored signals from an evidence overlay:

- role-specific tenure pressure
- qualifying significant dissent on management-sponsored resolutions in the existing Proxy Voting dataset
- official issuer profit-warning and material prospective profit-impact announcements

Profit-warning evidence is visible but not scored until coverage is comparable across the verified cohort. Share-price stress, activism, controversies, and broader news are not yet included.

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

The current source file contains three high-confidence events across Rentokil Initial, Marks & Spencer, and Kingfisher. This is intentionally a narrow initial set, not complete cohort coverage. A company without a badge should therefore be read as “no qualifying event captured in the current curated file,” not “no profit warning issued.”

The overlay does not alter the 0-100 pressure score in methodology `v0.2`. A bounded warning contribution will only be considered after the same research protocol has been applied across the full verified cohort.

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

The generated file records validation status, methodology version, source mode, generation time, evidence date, and limitations.

## Refresh model

`npm run data` refreshes the public constituent snapshot, rebuilds the Proxy Voting dataset, recalculates radar scores, and runs as part of the weekly GitHub Actions workflow.

Leadership appointments and profit-warning events remain manually curated because issuer disclosures vary and a false automated match would be more damaging than visibly incomplete coverage. The weekly workflow recalculates and validates approved evidence but does not yet discover and publish new events autonomously.
