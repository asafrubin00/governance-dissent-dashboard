import { useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { LeadershipProfilesData, LeadershipRadarData, MarketPerformanceData } from '../types'

type LeadershipRadarPageProps = {
  data: LeadershipRadarData
  marketData: MarketPerformanceData
  profilesData: LeadershipProfilesData
}

type RoleKey = 'ceo' | 'chair'
type UniverseKey = 'rated' | 'full'

const bandOrder = ['Acute', 'Elevated', 'Watch', 'Lower', 'Not applicable', 'Unrated']

function bandClass(band: string) {
  return `heat-tile--${band.toLowerCase().replaceAll(' ', '-')}`
}

function formatRole(role: RoleKey) {
  return role === 'ceo' ? 'CEO' : 'Chair'
}

export function LeadershipRadarPage({ data, marketData, profilesData }: LeadershipRadarPageProps) {
  const [role, setRole] = useState<RoleKey>('ceo')
  const [universe, setUniverse] = useState<UniverseKey>('rated')
  const [sector, setSector] = useState('All sectors')
  const [band, setBand] = useState('All bands')
  const [selectedTicker, setSelectedTicker] = useState('NXT')
  const [marketOpen, setMarketOpen] = useState(false)
  const [marketMetric, setMarketMetric] = useState<'price' | 'adjusted'>('adjusted')
  const [profileOpen, setProfileOpen] = useState(false)

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
      .filter((company) => universe === 'full' || company.roles[role].rated || company.roles[role].notApplicable)
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
  const successionCount = visibleCompanies.reduce(
    (total, company) => total + company.successionEvidence.cases.filter((item) => item.role === role).length,
    0,
  )
  const selected =
    data.companies.find((company) => company.ticker === selectedTicker) ?? visibleCompanies[0]
  const selectedRole = selected?.roles[role]
  const selectedSuccession = selected?.successionEvidence.cases.find((item) => item.role === role)
  const selectedMarket = marketData.companies.find((company) => company.ticker === selected?.ticker)
  const selectedProfileCompany = profilesData.companies.find((company) => company.ticker === selected?.ticker)
  const selectedProfile = selectedProfileCompany?.roles[role]
  const marketSeries = useMemo(() => {
    if (!selectedMarket) return []
    const startDate = selectedMarket.roles[role].roleStartDate
    const points = selectedMarket.points.filter((point) => point.date >= startDate)
    if (!points.length) return []
    const firstValue = marketMetric === 'price' ? points[0].close : points[0].adjustedClose
    const benchmarkByMonth = new Map(marketData.benchmark.points.map((point) => [point.date.slice(0, 7), point.close]))
    const firstBenchmark = benchmarkByMonth.get(points[0].date.slice(0, 7))
    return points.map((point) => {
      const value = marketMetric === 'price' ? point.close : point.adjustedClose
      const benchmark = benchmarkByMonth.get(point.date.slice(0, 7))
      return {
        date: point.date,
        companyReturn: (value / firstValue - 1) * 100,
        benchmarkReturn: benchmark && firstBenchmark ? (benchmark / firstBenchmark - 1) * 100 : null,
      }
    })
  }, [marketData.benchmark.points, marketMetric, role, selectedMarket])

  function resetFilters() {
    setSector('All sectors')
    setBand('All bands')
    setUniverse('rated')
  }

  function switchRole(nextRole: RoleKey) {
    setRole(nextRole)
    const current = data.companies.find((company) => company.ticker === selectedTicker)
    if (!current?.roles[nextRole].rated && !current?.roles[nextRole].notApplicable) {
      const firstRated = data.companies.find((company) => company.roles[nextRole].rated || company.roles[nextRole].notApplicable)
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
            <div><span>Acute / warnings / live process</span><strong>{acuteCount} / {warningCount} / {successionCount}</strong></div>
            <div><span>Evidence date</span><strong>{new Date(data.metadata.asOfDate).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}</strong></div>
          </div>

          <div className="radar-main-row">
            <section className="radar-map-panel">
              <div className="radar-map-panel__heading">
                <div><p>FTSE 100 leadership map</p><h2>{universe === 'rated' ? 'Source-verified cohort' : 'Full constituent research queue'}</h2></div>
                <span>{visibleCompanies.length} companies shown</span>
              </div>
              <div className={`heat-map ${universe === 'full' ? 'heat-map--full' : visibleCompanies.length > 30 ? 'heat-map--cohort' : 'heat-map--pilot'}`}>
                {visibleCompanies.map((company) => {
                  const roleData = company.roles[role]
                  return (
                    <button
                      aria-label={`${company.companyName}: ${roleData.rated ? `${roleData.score} ${roleData.band}` : roleData.notApplicable ? 'not applicable' : 'unrated'}`}
                      className={`heat-tile ${bandClass(roleData.band)} ${selected?.ticker === company.ticker ? 'is-selected' : ''}`}
                      key={company.ticker}
                      onClick={() => setSelectedTicker(company.ticker)}
                      type="button"
                    >
                      <span>{company.ticker}</span>
                      <small>{universe === 'rated' ? company.companyName : roleData.rated ? roleData.band : roleData.notApplicable ? 'N/A' : 'Pending'}</small>
                      <strong>{roleData.score?.toFixed(0) ?? '—'}</strong>
                      {company.profitWarningEvidence.count || company.successionEvidence.cases.some((item) => item.role === role) ? (
                        <span className="heat-tile__signals">
                          {company.profitWarningEvidence.count ? <i className="heat-tile__warning" title={`${company.profitWarningEvidence.count} qualifying warning event${company.profitWarningEvidence.count === 1 ? '' : 's'} captured`}>PW</i> : null}
                          {company.successionEvidence.cases.some((item) => item.role === role) ? <i className="heat-tile__succession" title={`Official ${formatRole(role)} succession process captured`}>SC</i> : null}
                        </span>
                      ) : null}
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
                        <div><dt>Role holder</dt><dd>{selectedProfile ? <button className="profile-link" onClick={() => setProfileOpen(true)} type="button">{selectedRole.name}</button> : selectedRole.name}</dd></div>
                        <div><dt>Tenure</dt><dd>{selectedRole.tenureYears?.toFixed(1)} years</dd></div>
                        <div><dt>Tenure pressure</dt><dd>{selectedRole.components?.tenurePressure.toFixed(0)} pts</dd></div>
                        <div><dt>Dissent uplift</dt><dd>+{selectedRole.components?.registeredDissentUplift.toFixed(0)} pts</dd></div>
                      </dl>
                      <p className="evidence-rail__readout">{selectedRole.reason}</p>
                      <a className="evidence-rail__source" href={selectedRole.sourceUrl} target="_blank" rel="noreferrer">View primary leadership source ↗</a>
                      {selectedMarket ? <button className="evidence-rail__market" onClick={() => setMarketOpen(true)} type="button">Open tenure performance pilot</button> : null}
                      {selectedSuccession ? (
                        <div className="evidence-rail__succession">
                          <div><span>Live succession process</span><time>{new Date(selectedSuccession.announcedDate).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</time></div>
                          <strong>{selectedSuccession.status === 'search-underway' ? `${formatRole(role)} search underway` : selectedSuccession.status === 'successor-announced' ? 'Successor announced' : 'Departure announced'}</strong>
                          <p>{selectedSuccession.summary}</p>
                          <a href={selectedSuccession.sourceUrl} target="_blank" rel="noreferrer">View official announcement ↗</a>
                        </div>
                      ) : null}
                      {selected.profitWarningEvidence.events[0] ? (
                        <div className="evidence-rail__warning">
                          <div><span>Profit warning signal</span><time>{new Date(selected.profitWarningEvidence.events[0].announcementDate).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</time></div>
                          <strong>{selected.profitWarningEvidence.events[0].eventType === 'guidance-cut' ? 'Guidance cut' : 'Material profit impact'}</strong>
                          <p>{selected.profitWarningEvidence.events[0].summary}</p>
                          <a href={selected.profitWarningEvidence.events[0].sourceUrl} target="_blank" rel="noreferrer">View official announcement ↗</a>
                        </div>
                      ) : null}
                    </>
                  ) : selectedRole.notApplicable ? (
                    <div className="evidence-rail__pending"><strong>Not applicable</strong><p>{selectedRole.reason}</p><a className="evidence-rail__source" href={selectedRole.sourceUrl} target="_blank" rel="noreferrer">View governance source ↗</a></div>
                  ) : (
                    <div className="evidence-rail__pending"><strong>Research pending</strong><p>{selectedRole.reason}</p><span>No score has been inferred.</span></div>
                  )}
                  <div className="evidence-rail__method">
                    <span>Method v{data.metadata.methodologyVersion}</span>
                    <p>{role === 'ceo' ? data.metadata.scoreDefinition.ceo : data.metadata.scoreDefinition.chair}</p>
                    <p>{data.metadata.scoreDefinition.dissent}</p>
                    <p>{data.metadata.scoreDefinition.profitWarnings}</p>
                    <p>{data.metadata.scoreDefinition.succession}</p>
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
      {marketOpen && selectedMarket ? (
        <div className="market-modal" role="dialog" aria-modal="true" aria-label={`${selectedMarket.companyName} market performance`}>
          <div className="market-modal__panel">
            <button className="market-modal__close" onClick={() => setMarketOpen(false)} type="button" aria-label="Close">×</button>
            <div className="market-modal__header">
              <div><p>Tenure performance pilot / {selectedMarket.ticker}</p><h2>{selectedMarket.companyName}</h2><span>{selectedMarket.roles[role].name} · {formatRole(role)} since {new Date(selectedMarket.roles[role].roleStartDate).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}</span></div>
              <div className="market-modal__toggle"><button className={marketMetric === 'adjusted' ? 'is-active' : ''} onClick={() => setMarketMetric('adjusted')} type="button">Dividend-adjusted</button><button className={marketMetric === 'price' ? 'is-active' : ''} onClick={() => setMarketMetric('price')} type="button">Share price</button></div>
            </div>
            <div className="market-modal__chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={marketSeries} margin={{ top: 16, right: 16, bottom: 4, left: 2 }}>
                  <CartesianGrid stroke="rgba(218,226,231,.09)" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(0, 4)} minTickGap={40} tick={{ fill: '#8797a3', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={(value: number) => `${value.toFixed(0)}%`} tick={{ fill: '#8797a3', fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
                  <Tooltip labelFormatter={(value) => new Date(String(value)).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })} formatter={(value, name) => [`${Number(value).toFixed(1)}%`, name === 'companyReturn' ? selectedMarket.companyName : 'FTSE 100 price index']} contentStyle={{ background: '#071016', border: '1px solid #31414b', borderRadius: 8 }} />
                  <Line type="monotone" dataKey="companyReturn" stroke="#efc64a" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="benchmarkReturn" stroke="#7f96a5" strokeWidth={1.5} strokeDasharray="5 5" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="market-modal__footer"><p>{marketData.metadata.methodology}</p><p>{marketData.metadata.limitations}</p><a href={marketData.metadata.sourceUrl} target="_blank" rel="noreferrer">{marketData.metadata.sourceName} ↗</a></div>
          </div>
        </div>
      ) : null}
      {profileOpen && selectedProfile && selected ? (
        <div className="profile-modal" role="dialog" aria-modal="true" aria-label={`${selectedProfile.name} profile`}>
          <div className="profile-modal__panel">
            <button className="market-modal__close" onClick={() => setProfileOpen(false)} type="button" aria-label="Close">×</button>
            <div className="profile-modal__portrait">
              {selectedProfile.portraitPath ? <img src={selectedProfile.portraitPath} alt={selectedProfile.name} /> : <span>{selectedProfile.name.split(' ').map((part) => part[0]).slice(0, 2).join('')}</span>}
            </div>
            <div className="profile-modal__copy">
              <p>{selected.companyName} / {formatRole(role)}</p>
              <h2>{selectedProfile.name}</h2>
              <span>In role since {new Date(selected.roles[role].roleStartDate ?? '').toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}</span>
              <p className="profile-modal__bio">{selectedProfile.summary}</p>
              <a href={selectedProfile.sourceUrl} target="_blank" rel="noreferrer">View official company biography ↗</a>
              <small>{profilesData.metadata.limitations}</small>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
