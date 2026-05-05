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
  votesForCount: number | null
  votesAgainstCount: number | null
  votesWithheldCount: number | null
  totalVotesCastCount: number | null
  statementInResults: boolean | null
  statementInResultsUrl: string | null
  updateStatement: boolean | null
  updateStatementUrl: string | null
  resolutionCategory: string
  resolutionCategoryLabel: string
  governanceNote: string
  sourceUrl: string
  recordOrigin: string
  recordOriginLabel: string
  officialAnnouncementUrl: string | null
  officialAnnouncementSource: string | null
  officialAnnouncementVerified: boolean
  officialAnnouncementStatus: string
  updateStatementParsed: boolean
  updateStatementSummary: string | null
  updateStatementDocumentType: string | null
}

export type TrackerData = {
  metadata: {
    title: string
    sourceName: string
    sourceUrl: string
    generatedAt: string
    refreshMode: string
    focusStatement: string
    coverageStatement: string
    coveragePeriod: {
      startDate: string | null
      endDate: string | null
    }
    sourceLayers: Array<{
      name: string
      role: string
    }>
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
      issuerAnnouncementPagesFetched: number
      issuerAnnouncementPagesParsed: number
      issuerAnnouncementRowsExtracted: number
      issuerVerifiedResolutions: number
      issuerOnlyResolutionsAdded: number
      officialVoteCountCoverage: number
      pdfDocumentsFetched: number
      pdfDocumentsParsed: number
      pdfUpdateStatementsEnriched: number
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
      issuerVerifiedCount: number
      issuerOnlyCount: number
      voteCountCoverage: number
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
