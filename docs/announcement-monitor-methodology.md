# Issuer announcement monitor methodology

## Purpose

The monitor identifies newly published earnings-related links on official issuer websites and places them in an editorial review queue. It is a discovery aid, not an autonomous profit-warning classifier.

Nothing detected by the monitor changes the Leadership Pressure Radar or its score automatically.

## Coverage

- The configuration contains one official issuer landing page for each of the 25 companies in the source-verified leadership cohort.
- The current baseline has 15 reachable sources, of which 11 expose monitorable earnings-related links in server-rendered HTML.
- Ten sources are currently unavailable to the monitor because of access controls, timeouts, or incompatible delivery.
- Source health is recalculated on every run and written to `public/data/announcement-monitor.json`.

Reachability is not the same as complete disclosure coverage. A reachable page may expose no matching links, and an unavailable page may still be accessible to a human browser.

## Detection rules

The monitor inspects links on each configured official page and retains links whose visible text or URL contains terms such as:

- full-year, half-year, interim or annual results
- profit, outlook or guidance
- trading statement, trading update or market update

The first successful set of links for a source establishes a baseline. Later unseen links become review candidates in `data/announcement_review_queue.json`.

## Editorial workflow

1. The weekly GitHub Action runs the monitor and commits newly detected candidates.
2. A reviewer opens the official issuer link and determines whether it meets the profit-warning methodology.
3. Non-qualifying items are marked `dismissed` in the queue with a short review note.
4. Qualifying items are added to `data/profit_warning_sources.json` and marked `promoted` in the queue.
5. The normal data build validates and publishes the approved evidence overlay.

## Publication safeguard

Keyword matching can produce false positives because ordinary results and positive trading updates use the same language as warnings. For that reason, candidates default to `pending` and are never copied automatically into the analytical dataset.

## Validation

The monitor fails before fetching if it finds:

- anything other than exactly 25 configured issuers
- monitor tickers that do not exactly match the verified leadership cohort
- duplicate ticker or review-candidate IDs
- missing company names, tickers, or HTTPS source URLs
- unsupported queue statuses

Individual website failures do not fail the full run. They are recorded as `unavailable` so gaps remain visible.
