# Proxy Wars

Proxy Wars is a focused FTSE 100 governance research portfolio project. It now contains two connected modules:

- **Leadership Pressure Radar**: a source-backed research preview that prioritises CEO and Chair succession signals.
- **Proxy Voting**: a resolution-level tracker for significant shareholder dissent against management.

The product is intentionally transparent about incomplete coverage. Unresearched leadership records remain visibly unrated, and the voting module covers significant dissent rather than general AGM voting books.

## Preview

![Proxy Wars module overview](docs/screenshots/overview.png)

![Leadership Pressure Radar](docs/screenshots/leadership-radar.png)

## Current coverage

### Leadership Pressure Radar

- Universe: a 100-company FTSE 100 public constituent snapshot.
- Verified cohort: 25 companies with official issuer sources for both CEO and Chair appointments.
- Signals in methodology `v0.3`: role tenure, qualifying registered dissent, source-verified profit-warning evidence, and officially announced live CEO or Chair succession processes.
- All 25 rated companies have received the same 36-month warning review. Four qualifying official issuer events are captured; warning evidence remains outside the score pending calibration and outcome testing.
- All 25 rated companies have also been reviewed for active CEO and Chair succession announcements. One live process is captured in the current evidence window.
- Excluded for now: market-price stress, activism, controversies, and broader news.
- Output: `public/data/leadership-radar.json`.

The score is a research-prioritisation device, not a prediction that an individual will leave office. Full details are in [the radar methodology](docs/leadership-radar-methodology.md).

### Proxy Voting

- 28 real significant-dissent resolutions across 24 matched FTSE 100 issuers in the current dataset.
- Primary layer: [Investment Association Public Register](https://www.theia.org/public-register).
- Verification layer: official issuer announcements and selected issuer-published AGM result PDFs.
- Focus: 20%+ opposition on remuneration, director elections, capital authorities, and other board-accountability resolutions.
- Output: `public/data/tracker-data.json`.

The IA Public Register stopped adding new cases after its October 2025 policy change. It remains useful as a historical base, but future Proxy Voting expansion depends on direct issuer sources.

## Stack

- React 19, TypeScript, and Vite
- React Router
- Recharts for Proxy Voting charts
- Python, Requests, Beautiful Soup, and pypdf for data ingestion
- Static JSON storage in the repository
- Vercel-ready static deployment

## Run locally

```bash
npm install
python3 -m pip install -r requirements.txt
npm run data
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`.

Create a production build with:

```bash
npm run build
```

## Data refresh

`npm run data` performs both builds:

1. Refreshes and verifies the significant-dissent dataset.
2. Fetches the public FTSE 100 roster snapshot, falling back to the cached snapshot if unavailable.
3. Joins the manually verified leadership source file.
4. Validates the 25-company profit-warning review and joins approved official warning evidence.
5. Validates and joins official active-succession evidence.
6. Recalculates role-specific pressure scores without allowing either overlay to change the score.
7. Runs validation before writing the public JSON files.

The GitHub Actions workflow in `.github/workflows/refresh-data.yml` runs weekly and can also be triggered manually. It refreshes calculations and the constituent roster, then checks 25 official issuer pages for new earnings-related links. Matches enter a review queue and never alter the radar automatically. Verified appointments, qualifying warning events, and active succession cases must still be approved in their source files before publication.

Run the monitor independently with `npm run data:monitor`. Its source health and editorial safeguards are explained in [the monitor methodology](docs/announcement-monitor-methodology.md).

## Project structure

```text
data/
  leadership_sources.json          # manually verified leadership evidence
  profit_warning_sources.json      # curated official warning events
  profit_warning_reviews.json      # 25-company review outcomes and sources
  succession_sources.json          # official active-succession evidence
  announcement_monitor_sources.json # official issuer monitoring configuration
  announcement_monitor_snapshot.json # previously seen announcement links
  announcement_review_queue.json  # candidates awaiting editorial review
  ftse100_constituents.json        # generated public roster snapshot
  company_metadata.json            # Proxy Voting issuer aliases
  issuer_source_config.json        # direct voting-source seeds
docs/
  leadership-radar-methodology.md
  announcement-monitor-methodology.md
  project-log.md
public/data/
  leadership-radar.json
  tracker-data.json
scripts/
  build_leadership_radar.py
  build_dataset.py
src/
  pages/LeadershipRadarPage.tsx
  pages/DashboardPage.tsx
```

## Analytical limitations

- Twenty-five companies are rated; the other 75 remain visibly unrated until both leadership roles are verified.
- CEO tenure has no formal UK governance limit; the ten-year horizon is an analytical reference only.
- Chair tenure is interpreted in the context of the Code's nine-year independence and succession guidance.
- The dissent uplift is based on a narrow 2025 source window, not complete historical voting coverage.
- The profit-warning audit applies a consistent definition, but issuer archive structures and disclosure language still create residual discovery risk.
- Warning and succession evidence are excluded from the score pending calibration and outcome testing.
- A public constituent table is used for reproducibility and is not an official FTSE Russell feed.
- Classification and parsing rules remain suitable for a portfolio MVP, not a commercial proxy-research service.

## Product roadmap

- Improve monitor coverage where official sites currently block automated access or render no usable links.
- Add compact company logos to heatmap tiles and the evidence rail using issuer-approved assets, with a text fallback and no analytical effect.
- Add concise leader profiles and tenure-aligned share-price/TSR analysis in staged releases.
- Evaluate warning and succession score contributions only after back-testing, sensitivity analysis, and a documented governance rationale.

## Verification

The current build is checked with:

```bash
npm run data:radar
npm run lint
npm run build
```
