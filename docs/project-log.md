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
- Phase 2 now parses official HTML issuer announcement pages where available, but PDF-only AGM result announcements remain outside the live parser layer.
- A narrow PDF layer now parses linked follow-up statement PDFs where text extraction is reliable, but that is not yet a general poll-result PDF parser.

## Tradeoffs made

- Chose a static React app with in-repo JSON over a database-backed app to keep local setup simple and recruiter-friendly.
- Chose a Python scraper over a browser-based ingestion flow because the source HTML is tabular and easier to parse reliably with a small script.
- Kept the UX focused on homepage, dashboard, and resolution detail rather than adding maps, accounts, or advanced export tools.
- Used a curated FTSE 100 company metadata file for the companies covered in v1 rather than trying to automate constituent classification from unstable free sources.
- For Phase 2, used issuer-linked HTML announcement pages as the second source layer before attempting any PDF extraction or market-wide discovery crawler.
- Added a lightweight PDF text-extraction step only for linked follow-up statements, so the first PDF capability improves disclosure context without pretending to solve all PDF result formats.

## Blockers and pivots

- If the Public Register structure changes, the next-best realistic source remains direct company AGM poll result announcements or FCA/LSEG-hosted meeting result pages.
- The current issuer-announcement layer works best on HTML tables. PDF-only result packs still need a separate extraction pass if broader current coverage becomes a priority.
- The current PDF layer is intentionally narrow and should next be extended issuer-by-issuer rather than generalized all at once.
- If future public coverage is needed beyond the discontinued register window, the next evolution should be:
  1. maintain a small issuer source-config file
  2. expand HTML parsing coverage
  3. add PDF parsing only for high-value issuers where HTML is unavailable
