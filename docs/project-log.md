# Project log

## Assumptions

- V1 should privilege credibility and governance relevance over full FTSE 100 completeness.
- The cleanest free public starting point is the Investment Association Public Register because it already captures significant votes against management and links back to company results.
- A narrower but real dataset is better than claiming complete FTSE 100 coverage when free source quality varies by issuer.

## Data-source limitations

- The Public Register captures significant dissent and withdrawn resolutions, not the full universe of AGM resolutions.
- The Investment Association states that it stopped adding new resolutions or companies to the Public Register after the October 2025 policy change, so v1 is strongest as a historical tracker rather than a fully current monitoring product.
- Company names in the source use issuer formatting conventions, so FTSE 100 matching relies on a maintained alias file.
- Category tagging is rules-based and therefore suitable for an MVP, but not equivalent to a hand-reviewed governance taxonomy.
- Validation checks now cover duplicate records, missing company names, missing dates, and out-of-range percentage fields.
- Phase 2 now parses official HTML issuer announcement pages where available and a small set of issuer-specific AGM result PDFs where text extraction is clean enough to trust.
- A narrow PDF layer also parses linked follow-up statement PDFs where text extraction is reliable, but this is still not a general poll-result PDF parser.

## Tradeoffs made

- Chose a static React app with in-repo JSON over a database-backed app to keep local setup simple and recruiter-friendly.
- Chose a Python scraper over a browser-based ingestion flow because the source HTML is tabular and easier to parse reliably with a small script.
- Kept the UX focused on homepage, dashboard, and resolution detail rather than adding maps, accounts, or advanced export tools.
- Used a curated FTSE 100 company metadata file for the companies covered in v1 rather than trying to automate constituent classification from unstable free sources.
- For Phase 2, used issuer-linked HTML announcement pages as the second source layer before adding narrowly scoped PDF result parsing for a few high-value issuers.
- Kept PDF parsing issuer-specific rather than generic, so the pipeline can verify more real cases without pretending to solve every AGM result format at once.

## Blockers and pivots

- If the Public Register structure changes, the next-best realistic source remains direct company AGM poll result announcements or FCA/LSEG-hosted meeting result pages.
- The current issuer-announcement layer works best on HTML tables. PDF result coverage is improving, but still depends on issuer-specific parsing rules.
- The current PDF layer is intentionally narrow and should next be extended issuer-by-issuer rather than generalized all at once.
- If future public coverage is needed beyond the discontinued register window, the next evolution should be:
  1. maintain a small issuer source-config file
  2. expand HTML parsing coverage
  3. add PDF parsing only for high-value issuers where HTML is unavailable

## Leadership Pressure Radar v0.1

### Assumptions

- The first leadership release should prioritise transparent evidence over nominal FTSE 100 score coverage.
- A leadership pressure score is useful as a research queue, but must not be described as a probability of departure.
- CEO and Chair tenure require different governance framing because the CEO role has no formal UK tenure limit while the Code gives a nine-year reference point for Chair independence and succession.

### Coverage decision

- The interface carries a 100-company public constituent snapshot.
- Twenty-five companies are rated from official issuer leadership sources.
- The remaining 75 companies are explicitly marked `Unrated` rather than receiving inferred leaders, dates, or scores.

### Data-quality decision

- Shareholder proposals and shareholder-requisitioned resolutions are excluded from the leadership radar's dissent uplift.
- This avoids misclassifying votes against a shareholder proposal as opposition to management when the board recommended voting against it.
- Missing dissent in the narrow tracker window is not presented as evidence of zero dissent.

### Deferred signals

- Profit warnings, share-price stress, activism, controversies, and general news are deferred until each signal has a stable definition, primary source, lookback window, and validation rule.

## Leadership Pressure Radar cohort expansion

### Coverage decision

- Expanded the source-verified cohort from 8 to 25 current FTSE 100 constituents.
- Selected companies against the current public constituent snapshot rather than retaining former constituents simply because they appear in the Proxy Voting dataset.
- Retained 75 companies as explicitly `Unrated`; no leadership identities or dates were inferred.

### Evidence decision

- Verified both CEO and Chair incumbents and role-start dates from official issuer announcements, board profiles, AGM materials, or annual reports.
- Used 6 August 2026 as a fixed evidence cutoff and incorporated recent successions at HSBC, BP, Convatec, Rentokil Initial, Melrose Industries, and National Grid.
- Kept Kingfisher's announced CEO transition tied to the incumbent who remained in office at the evidence cutoff.

### Methodology decision

- Left methodology `v0.1` and all score weights unchanged so the expanded cohort is comparable with the first release.

## Profit-warning evidence overlay v0.2

### Scope decision

- Added a 36-month source-backed overlay for explicit full-year guidance cuts and quantified material prospective profit impacts.
- Included three high-confidence official issuer events: Rentokil Initial, Marks & Spencer, and Kingfisher.
- Excluded ambiguous trading commentary, routine earnings misses, and operating-metric revisions without a clear profit implication.

