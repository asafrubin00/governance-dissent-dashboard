import { Link, useOutletContext } from 'react-router-dom'
import { InfoHint } from '../components/InfoHint'
import { StatCard } from '../components/StatCard'
import { getRecentHighlights, getTopDissent } from '../lib/analytics'
import { formatDate, formatShortPercent } from '../lib/format'
import type { TrackerData } from '../types'

type HomePageProps = {
  data: TrackerData
}

export function HomePage({ data }: HomePageProps) {
  const { generatedAt } = useOutletContext<{ generatedAt: string }>()
  const highlights = getRecentHighlights(data.resolutions, 4)
  const topDissent = getTopDissent(data.resolutions, 3)
  const { summary, coveragePeriod, methodology } = data.metadata

  return (
    <div className="page-flow">
      <section className="hero-screen hero-screen--cover">
        <div className="hero-screen__overlay" />
        <div className="hero-screen__hint" aria-hidden="true">
          <span />
          <span />
        </div>
      </section>

      <section className="workspace-screen workspace-screen--overview">
        <div className="workspace-overview">
          <div className="workspace-overview__left">
            <section className="workspace-copy">
              <h2 className="workspace-copy__title">
                Significant shareholder dissent, not general AGM voting coverage
              </h2>
              <p className="workspace-copy__body">
                A narrow governance tracker focused on resolutions where opposition to
                management reached a level that matters in UK stewardship practice.
              </p>
            </section>

            <section className="workspace-scope">
              <div className="section-heading">
                <h3>Analytical scope</h3>
                <InfoHint
                  label="Analytical scope note"
                  content="This tracker follows significant shareholder dissent only. It excludes routine AGM resolutions and does not attempt to reproduce full meeting voting books."
                />
              </div>
              <p className="workspace-scope__text">{data.metadata.coverageStatement}</p>
              <p className="workspace-scope__text workspace-scope__text--strong">
                {methodology.sourceCredibilityNote}
              </p>
            </section>

            <section className="workspace-summary">
              <div className="section-heading">
                <h3>Coverage summary</h3>
                <InfoHint
                  label="Coverage summary note"
                  content="Coverage reflects the matched FTSE 100 subset of the IA Public Register visible in the generated local dataset."
                />
              </div>
              <div className="workspace-summary__grid">
                <StatCard
                  compact
                  label="Companies represented"
                  value={String(summary.companyCount)}
                  note="Matched FTSE 100 issuers in the current build."
                />
                <StatCard
                  compact
                  label="Dissent resolutions captured"
                  value={String(summary.resolutionCount)}
                  note="Significant dissent records only."
                />
                <StatCard
                  compact
                  label="Period covered"
                  value={
                    coveragePeriod.startDate && coveragePeriod.endDate
                      ? `${formatDate(coveragePeriod.startDate)} - ${formatDate(
                          coveragePeriod.endDate,
                        )}`
                      : 'n/a'
                  }
                  note="Current visible date span from the source-backed dataset."
                />
                <StatCard
                  compact
                  label="Primary source"
                  value="Investment Association Public Register"
                  note="A UK governance source focused on votes against management."
                />
              </div>
            </section>
          </div>

          <div className="workspace-overview__right">
            <article className="workspace-panel">
              <p className="workspace-panel__eyebrow">Governance framing</p>
              <h3>Why the 20% threshold matters</h3>
              <ul className="workspace-panel__list">
                <li>
                  In the UK market, 20% or more against management is widely treated as a
                  significant dissent signal.
                </li>
                <li>
                  It matters most on remuneration, director elections, and other
                  board-accountability items.
                </li>
              </ul>
            </article>

            <article className="workspace-panel">
              <p className="workspace-panel__eyebrow">Recent highlights</p>
              <h3>Latest notable cases in scope</h3>
              <div className="workspace-mini-list">
                {highlights.slice(0, 2).map((item) => (
                  <Link
                    className="workspace-mini-list__item"
                    key={item.id}
                    to={`/resolution/${item.id}`}
                  >
                    <span>{item.companyName}</span>
                    <strong>{formatShortPercent(item.votesAgainstPct)}</strong>
                  </Link>
                ))}
              </div>
            </article>

            <article className="workspace-panel">
              <p className="workspace-panel__eyebrow">Top dissent</p>
              <h3>Strongest opposition in the dataset</h3>
              <div className="workspace-mini-list">
                {topDissent.slice(0, 2).map((item) => (
                  <Link
                    className="workspace-mini-list__item workspace-mini-list__item--stacked"
                    key={item.id}
                    to={`/resolution/${item.id}`}
                  >
                    <span>{item.companyName}</span>
                    <small>{item.resolutionTitle}</small>
                  </Link>
                ))}
              </div>
            </article>

            <article className="workspace-panel">
              <p className="workspace-panel__eyebrow">Method & coverage</p>
              <h3>Included and excluded on purpose</h3>
              <ul className="workspace-panel__list workspace-panel__list--dense">
                {methodology.included.slice(0, 2).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="workspace-panel__subhead">Excluded</p>
              <ul className="workspace-panel__list workspace-panel__list--dense">
                {methodology.excluded.slice(0, 2).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </div>
        </div>

        <div className="workspace-micro-note">
          <span>Generated {new Date(generatedAt).toLocaleDateString('en-GB')}</span>
          <span>Significant shareholder dissent only</span>
        </div>
      </section>
    </div>
  )
}
