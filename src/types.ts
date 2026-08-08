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

export type LeadershipRole = {
  rated: boolean
  notApplicable?: boolean
  status?: 'not-applicable'
  name?: string
  roleStartDate?: string
  sourceUrl?: string
  sourceLabel?: string
  datePrecision?: 'day' | 'month' | 'year'
  tenureYears?: number
  score: number | null
  band: 'Lower' | 'Watch' | 'Elevated' | 'Acute' | 'Unrated' | 'Not applicable'
  reason: string
  components?: {
    tenurePressure: number
    registeredDissentUplift: number
  }
  dissentEvidence?: {
    count: number
    maxVotesAgainstPct: number | null
    records: Array<{
      id: string
      title: string
      votesAgainstPct: number
      meetingDate: string
    }>
  }
}

export type LeadershipCompany = {
  companyName: string
  ticker: string
  sector: string
  profitWarningEvidence: {
    count: number
    latestDate: string | null
    events: Array<{
      id: string
      ticker: string
      companyName: string
      announcementDate: string
      eventType: 'guidance-cut' | 'material-profit-impact'
      severity: 'material' | 'severe'
      affectedPeriod: string
      metric: string
      previousGuidance: string | null
      revisedGuidance: string
      changePct: number | null
      summary: string
      drivers: string[]
      sourceUrl: string
      sourceLabel: string
    }>
    review: {
      ticker: string
      outcome: 'qualifying-event-captured' | 'reviewed-no-qualifying-event'
      sourceUrl: string
      reviewNote: string
    } | null
  }
  successionEvidence: {
    count: number
    cases: Array<{
      id: string
      ticker: string
      role: 'ceo' | 'chair'
      status: 'search-underway' | 'successor-announced' | 'departure-announced'
      announcedDate: string
      incumbentName: string
      successorName: string | null
      incumbentDepartureDate: string | null
      successorStartDate: string | null
      summary: string
      sourceUrl: string
      sourceLabel: string
    }>
  }
  roles: {
    ceo: LeadershipRole
    chair: LeadershipRole
  }
}

export type LeadershipRadarData = {
  metadata: {
    title: string
    generatedAt: string
    asOfDate: string
    methodologyVersion: string
    sourceVerifiedCompanyCount: number
    ratedCompanyCount: number
    constituentCount: number
    calibration: {
      methodologyVersion: string
      outcomeCount: number
      comparisonObservationCount: number
      decision: 'retain-current-weights'
      note: string
    }
    profitWarningCoverage: {
      eventCount: number
      companyCount: number
      reviewedCompanyCount: number
      asOfDate: string
      lookbackMonths: number
      definition: string
      scoreTreatment: string
    }
    successionCoverage: {
      activeCaseCount: number
      reviewedCompanyCount: number
      asOfDate: string
      definition: string
      scoreTreatment: string
    }
    rosterSource: {
      name: string
      url: string
      mode: string
      note: string
    }
    scoreDefinition: {
      label: string
      notAProbability: boolean
      ceo: string
      chair: string
      dissent: string
      profitWarnings: string
      succession: string
      bands: Record<string, string>
    }
    limitations: string[]
    validation: {
      status: string
      errors: string[]
    }
  }
  companies: LeadershipCompany[]
}

export type MarketPerformanceData = {
  metadata: {
    generatedAt: string
    companyCount: number
    sourceName: string
    sourceUrl: string
    frequency: string
    methodology: string
    scaleTreatment: string
    scaleAdjustmentCount: number
    limitations: string
    validation: { status: string; errors: string[] }
  }
  benchmark: {
    symbol: string
    name: string
    points: MarketPerformancePoint[]
  }
  companies: Array<{
    ticker: string
    companyName: string
    marketSymbol: string
    scaleAdjustmentCount: number
    roles: Record<'ceo' | 'chair', { name: string; roleStartDate: string | null }>
    points: MarketPerformancePoint[]
  }>
}

export type MarketPerformancePoint = {
  date: string
  close: number
  adjustedClose: number
  priceReturnPct: number
  dividendAdjustedReturnPct: number
}

export type LeadershipProfilesData = {
  metadata: {
    asOfDate: string
    companyCount: number
    scope: string
    limitations: string
    validation: { status: string; errors: string[] }
  }
  companies: Array<{
    ticker: string
    roles: Record<'ceo' | 'chair', {
      name: string
      summary: string
      sourceUrl: string
      portraitPath: string | null
    }>
  }>
}
