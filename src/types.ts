export type ResolutionRecord = {
  id: string
  companyName: string
  companySlug: string
  sourceCompanyName: string
  sector: string
  meetingDate: string
  meetingYear: number
  meetingType: string
  sourceGroup: string
  resolutionTitle: string
  votesForPct: number | null
  votesAgainstPct: number | null
  votesWithheldPct: number | null
  issuedShareCapitalVotedPct: number | null
  statementInResults: boolean | null
  statementInResultsUrl: string | null
  updateStatement: boolean | null
  updateStatementUrl: string | null
  resolutionCategory: string
  resolutionCategoryLabel: string
  governanceNote: string
  sourceUrl: string
}

export type TrackerData = {
  metadata: {
    title: string
    sourceName: string
    sourceUrl: string
    generatedAt: string
    focusStatement: string
    coverageStatement: string
    coveragePeriod: {
      startDate: string | null
      endDate: string | null
    }
    methodology: {
      included: string[]
      excluded: string[]
      sourceCredibilityNote: string
    }
    limitations: string[]
    stats: {
      allShareRowsParsed: number
      ftse100RowsIncluded: number
      tableCount: number
    }
    validation: {
      duplicateRecords: string[]
      missingCompanyNames: string[]
      missingDates: string[]
      impossiblePercentages: string[]
      status: string
    }
    summary: {
      companyCount: number
      resolutionCount: number
      yearsCovered: number[]
      highestVotesAgainstPct: number
      categoryBreakdown: Record<string, number>
      remunerationCount: number
      directorElectionCount: number
    }
    unmatchedCompanies: string[]
  }
  resolutions: ResolutionRecord[]
}

export type Filters = {
  company: string
  year: string
  sector: string
  category: string
}
