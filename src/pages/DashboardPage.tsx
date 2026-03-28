import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { FilterBar } from '../components/FilterBar'
import { StatCard } from '../components/StatCard'
import {
  filterResolutions,
  getCategoryBreakdown,
  getCompanyPatterns,
  getFilterOptions,
  getSummaryMetrics,
  getTimeline,
  getTopDissent,
} from '../lib/analytics'
import { formatDate, formatShortPercent } from '../lib/format'
import type { Filters, TrackerData } from '../types'

const palette = ['#1f3b57', '#5c7488', '#8da0af', '#b2c0b0', '#c6a773']

type DashboardPageProps = {
  data: TrackerData
}

const defaultFilters: Filters = {
  company: 'All companies',
  year: 'All years',
  sector: 'All sectors',
  category: 'All categories',
}

export function DashboardPage({ data }: DashboardPageProps) {
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const options = useMemo(() => getFilterOptions(data.resolutions), [data.resolutions])
  const filtered = useMemo(
    () => filterResolutions(data.resolutions, filters),
    [data.resolutions, filters],
  )
  const metrics = useMemo(() => getSummaryMetrics(filtered), [filtered])
  const topDissent = useMemo(() => getTopDissent(filtered, 8), [filtered])
  const timeline = useMemo(() => getTimeline(filtered), [filtered])
  const categories = useMemo(() => getCategoryBreakdown(filtered), [filtered])
  const companyPatterns = useMemo(() => getCompanyPatterns(filtered).slice(0, 8), [filtered])

  function updateFilter(name: keyof Filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }))
  }

  return (
    <div className="page-stack">
      <section className="page-heading page-heading--dashboard">
        <p className="eyebrow">Dashboard</p>
        <h1>Resolution-level view of significant votes against management</h1>
        <p className="lede">
          This dashboard tracks significant shareholder dissent only. It does not aim to
          show every AGM resolution; it shows the subset of high-salience dissent cases
          captured by the current source and matched to FTSE 100 issuers.
        </p>
      </section>

      <section className="panel panel--methodology">
        <div className="panel__header">
          <p className="eyebrow">Methodology and coverage</p>
          <h2>What this dashboard includes</h2>
        </div>
        <div className="content-grid content-grid--tight">
          <div>
            <p className="panel__intro">{data.metadata.coverageStatement}</p>
            <ul className="plain-list">
              {data.metadata.methodology.included.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="panel__intro">Excluded from scope:</p>
            <ul className="plain-list">
              {data.metadata.methodology.excluded.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="panel__intro">{data.metadata.methodology.sourceCredibilityNote}</p>
            <p className="panel__intro">
              Validation checks: {data.metadata.validation.status.toUpperCase()}
            </p>
          </div>
        </div>
      </section>

      <FilterBar
        filters={filters}
        options={options}
        onChange={updateFilter}
        onReset={() => setFilters(defaultFilters)}
      />

      <section className="stats-grid stats-grid--summary">
        <StatCard
          label="Filtered resolutions"
          value={String(metrics.resolutions)}
          note="Current view after applying the dashboard filters."
        />
        <StatCard
          label="Companies represented"
          value={String(metrics.companies)}
          note="Distinct FTSE 100 issuers in the filtered set."
        />
        <StatCard
          label="Average vote against"
          value={formatShortPercent(metrics.averageAgainst)}
          note="A quick read on how forceful dissent is in this slice."
        />
        <StatCard
          label="Votes above 50% against"
          value={String(metrics.severeVotes)}
          note="Cases where opposition moved into an especially acute zone."
        />
      </section>

      <section className="chart-grid chart-grid--dashboard">
        <article className="panel chart-panel chart-panel--primary">
          <div className="panel__header">
            <p className="eyebrow">Top dissenting votes</p>
            <h2>Highest votes against management</h2>
          </div>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topDissent} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#d7ddd8" />
                <XAxis type="number" domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
                <YAxis
                  type="category"
                  dataKey="companyName"
                  width={120}
                  tick={{ fill: '#304556', fontSize: 12 }}
                />
                <Tooltip />
                <Bar dataKey="votesAgainstPct" fill="#1f3b57" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel chart-panel--secondary">
          <div className="panel__header">
            <p className="eyebrow">Trend over time</p>
            <h2>AGM season timeline</h2>
          </div>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeline} margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#d7ddd8" />
                <XAxis dataKey="label" tick={{ fill: '#304556', fontSize: 12 }} />
                <YAxis yAxisId="left" tick={{ fill: '#304556', fontSize: 12 }} />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tickFormatter={(value) => `${value}%`}
                  tick={{ fill: '#304556', fontSize: 12 }}
                />
                <Tooltip />
                <Bar yAxisId="left" dataKey="resolutions" fill="#9fb0a3" radius={[6, 6, 0, 0]} />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="avgAgainst"
                  stroke="#1f3b57"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel chart-panel--secondary">
          <div className="panel__header">
            <p className="eyebrow">Dissent by category</p>
            <h2>Most frequent governance themes</h2>
          </div>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={categories}
                  dataKey="count"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={92}
                  innerRadius={54}
                  paddingAngle={2}
                >
                  {categories.map((entry, index) => (
                    <Cell key={entry.category} fill={palette[index % palette.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="legend-list">
            {categories.map((entry, index) => (
              <div className="legend-list__item" key={entry.category}>
                <span
                  className="legend-list__swatch"
                  style={{ backgroundColor: palette[index % palette.length] }}
                />
                <span>{entry.category}</span>
                <strong>{entry.count}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel chart-panel chart-panel--secondary">
          <div className="panel__header">
            <p className="eyebrow">Company patterns</p>
            <h2>Where dissent recurs</h2>
          </div>
          <div className="table-card">
            <table className="data-table condensed-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Sector</th>
                  <th>Resolutions</th>
                  <th>Avg against</th>
                  <th>Peak against</th>
                </tr>
              </thead>
              <tbody>
                {companyPatterns.map((item) => (
                  <tr key={item.company}>
                    <td>{item.company}</td>
                    <td>{item.sector}</td>
                    <td>{item.resolutions}</td>
                    <td>{formatShortPercent(item.avgAgainst)}</td>
                    <td>{formatShortPercent(item.maxAgainst)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section className="panel panel--table">
        <div className="panel__header">
          <p className="eyebrow">Resolution table</p>
          <h2>Detailed dissent records</h2>
        </div>
        <p className="panel__intro">
          Showing {filtered.length} of {data.resolutions.length} total v1 records.
        </p>
        <div className="table-card">
          <table className="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Date</th>
                <th>Category</th>
                <th>Votes against</th>
                <th>Resolution</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td>{item.companyName}</td>
                  <td>{formatDate(item.meetingDate)}</td>
                  <td>{item.resolutionCategoryLabel}</td>
                  <td>{formatShortPercent(item.votesAgainstPct)}</td>
                  <td>
                    <Link className="table-link" to={`/resolution/${item.id}`}>
                      {item.resolutionTitle}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
