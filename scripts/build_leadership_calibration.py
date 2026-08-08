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
SUCCESSION_PATH = ROOT / "data" / "succession_sources.json"
TRACKER_PATH = ROOT / "public" / "data" / "tracker-data.json"
RADAR_PATH = ROOT / "public" / "data" / "leadership-radar.json"
MARKET_PATH = ROOT / "public" / "data" / "market-performance.json"
OUTPUT_PATH = ROOT / "public" / "data" / "leadership-calibration.json"


def normalise(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def years_between(start: str, end: str) -> float:
    return round((date.fromisoformat(end) - date.fromisoformat(start)).days / 365.2425, 1)


def tenure_pressure(role: str, tenure_years: float) -> float:
    reference_years = 10 if role == "ceo" else 9
    return round(min(80, max(0, tenure_years / reference_years * 80)), 1)


def dissent_uplift(max_against: float | None, count: int) -> float:
    if max_against is None:
        return 0
    base = 15 if max_against >= 50 else 8 if max_against >= 30 else 4 if max_against >= 20 else 0
    return float(min(20, base + max(0, count - 1) * 3))


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
        if not case["sourceUrl"].startswith("https://"):
            errors.append(f"Outcome source must use HTTPS for {case['id']}.")
        if date.fromisoformat(case["roleStartDate"]) >= date.fromisoformat(case["announcementDate"]):
            errors.append(f"Outcome role start must precede announcement for {case['id']}.")
        if date.fromisoformat(case["announcementDate"]) > date.fromisoformat(as_of):
            errors.append(f"Future-dated calibration outcome: {case['id']}.")

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
        baseline = min(100, tenure_pressure(record["role"], tenure_years) + dissent_uplift(max_dissent, len(prior_dissent)))
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

    pooled = [*enriched_outcomes, *comparisons]
    baseline_threshold = percentile([record["baselineScore"] for record in pooled], 0.75)
    warning_threshold = percentile([record["warningSensitivityScore"] for record in pooled], 0.75)
    combined_threshold = percentile([record["combinedSensitivityScore"] for record in pooled], 0.75)
    sensitivity = {
        "baselineTopQuartileThreshold": baseline_threshold,
        "baselineOutcomeCapturePct": round(sum(record["baselineScore"] >= baseline_threshold for record in enriched_outcomes) / len(enriched_outcomes) * 100, 1),
        "warningTopQuartileThreshold": warning_threshold,
        "warningOutcomeCapturePct": round(sum(record["warningSensitivityScore"] >= warning_threshold for record in enriched_outcomes) / len(enriched_outcomes) * 100, 1),
        "candidateWarningRule": "Exploratory only: 6 points for a material warning or 12 for any severe warning, plus 3 for each repeat event, capped at 18.",
        "combinedTopQuartileThreshold": combined_threshold,
        "combinedOutcomeCapturePct": round(sum(record["combinedSensitivityScore"] >= combined_threshold for record in enriched_outcomes) / len(enriched_outcomes) * 100, 1),
        "candidatePerformanceRule": "Exploratory only: 8 points for trailing relative underperformance of at least 20 percentage points and 15 points at 40 percentage points.",
    }

    if errors:
        raise RuntimeError("; ".join(errors))

    recommendation = {
        "decision": "retain-current-weights",
        "rationale": "The cohort is directionally useful but too small and temporally uneven to justify production score changes. Warning and market-performance sensitivities remain research-only, and the combined model does not improve top-quartile capture beyond warnings alone.",
        "minimumNextEvidence": "Expand to at least 30 source-backed transition outcomes with aligned 36-month warning, voting and market-performance histories before estimating or promoting new weights.",
    }
    payload = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "asOfDate": as_of,
            "methodologyVersion": "0.1",
            "outcomeCount": len(enriched_outcomes),
            "completedOutcomeCount": sum(record["cohort"] == "completed" for record in enriched_outcomes),
            "activeOutcomeCount": sum(record["cohort"] == "active" for record in enriched_outcomes),
            "comparisonObservationCount": len(comparisons),
            "excludedActiveCases": excluded_active,
            "validation": {"status": "pass", "errors": []},
        },
        "method": {
            "outcomeDefinition": "An official issuer announcement of a CEO or Chair departure, retirement, board-led replacement or active succession process.",
            "cutoffRule": "Outcome signals are counted only when dated on or before the transition announcement. Current comparison observations use the evidence date.",
            "longTenureRule": "Eight years for a CEO and seven years for a Chair, used as an exploratory discriminator rather than a governance breach threshold.",
            "marketPerformanceTreatment": "Exploratory two-year dividend-adjusted company return less FTSE 100 price-index return. Isolated GBP/GBp scale switches are corrected and validated before use.",
            "limitations": [
                "This is a retrospective discrimination audit, not a prospective probability model.",
                "The outcome cohort is small and deliberately high-confidence rather than comprehensive.",
                "Current-role comparisons are right-censored observations, not proven non-events.",
                "The voting dataset is concentrated in 2025 and cannot provide an aligned history for every outcome.",
                "Profit-warning coverage is limited to the curated 36-month evidence window.",
                "The market comparison mixes a dividend-adjusted company proxy with a price-only benchmark and is suitable only for sensitivity analysis.",
            ],
        },
        "summary": {
            "outcomes": group_summary(enriched_outcomes),
            "currentComparisons": group_summary(comparisons),
            "sensitivity": sensitivity,
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
