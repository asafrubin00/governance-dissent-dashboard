# PROXY WARS: A FTSE 100 Shareholder Dissent Tracker

A tightly scoped governance portfolio project that tracks significant votes against management at UK AGMs, with a deliberate focus on the kinds of resolutions that matter most in stewardship and corporate governance work: remuneration, director elections, capital authorities, and other notable governance signals.

This is an MVP by design. It aims to be credible, clear, and locally runnable rather than broad, fragile, or over-engineered.

## Preview

The current build uses a two-stage experience:

- a cinematic landing screen first
- one scroll into a fixed-height analytics workspace

Run locally with `npm run dev` to view both the overview and dashboard surfaces as intended.

## What it does

- Ingests real AGM voting outcomes from a free public source.
- Standardises results at resolution level.
- Filters the dataset to matched FTSE 100 companies in scope for v1.
- Highlights significant dissent, especially votes with 20% or more against management.
- Presents a professional public-facing dashboard with charts, filters, and resolution detail pages.
- Adds short governance-oriented commentary so the output reads more like stewardship analysis than generic BI.

## Current v1 scope

- Source: Investment Association Public Register.
- Coverage: matched FTSE 100 companies captured by that source in the current v1 dataset.
- Time horizon: the current build is effectively a 2025 AGM-season tracker because that is what the accessible public register page currently exposes.
- Data shape: 29 real significant dissent resolutions across 24 matched FTSE 100 companies.

## Phase 2 upgrade

The tracker now includes a second source layer:

- `IA Public Register` as the historical significant-dissent base.
- `Official issuer announcement pages and selected issuer-published result PDFs` where vote outcomes can be parsed reliably.

This does two useful things:

- enriches resolution records with full vote counts where issuers disclose them in HTML tables
- adds company-specific PDF result parsing for issuers where official AGM outcomes are published as documents rather than HTML tables
- creates a path to refresh beyond the discontinued IA register by adding issuer announcement seeds over time
- begins a PDF-capable layer for linked company follow-up statements where text extraction is reliable

## Why the scope is narrow

This project deliberately starts from the cleanest free source for UK significant dissent rather than pretending to offer complete FTSE 100 coverage from day one.

That matters because:

- The IA register captures significant votes against management cleanly and at resolution level.
- Free issuer-by-issuer AGM result collection is feasible, but much more fragmented.
- For a recruiter-facing MVP, a narrower real dataset is more credible than fake breadth.

## Data source and governance context

Primary source:

