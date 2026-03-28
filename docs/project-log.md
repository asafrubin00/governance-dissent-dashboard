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

## Tradeoffs made

- Chose a static React app with in-repo JSON over a database-backed app to keep local setup simple and recruiter-friendly.
- Chose a Python scraper over a browser-based ingestion flow because the source HTML is tabular and easier to parse reliably with a small script.
- Kept the UX focused on homepage, dashboard, and resolution detail rather than adding maps, accounts, or advanced export tools.
- Used a curated FTSE 100 company metadata file for the companies covered in v1 rather than trying to automate constituent classification from unstable free sources.

## Blockers and pivots

- If the Public Register structure changes, the next-best realistic source for extension is direct company AGM poll result announcements or LSEG RNS pages linked from the register.
- If future public coverage is needed beyond the discontinued register window, the scraper should evolve into a two-stage pipeline:
  1. discover meeting result announcements by issuer
  2. parse issuer-specific result pages or PDFs
