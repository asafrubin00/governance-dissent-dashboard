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
import { InfoHint } from '../components/InfoHint'
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

const palette = ['#f0be2a', '#89a4ba', '#5f7a91', '#3f5d74', '#b99b68']

type DashboardPageProps = {
  data: TrackerData
}

const defaultFilters: Filters = {
  company: 'All companies',
  year: 'All years',
  sector: 'All sectors',
  category: 'All categories',
}

type ActivePanel = 'top' | 'category' | 'trend' | 'patterns'

export function DashboardPage({ data }: DashboardPageProps) {
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [activePanel, setActivePanel] = useState<ActivePanel>('top')
  const [showTable, setShowTable] = useState(false)
  const options = useMemo(() => getFilterOptions(data.resolutions), [data.resolutions])
  const filtered = useMemo(
    () => filterResolutions(data.resolutions, filters),
    [data.resolutions, filters],
  )
  const metrics = useMemo(() => getSummaryMetrics(filtered), [filtered])
  const topDissent = useMemo(() => getTopDissent(filtered, 8), [filtered])
  const timeline = useMemo(() => getTimeline(filtered), [filtered])
  const categories = useMemo(() => getCategoryBreakdown(filtered), [filtered])
  const companyPatterns = useMemo(
    () => getCompanyPatterns(filtered).slice(0, 8),
    [filtered],
  )
  const quickSelectors = ['All', ...options.categories
    .filter((option) => option !== 'All categories')
    .slice(0, 5)]

  function updateFilter(name: keyof Filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }))
  }

  function formatTooltipPercent(value: unknown) {
    return typeof value === 'number' ? `${value.toFixed(1)}%` : String(value ?? '')
  }

  function formatTooltipLabel(label: unknown, prefix: string) {
    return `${prefix}: ${String(label ?? '')}`
  }

  return (
    <div className="page-flow">
      <section className="hero-screen hero-screen--cover">
        <div className="hero-screen__overlay" />
        <div className="hero-screen__hint" aria-hidden="true">
          <span />
          <span />
        </div>
      </section>

      <section className="workspace-screen workspace-screen--dashboard">
        <div className="workspace-dashboard">
          <div className="workspace-dashboard__controls">
            <FilterBar
              filters={filters}
              options={options}
              onChange={updateFilter}
              onReset={() => setFilters(defaultFilters)}
              showReset={false}
            />
          </div>

          <div className="workspace-dashboard__tabs">
            <button
              className={activePanel === 'top' ? 'is-active' : ''}
              onClick={() => setActivePanel('top')}
              type="button"
            >
              Top dissenting votes
            </button>
            <button
              className={activePanel === 'category' ? 'is-active' : ''}
              onClick={() => setActivePanel('category')}
              type="button"
            >
              Dissent by category
            </button>
            <button
              className={activePanel === 'trend' ? 'is-active' : ''}
              onClick={() => setActivePanel('trend')}
              type="button"
            >
              Trend over time
            </button>
            <button
              className={activePanel === 'patterns' ? 'is-active' : ''}
              onClick={() => setActivePanel('patterns')}
              type="button"
            >
              Company patterns
            </button>
          </div>

          <div className="workspace-dashboard__selectors">
            {quickSelectors.map((item) => (
              <button
                key={item}
                className={
                  (item === 'All' && filters.category === 'All categories') ||
                  filters.category === item
                    ? 'is-active'
                    : ''
                }
                onClick={() =>
                  setFilters((current) => ({
                    ...current,
                    category:
                      item === 'All'
                        ? 'All categories'
                        : current.category === item
                          ? 'All categories'
                          : item,
                  }))
                }
                type="button"
              >
                {item}
              </button>
            ))}
          </div>

          <div className="workspace-dashboard__kpis">
            <StatCard
              compact
              label="Filtered resolutions"
              value={String(metrics.resolutions)}
              note="Current view after applying the dashboard filters."
            />
            <StatCard
              compact
              label="Companies represented"
              value={String(metrics.companies)}
              note="Distinct FTSE 100 issuers in the filtered set."
            />
            <StatCard
              compact
              label="Average vote against"
              value={formatShortPercent(metrics.averageAgainst)}
              note="A quick read on how forceful dissent is in this slice."
            />
            <StatCard
              compact
              label="Votes above 50% against"
              value={String(metrics.severeVotes)}
              note="Cases where opposition moved into an especially acute zone."
            />
          </div>

          <div className="workspace-dashboard__main-row">
            <article className="workspace-chart">
              <div className="workspace-chart__header">
                <div>
                  <p className="workspace-chart__eyebrow">
                    {activePanel === 'top'
                      ? 'Highest votes against management'
                      : activePanel === 'category'
                        ? 'Most frequent governance themes'
                        : activePanel === 'trend'
                          ? 'AGM season timeline'
                          : 'Where dissent recurs'}
                  </p>
                  <h2>
                    {activePanel === 'top'
                      ? 'Top dissent'
                      : activePanel === 'category'
                        ? 'Dissent by category'
                        : activePanel === 'trend'
                          ? 'Trend over time'
                          : 'Company patterns'}
                  </h2>
                </div>
              </div>

              <div className="workspace-chart__body">
                {activePanel === 'top' ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={topDissent}
                      layout="vertical"
                      margin={{ left: 10, right: 10, top: 6, bottom: 6 }}
                    >
                      <CartesianGrid
                        strokeDasharray="2 5"
                        stroke="rgba(255,255,255,0.08)"
                        horizontal
                        vertical={false}
                      />
                      <XAxis
                        type="number"
                        domain={[0, 100]}
                        tickFormatter={(value) => `${value}%`}
                        tick={{ fill: '#93a7b8', fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="companyName"
                        width={132}
                        tick={{ fill: '#f1f5f8', fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        formatter={(value) => [formatTooltipPercent(value), 'Votes Against']}
                        labelFormatter={(label) => formatTooltipLabel(label, 'Company')}
                        contentStyle={{
                          background: '#07131d',
                          border: '1px solid rgba(255,255,255,0.12)',
                          borderRadius: 10,
                          color: '#f3f7fb',
                        }}
                        cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                      />
                      <Bar
                        dataKey="votesAgainstPct"
                        fill="#f0be2a"
                        radius={[0, 8, 8, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : null}

                {activePanel === 'category' ? (
                  <div className="workspace-chart__split">
                    <ResponsiveContainer width="58%" height="100%">
                      <PieChart>
                        <Pie
                          data={categories}
                          dataKey="count"
                          nameKey="category"
                          cx="50%"
                          cy="50%"
                          outerRadius={96}
                          innerRadius={54}
                          paddingAngle={3}
                        >
                          {categories.map((entry, index) => (
                            <Cell
                              key={entry.category}
                              fill={palette[index % palette.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value) => [String(value ?? ''), 'Resolutions']}
                          labelFormatter={(label) => formatTooltipLabel(label, 'Category')}
                          contentStyle={{
                            background: '#07131d',
                            border: '1px solid rgba(255,255,255,0.12)',
                            borderRadius: 10,
                            color: '#f3f7fb',
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="workspace-chart__legend">
                      {categories.map((entry, index) => (
                        <div
                          className="legend-list__item legend-list__item--workspace"
                          key={entry.category}
                        >
                          <span
                            className="legend-list__swatch"
                            style={{ backgroundColor: palette[index % palette.length] }}
                          />
                          <span>{entry.category}</span>
                          <strong>{entry.count}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {activePanel === 'trend' ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={timeline}
                      margin={{ left: 10, right: 14, top: 12, bottom: 6 }}
                    >
                      <CartesianGrid
                        strokeDasharray="2 5"
                        stroke="rgba(255,255,255,0.08)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: '#93a7b8', fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        yAxisId="left"
                        tick={{ fill: '#93a7b8', fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        tickFormatter={(value) => `${value}%`}
                        tick={{ fill: '#93a7b8', fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        formatter={(value, name) => {
                          if (name === 'resolutions') {
                            return [String(value ?? ''), 'Resolutions']
                          }

                          return [formatTooltipPercent(value), 'Average votes against']
                        }}
                        labelFormatter={(label) => formatTooltipLabel(label, 'Period')}
                        contentStyle={{
                          background: '#07131d',
                          border: '1px solid rgba(255,255,255,0.12)',
                          borderRadius: 10,
                          color: '#f3f7fb',
                        }}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="resolutions"
                        fill="#10364c"
                        radius={[8, 8, 0, 0]}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="avgAgainst"
                        stroke="#f0be2a"
                        strokeWidth={2.6}
                        dot={{ r: 3, fill: '#f0be2a' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : null}

                {activePanel === 'patterns' ? (
                  <div className="workspace-pattern-table">
                    <table className="data-table data-table--workspace">
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
                ) : null}
              </div>
            </article>

            <aside className="workspace-rail">
              <section className="workspace-rail__panel workspace-rail__panel--info-list">
                <p className="workspace-rail__eyebrow">Analysis rail</p>
                <div className="workspace-rail__info-item">
                  <span>About</span>
                  <InfoHint
                    label="About"
                    content={`${data.metadata.focusStatement} ${data.metadata.coverageStatement}`}
                  />
                </div>
                <div className="workspace-rail__info-item">
                  <span>Current read-through</span>
                  <InfoHint
                    label="Current read-through"
                    content={`${metrics.resolutions} significant dissent resolutions in the current filtered view. ${metrics.companies} FTSE 100 issuers represented after current filters. ${formatShortPercent(metrics.averageAgainst)} average opposition across the filtered set.`}
                  />
                </div>
                <div className="workspace-rail__info-item">
                  <span>Method snapshot</span>
                  <InfoHint
                    label="Method snapshot"
                    content={data.metadata.methodology.included.slice(0, 2).join(' ')}
                  />
                </div>
                <div className="workspace-rail__info-item">
                  <span>Coverage note</span>
                  <InfoHint
                    label="Coverage note"
                    content={data.metadata.coverageStatement}
                  />
                </div>
              </section>

              <section className="workspace-rail__panel workspace-rail__panel--actions">
                <button
                  className="action-button action-button--primary"
                  onClick={() => setShowTable(true)}
                  type="button"
                >
                  Open detailed dissent records
                </button>
                <button
                  className="action-button"
                  onClick={() => setFilters(defaultFilters)}
                  type="button"
                >
                  Reset filters
                </button>
              </section>
            </aside>
          </div>

          <div className="workspace-micro-note">
            <span>{data.metadata.sourceName}</span>
            <span>{data.metadata.validation.status.toUpperCase()} validation</span>
          </div>
        </div>

        {showTable ? (
          <div className="modal-shell" role="dialog" aria-modal="true">
            <div className="modal-panel">
              <div className="modal-panel__header">
                <div>
                  <p className="eyebrow">Resolution table</p>
                  <h2>Detailed dissent records</h2>
                  <p className="panel__intro">
                    Showing {filtered.length} of {data.resolutions.length} total v1 records.
                  </p>
                </div>
                <button
                  className="modal-panel__close"
                  onClick={() => setShowTable(false)}
                  type="button"
                >
                  Close
                </button>
              </div>
              <div className="table-card modal-table-card">
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
            </div>
          </div>
        ) : null}
      </section>
    </div>
  )
}