- [Investment Association Public Register](https://www.theia.org/public-register)

Methodology note:

- The IA methodology page explains that the register includes companies where a resolution received 20% or more votes against, or a resolution was withdrawn.
- The IA also states that the Public Register stopped adding new companies or resolutions after the October 2025 policy change, which makes it a strong historical source but not a complete long-run current feed on its own.

## Stack

- Front end: React + TypeScript + Vite
- Routing: React Router
- Charts: Recharts
- Data pipeline: Python with `requests`, `beautifulsoup4`, and `pypdf`
- Storage: in-repo JSON and CSV
- Deployment recommendation: Vercel or Netlify static deployment

## Project structure

```text
.
├── data/
│   ├── company_metadata.json         # curated FTSE 100 company aliases and sectors
│   ├── issuer_source_config.json     # manual issuer source seeds for future expansion
│   └── processed/                    # generated cleaned outputs and source audits
├── docs/
│   └── project-log.md                # assumptions, blockers, tradeoffs
├── public/
│   └── data/
│       └── tracker-data.json         # app-facing generated dataset
├── scripts/
│   └── build_dataset.py              # scraper, verifier, and enrichment pipeline
├── src/
│   ├── components/
│   ├── lib/
│   ├── pages/
│   └── types.ts
└── README.md
```

## Local setup

### 1. Install dependencies

```bash
npm install
python3 -m pip install -r requirements.txt
```

### 2. Build the local dataset

```bash
npm run data
```

This fetches the IA Public Register, parses linked issuer documents where possible, and writes:

- `public/data/tracker-data.json`
- `data/processed/ftse100_resolutions.json`
- `data/processed/ftse100_resolutions.csv`
- `data/processed/unmatched_companies.json`
- `data/processed/issuer_announcement_audit.json`
- `data/processed/issuer_document_audit.json`

### 3. Start the app locally

```bash
npm run dev
```

### 4. Create a production build

```bash
npm run build
```

## How the scraper works

The pipeline is intentionally simple:

1. Fetch the IA Public Register HTML.
2. Parse each server-rendered table and use the table caption as a source group.
3. Read each row into a structured resolution record.
4. Match issuer names to a curated FTSE 100 metadata file using aliases.
5. Collect linked official issuer announcement pages and manual issuer seeds.
6. Parse vote tables from issuer HTML pages to recover full vote counts and official percentages where available.
7. Parse selected official AGM result PDFs with narrow issuer-specific rules where HTML tables are unavailable but text extraction is clean enough to trust.
8. Parse linked PDF follow-up statements where text extraction is reliable enough to generate a board-response summary.
9. Use issuer sources to verify existing IA-linked records and add any additional `20%+` dissent resolutions if found in the same official source layer.
10. Classify each resolution into a governance category using lightweight text rules.
11. Generate a short governance note for the resolution detail view.
12. Export JSON and CSV for local use by the app.

This approach is not meant to be perfect. It is meant to be dependable and transparent.

## Refreshing the data

Current refresh modes:

- `Local manual refresh`: run `npm run data`
- `GitHub Actions refresh`: the repo now includes `.github/workflows/refresh-data.yml`

What that means in practice:

- The app does not refresh itself at runtime.
- The generated JSON changes only when the scraper is run.
- The GitHub Action can be triggered manually, and it is also scheduled weekly.
- PDF parsing is still narrow and issuer-specific. It should be treated as targeted enrichment rather than full market-wide PDF coverage.

Important limitation:

- The IA Public Register stopped adding new cases after October 2025.
- So future meaningful refreshes depend increasingly on extending `data/issuer_source_config.json` and the issuer-announcement parser layer.

## Key governance categories in v1

- Remuneration
- Director election
- Capital authority
- Audit
- Climate and transition
- Shareholder proposal
- Other governance

## What the UI includes

- Homepage with governance framing and headline metrics
- Dashboard page with filters for company, year, sector, and category
- Top dissent chart
- AGM season timeline
- Category breakdown
- Company pattern table
- Resolution detail view with voting outcomes, tags, governance interpretation, and follow-up disclosure summaries where parsed

## Data limitations

- The IA register captures significant dissent, not the full universe of AGM resolutions.
- V1 depends on a curated FTSE 100 alias file rather than a live constituent feed.
- Resolution categories are heuristic and suitable for MVP analysis, not a final research taxonomy.
- The accessible dataset in this build is concentrated in the 2025 AGM season.
- Some issuers outside the alias file remain in `data/processed/unmatched_companies.json`.
- The build includes validation checks for duplicate records, missing company names, missing dates, and out-of-range percentage fields.
- Issuer-announcement enrichment currently covers HTML result pages, a small set of issuer-specific AGM result PDFs, and a narrow set of linked PDF follow-up statements.

## Future improvements

- Extend the issuer-specific PDF result parser layer to more FTSE 100 companies that publish AGM outcomes only as downloadable PDFs.
- Extend `data/issuer_source_config.json` with direct issuer seeds for companies not already linked through the IA register.
- Add issuer pages with multi-resolution histories.
- Add a cleaner FTSE 100 constituent snapshot workflow by year.
- Add simple tests around parsing and classification rules.

## Deployment recommendation

For a portfolio piece, deploy this as a static site:

- Vercel if you want the simplest React deployment flow.
- Netlify if you prefer a very straightforward static-hosting setup.

Because the dataset is generated into `public/data`, the app does not need a runtime backend for v1.

## Notes

- `docs/project-log.md` records assumptions, tradeoffs, and source limitations.
- No placeholder voting data is used.
- No auth, admin, or irrelevant product features are included.

## Verification

The project has been verified locally with:

- `npm run data`
- `npm run build`
