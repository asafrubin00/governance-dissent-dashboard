# Issuer announcement monitor methodology

## Purpose

The monitor identifies newly published earnings- and leadership-succession-related links on official issuer websites and places them in a typed editorial review queue. It is a discovery aid, not an autonomous classifier.

Nothing detected by the monitor changes the Leadership Pressure Radar or its score automatically.

## Coverage

- The configuration contains one official issuer landing page for each of the 100 companies in the source-verified leadership cohort.
- The current monitor baseline reached 86 sources, of which 52 exposed monitorable links in server-rendered HTML.
- Fourteen sources were unavailable to that run because of access controls, timeouts, TLS incompatibility, or incompatible delivery.
- Source health is recalculated on every run and written to `public/data/announcement-monitor.json`.

Reachability is not the same as complete disclosure coverage. A reachable page may expose no matching links, and an unavailable page may still be accessible to a human browser.

The monitor uses modest connection and response timeouts so slower issuer sites are not incorrectly classified as unavailable. It does not bypass access controls or substitute third-party news feeds where an official site blocks automated requests.

## Detection rules

The monitor inspects links on each configured official page and assigns matching links to one or both review types.

Earnings terms include:

- full-year, half-year, interim or annual results
- profit, outlook or guidance
- trading statement, trading update or market update

Succession terms include:

- chief executive or CEO
- chair succession, chair designate or chair appointment
- directorate or board change
- succession plan, step down or retire

The first successful set of links for a source establishes a baseline. Later unseen links become review candidates in `data/announcement_review_queue.json`.

## Editorial workflow

1. The weekly GitHub Action runs the monitor and commits newly detected candidates.
2. A reviewer opens the official issuer link and determines whether it meets the profit-warning or active-succession methodology.
3. Non-qualifying items are marked `dismissed` in the queue with a short review note.
4. Qualifying items are added to `data/profit_warning_sources.json` or `data/succession_sources.json` and marked `promoted` in the queue.
5. The normal data build validates and publishes the approved evidence overlay.

## Publication safeguard

Keyword matching can produce false positives because routine results, completed appointments, and generic governance language share terms with qualifying events. For that reason, candidates default to `pending` and are never copied automatically into the analytical dataset.

## Validation

The monitor fails before fetching if it finds:

- monitor tickers that do not exactly match the verified leadership cohort
- duplicate ticker or review-candidate IDs
- missing company names, tickers, or HTTPS source URLs
- unsupported queue statuses or signal types

Individual website failures do not fail the full run. They are recorded as `unavailable` so gaps remain visible.
