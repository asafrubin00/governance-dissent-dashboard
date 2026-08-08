#!/usr/bin/env python3
"""Build a transparent, source-backed leadership-score calibration audit."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTCOME_PATH = ROOT / "data" / "leadership_transition_outcomes.json"
LEADERSHIP_PATH = ROOT / "data" / "leadership_sources.json"
LEADERSHIP_EXPANSION_PATH = ROOT / "data" / "leadership_sources_expansion.json"
WARNING_PATH = ROOT / "data" / "profit_warning_sources.json"
HISTORICAL_EVIDENCE_PATH = ROOT / "data" / "calibration_historical_evidence.json"
SUCCESSION_PATH = ROOT / "data" / "succession_sources.json"
TRACKER_PATH = ROOT / "public" / "data" / "tracker-data.json"
RADAR_PATH = ROOT / "public" / "data" / "leadership-radar.json"
MARKET_PATH = ROOT / "public" / "data" / "market-performance.json"
OUTPUT_PATH = ROOT / "public" / "data" / "leadership-calibration.json"
ALLOWED_OUTCOME_TYPES = {
    "active-process",
    "board-led-change",
    "planned-retirement",
    "planned-succession",
    "unplanned-departure",
}
ALLOWED_DATE_PRECISIONS = {"day", "month", "year"}
ALLOWED_COVERAGE_STATUSES = {"complete", "partial"}


def normalise(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def years_between(start: str, end: str) -> float:
    return round((date.fromisoformat(end) - date.fromisoformat(start)).days / 365.2425, 1)


def tenure_pressure(role: str, tenure_years: float) -> float:
    reference_years = 10 if role == "ceo" else 9
    return round(min(80, max(0, tenure_years / reference_years * 80)), 1)


def warning_uplift(events: list[dict[str, Any]]) -> float:
    if not events:
        return 0
    base = 12 if any(event["severity"] == "severe" for event in events) else 6
    return float(min(18, base + max(0, len(events) - 1) * 3))


def performance_uplift(relative_performance: float | None) -> float:
    if relative_performance is None:
        return 0
    if relative_performance <= -40:
        return 15
    if relative_performance <= -20:
        return 8
    return 0


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def years_ago(value: str, years: int) -> str:
    parsed = date.fromisoformat(value)
    try:
        return parsed.replace(year=parsed.year - years).isoformat()
    except ValueError:
        return parsed.replace(year=parsed.year - years, day=28).isoformat()


def capture_rate(records: list[dict[str, Any]], field: str, threshold: float) -> float:
    if not records:
        return 0
    return round(sum(record[field] >= threshold for record in records) / len(records) * 100, 1)


def group_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"count": 0}
    market_records = [record for record in records if record["relativePerformancePct"] is not None]
    return {
        "count": len(records),
        "medianTenureYears": round(median(record["tenureYears"] for record in records), 1),
        "medianBaselineScore": round(median(record["baselineScore"] for record in records), 1),
        "medianWarningSensitivityScore": round(median(record["warningSensitivityScore"] for record in records), 1),
        "longTenureRatePct": round(sum(record["longTenure"] for record in records) / len(records) * 100, 1),
        "priorWarningRatePct": round(sum(record["priorWarningCount"] > 0 for record in records) / len(records) * 100, 1),
        "priorDissentRatePct": round(sum(record["priorDissentCount"] > 0 for record in records) / len(records) * 100, 1),
        "marketCoveragePct": round(len(market_records) / len(records) * 100, 1),
        "medianRelativePerformancePct": round(median(record["relativePerformancePct"] for record in market_records), 1) if market_records else None,
        "marketStressRatePct": round(sum(record["marketStress"] for record in market_records) / len(market_records) * 100, 1) if market_records else None,
    }


def main() -> None:
    outcome_source = json.loads(OUTCOME_PATH.read_text(encoding="utf-8"))
    leadership = json.loads(LEADERSHIP_PATH.read_text(encoding="utf-8"))
    expansion = json.loads(LEADERSHIP_EXPANSION_PATH.read_text(encoding="utf-8"))
    warnings = json.loads(WARNING_PATH.read_text(encoding="utf-8"))
    historical = json.loads(HISTORICAL_EVIDENCE_PATH.read_text(encoding="utf-8"))
    successions = json.loads(SUCCESSION_PATH.read_text(encoding="utf-8"))
    tracker = json.loads(TRACKER_PATH.read_text(encoding="utf-8"))
    radar = json.loads(RADAR_PATH.read_text(encoding="utf-8"))
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    companies = [*leadership["companies"], *expansion["companies"]]
    leadership_by_ticker = {company["ticker"]: company for company in companies}
    market_by_ticker = {company["ticker"]: company for company in market["companies"]}
    benchmark_by_month = {point["date"][:7]: point for point in market["benchmark"]["points"]}
    as_of = outcome_source["asOfDate"]
    errors: list[str] = []
    excluded_active: list[dict[str, str]] = []
    if historical.get("asOfDate") != as_of:
        errors.append("Historical evidence date does not match the outcome cohort.")
    if historical.get("lookbackMonths") != 36:
        errors.append("Historical evidence must use an exact 36-month lookback.")

    outcome_cases = [dict(case, cohort="completed") for case in outcome_source["completedCases"]]
    for case in successions["cases"]:
        role = leadership_by_ticker[case["ticker"]]["roles"][case["role"]]
        role_start = role.get("roleStartDate")
        if not role_start or role_start >= case["announcedDate"]:
            excluded_active.append({
                "id": case["id"],
                "reason": "Incumbent role start is not before the process announcement, so tenure-at-announcement cannot be interpreted consistently.",
            })
            continue
        outcome_cases.append({
            "id": case["id"],
            "ticker": case["ticker"],
            "companyName": leadership_by_ticker[case["ticker"]]["companyName"],
            "role": case["role"],
            "incumbentName": case["incumbentName"],
            "roleStartDate": role_start,
            "announcementDate": case["announcedDate"],
            "departureDate": case.get("incumbentDepartureDate"),
            "outcomeType": "active-process",
            "sourceUrl": case["sourceUrl"],
            "sourceLabel": case["sourceLabel"],
            "cohort": "active",
        })

    case_ids = [case.get("id") for case in outcome_cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("Duplicate calibration outcome ID found.")
    for case in outcome_cases:
        if case["ticker"] not in leadership_by_ticker:
            errors.append(f"Outcome ticker is outside the leadership cohort: {case['ticker']}.")
        if case["role"] not in {"ceo", "chair"}:
            errors.append(f"Unsupported outcome role for {case['id']}.")
        if case["outcomeType"] not in ALLOWED_OUTCOME_TYPES:
            errors.append(f"Unsupported outcome type for {case['id']}.")
        if case.get("roleStartDatePrecision", "day") not in ALLOWED_DATE_PRECISIONS:
            errors.append(f"Unsupported role-start precision for {case['id']}.")
        if not case["sourceUrl"].startswith("https://"):
            errors.append(f"Outcome source must use HTTPS for {case['id']}.")
        if not case.get("sourceLabel", "").strip():
            errors.append(f"Outcome source label is missing for {case['id']}.")
        if date.fromisoformat(case["roleStartDate"]) >= date.fromisoformat(case["announcementDate"]):
            errors.append(f"Outcome role start must precede announcement for {case['id']}.")
        if date.fromisoformat(case["announcementDate"]) > date.fromisoformat(as_of):
            errors.append(f"Future-dated calibration outcome: {case['id']}.")
        if case.get("departureDate") and date.fromisoformat(case["departureDate"]) < date.fromisoformat(case["announcementDate"]):
            errors.append(f"Outcome departure predates announcement for {case['id']}.")

    completed_cases = [case for case in outcome_cases if case["cohort"] == "completed"]
    completed_by_id = {case["id"]: case for case in completed_cases}
    reviews = historical.get("reviews", [])
    review_ids = [review.get("outcomeId") for review in reviews]
    if len(review_ids) != len(set(review_ids)):
        errors.append("Duplicate historical-evidence review found.")
    if set(review_ids) != set(completed_by_id):
        missing = sorted(set(completed_by_id) - set(review_ids))
        unexpected = sorted(set(review_ids) - set(completed_by_id))
        errors.append(f"Historical review coverage mismatch; missing={missing}, unexpected={unexpected}.")
    review_by_outcome = {review["outcomeId"]: review for review in reviews}
    for review in reviews:
        case = completed_by_id.get(review["outcomeId"])
        if not case:
            continue
        if review.get("ticker") != case["ticker"]:
            errors.append(f"Historical review ticker mismatch for {case['id']}.")
        if review.get("windowStart") != years_ago(case["announcementDate"], 3) or review.get("windowEnd") != case["announcementDate"]:
            errors.append(f"Historical review window is not aligned to 36 months for {case['id']}.")
        for coverage_name in ("warningCoverage", "dissentCoverage"):
            coverage = review.get(coverage_name, {})
            if coverage.get("status") not in ALLOWED_COVERAGE_STATUSES:
                errors.append(f"Unsupported {coverage_name} status for {case['id']}.")
            if not coverage.get("sourceUrl", "").startswith("https://"):
                errors.append(f"Missing HTTPS {coverage_name} source for {case['id']}.")
            if not coverage.get("reviewNote", "").strip():
                errors.append(f"Missing {coverage_name} review note for {case['id']}.")

    historical_warning_ids = [event.get("id") for event in historical.get("warningEvents", [])]
    historical_dissent_ids = [event.get("id") for event in historical.get("dissentEvents", [])]
    if len(historical_warning_ids) != len(set(historical_warning_ids)):
        errors.append("Duplicate historical warning-event ID found.")
    if len(historical_dissent_ids) != len(set(historical_dissent_ids)):
        errors.append("Duplicate historical dissent-event ID found.")
    historical_warnings_by_outcome: dict[str, list[dict[str, Any]]] = {}
    historical_dissent_by_outcome: dict[str, list[dict[str, Any]]] = {}
    for event in historical.get("warningEvents", []):
        case = completed_by_id.get(event.get("outcomeId"))
        if not case:
            errors.append(f"Historical warning references an unknown outcome: {event.get('id')}.")
            continue
        review = review_by_outcome[case["id"]]
        try:
            event_date = date.fromisoformat(event.get("announcementDate", ""))
        except ValueError:
            errors.append(f"Historical warning date is invalid for {event.get('id')}.")
            continue
        if event.get("ticker") != case["ticker"] or not date.fromisoformat(review["windowStart"]) <= event_date <= date.fromisoformat(review["windowEnd"]):
            errors.append(f"Historical warning is misaligned for {event.get('id')}.")
        if event.get("severity") not in {"material", "severe"} or event.get("eventType") not in {"guidance-cut", "material-profit-impact"}:
            errors.append(f"Historical warning classification is invalid for {event.get('id')}.")
        if not event.get("sourceUrl", "").startswith("https://") or not event.get("summary", "").strip():
            errors.append(f"Historical warning source or summary is missing for {event.get('id')}.")
        historical_warnings_by_outcome.setdefault(case["id"], []).append(event)
    for event in historical.get("dissentEvents", []):
        case = completed_by_id.get(event.get("outcomeId"))
        if not case:
            errors.append(f"Historical dissent references an unknown outcome: {event.get('id')}.")
            continue
        review = review_by_outcome[case["id"]]
        pct = event.get("votesAgainstPct")
        try:
            meeting_date = date.fromisoformat(event.get("meetingDate", ""))
        except ValueError:
            errors.append(f"Historical dissent date is invalid for {event.get('id')}.")
            continue
        if event.get("ticker") != case["ticker"] or not date.fromisoformat(review["windowStart"]) <= meeting_date <= date.fromisoformat(review["windowEnd"]):
            errors.append(f"Historical dissent is misaligned for {event.get('id')}.")
        if not isinstance(pct, (int, float)) or not 20 <= pct <= 100:
            errors.append(f"Historical dissent percentage is impossible for {event.get('id')}.")
        if event.get("managementSponsored") is not True:
            errors.append(f"Historical dissent is not management-sponsored for {event.get('id')}.")
        if not event.get("sourceUrl", "").startswith("https://") or not event.get("resolutionTitle", "").strip():
            errors.append(f"Historical dissent source or title is missing for {event.get('id')}.")
        historical_dissent_by_outcome.setdefault(case["id"], []).append(event)

    dissent_by_ticker: dict[str, list[dict[str, Any]]] = {}
    alias_to_ticker = {
        normalise(alias): company["ticker"]
        for company in companies
        for alias in company.get("trackerAliases", [])
    }
    for record in tracker["resolutions"]:
        ticker = alias_to_ticker.get(normalise(record["companyName"]))
        pct = record.get("votesAgainstPct")
        if not ticker or pct is None or pct < 20 or record["resolutionCategory"] == "shareholder-proposal":
            continue
        dissent_by_ticker.setdefault(ticker, []).append(record)

    def enrich(record: dict[str, Any], cutoff: str) -> dict[str, Any]:
        cutoff_date = date.fromisoformat(cutoff)
        historical_review = review_by_outcome.get(record["id"])
        if historical_review:
            prior_warnings = historical_warnings_by_outcome.get(record["id"], [])
            prior_dissent = historical_dissent_by_outcome.get(record["id"], [])
        else:
            warning_start = cutoff_date - timedelta(days=round(warnings["lookbackMonths"] * 365.2425 / 12))
            prior_warnings = [
                event for event in warnings["events"]
                if event["ticker"] == record["ticker"]
                and warning_start <= date.fromisoformat(event["announcementDate"]) <= cutoff_date
            ]
            prior_dissent = [
                item for item in dissent_by_ticker.get(record["ticker"], [])
                if date.fromisoformat(item["meetingDate"]) <= cutoff_date
            ]
        tenure_years = years_between(record["roleStartDate"], cutoff)
        max_dissent = max((item["votesAgainstPct"] for item in prior_dissent), default=None)
        baseline = tenure_pressure(record["role"], tenure_years)
        warning_score = min(100, baseline + warning_uplift(prior_warnings))
        market_record = market_by_ticker.get(record["ticker"])
        window_start = max(date.fromisoformat(record["roleStartDate"]), cutoff_date - timedelta(days=730))
        market_points = [
            point for point in market_record["points"]
            if window_start <= date.fromisoformat(point["date"]) <= cutoff_date
        ] if market_record else []
        relative_performance = None
        company_return = None
        benchmark_return = None
        if len(market_points) >= 2:
            first_point, last_point = market_points[0], market_points[-1]
            first_benchmark = benchmark_by_month.get(first_point["date"][:7])
            last_benchmark = benchmark_by_month.get(last_point["date"][:7])
            if first_benchmark and last_benchmark:
                company_return = (float(last_point["adjustedClose"]) / float(first_point["adjustedClose"]) - 1) * 100
                benchmark_return = (float(last_benchmark["close"]) / float(first_benchmark["close"]) - 1) * 100
                relative_performance = company_return - benchmark_return
        combined_score = min(100, warning_score + performance_uplift(relative_performance))
        return {
            **record,
            "cutoffDate": cutoff,
            "tenureYears": tenure_years,
            "longTenure": tenure_years >= (8 if record["role"] == "ceo" else 7),
            "priorWarningCount": len(prior_warnings),
            "priorSevereWarningCount": sum(event["severity"] == "severe" for event in prior_warnings),
            "priorWarningIds": [event["id"] for event in prior_warnings],
            "priorDissentCount": len(prior_dissent),
            "maxPriorDissentPct": max_dissent,
            "priorDissentIds": [item["id"] for item in prior_dissent],
            "warningCoverageStatus": historical_review["warningCoverage"]["status"] if historical_review else "current-window",
            "dissentCoverageStatus": historical_review["dissentCoverage"]["status"] if historical_review else "current-window",
            "baselineScore": round(baseline, 1),
            "exploratoryWarningUplift": warning_uplift(prior_warnings),
            "warningSensitivityScore": round(warning_score, 1),
            "marketWindowStart": market_points[0]["date"] if market_points else None,
            "marketWindowEnd": market_points[-1]["date"] if market_points else None,
            "companyDividendAdjustedReturnPct": round(company_return, 1) if company_return is not None else None,
            "benchmarkPriceReturnPct": round(benchmark_return, 1) if benchmark_return is not None else None,
            "relativePerformancePct": round(relative_performance, 1) if relative_performance is not None else None,
            "marketStress": relative_performance is not None and relative_performance <= -20,
            "exploratoryPerformanceUplift": performance_uplift(relative_performance),
            "combinedSensitivityScore": round(combined_score, 1),
        }

    enriched_outcomes = [enrich(case, case["announcementDate"]) for case in outcome_cases]
    active_keys = {(case["ticker"], case["role"]) for case in outcome_cases if case["cohort"] == "active"}
    comparisons: list[dict[str, Any]] = []
    for company in radar["companies"]:
        for role_name in ("ceo", "chair"):
            role = company["roles"][role_name]
            if not role.get("rated") or (company["ticker"], role_name) in active_keys:
                continue
            comparisons.append(enrich({
                "id": f"{company['ticker'].lower()}-{role_name}-comparison",
                "ticker": company["ticker"],
                "companyName": company["companyName"],
                "role": role_name,
                "incumbentName": role["name"],
                "roleStartDate": role["roleStartDate"],
                "cohort": "current-comparison",
            }, as_of))

    baseline_threshold = percentile([record["baselineScore"] for record in comparisons], 0.75)
    warning_threshold = percentile([record["warningSensitivityScore"] for record in comparisons], 0.75)
    combined_threshold = percentile([record["combinedSensitivityScore"] for record in comparisons], 0.75)
    sensitivity = {
        "baselineTopQuartileThreshold": baseline_threshold,
        "baselineOutcomeCapturePct": capture_rate(enriched_outcomes, "baselineScore", baseline_threshold),
        "warningTopQuartileThreshold": warning_threshold,
        "warningOutcomeCapturePct": capture_rate(enriched_outcomes, "warningSensitivityScore", warning_threshold),
        "candidateWarningRule": "Exploratory only: 6 points for a material warning or 12 for any severe warning, plus 3 for each repeat event, capped at 18.",
        "combinedTopQuartileThreshold": combined_threshold,
        "combinedOutcomeCapturePct": capture_rate(enriched_outcomes, "combinedSensitivityScore", combined_threshold),
        "candidatePerformanceRule": "Exploratory only: 8 points for trailing relative underperformance of at least 20 percentage points and 15 points at 40 percentage points.",
    }

    completed_outcomes = sorted(
        (record for record in enriched_outcomes if record["cohort"] == "completed"),
        key=lambda record: record["announcementDate"],
    )
    holdout_size = min(6, max(1, len(completed_outcomes) // 4))
    training_outcomes = completed_outcomes[:-holdout_size]
    holdout_outcomes = completed_outcomes[-holdout_size:]
    held_out_validation = {
        "design": "Out-of-time holdout using the six most recent completed transitions. Risk thresholds are the current-comparison cohort's 75th percentiles and do not use outcome observations.",
        "trainingOutcomeIds": [record["id"] for record in training_outcomes],
        "holdoutOutcomeIds": [record["id"] for record in holdout_outcomes],
        "thresholdSource": "current-comparison-only",
        "thresholds": {
            "tenureOnly": baseline_threshold,
            "tenureAndWarnings": warning_threshold,
            "tenureWarningsAndPerformance": combined_threshold,
        },
        "trainingCapturePct": {
            "tenureOnly": capture_rate(training_outcomes, "baselineScore", baseline_threshold),
            "tenureAndWarnings": capture_rate(training_outcomes, "warningSensitivityScore", warning_threshold),
            "tenureWarningsAndPerformance": capture_rate(training_outcomes, "combinedSensitivityScore", combined_threshold),
        },
        "holdoutCapturePct": {
            "tenureOnly": capture_rate(holdout_outcomes, "baselineScore", baseline_threshold),
            "tenureAndWarnings": capture_rate(holdout_outcomes, "warningSensitivityScore", warning_threshold),
            "tenureWarningsAndPerformance": capture_rate(holdout_outcomes, "combinedSensitivityScore", combined_threshold),
        },
        "caveat": "Six holdout cases are sufficient to detect gross overfitting, not to estimate stable predictive accuracy. Current comparisons are right-censored rather than confirmed negatives.",
    }

    if errors:
        raise RuntimeError("; ".join(errors))

    recommendation = {
        "decision": "retain-current-weights",
        "rationale": "Warning and market-performance signals now use announcement-aligned windows and have been tested on a small out-of-time holdout. The sample remains too small and current comparisons are right-censored, so exploratory uplifts do not become production weights.",
        "minimumNextEvidence": "Expand to at least 50 completed outcomes, preserve an untouched out-of-time holdout, and establish complete resolution-level AGM coverage before testing dissent as a predictive input.",
    }
    payload = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "asOfDate": as_of,
            "methodologyVersion": "0.3",
            "outcomeCount": len(enriched_outcomes),
            "completedOutcomeCount": sum(record["cohort"] == "completed" for record in enriched_outcomes),
            "activeOutcomeCount": sum(record["cohort"] == "active" for record in enriched_outcomes),
            "comparisonObservationCount": len(comparisons),
            "excludedActiveCases": excluded_active,
            "validation": {"status": "pass", "errors": []},
            "historicalEvidence": {
                "reviewedOutcomeCount": len(reviews),
                "completeWarningWindowCount": sum(review["warningCoverage"]["status"] == "complete" for review in reviews),
                "completeDissentWindowCount": sum(review["dissentCoverage"]["status"] == "complete" for review in reviews),
                "warningEventCount": len(historical.get("warningEvents", [])),
                "dissentEventCount": len(historical.get("dissentEvents", [])),
            },
        },
        "method": {
            "outcomeDefinition": "An official issuer announcement of a CEO or Chair departure, retirement, board-led replacement or active succession process.",
            "caseSelectionRule": "Completed cases are included only where an official issuer source identifies the incumbent, transition outcome and announcement timing. The cohort is high-confidence and purposive, not a complete census of FTSE 100 transitions.",
            "cutoffRule": "Completed-outcome warning evidence uses a fixed 36-month window ending on the transition announcement. Market evidence ends at the announcement. Current comparison observations use the evidence date.",
            "datePrecisionRule": "Where an issuer source gives only a month for a role start, the first day is stored for calculation and roleStartDatePrecision is set to month; this can shift calculated tenure by less than one month.",
            "longTenureRule": "Eight years for a CEO and seven years for a Chair, used as an exploratory discriminator rather than a governance breach threshold.",
            "marketPerformanceTreatment": "Exploratory two-year dividend-adjusted company return less FTSE 100 price-index return. Isolated GBP/GBp scale switches are corrected and validated before use.",
            "limitations": [
                "This is a retrospective discrimination audit, not a prospective probability model.",
                "The outcome cohort is deliberately high-confidence and purposive rather than comprehensive.",
                "Current-role comparisons are right-censored observations, not proven non-events.",
                "Historical voting evidence is event-backed but meeting coverage remains partial, so dissent is disclosed but excluded from the aligned score.",
                "Historical profit-warning reviews cover all completed outcomes but depend on issuer archive availability and the stated strict warning definition.",
                "The market comparison mixes a dividend-adjusted company proxy with a price-only benchmark and is suitable only for sensitivity analysis.",
            ],
        },
        "summary": {
            "outcomes": group_summary(enriched_outcomes),
            "currentComparisons": group_summary(comparisons),
            "sensitivity": sensitivity,
            "heldOutValidation": held_out_validation,
            "recommendation": recommendation,
        },
        "outcomes": enriched_outcomes,
        "currentComparisons": comparisons,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    radar["metadata"]["calibration"] = {
        "methodologyVersion": payload["metadata"]["methodologyVersion"],
        "outcomeCount": payload["metadata"]["outcomeCount"],
        "comparisonObservationCount": payload["metadata"]["comparisonObservationCount"],
        "decision": recommendation["decision"],
        "note": recommendation["rationale"],
    }
    RADAR_PATH.write_text(json.dumps(radar, indent=2) + "\n", encoding="utf-8")
    print(f"Built calibration audit with {len(enriched_outcomes)} outcomes and {len(comparisons)} comparison observations.")


if __name__ == "__main__":
    main()
