import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { LegalLine } from '../components/LegalLine'
import type { LeadershipProfilesData, LeadershipRadarData, MarketPerformanceData } from '../types'

type LeadershipRadarPageProps = {
  data: LeadershipRadarData
  marketData: MarketPerformanceData
  profilesData: LeadershipProfilesData
}

type RoleKey = 'ceo' | 'chair'
type UniverseKey = 'rated' | 'full'
type LensKey = 'integrated' | 'voting'

const bandOrder = ['Acute', 'Elevated', 'Watch', 'Lower', 'Not applicable', 'Unrated']
const votingBandOrder = ['Severe', 'Strong', 'Significant', 'No captured signal']

function bandClass(band: string) {
  return `heat-tile--${band.toLowerCase().replaceAll(' ', '-')}`
}

function formatRole(role: RoleKey) {
  return role === 'ceo' ? 'CEO' : 'Chair'
}

function votingBand(maxDissent: number | null | undefined) {
  if (maxDissent == null) return 'No captured signal'
  if (maxDissent >= 50) return 'Severe'
  if (maxDissent >= 30) return 'Strong'
  return 'Significant'
}

function votingBandClass(maxDissent: number | null | undefined) {
  return `heat-tile--vote-${votingBand(maxDissent).toLowerCase().replaceAll(' ', '-')}`
}

