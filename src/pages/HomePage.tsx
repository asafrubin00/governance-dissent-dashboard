import { Link } from 'react-router-dom'
import { StatCard } from '../components/StatCard'
import { getRecentHighlights, getTopDissent } from '../lib/analytics'
import { formatDate, formatShortPercent } from '../lib/format'
import type { TrackerData } from '../types'

type HomePageProps = {
  data: TrackerData
}

export function HomePage({ data }: HomePageProps) {
  const highlights = getRecentHighlights(data.resolutions, 4)
  const topDissent = getTopDissent(data.resolutions, 3)
  const { summary, coveragePeriod, methodology } = data.metadata

  return (
    <div className="page-stack">
      <section className="hero-panel hero-panel--home">
        <div className="hero-panel__main">
          <p className="eyebrow">UK governance and stewardship</p>
          <h1>Tracking significant shareholder dissent across the FTSE 100</h1>
          <p className="lede">
            This portfolio project focuses on one narrow but meaningful governance signal:
            shareholder dissent at AGMs, especially where 20% or more of votes are cast
            against management. In UK governance practice, that level of opposition is a
            serious prompt for board engagement and explanation.
          </p>
          <div className="hero-panel__actions">
            <Link className="primary-button" to="/dashboard">
              Open dashboard
            </Link>
          </div>
        </div>
        <div className="hero-panel__aside hero-panel__aside--note">
          <p className="callout-title">Analytical scope</p>
          <p className="callout-copy">
            A significant-dissent tracker, not a general AGM voting database. It only
            includes real high-salience dissent cases from the Investment Association
            Public Register that could be matched confidently to FTSE 100 issuers.
          </p>
          <p className="callout-caption">
            The intent is to surface governance signalling, not to recreate full meeting
            registers.
          </p>
        </div>
      </section>

      <section className="stats-grid stats-grid--summary">
        <StatCard
          label="FTSE 100 companies in v1"
          value={String(summary.companyCount)}
          note="Matched to a curated issuer list for the 2025 AGM season."
        />
        <StatCard
          label="Significant dissent resolutions"
          value={String(summary.resolutionCount)}
          note="All records are real public cases sourced from the IA register."
        />
        <StatCard
          label="Remuneration cases"
          value={String(summary.remunerationCount)}
          note="Pay remains the single biggest theme in the current v1 dataset."
        />
        <StatCard
          label="Highest vote against"
          value={formatShortPercent(summary.highestVotesAgainstPct)}
          note="Useful for highlighting where dissent moved from notable to severe."
        />
      </section>

      <section className="panel panel--coverage">
        <div className="panel__header">
          <p className="eyebrow">Coverage summary</p>
          <h2>Exactly what is in scope</h2>
        </div>
        <div className="coverage-grid">
          <div className="coverage-item">
            <span>Companies represented</span>
            <strong>{summary.companyCount}</strong>
          </div>
          <div className="coverage-item">
            <span>Dissent resolutions captured</span>
            <strong>{summary.resolutionCount}</strong>
          </div>
          <div className="coverage-item">
            <span>Period covered</span>
            <strong>
              {coveragePeriod.startDate ? formatDate(coveragePeriod.startDate) : 'n/a'} to{' '}
              {coveragePeriod.endDate ? formatDate(coveragePeriod.endDate) : 'n/a'}
            </strong>
          </div>
          <div className="coverage-item">
            <span>Primary source</span>
            <strong>{data.metadata.sourceName}</strong>
          </div>
        </div>
      </section>

      <section className="content-grid content-grid--editorial">
        <article className="panel panel--essay">
          <div className="panel__header">
            <p className="eyebrow">Governance framing</p>
            <h2>Why the 20% threshold matters</h2>
          </div>
          <p>
            In the UK market, a vote against of 20% or more is typically treated as a
            significant signal of shareholder dissatisfaction. It is especially relevant
            on remuneration resolutions, director elections, and other board-accountability
            items, because it can point to concerns around judgement, alignment, or
            responsiveness to investors.
          </p>
          <p>
            This tracker is designed to feel closer to stewardship analysis than a generic
            BI dashboard: it highlights where dissent clusters, which governance themes
            recur, and where boards may have faced reputational or accountability pressure.
          </p>
        </article>

        <article className="panel panel--highlights">
          <div className="panel__header">
            <p className="eyebrow">Recent highlights</p>
            <h2>Latest notable cases in scope</h2>
          </div>
          <div className="highlight-list">
            {highlights.map((item) => (
              <Link className="highlight-card" key={item.id} to={`/resolution/${item.id}`}>
                <p className="highlight-card__meta">
                  {item.companyName} · {formatDate(item.meetingDate)}
                </p>
                <h3>{item.resolutionTitle}</h3>
                <p className="highlight-card__metric">
                  {formatShortPercent(item.votesAgainstPct)} voted against
                </p>
              </Link>
            ))}
          </div>
        </article>
      </section>

      <section className="content-grid content-grid--editorial-lower">
        <article className="panel panel--rankings">
          <div className="panel__header">
            <p className="eyebrow">Top dissent</p>
            <h2>Strongest opposition in the current dataset</h2>
          </div>
          <div className="ranked-list">
            {topDissent.map((item) => (
              <div className="ranked-list__item" key={item.id}>
                <div>
                  <p className="ranked-list__label">{item.companyName}</p>
                  <p className="ranked-list__title">{item.resolutionTitle}</p>
                </div>
                <strong>{formatShortPercent(item.votesAgainstPct)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel panel--method">
          <div className="panel__header">
            <p className="eyebrow">Method and coverage</p>
            <h2>Included and excluded on purpose</h2>
          </div>
          <p>{data.metadata.focusStatement}</p>
          <ul className="plain-list">
            {methodology.included.slice(0, 2).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="panel__intro">Excluded:</p>
          <ul className="plain-list">
            {methodology.excluded.slice(0, 2).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </section>
    </div>
  )
}
