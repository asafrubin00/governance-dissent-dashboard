import { Link, Navigate, useParams } from 'react-router-dom'
import { formatDate, formatPercent, formatShortPercent } from '../lib/format'
import type { TrackerData } from '../types'

type ResolutionPageProps = {
  data: TrackerData
}

export function ResolutionPage({ data }: ResolutionPageProps) {
  const params = useParams()
  const resolution = data.resolutions.find((item) => item.id === params.id)

  if (!resolution) {
    return <Navigate to="/dashboard" replace />
  }

  const related = data.resolutions
    .filter(
      (item) =>
        item.companyName === resolution.companyName && item.id !== resolution.id,
    )
    .slice(0, 4)

  return (
    <div className="page-stack">
      <div className="back-link-row">
        <Link className="back-link" to="/dashboard">
          Back to dashboard
        </Link>
      </div>

      <section className="detail-hero panel">
        <p className="eyebrow">Resolution detail</p>
        <h1>{resolution.companyName}</h1>
        <p className="detail-hero__meta">
          {formatDate(resolution.meetingDate)} · {resolution.meetingType} ·{' '}
          {resolution.resolutionCategoryLabel}
        </p>
        <p className="detail-hero__title">{resolution.resolutionTitle}</p>
      </section>

      <section className="detail-grid">
        <article className="panel">
          <div className="panel__header">
            <p className="eyebrow">Voting outcome</p>
            <h2>Resolution metrics</h2>
          </div>
          <div className="detail-metrics">
            <div>
              <span>Votes for</span>
              <strong>{formatPercent(resolution.votesForPct)}</strong>
            </div>
            <div>
              <span>Votes against</span>
              <strong>{formatPercent(resolution.votesAgainstPct)}</strong>
            </div>
            <div>
              <span>Withheld</span>
              <strong>{formatPercent(resolution.votesWithheldPct)}</strong>
            </div>
            <div>
              <span>Issued share capital voted</span>
              <strong>{formatPercent(resolution.issuedShareCapitalVotedPct)}</strong>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <p className="eyebrow">Governance interpretation</p>
            <h2>Why this may matter</h2>
          </div>
          <p>{resolution.governanceNote}</p>
          <div className="detail-tags">
            <span>{resolution.sector}</span>
            <span>{resolution.sourceGroup}</span>
            <span>{formatShortPercent(resolution.votesAgainstPct)} against</span>
          </div>
        </article>
      </section>

      <section className="content-grid">
        <article className="panel">
          <div className="panel__header">
            <p className="eyebrow">Source disclosure</p>
            <h2>Public evidence trail</h2>
          </div>
          <ul className="plain-list">
            <li>
              <a href={resolution.sourceUrl} target="_blank" rel="noreferrer">
                Investment Association Public Register entry
              </a>
            </li>
            {resolution.statementInResultsUrl ? (
              <li>
                <a href={resolution.statementInResultsUrl} target="_blank" rel="noreferrer">
                  AGM or meeting result announcement
                </a>
              </li>
            ) : null}
            {resolution.updateStatementUrl ? (
              <li>
                <a href={resolution.updateStatementUrl} target="_blank" rel="noreferrer">
                  Company follow-up or update statement
                </a>
              </li>
            ) : null}
          </ul>
        </article>

        <article className="panel">
          <div className="panel__header">
            <p className="eyebrow">Related company votes</p>
            <h2>Other dissent at this issuer</h2>
          </div>
          {related.length === 0 ? (
            <p>No other matched dissent cases for this company in the current v1 dataset.</p>
          ) : (
            <div className="ranked-list">
              {related.map((item) => (
                <Link className="ranked-list__item ranked-list__item--link" key={item.id} to={`/resolution/${item.id}`}>
                  <div>
                    <p className="ranked-list__label">{formatDate(item.meetingDate)}</p>
                    <p className="ranked-list__title">{item.resolutionTitle}</p>
                  </div>
                  <strong>{formatShortPercent(item.votesAgainstPct)}</strong>
                </Link>
              ))}
            </div>
          )}
        </article>
      </section>
    </div>
  )
}
