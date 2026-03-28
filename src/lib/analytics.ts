import type { Filters, ResolutionRecord } from '../types'
import { formatMonth } from './format'

export function filterResolutions(
  resolutions: ResolutionRecord[],
  filters: Filters,
) {
  return resolutions.filter((resolution) => {
    const companyPass =
      filters.company === 'All companies' ||
      resolution.companyName === filters.company
    const yearPass =
      filters.year === 'All years' ||
      String(resolution.meetingYear) === filters.year
    const sectorPass =
      filters.sector === 'All sectors' || resolution.sector === filters.sector
    const categoryPass =
      filters.category === 'All categories' ||
      resolution.resolutionCategoryLabel === filters.category

    return companyPass && yearPass && sectorPass && categoryPass
  })
}

export function getFilterOptions(resolutions: ResolutionRecord[]) {
  return {
    companies: [
      'All companies',
      ...Array.from(new Set(resolutions.map((item) => item.companyName))).sort(),
    ],
    years: [
      'All years',
      ...Array.from(new Set(resolutions.map((item) => String(item.meetingYear)))).sort(),
    ],
    sectors: [
      'All sectors',
      ...Array.from(new Set(resolutions.map((item) => item.sector))).sort(),
    ],
    categories: [
      'All categories',
      ...Array.from(
        new Set(resolutions.map((item) => item.resolutionCategoryLabel)),
      ).sort(),
    ],
  }
}

export function getTopDissent(resolutions: ResolutionRecord[], limit = 8) {
  return [...resolutions]
    .sort((left, right) => (right.votesAgainstPct ?? 0) - (left.votesAgainstPct ?? 0))
    .slice(0, limit)
}

export function getTimeline(resolutions: ResolutionRecord[]) {
  const grouped = new Map<
    string,
    { label: string; monthKey: string; resolutions: number; avgAgainst: number }
  >()

  for (const item of resolutions) {
    const date = new Date(item.meetingDate)
    const monthKey = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`
    const existing = grouped.get(monthKey)
    if (existing) {
      const total = existing.avgAgainst * existing.resolutions + (item.votesAgainstPct ?? 0)
      existing.resolutions += 1
      existing.avgAgainst = total / existing.resolutions
      continue
    }

    grouped.set(monthKey, {
      label: formatMonth(item.meetingDate),
      monthKey,
      resolutions: 1,
      avgAgainst: item.votesAgainstPct ?? 0,
    })
  }

  return [...grouped.values()].sort((left, right) =>
    left.monthKey.localeCompare(right.monthKey),
  )
}

export function getCategoryBreakdown(resolutions: ResolutionRecord[]) {
  const grouped = new Map<string, number>()

  for (const item of resolutions) {
    grouped.set(
      item.resolutionCategoryLabel,
      (grouped.get(item.resolutionCategoryLabel) ?? 0) + 1,
    )
  }

  return [...grouped.entries()]
    .map(([category, count]) => ({ category, count }))
    .sort((left, right) => right.count - left.count)
}

export function getCompanyPatterns(resolutions: ResolutionRecord[]) {
  const grouped = new Map<
    string,
    {
      company: string
      sector: string
      resolutions: number
      avgAgainst: number
      maxAgainst: number
    }
  >()

  for (const item of resolutions) {
    const existing = grouped.get(item.companyName)
    const against = item.votesAgainstPct ?? 0
    if (existing) {
      const total = existing.avgAgainst * existing.resolutions + against
      existing.resolutions += 1
      existing.avgAgainst = total / existing.resolutions
      existing.maxAgainst = Math.max(existing.maxAgainst, against)
      continue
    }

    grouped.set(item.companyName, {
      company: item.companyName,
      sector: item.sector,
      resolutions: 1,
      avgAgainst: against,
      maxAgainst: against,
    })
  }

  return [...grouped.values()].sort((left, right) => {
    if (right.resolutions === left.resolutions) {
      return right.maxAgainst - left.maxAgainst
    }
    return right.resolutions - left.resolutions
  })
}

export function getSummaryMetrics(resolutions: ResolutionRecord[]) {
  const companies = new Set(resolutions.map((item) => item.companyName))
  const avgAgainst =
    resolutions.reduce((total, item) => total + (item.votesAgainstPct ?? 0), 0) /
      (resolutions.length || 1)

  return {
    resolutions: resolutions.length,
    companies: companies.size,
    averageAgainst: avgAgainst,
    severeVotes: resolutions.filter((item) => (item.votesAgainstPct ?? 0) >= 50).length,
  }
}

export function getRecentHighlights(resolutions: ResolutionRecord[], limit = 4) {
  return [...resolutions]
    .sort((left, right) => {
      const dateOrder = right.meetingDate.localeCompare(left.meetingDate)
      if (dateOrder !== 0) {
        return dateOrder
      }
      return (right.votesAgainstPct ?? 0) - (left.votesAgainstPct ?? 0)
    })
    .slice(0, limit)
}
