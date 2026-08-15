import { Link, useOutletContext } from 'react-router-dom'
import { LegalLine } from '../components/LegalLine'
import type { LeadershipRadarData, TrackerData } from '../types'

type HomePageProps = {
  data: TrackerData
  radarData: LeadershipRadarData
}

export function HomePage({ data, radarData }: HomePageProps) {
  const { generatedAt } = useOutletContext<{ generatedAt: string }>()

  return (
    <div className="page-flow">
      <section className="workspace-screen workspace-screen--overview" id="workspace">
        <div className="module-overview">
          <header className="module-overview__intro">
            <p className="workspace-panel__eyebrow">FTSE 100 governance intelligence</p>
            <h2>Signals that merit closer board and stewardship attention</h2>
            <p>
              Proxy Wars brings leadership transition pressure and significant shareholder
              dissent into one deliberately transparent research workspace.
            </p>
          </header>

          <div className="module-overview__grid">
            <Link className="module-card module-card--primary" to="/radar">
              <div className="module-card__topline">
                <span>01 / Governance radar</span>
                <strong>Main workspace</strong>
              </div>
              <div>
                <p className="module-card__eyebrow">Integrated governance radar</p>
                <h3>Where leadership and stewardship signals concentrate</h3>
                <p className="module-card__copy">
                  Compare CEO and Chair pressure across the FTSE 100, then switch to a
                  voting lens without leaving the company-level research workspace.
                </p>
                <div className="module-card__signal-list">
                  <span><i>01</i> CEO tenure reference horizon</span>
                  <span><i>02</i> Chair nine-year Code reference</span>
                  <span><i>03</i> Registered management-resolution dissent</span>
                </div>
              </div>
              <div className="module-card__metrics">
                <span><strong>{radarData.metadata.ratedCompanyCount}</strong> rated</span>
                <span><strong>{radarData.metadata.constituentCount}</strong> in universe</span>
                <span><strong>2</strong> role views</span>
              </div>
              <span className="module-card__action">Enter governance radar</span>
            </Link>

            <Link className="module-card" to="/proxy-voting">
              <div className="module-card__topline">
                <span>02 / Evidence</span>
                <strong>Supporting workspace</strong>
              </div>
              <div>
                <p className="module-card__eyebrow">Vote Explorer</p>
                <h3>Inspect significant dissent at resolution level</h3>
                <p className="module-card__copy">
                  Explore verified 20%+ votes on remuneration, elections, capital
                  authorities, and other board-accountability resolutions.
                </p>
                <div className="module-card__signal-list">
                  <span><i>01</i> Significant 20%+ opposition</span>
                  <span><i>02</i> Resolution-level governance taxonomy</span>
                  <span><i>03</i> Official issuer verification layer</span>
                </div>
              </div>
              <div className="module-card__metrics">
                <span><strong>{data.metadata.summary.companyCount}</strong> companies</span>
                <span><strong>{data.metadata.summary.resolutionCount}</strong> resolutions</span>
                <span><strong>20%+</strong> threshold</span>
              </div>
              <span className="module-card__action">Open Vote Explorer</span>
            </Link>
          </div>

          <div className="module-overview__principles">
            <div><span>Evidence first</span><p>Official issuer sources underpin every rated leadership record.</p></div>
            <div><span>Analytically honest</span><p>Unresearched companies remain unrated rather than receiving inferred scores.</p></div>
            <div><span>Decision useful</span><p>Scores prioritise research; they do not predict individual departures.</p></div>
          </div>
        </div>

        <div className="workspace-micro-note">
          <span>Generated {new Date(generatedAt).toLocaleDateString('en-GB')}</span>
          <LegalLine />
          <span>FTSE 100 governance research</span>
        </div>
      </section>
    </div>
  )
}
