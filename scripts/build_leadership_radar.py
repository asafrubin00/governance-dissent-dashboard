#!/usr/bin/env python3
"""Build the source-backed FTSE 100 leadership pressure radar dataset."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "leadership_sources.json"
EXPANSION_SOURCE_PATH = ROOT / "data" / "leadership_sources_expansion.json"
PROFIT_WARNING_PATH = ROOT / "data" / "profit_warning_sources.json"
PROFIT_WARNING_REVIEW_PATH = ROOT / "data" / "profit_warning_reviews.json"
SUCCESSION_PATH = ROOT / "data" / "succession_sources.json"
ROSTER_PATH = ROOT / "data" / "ftse100_constituents.json"
TRACKER_PATH = ROOT / "public" / "data" / "tracker-data.json"
OUTPUT_PATH = ROOT / "public" / "data" / "leadership-radar.json"
ROSTER_URL = "https://en.wikipedia.org/wiki/FTSE_100_Index"


def normalise(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def fetch_roster() -> list[dict[str, str]]:
    response = requests.get(
        ROSTER_URL,
        headers={"User-Agent": "ProxyWarsGovernanceResearch/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if not first_row:
            continue
        headers = [cell.get_text(" ", strip=True) for cell in first_row.find_all(["th", "td"])]
        if "Company" not in headers or "Ticker" not in headers:
            continue

        rows = []
        for row in table.find_all("tr")[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if len(cells) < 3:
                continue
            rows.append({"companyName": cells[0], "ticker": cells[1], "sector": cells[2]})
        if len(rows) == 100:
            return rows

    raise RuntimeError("Could not find a 100-company constituent table.")


def load_roster() -> tuple[list[dict[str, str]], str]:
    try:
        roster = fetch_roster()
        ROSTER_PATH.write_text(json.dumps(roster, indent=2) + "\n", encoding="utf-8")
        return roster, "live-public-snapshot"
    except Exception as error:
        if not ROSTER_PATH.exists():
            raise
        print(f"Roster refresh failed; using cached snapshot: {error}")
        return json.loads(ROSTER_PATH.read_text(encoding="utf-8")), "cached-public-snapshot"


def years_between(start: str, end: str) -> float:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    return round((end_date - start_date).days / 365.2425, 1)


def tenure_pressure(role: str, tenure_years: float) -> float:
    reference_years = 10 if role == "ceo" else 9
    return round(min(80, max(0, tenure_years / reference_years * 80)), 1)


def dissent_uplift(max_against: float | None, count: int) -> float:
    if max_against is None:
        return 0
    if max_against >= 50:
        base = 15
    elif max_against >= 30:
        base = 8
    elif max_against >= 20:
        base = 4
    else:
        base = 0
    return float(min(20, base + max(0, count - 1) * 3))


def pressure_band(score: float) -> str:
    if score >= 70:
        return "Acute"
    if score >= 50:
        return "Elevated"
    if score >= 25:
        return "Watch"
    return "Lower"


def management_dissent_by_company() -> dict[str, dict[str, Any]]:
    tracker = json.loads(TRACKER_PATH.read_text(encoding="utf-8"))
    grouped: dict[str, dict[str, Any]] = {}
    excluded_terms = ("SHAREHOLDER REQUISITION", "SHAREHOLDER-REQUISITION")

    for row in tracker["resolutions"]:
        title = row["resolutionTitle"].upper()
        if row["resolutionCategory"] == "shareholder-proposal" or any(term in title for term in excluded_terms):
            continue
        pct = row.get("votesAgainstPct")
        if pct is None or pct < 20:
            continue
        key = normalise(row["companyName"])
        current = grouped.setdefault(key, {"count": 0, "maxVotesAgainstPct": None, "records": []})
        current["count"] += 1
        current["maxVotesAgainstPct"] = max(current["maxVotesAgainstPct"] or 0, pct)
        current["records"].append(
            {
                "id": row["id"],
                "title": row["resolutionTitle"],
                "votesAgainstPct": pct,
                "meetingDate": row["meetingDate"],
            }
        )
    return grouped


def profit_warnings_by_company(
    warning_source: dict[str, Any],
    roster_tickers: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    allowed_types = {"guidance-cut", "material-profit-impact"}
    allowed_severities = {"material", "severe"}
    as_of = date.fromisoformat(warning_source["asOfDate"])
    lookback_months = warning_source["lookbackMonths"]
    lookback_days = round(lookback_months * 365.2425 / 12)
    grouped: dict[str, dict[str, Any]] = {}

    for event in warning_source["events"]:
        event_id = event.get("id", "")
        ticker = event.get("ticker", "")
        if not event_id or event_id in seen_ids:
            errors.append(f"Missing or duplicate profit-warning event ID: {event_id or '[blank]' }.")
        seen_ids.add(event_id)
        if ticker not in roster_tickers:
            errors.append(f"Profit-warning ticker is outside the current roster: {ticker}.")
        if event.get("eventType") not in allowed_types:
            errors.append(f"Unsupported profit-warning event type for {event_id}.")
        if event.get("severity") not in allowed_severities:
            errors.append(f"Unsupported profit-warning severity for {event_id}.")
        if not event.get("companyName") or not event.get("sourceUrl") or not event.get("summary"):
            errors.append(f"Missing required profit-warning evidence for {event_id}.")
        try:
            event_date = date.fromisoformat(event["announcementDate"])
        except (KeyError, ValueError):
            errors.append(f"Invalid profit-warning date for {event_id}.")
            continue
        if event_date > as_of:
            errors.append(f"Future-dated profit-warning event: {event_id}.")
        if (as_of - event_date).days > lookback_days:
            errors.append(f"Profit-warning event falls outside the {lookback_months}-month window: {event_id}.")
        change_pct = event.get("changePct")
        if change_pct is not None and not -100 <= change_pct <= 0:
            errors.append(f"Impossible profit-warning percentage change for {event_id}.")
        grouped.setdefault(ticker, {"count": 0, "latestDate": None, "events": []})
        grouped[ticker]["count"] += 1
        grouped[ticker]["events"].append(event)
        if grouped[ticker]["latestDate"] is None or event["announcementDate"] > grouped[ticker]["latestDate"]:
            grouped[ticker]["latestDate"] = event["announcementDate"]

    for evidence in grouped.values():
        evidence["events"].sort(key=lambda item: item["announcementDate"], reverse=True)
    return grouped, errors


def validate_profit_warning_reviews(
    review_source: dict[str, Any],
    curated_tickers: set[str],
    warning_tickers: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    reviews = review_source.get("reviews", [])
    review_tickers = [review.get("ticker") for review in reviews]
    allowed_outcomes = {"qualifying-event-captured", "reviewed-no-qualifying-event"}
    if set(review_tickers) != curated_tickers or len(review_tickers) != len(curated_tickers):
        errors.append("Profit-warning reviews do not exactly cover the verified leadership cohort.")
    if len(review_tickers) != len(set(review_tickers)):
        errors.append("Duplicate profit-warning review ticker found.")
    captured_tickers = set()
    for review in reviews:
        if review.get("outcome") not in allowed_outcomes:
            errors.append(f"Unsupported profit-warning review outcome for {review.get('ticker')}.")
        if not review.get("sourceUrl") or not review.get("reviewNote"):
            errors.append(f"Missing profit-warning review evidence for {review.get('ticker')}.")
        if review.get("outcome") == "qualifying-event-captured":
            captured_tickers.add(review.get("ticker"))
    if captured_tickers != warning_tickers:
        errors.append("Captured profit-warning review tickers do not match the event dataset.")
    return {review["ticker"]: review for review in reviews}, errors


def succession_by_company(
    succession_source: dict[str, Any],
    curated_by_ticker: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    curated_tickers = set(curated_by_ticker)
    reviewed_tickers = succession_source.get("reviewedTickers", [])
    if set(reviewed_tickers) != curated_tickers or len(reviewed_tickers) != len(curated_tickers):
        errors.append("Succession reviews do not exactly cover the verified leadership cohort.")
    if len(reviewed_tickers) != len(set(reviewed_tickers)):
        errors.append("Duplicate succession review ticker found.")
    allowed_statuses = {"search-underway", "successor-announced", "departure-announced"}
    grouped: dict[str, dict[str, Any]] = {}
    seen_ids: set[str] = set()
    as_of = date.fromisoformat(succession_source["asOfDate"])
    for case in succession_source.get("cases", []):
        case_id = case.get("id", "")
        ticker = case.get("ticker", "")
        role = case.get("role")
        if not case_id or case_id in seen_ids:
            errors.append(f"Missing or duplicate succession case ID: {case_id or '[blank]'}.")
        seen_ids.add(case_id)
        if ticker not in curated_tickers or role not in {"ceo", "chair"}:
            errors.append(f"Invalid succession ticker or role for {case_id}.")
            continue
        if case.get("status") not in allowed_statuses:
            errors.append(f"Unsupported succession status for {case_id}.")
        if case.get("incumbentName") != curated_by_ticker[ticker]["roles"][role]["name"]:
            errors.append(f"Succession incumbent does not match leadership evidence for {case_id}.")
        if not case.get("sourceUrl") or not case.get("summary"):
            errors.append(f"Missing succession evidence for {case_id}.")
        try:
            if date.fromisoformat(case["announcedDate"]) > as_of:
                errors.append(f"Future-dated succession case: {case_id}.")
        except (KeyError, ValueError):
            errors.append(f"Invalid succession announcement date for {case_id}.")
        grouped.setdefault(ticker, {"count": 0, "cases": []})
        grouped[ticker]["count"] += 1
        grouped[ticker]["cases"].append(case)
    return grouped, errors


def validate(
    roster: list[dict[str, str]],
    curated: list[dict[str, Any]],
    companies: list[dict[str, Any]],
    as_of: str,
    warning_errors: list[str],
    review_errors: list[str],
    succession_errors: list[str],
) -> dict[str, Any]:
    errors: list[str] = [*warning_errors, *review_errors, *succession_errors]
    tickers = [row["ticker"] for row in roster]
    if len(roster) != 100:
        errors.append(f"Expected 100 constituents, found {len(roster)}.")
    if len(tickers) != len(set(tickers)):
        errors.append("Duplicate constituent tickers found.")
    if len({row["ticker"] for row in curated}) != len(curated):
        errors.append("Duplicate curated leadership tickers found.")
    roster_tickers = set(tickers)
    curated_tickers = {row["ticker"] for row in curated}
    if curated_tickers != roster_tickers:
        errors.append("Leadership evidence does not exactly match the current FTSE 100 roster.")
    for company in companies:
        for role_name, role in company["roles"].items():
            if role["score"] is not None and not 0 <= role["score"] <= 100:
                errors.append(f"Impossible {role_name} score for {company['ticker']}.")
            if role["rated"] and not role.get("sourceUrl"):
                errors.append(f"Missing source URL for {company['ticker']} {role_name}.")
            if role.get("notApplicable") and not role.get("sourceUrl"):
                errors.append(f"Missing structural source for {company['ticker']} {role_name}.")
            if role.get("sourceUrl") and not role["sourceUrl"].startswith("https://"):
                errors.append(f"Non-HTTPS source URL for {company['ticker']} {role_name}.")
            if role.get("roleStartDate") and date.fromisoformat(role["roleStartDate"]) > date.fromisoformat(as_of):
                errors.append(f"Future role start date for {company['ticker']} {role_name}.")
    return {"status": "pass" if not errors else "fail", "errors": errors}


def main() -> None:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    expansion = json.loads(EXPANSION_SOURCE_PATH.read_text(encoding="utf-8"))
    source["companies"] = [*source["companies"], *expansion["companies"]]
    warning_source = json.loads(PROFIT_WARNING_PATH.read_text(encoding="utf-8"))
    warning_review_source = json.loads(PROFIT_WARNING_REVIEW_PATH.read_text(encoding="utf-8"))
    succession_source = json.loads(SUCCESSION_PATH.read_text(encoding="utf-8"))
    roster, roster_mode = load_roster()
    dissent = management_dissent_by_company()
    warnings, warning_errors = profit_warnings_by_company(
        warning_source,
        {row["ticker"] for row in roster},
    )
    curated_by_ticker = {row["ticker"]: row for row in source["companies"]}
    warning_reviews, review_errors = validate_profit_warning_reviews(
        warning_review_source,
        set(curated_by_ticker),
        set(warnings),
    )
    successions, succession_errors = succession_by_company(succession_source, curated_by_ticker)
    as_of = source["asOfDate"]
    companies = []

    for constituent in roster:
        curated = curated_by_ticker.get(constituent["ticker"])
        role_output: dict[str, Any] = {}
        aliases = curated.get("trackerAliases", []) if curated else []
        dissent_record = next(
            (dissent[normalise(alias)] for alias in aliases if normalise(alias) in dissent),
            None,
        )
        warning_record = warnings.get(
            constituent["ticker"],
            {"count": 0, "latestDate": None, "events": []},
        )
        warning_record = {
            **warning_record,
            "review": warning_reviews.get(constituent["ticker"]),
        }
        succession_record = successions.get(
            constituent["ticker"],
            {"count": 0, "cases": []},
        )

        for role_name in ("ceo", "chair"):
            if not curated or role_name not in curated["roles"]:
                role_output[role_name] = {
                    "rated": False,
                    "score": None,
                    "band": "Unrated",
                    "reason": "Leadership evidence not yet researched for this release.",
                }
                continue

            role = curated["roles"][role_name]
            if role.get("status") == "not-applicable":
                role_output[role_name] = {
                    **role,
                    "rated": False,
                    "notApplicable": True,
                    "score": None,
                    "band": "Not applicable",
                }
                continue
            tenure_years = years_between(role["roleStartDate"], as_of)
            tenure_score = tenure_pressure(role_name, tenure_years)
            max_against = dissent_record["maxVotesAgainstPct"] if dissent_record else None
            dissent_count = dissent_record["count"] if dissent_record else 0
            uplift = dissent_uplift(max_against, dissent_count)
            score = round(min(100, tenure_score + uplift), 1)
            role_output[role_name] = {
                **role,
                "rated": True,
                "tenureYears": tenure_years,
                "score": score,
                "band": pressure_band(score),
                "components": {
                    "tenurePressure": tenure_score,
                    "registeredDissentUplift": uplift,
                },
                "dissentEvidence": dissent_record or {
                    "count": 0,
                    "maxVotesAgainstPct": None,
                    "records": [],
                },
                "reason": (
                    f"{tenure_years:.1f} years in role"
                    + (f" plus {dissent_count} qualifying management-resolution dissent signal(s)." if dissent_count else "; no qualifying management-resolution dissent signal is added in the current tracker window.")
                ),
            }

        companies.append({
            **constituent,
            "roles": role_output,
            "profitWarningEvidence": warning_record,
            "successionEvidence": succession_record,
        })

    validation = validate(
        roster,
        source["companies"],
        companies,
        as_of,
        warning_errors,
        review_errors,
        succession_errors,
    )
    if validation["status"] != "pass":
        raise RuntimeError("; ".join(validation["errors"]))

    payload = {
        "metadata": {
            "title": "FTSE 100 Leadership Pressure Radar",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "asOfDate": as_of,
            "methodologyVersion": source["methodologyVersion"],
            "rosterSource": {
                "name": "Wikipedia FTSE 100 constituent table",
                "url": ROSTER_URL,
                "mode": roster_mode,
                "note": "Used only as a reproducible public constituent snapshot; FTSE Russell remains the index authority.",
            },
            "sourceVerifiedCompanyCount": len(source["companies"]),
            "ratedCompanyCount": sum(
                1 for company in companies if company["roles"]["ceo"]["rated"] and company["roles"]["chair"]["rated"]
            ),
            "constituentCount": len(roster),
            "profitWarningCoverage": {
                "eventCount": len(warning_source["events"]),
                "companyCount": len(warnings),
                "reviewedCompanyCount": len(warning_review_source["reviews"]),
                "asOfDate": warning_source["asOfDate"],
                "lookbackMonths": warning_source["lookbackMonths"],
                "definition": warning_source["definition"],
                "scoreTreatment": "Displayed as a source-verified overlay and excluded from the pressure score pending calibration and outcome testing.",
            },
            "successionCoverage": {
                "activeCaseCount": len(succession_source["cases"]),
                "reviewedCompanyCount": len(succession_source["reviewedTickers"]),
                "asOfDate": succession_source["asOfDate"],
                "definition": succession_source["definition"],
                "scoreTreatment": "Displayed as a source-verified status and excluded from the pressure score.",
            },
            "scoreDefinition": {
                "label": "Leadership transition pressure",
                "notAProbability": True,
                "ceo": "Tenure pressure rises over a ten-year reference horizon, capped at 80 points.",
                "chair": "Tenure pressure rises toward the UK Code's nine-year chair independence and succession reference point, capped at 80 points.",
                "dissent": "Up to 20 additional points reflect verified 20%+ dissent on management-sponsored resolutions in the existing tracker window. Shareholder proposals are excluded.",
                "profitWarnings": "Qualifying official issuer events are shown as an evidence overlay but do not yet alter the score.",
                "succession": "Officially announced active CEO and Chair succession processes are shown as a status overlay but do not alter the score.",
                "bands": {"Lower": "0-24", "Watch": "25-49", "Elevated": "50-69", "Acute": "70-100"},
            },
            "limitations": [
                "This is a research prioritisation score, not a prediction that an individual will leave office.",
                f"All {len(source['companies'])} companies have source-verified leadership records in methodology {source['methodologyVersion']}; externally managed issuers without a chief executive are marked not applicable rather than scored.",
                "The dissent uplift uses the narrow 2025 significant-dissent dataset and is not a complete voting-history measure.",
                f"The profit-warning review covers {len(warning_review_source['reviews'])} of {len(source['companies'])} source-verified companies; a no-event outcome means no qualifying issuer announcement was identified under the stated definition and review window.",
                "Succession status reflects official announcements found by the evidence date and may change between refreshes.",
                "Profit warnings do not yet affect the pressure score; share-price stress, activism, and broader news signals remain excluded.",
            ],
            "validation": validation,
        },
        "companies": companies,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(companies)} constituents and {len(source['companies'])} source-verified companies.")


if __name__ == "__main__":
    main()
