import { useEffect, useMemo, useState } from 'react'
import type { LeadershipRadarData } from '../types'

type LeadershipRadarPageProps = {
  data: LeadershipRadarData
}

type RoleKey = 'ceo' | 'chair'
type UniverseKey = 'rated' | 'full'

const bandOrder = ['Acute', 'Elevated', 'Watch', 'Lower', 'Unrated']

function bandClass(band: string) {
  return `heat-tile--${band.toLowerCase()}`
}

function formatRole(role: RoleKey) {
  return role === 'ceo' ? 'CEO' : 'Chair'
}

export function LeadershipRadarPage({ data }: LeadershipRadarPageProps) {
  const [role, setRole] = useState<RoleKey>('ceo')
  const [universe, setUniverse] = useState<UniverseKey>('rated')
  const [sector, setSector] = useState('All sectors')
  const [band, setBand] = useState('All bands')
  const [selectedTicker, setSelectedTicker] = useState('NXT')

  useEffect(() => {
    if (window.location.hash === '#workspace') {
      const previousBehavior = document.documentElement.style.scrollBehavior
      document.documentElement.style.scrollBehavior = 'auto'
      document.getElementById('workspace')?.scrollIntoView()
      requestAnimationFrame(() => {
        document.documentElement.style.scrollBehavior = previousBehavior
      })
    }
  }, [])

  const sectors = useMemo(
    () => ['All sectors', ...Array.from(new Set(data.companies.map((item) => item.sector))).sort()],
    [data.companies],
  )

  const visibleCompanies = useMemo(() => {
    return data.companies
      .filter((company) => universe === 'full' || company.roles[role].rated)
      .filter((company) => sector === 'All sectors' || company.sector === sector)
      .filter((company) => band === 'All bands' || company.roles[role].band === band)
      .sort((a, b) => (b.roles[role].score ?? -1) - (a.roles[role].score ?? -1))
  }, [band, data.companies, role, sector, universe])

  const ratedVisible = visibleCompanies.filter((company) => company.roles[role].rated)
  const averageScore = ratedVisible.length
    ? ratedVisible.reduce((total, company) => total + (company.roles[role].score ?? 0), 0) /
      ratedVisible.length
    : 0
  const acuteCount = ratedVisible.filter((company) => company.roles[role].band === 'Acute').length
  const warningCount = visibleCompanies.reduce(
    (total, company) => total + company.profitWarningEvidence.count,
    0,
  )
  const selected =
    data.companies.find((company) => company.ticker === selectedTicker) ?? visibleCompanies[0]
  const selectedRole = selected?.roles[role]

  function resetFilters() {
    setSector('All sectors')
    setBand('All bands')
    setUniverse('rated')
  }

  function switchRole(nextRole: RoleKey) {
    setRole(nextRole)
    const current = data.companies.find((company) => company.ticker === selectedTicker)
    if (!current?.roles[nextRole].rated) {
      const firstRated = data.companies.find((company) => company.roles[nextRole].rated)
      if (firstRated) setSelectedTicker(firstRated.ticker)
    }
  }

  return (
    <div className="page-flow">
      <section className="hero-screen hero-screen--cover">
        <div className="hero-screen__overlay" />
        <div className="hero-screen__hint" aria-hidden="true"><span /><span /></div>
      </section>

      <section className="workspace-screen workspace-screen--radar" id="workspace">
        <div className="radar-workspace">
          <div className="radar-controls">
            <fieldset className="segmented-control">
              <legend>Role</legend>
              <button className={role === 'ceo' ? 'is-active' : ''} onClick={() => switchRole('ceo')} type="button">CEO</button>
              <button className={role === 'chair' ? 'is-active' : ''} onClick={() => switchRole('chair')} type="button">Chair</button>
            </fieldset>
            <fieldset className="segmented-control">
              <legend>Universe</legend>
              <button className={universe === 'rated' ? 'is-active' : ''} onClick={() => setUniverse('rated')} type="button">Verified cohort</button>
              <button className={universe === 'full' ? 'is-active' : ''} onClick={() => setUniverse('full')} type="button">Full FTSE 100</button>
            </fieldset>
            <label className="radar-select"><span>Sector</span><select value={sector} onChange={(event) => setSector(event.target.value)}>{sectors.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label className="radar-select"><span>Pressure band</span><select value={band} onChange={(event) => setBand(event.target.value)}><option>All bands</option>{bandOrder.map((item) => <option key={item}>{item}</option>)}</select></label>
          </div>

          <div className="radar-headline">
            <div><span>Leadership pressure radar</span><strong>{formatRole(role)} transition signals</strong></div>
            <p>Research prioritisation, not a departure forecast. Select a tile to inspect its evidence.</p>
            <div className="radar-legend" aria-label="Pressure bands">{bandOrder.map((item) => <span key={item}><i className={bandClass(item)} />{item}</span>)}</div>
          </div>

          <div className="radar-kpis">
            <div><span>Rated in view</span><strong>{ratedVisible.length}</strong></div>
            <div><span>Average pressure</span><strong>{averageScore.toFixed(0)}</strong></div>
            <div><span>Acute / warning signals</span><strong>{acuteCount} / {warningCount}</strong></div>
            <div><span>Evidence date</span><strong>{new Date(data.metadata.asOfDate).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}</strong></div>
          </div>

          <div className="radar-main-row">
            <section className="radar-map-panel">
              <div className="radar-map-panel__heading">
                <div><p>FTSE 100 leadership map</p><h2>{universe === 'rated' ? 'Source-verified cohort' : 'Full constituent research queue'}</h2></div>
                <span>{visibleCompanies.length} companies shown</span>
              </div>
              <div className={`heat-map ${universe === 'full' ? 'heat-map--full' : 'heat-map--pilot'}`}>
                {visibleCompanies.map((company) => {
                  const roleData = company.roles[role]
                  return (
                    <button
                      aria-label={`${company.companyName}: ${roleData.rated ? `${roleData.score} ${roleData.band}` : 'unrated'}`}
                      className={`heat-tile ${bandClass(roleData.band)} ${selected?.ticker === company.ticker ? 'is-selected' : ''}`}
                      key={company.ticker}
                      onClick={() => setSelectedTicker(company.ticker)}
                      type="button"
                    >
                      <span>{company.ticker}</span>
                      <small>{universe === 'rated' ? company.companyName : roleData.rated ? roleData.band : 'Pending'}</small>
                      <strong>{roleData.score?.toFixed(0) ?? '—'}</strong>
                      {company.profitWarningEvidence.count ? <i className="heat-tile__warning" title={`${company.profitWarningEvidence.count} qualifying warning event${company.profitWarningEvidence.count === 1 ? '' : 's'} captured`}>PW</i> : null}
                    </button>
                  )
                })}
                {!visibleCompanies.length ? <p className="heat-map__empty">No companies match these filters.</p> : null}
              </div>
            </section>

            <aside className="evidence-rail">
              {selected && selectedRole ? (
                <>
                  <div className="evidence-rail__header">
                    <div><p>{selected.ticker} / {formatRole(role)}</p><h2>{selected.companyName}</h2></div>
                    <span className={bandClass(selectedRole.band)}>{selectedRole.band}</span>
                  </div>
                  {selectedRole.rated ? (
                    <>
                      <div className="evidence-rail__score"><strong>{selectedRole.score?.toFixed(0)}</strong><span>pressure score<br />out of 100</span></div>
                      <dl className="evidence-rail__facts">
                        <div><dt>Role holder</dt><dd>{selectedRole.name}</dd></div>
                        <div><dt>Tenure</dt><dd>{selectedRole.tenureYears?.toFixed(1)} years</dd></div>
                        <div><dt>Tenure pressure</dt><dd>{selectedRole.components?.tenurePressure.toFixed(0)} pts</dd></div>
                        <div><dt>Dissent uplift</dt><dd>+{selectedRole.components?.registeredDissentUplift.toFixed(0)} pts</dd></div>
                      </dl>
                      <p className="evidence-rail__readout">{selectedRole.reason}</p>
                      <a className="evidence-rail__source" href={selectedRole.sourceUrl} target="_blank" rel="noreferrer">View primary leadership source ↗</a>
                      {selected.profitWarningEvidence.events[0] ? (
                        <div className="evidence-rail__warning">
                          <div><span>Profit warning signal</span><time>{new Date(selected.profitWarningEvidence.events[0].announcementDate).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</time></div>
                          <strong>{selected.profitWarningEvidence.events[0].eventType === 'guidance-cut' ? 'Guidance cut' : 'Material profit impact'}</strong>
                          <p>{selected.profitWarningEvidence.events[0].summary}</p>
                          <a href={selected.profitWarningEvidence.events[0].sourceUrl} target="_blank" rel="noreferrer">View official announcement ↗</a>
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <div className="evidence-rail__pending"><strong>Research pending</strong><p>{selectedRole.reason}</p><span>No score has been inferred.</span></div>
                  )}
                  <div className="evidence-rail__method">
                    <span>Method v{data.metadata.methodologyVersion}</span>
                    <p>{role === 'ceo' ? data.metadata.scoreDefinition.ceo : data.metadata.scoreDefinition.chair}</p>
                    <p>{data.metadata.scoreDefinition.dissent}</p>
                    <p>{data.metadata.scoreDefinition.profitWarnings}</p>
                  </div>
                </>
              ) : null}
            </aside>
          </div>

          <div className="radar-footer">
            <span>{data.metadata.rosterSource.name} / {data.metadata.constituentCount} constituents</span>
            <button onClick={resetFilters} type="button">Reset filters</button>
            <span className={data.metadata.validation.status === 'pass' ? 'is-pass' : ''}>{data.metadata.validation.status} validation</span>
          </div>
        </div>
      </section>
    </div>
  )
}