export function LeadershipRadarPage({ data, marketData, profilesData }: LeadershipRadarPageProps) {
  const [role, setRole] = useState<RoleKey>('ceo')
  const [lens, setLens] = useState<LensKey>('integrated')
  const [universe, setUniverse] = useState<UniverseKey>('rated')
  const [sector, setSector] = useState('All sectors')
  const [band, setBand] = useState('All bands')
  const [selectedTicker, setSelectedTicker] = useState('NXT')
  const [marketOpen, setMarketOpen] = useState(false)
  const [marketMetric, setMarketMetric] = useState<'price' | 'adjusted'>('adjusted')
  const [profileOpen, setProfileOpen] = useState(false)

  const sectors = useMemo(
    () => ['All sectors', ...Array.from(new Set(data.companies.map((item) => item.sector))).sort()],
    [data.companies],
  )

  const visibleCompanies = useMemo(() => {
    return data.companies
      .filter((company) => universe === 'full' || company.roles[role].rated || company.roles[role].notApplicable)
      .filter((company) => sector === 'All sectors' || company.sector === sector)
      .filter((company) => {
        if (band === 'All bands') return true
        if (lens === 'voting') return votingBand(company.roles[role].dissentEvidence?.maxManagementDissentPct) === band
        return company.roles[role].band === band
      })
      .sort((a, b) => {
        if (lens === 'voting') {
          return (b.roles[role].dissentEvidence?.maxManagementDissentPct ?? -1) -
            (a.roles[role].dissentEvidence?.maxManagementDissentPct ?? -1)
        }
        return (b.roles[role].score ?? -1) - (a.roles[role].score ?? -1)
      })
  }, [band, data.companies, lens, role, sector, universe])

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
  const votingCompanies = visibleCompanies.filter((company) => (company.roles[role].dissentEvidence?.count ?? 0) > 0)
  const votingResolutionCount = votingCompanies.reduce(
    (total, company) => total + (company.roles[role].dissentEvidence?.count ?? 0),
    0,
  )
  const severeVotingCount = votingCompanies.filter(
    (company) => (company.roles[role].dissentEvidence?.maxManagementDissentPct ?? 0) >= 50,
  ).length
  const averageStrongestDissent = votingCompanies.length
    ? votingCompanies.reduce(
      (total, company) => total + (company.roles[role].dissentEvidence?.maxManagementDissentPct ?? 0),
      0,
    ) / votingCompanies.length
    : 0
  const selected =
    data.companies.find((company) => company.ticker === selectedTicker) ?? visibleCompanies[0]
  const selectedRole = selected?.roles[role]
  const selectedVoting = selectedRole?.dissentEvidence
  const selectedSuccession = selected?.successionEvidence.cases.find((item) => item.role === role)
  const selectedMarketRecord = marketData.companies.find((company) => company.ticker === selected?.ticker)
  const selectedMarket = selectedMarketRecord?.roles[role].roleStartDate ? selectedMarketRecord : undefined
  const selectedProfileCompany = profilesData.companies.find((company) => company.ticker === selected?.ticker)
  const selectedProfile = selectedProfileCompany?.roles[role]
  const marketSeries = useMemo(() => {
    if (!selectedMarket) return []
    const startDate = selectedMarket.roles[role].roleStartDate
    if (!startDate) return []
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

  function switchLens(nextLens: LensKey) {
    setLens(nextLens)
    setBand('All bands')
  }

  return (
    <div className="page-flow">
      <section className="workspace-screen workspace-screen--radar" id="workspace">
        <div className="radar-workspace">
          <div className="radar-controls">
            <fieldset className="segmented-control">
              <legend>Signal lens</legend>
              <button className={lens === 'integrated' ? 'is-active' : ''} onClick={() => switchLens('integrated')} type="button">Integrated</button>
              <button className={lens === 'voting' ? 'is-active' : ''} onClick={() => switchLens('voting')} type="button">Voting</button>
            </fieldset>
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
            <label className="radar-select"><span>{lens === 'voting' ? 'Voting signal' : 'Pressure band'}</span><select value={band} onChange={(event) => setBand(event.target.value)}><option>All bands</option>{(lens === 'voting' ? votingBandOrder : bandOrder).map((item) => <option key={item}>{item}</option>)}</select></label>
          </div>

          <div className="radar-headline">
            <div><span>{lens === 'voting' ? 'Stewardship evidence' : 'Governance pressure radar'}</span><strong>{lens === 'voting' ? 'Significant dissent signals' : `${formatRole(role)} transition signals`}</strong></div>
            <p>{lens === 'voting' ? 'Verified 20%+ opposition to management. Absence is not evidence of zero dissent.' : 'Research prioritisation, not a departure forecast. Select a tile to inspect its evidence.'}</p>
            <div className="radar-legend" aria-label={lens === 'voting' ? 'Voting signal bands' : 'Pressure bands'}>{(lens === 'voting' ? votingBandOrder : bandOrder).map((item) => <span key={item}><i className={lens === 'voting' ? `heat-tile--vote-${item.toLowerCase().replaceAll(' ', '-')}` : bandClass(item)} />{item}</span>)}</div>
          </div>

          <div className="radar-kpis">
            <div><span>{lens === 'voting' ? 'Companies with signals' : 'Rated in view'}</span><strong>{lens === 'voting' ? votingCompanies.length : ratedVisible.length}</strong></div>
            <div><span>{lens === 'voting' ? 'Qualifying resolutions' : 'Average pressure'}</span><strong>{lens === 'voting' ? votingResolutionCount : averageScore.toFixed(0)}</strong></div>
            <div><span>{lens === 'voting' ? 'Average strongest / severe' : 'Acute / warnings / live process'}</span><strong>{lens === 'voting' ? `${averageStrongestDissent.toFixed(1)}% / ${severeVotingCount}` : `${acuteCount} / ${warningCount} / ${successionCount}`}</strong></div>
            <div><span>Evidence date</span><strong>{new Date(data.metadata.asOfDate).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}</strong></div>
          </div>

          <div className="radar-main-row">
            <section className="radar-map-panel">
              <div className="radar-map-panel__heading">
                <div><p>{lens === 'voting' ? 'FTSE 100 voting map' : 'FTSE 100 leadership map'}</p><h2>{lens === 'voting' ? 'Significant dissent evidence' : universe === 'rated' ? 'Source-verified cohort' : 'Full constituent research queue'}</h2></div>
                <span>{visibleCompanies.length} companies shown</span>
              </div>
              <div className={`heat-map ${universe === 'full' ? 'heat-map--full' : visibleCompanies.length > 30 ? 'heat-map--cohort' : 'heat-map--pilot'}`}>
                {visibleCompanies.map((company) => {
                  const roleData = company.roles[role]
                  const voteMax = roleData.dissentEvidence?.maxManagementDissentPct
                  const tileBand = lens === 'voting' ? votingBand(voteMax) : roleData.band
                  return (
                    <button
                      aria-label={`${company.companyName}: ${lens === 'voting' ? voteMax == null ? 'no captured significant dissent' : `${voteMax}% maximum management dissent` : roleData.rated ? `${roleData.score} ${roleData.band}` : roleData.notApplicable ? 'not applicable' : 'unrated'}`}
                      className={`heat-tile ${lens === 'voting' ? votingBandClass(voteMax) : bandClass(roleData.band)} ${selected?.ticker === company.ticker ? 'is-selected' : ''}`}
                      key={company.ticker}
                      onClick={() => setSelectedTicker(company.ticker)}
                      type="button"
                    >
                      <span>{company.ticker}</span>
                      <small>{lens === 'voting' ? tileBand : universe === 'rated' ? company.companyName : roleData.rated ? roleData.band : roleData.notApplicable ? 'N/A' : 'Pending'}</small>
                      <strong>{lens === 'voting' ? voteMax == null ? '—' : `${voteMax.toFixed(0)}%` : roleData.score?.toFixed(0) ?? '—'}</strong>
                      {lens === 'integrated' && (company.profitWarningEvidence.count || company.successionEvidence.cases.some((item) => item.role === role) || (roleData.dissentEvidence?.count ?? 0) > 0) ? (
                        <span className="heat-tile__signals">
                          {company.profitWarningEvidence.count ? <abbr className="heat-tile__warning" title={`${company.profitWarningEvidence.count} qualifying profit warning event${company.profitWarningEvidence.count === 1 ? '' : 's'} captured`}>PW</abbr> : null}
                          {company.successionEvidence.cases.some((item) => item.role === role) ? <abbr className="heat-tile__succession" title={`Official ${formatRole(role)} succession process captured`}>SC</abbr> : null}
                          {(roleData.dissentEvidence?.count ?? 0) > 0 ? <abbr className="heat-tile__vote" title={`${roleData.dissentEvidence?.count} significant voting signal${roleData.dissentEvidence?.count === 1 ? '' : 's'} captured`}>AGM</abbr> : null}
                        </span>
                      ) : null}
                    </button>
                  )
                })}
                {!visibleCompanies.length ? <p className="heat-map__empty">No companies match these filters.</p> : null}
              </div>
            </section>

            <aside className={`evidence-rail ${lens === 'voting' ? 'evidence-rail--voting' : ''}`}>
              {selected && selectedRole ? (
                <>
                  <div className="evidence-rail__header">
                    <div><p>{selected.ticker} / {formatRole(role)}</p><h2>{selected.companyName}</h2></div>
                    <span className={lens === 'voting' ? votingBandClass(selectedVoting?.maxManagementDissentPct) : bandClass(selectedRole.band)}>{lens === 'voting' ? votingBand(selectedVoting?.maxManagementDissentPct) : selectedRole.band}</span>
                  </div>
                  {lens === 'voting' ? (
                    <>
                      <div className="evidence-rail__score"><strong>{selectedVoting?.maxManagementDissentPct == null ? '—' : `${selectedVoting.maxManagementDissentPct.toFixed(1)}%`}</strong><span>highest captured<br />management dissent</span></div>
                      <dl className="evidence-rail__facts">
                        <div><dt>Signals captured</dt><dd>{selectedVoting?.count ?? 0}</dd></div>
                        <div><dt>Score eligible</dt><dd>{selectedVoting?.scoredCount ?? 0}</dd></div>
                        <div><dt>Latest signal</dt><dd>{selectedVoting?.records[0] ? new Date(selectedVoting.records[0].meetingDate).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' }) : 'None captured'}</dd></div>
                        <div><dt>Coverage</dt><dd>Significant votes only</dd></div>
                      </dl>
                      {selectedVoting?.records.length ? (
                        <div className="evidence-rail__votes">
                          <span>Resolution evidence</span>
                          {selectedVoting.records.slice(0, 3).map((record) => (
                            <Link key={record.id} to={`/resolution/${record.id}`}>
                              <span>{record.categoryLabel} · {new Date(record.meetingDate).getFullYear()}</span>
                              <strong>{record.title}</strong>
                              <small>{record.managementDissentPct.toFixed(1)}% opposition to management · {record.scoreTreatment === 'included' ? 'score eligible' : 'context only'}</small>
                            </Link>
                          ))}
                        </div>
                      ) : <p className="evidence-rail__readout">No qualifying vote is captured in the current tracker. This is not evidence of zero dissent or complete AGM coverage.</p>}
                      <div className="evidence-rail__method">
                        <span>Voting methodology</span>
                        <p>Management-sponsored resolutions can inform the pressure score. Board-opposed shareholder proposals remain visible context and do not automatically imply CEO or Chair pressure.</p>
                      </div>
                      <Link className="evidence-rail__explorer" to="/proxy-voting">Open full Vote Explorer</Link>
                    </>
                  ) : selectedRole.rated ? (
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
                      {selectedMarket ? <button className="evidence-rail__market" onClick={() => setMarketOpen(true)} type="button">Open tenure performance</button> : null}
                      {selectedVoting?.records[0] ? (
                        <div className="evidence-rail__dissent">
                          <div><span>Voting evidence</span><strong>{selectedVoting.maxManagementDissentPct?.toFixed(1)}%</strong></div>
                          <Link to={`/resolution/${selectedVoting.records[0].id}`}>{selectedVoting.records[0].title}</Link>
                          <small>{selectedVoting.count} significant signal{selectedVoting.count === 1 ? '' : 's'} · {selectedVoting.scoredCount} score eligible</small>
                        </div>
                      ) : null}
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
                    <p>Calibration v{data.metadata.calibration.methodologyVersion}: {data.metadata.calibration.completedOutcomeCount} completed transitions and {data.metadata.calibration.activeOutcomeCount} active processes reviewed; {data.metadata.calibration.alignedCompletedOutcomeCount} completed cases have aligned warning windows. Production weights retained.</p>
                  </div>
                </>
              ) : null}
            </aside>
          </div>

          <div className="radar-footer">
            <span>{data.metadata.rosterSource.name} / {data.metadata.constituentCount} constituents</span>
            <LegalLine />
            <div className="radar-key">
              <button type="button">Abbreviations</button>
              <div className="radar-key__popover" role="tooltip">
                <span><strong>PW</strong> Profit warning</span>
                <span><strong>SC</strong> Succession process</span>
                <span><strong>AGM</strong> Significant voting signal</span>
                <span><strong>CEO</strong> Chief Executive Officer</span>
                <span><strong>AGM</strong> Annual General Meeting</span>
                <span><strong>N/A</strong> Not applicable</span>
              </div>
            </div>
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
              <div><p>Tenure performance / {selectedMarket.ticker}</p><h2>{selectedMarket.companyName}</h2><span>{selectedMarket.roles[role].name} · {formatRole(role)} since {new Date(selectedMarket.roles[role].roleStartDate!).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}</span></div>
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