### Score decision

- Kept the pressure-score weights unchanged until the same warning research protocol covers the full verified cohort.
- Added visible warning markers and source-linked evidence without treating uncaptured events as evidence of absence.

### Refresh decision

- The weekly build now validates and republishes the curated warning file automatically.
- New-event discovery remains editorially verified; automated issuer monitoring should create a review queue rather than publishing matches directly.

### Presentation roadmap

- Add small issuer-approved company logos to heatmap tiles and the selected-company rail after the analytical layers stabilise.
- Logos will use a text fallback and will never affect scoring.

## Official issuer announcement monitor

### Automation decision

- Added a weekly review-first monitor for all 25 companies in the verified leadership cohort.
- New earnings-related links are written to an editorial queue and never published as profit-warning evidence automatically.
- The first baseline recorded 15 reachable issuer pages, seven active monitor sources, and ten unavailable sources.

### Integrity decision

- Source health distinguishes active pages, reachable pages with no monitorable matches, and unavailable pages.
- A newly reachable source establishes a baseline before generating candidates, preventing a full historic archive from flooding the queue.
- The monitor validates exact cohort alignment, unique candidate IDs, HTTPS source URLs, and review statuses.

## Evidence audit and active succession overlay v0.3

### Warning audit decision

- Applied one explicit 36-month review protocol to all 25 companies in the source-verified cohort.
- Captured four qualifying official issuer events: Marks & Spencer, Computacenter, Rentokil Initial, and Kingfisher.
- Recorded a source and review outcome for every company, including transparent exclusions for operating-metric, production, cost, and segment-level changes that did not meet the Group earnings definition.
- Kept warnings outside the score pending calibration and outcome testing; complete review coverage does not by itself justify a weighting.

### Succession decision

- Reviewed the same 25-company cohort for official active CEO and Chair succession announcements.
- Captured Kingfisher's active CEO search and linked the official directorate-change announcement.
- Excluded informal speculation, generic succession-planning language, completed appointments, and governance-relevant tenure extensions where no active process was announced.
- Added exact-cohort, incumbent, role, status, date, and source validation while leaving the pressure score unchanged.

### Monitor improvement

- Repointed six issuer configurations to more stable official results or announcement hubs.
- Increased active monitor coverage from seven to 11 sources; 15 remain reachable and ten unavailable to the automated fetcher.
- Re-established the monitor baseline without creating retrospective review noise.

## Leadership cohort and succession monitor v0.4

### Coverage decision

- Expanded the source-verified CEO and Chair cohort from 25 to 50 current FTSE 100 constituents.
- Selected the additional companies for sector breadth and accessible official appointment evidence; the remaining 50 stay visibly unrated.
- Preserved every existing score weight and calculation rule, so the release changes evidence coverage rather than methodology economics.
- Kept the completed warning-history audit explicitly at 25 companies instead of implying that leadership verification also completed profit-warning research.

### Live succession decision

- Reviewed all 50 rated companies for active official CEO and Chair transition announcements to 8 August 2026.
- Added live CEO cases for Babcock International, Barratt Redrow, and British Land, plus Chair cases for British American Tobacco and Burberry; Kingfisher remains active.
- Recorded named successors and exact dates where disclosed, while retaining null dates where issuers stated only a quarter, year-end, or results-event trigger.

### Automation decision

- Expanded the weekly monitor from 25 to 50 official issuer sources and removed the hard-coded cohort size.
- Split monitor terms into `earnings` and `succession` groups so candidates carry their review purpose.
- Baselined existing links before monitoring; the first normal run reached 39 sources, found monitorable links on 22, and created no retrospective candidates.

## Full leadership universe and performance pilot

### Coverage decision

- Completed source verification for all 100 current roster constituents; 94 have scoreable CEO and Chair pairs.
- Marked six externally managed issuers as CEO `Not applicable` rather than treating a structural absence as missing research.
- Expanded the profit-warning audit to 50 companies, capturing 11 qualifying official events across nine issuers.
- Reviewed all 100 companies for active official succession evidence and added JD Sports' interim-Chair search as the seventh live case.

### Performance and profile decision

- Added a ten-company monthly performance pilot using public Yahoo chart data: unadjusted close for share-price return and adjusted close for a clearly qualified dividend-adjusted return proxy.
- Added the FTSE 100 price index as context and kept the feature in an on-demand modal so the fixed-height research workspace remains intact.
- Added concise official-source CEO and Chair profiles for the same ten companies, with cached issuer assets only where stable and initials fallbacks elsewhere.

### Automation and validation

- Expanded the weekly announcement monitor to 100 official issuer sources; the new baseline reached 75 pages and found monitorable matches on 48 without creating retrospective queue noise.
- Added exact roster alignment, future-date, HTTPS-source, structural-not-applicable, market-series, duplicate-date, and cross-pilot reconciliation checks.
- Kept warning, succession, profile, and market evidence outside the leadership pressure score pending calibration and outcome testing.
