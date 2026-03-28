from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://www.theia.org/public-register"
ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = ROOT / "data" / "company_metadata.json"
PROCESSED_DIR = ROOT / "data" / "processed"
PUBLIC_DATA_DIR = ROOT / "public" / "data"


@dataclass
class CompanyRecord:
    canonical_name: str
    sector: str
    aliases: list[str]


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_company_metadata() -> tuple[dict[str, CompanyRecord], list[CompanyRecord]]:
    raw = json.loads(METADATA_PATH.read_text())
    records = [
        CompanyRecord(
            canonical_name=item["canonicalName"],
            sector=item["sector"],
            aliases=item["aliases"],
        )
        for item in raw
    ]
    lookup: dict[str, CompanyRecord] = {}
    for record in records:
        for alias in record.aliases:
            lookup[normalise_name(alias)] = record
    return lookup, records


def normalise_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip().upper())
    cleaned = cleaned.replace("P.L.C.", "PLC")
    cleaned = cleaned.replace("LIMITED", "LTD")
    cleaned = cleaned.replace("AND", "&")
    cleaned = re.sub(r"[^A-Z0-9& ]", "", cleaned)
    return cleaned


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def parse_percent(value: str) -> float | None:
    stripped = value.replace("%", "").strip()
    if not stripped:
        return None
    return round(float(stripped), 2)


def parse_date(value: str) -> tuple[str, int]:
    parsed = datetime.strptime(value.strip(), "%d/%m/%Y")
    return parsed.date().isoformat(), parsed.year


def extract_link(cell: Any) -> tuple[bool | None, str | None]:
    text = cell.get_text(" ", strip=True)
    lowered = text.lower()
    if lowered.startswith("yes"):
        link = cell.find("a")
        return True, link["href"] if link else None
    if lowered.startswith("no"):
        return False, None
    return None, None


def classify_resolution(source_group: str, resolution_title: str) -> tuple[str, str]:
    group = source_group.lower()
    title = resolution_title.lower()

    if "remuneration" in group or "remuneration" in title or "bonus" in title:
        return "remuneration", "Remuneration"

    director_keywords = [
        "re-elect",
        "re elect",
        "elect",
        "appointment of director",
        "appoint director",
        "remove",
        "director of the company",
    ]
    if "director" in group or any(keyword in title for keyword in director_keywords):
        return "director-election", "Director election"

    capital_keywords = [
        "allot",
        "pre-emption",
        "pre emption",
        "disapply",
        "purchase own shares",
        "share buyback",
        "authority to",
        "capital",
    ]
    if "capital" in group or any(keyword in title for keyword in capital_keywords):
        return "capital-authority", "Capital authority"

    audit_keywords = ["auditor", "audit", "kpmg", "pwc", "ey", "deloitte"]
    if "audit" in group or any(keyword in title for keyword in audit_keywords):
        return "audit", "Audit"

    if "climate" in title or "net zero" in title or "emissions" in title:
        return "climate", "Climate and transition"

    if "employee pay" in title or "supplier" in title or "shareaction" in title:
        return "shareholder-proposal", "Shareholder proposal"

    return "other-governance", "Other governance"


def governance_note(category_key: str, votes_against: float | None, resolution_title: str) -> str:
    against = votes_against or 0.0
    intensity = "Meaningful dissent" if against < 35 else "Strong dissent" if against < 50 else "Severe dissent"

    templates = {
        "remuneration": (
            f"{intensity} on pay is a classic stewardship signal. In UK practice, sizeable opposition to remuneration "
            "can indicate concerns about alignment, incentive design, or the board's judgement on executive reward."
        ),
        "director-election": (
            f"{intensity} on a director election points to accountability pressure on the board. Votes of this kind can "
            "signal investor unease with oversight, independence, succession, or specific committee responsibilities."
        ),
        "capital-authority": (
            f"{intensity} on capital authorities suggests investors were not fully comfortable with the board's requested "
            "flexibility around issuance, pre-emption, or buyback powers."
        ),
        "audit": (
            f"{intensity} on an audit-related resolution is notable because audit votes are usually routine. When opposition rises, "
            "it may reflect broader concerns about controls, reporting quality, or auditor tenure."
        ),
        "climate": (
            f"{intensity} on a climate-related resolution shows that voting outcomes are being used to test the credibility of "
            "transition planning and long-term governance commitments."
        ),
        "shareholder-proposal": (
            f"{intensity} on a shareholder proposal matters as a governance signal even when the board opposes it. "
            "A substantial minority can still shape future engagement and disclosure expectations."
        ),
        "other-governance": (
            f"{intensity} on this resolution suggests a governance issue that investors regarded as material enough to register "
            "public opposition against management or the board's preferred outcome."
        ),
    }
    note = templates.get(category_key, templates["other-governance"])
    if "withdraw" in resolution_title.lower():
        return (
            "The resolution appears to relate to a withdrawn or contested item. That is often a sign that investor pushback "
            "was strong enough to alter the board's intended path before or during the meeting process."
        )
    return note


def build_row_id(company_slug: str, meeting_date: str, resolution_title: str) -> str:
    digest = hashlib.sha1(f"{company_slug}|{meeting_date}|{resolution_title}".encode("utf-8")).hexdigest()
    return digest[:12]


def fetch_public_register() -> str:
    response = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "FTSE100-Dissent-Tracker/1.0"},
        timeout=60,
    )
    response.raise_for_status()
    return response.text


def parse_tables(html: str, lookup: dict[str, CompanyRecord]) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", class_="cols-11")
    resolutions: list[dict[str, Any]] = []
    unmatched_companies: list[str] = []
    all_share_count = 0

    for table in tables:
        caption = table.find("caption")
        source_group = caption.get_text(" ", strip=True) if caption else "Unlabelled section"
        body = table.find("tbody")
        if body is None:
            continue

        for row in body.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 11:
                continue

            all_share_count += 1
            company_name = cells[1].get_text(" ", strip=True)
            meeting_date, meeting_year = parse_date(cells[2].get_text(" ", strip=True))
            meeting_type = cells[3].get_text(" ", strip=True)
            resolution_title = cells[4].get_text(" ", strip=True)
            votes_for = parse_percent(cells[5].get_text(" ", strip=True))
            votes_against = parse_percent(cells[6].get_text(" ", strip=True))
            votes_withheld = parse_percent(cells[7].get_text(" ", strip=True))
            issued_capital_voted = parse_percent(cells[8].get_text(" ", strip=True))
            statement_in_results, results_link = extract_link(cells[9])
            update_statement, update_link = extract_link(cells[10])

            company_match = lookup.get(normalise_name(company_name))
            if company_match is None:
                unmatched_companies.append(company_name)
                continue

            category_key, category_label = classify_resolution(source_group, resolution_title)
            company_slug = slugify(company_match.canonical_name)
            record = {
                "id": build_row_id(company_slug, meeting_date, resolution_title),
                "companyName": company_match.canonical_name,
                "companySlug": company_slug,
                "sourceCompanyName": company_name,
                "sector": company_match.sector,
                "meetingDate": meeting_date,
                "meetingYear": meeting_year,
                "meetingType": meeting_type,
                "sourceGroup": source_group,
                "resolutionTitle": resolution_title,
                "votesForPct": votes_for,
                "votesAgainstPct": votes_against,
                "votesWithheldPct": votes_withheld,
                "issuedShareCapitalVotedPct": issued_capital_voted,
                "statementInResults": statement_in_results,
                "statementInResultsUrl": results_link,
                "updateStatement": update_statement,
                "updateStatementUrl": update_link,
                "resolutionCategory": category_key,
                "resolutionCategoryLabel": category_label,
                "governanceNote": governance_note(category_key, votes_against, resolution_title),
                "sourceUrl": SOURCE_URL,
            }
            resolutions.append(record)

    unique_unmatched = sorted(set(unmatched_companies))
    resolutions.sort(key=lambda item: (item["meetingDate"], item["companyName"], item["resolutionTitle"]), reverse=True)
    stats = {
        "allShareRowsParsed": all_share_count,
        "ftse100RowsIncluded": len(resolutions),
        "tableCount": len(tables),
    }
    return resolutions, unique_unmatched, stats


def write_csv(resolutions: list[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "companyName",
        "companySlug",
        "sourceCompanyName",
        "sector",
        "meetingDate",
        "meetingYear",
        "meetingType",
        "sourceGroup",
        "resolutionTitle",
        "votesForPct",
        "votesAgainstPct",
        "votesWithheldPct",
        "issuedShareCapitalVotedPct",
        "statementInResults",
        "statementInResultsUrl",
        "updateStatement",
        "updateStatementUrl",
        "resolutionCategory",
        "resolutionCategoryLabel",
        "governanceNote",
        "sourceUrl",
    ]
    with (PROCESSED_DIR / "ftse100_resolutions.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(resolutions)


def build_summary(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    companies = sorted({item["companyName"] for item in resolutions})
    categories = Counter(item["resolutionCategoryLabel"] for item in resolutions)
    years = sorted({item["meetingYear"] for item in resolutions})
    highest = max((item["votesAgainstPct"] or 0.0 for item in resolutions), default=0.0)
    remuneration_count = sum(1 for item in resolutions if item["resolutionCategory"] == "remuneration")
    director_count = sum(1 for item in resolutions if item["resolutionCategory"] == "director-election")

    return {
        "companyCount": len(companies),
        "resolutionCount": len(resolutions),
        "yearsCovered": years,
        "highestVotesAgainstPct": highest,
        "categoryBreakdown": categories,
        "remunerationCount": remuneration_count,
        "directorElectionCount": director_count,
    }


def validate_records(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    duplicate_keys: list[str] = []
    missing_company: list[str] = []
    missing_dates: list[str] = []
    impossible_percentages: list[str] = []

    seen: set[tuple[str, str, str]] = set()
    percent_fields = [
        "votesForPct",
        "votesAgainstPct",
        "votesWithheldPct",
        "issuedShareCapitalVotedPct",
    ]

    for item in resolutions:
        key = (item["companyName"], item["meetingDate"], item["resolutionTitle"])
        if key in seen:
            duplicate_keys.append(" | ".join(key))
        seen.add(key)

        if not item["companyName"].strip():
            missing_company.append(item["id"])

        if not item["meetingDate"].strip():
            missing_dates.append(item["id"])

        for field in percent_fields:
            value = item.get(field)
            if value is None:
                continue
            if value < 0 or value > 100:
                impossible_percentages.append(f"{item['id']}::{field}::{value}")

    return {
        "duplicateRecords": duplicate_keys,
        "missingCompanyNames": missing_company,
        "missingDates": missing_dates,
        "impossiblePercentages": impossible_percentages,
        "status": "pass"
        if not any(
            [duplicate_keys, missing_company, missing_dates, impossible_percentages]
        )
        else "fail",
    }


def write_outputs(
    resolutions: list[dict[str, Any]],
    unmatched: list[str],
    stats: dict[str, Any],
    validation: dict[str, Any],
) -> None:
    summary = build_summary(resolutions)
    generated_at = datetime.now(timezone.utc).isoformat()
    start_date = min((item["meetingDate"] for item in resolutions), default=None)
    end_date = max((item["meetingDate"] for item in resolutions), default=None)
    payload = {
        "metadata": {
            "title": "FTSE 100 Shareholder Dissent Tracker",
            "sourceName": "Investment Association Public Register",
            "sourceUrl": SOURCE_URL,
            "generatedAt": generated_at,
            "focusStatement": "This app tracks significant shareholder dissent, not general AGM voting coverage.",
            "coverageStatement": (
                "V1 uses the Investment Association Public Register to capture real significant votes against "
                "management, then filters those records to companies matched to a curated FTSE 100 issuer list."
            ),
            "coveragePeriod": {
                "startDate": start_date,
                "endDate": end_date,
            },
            "methodology": {
                "included": [
                    "Resolutions listed on the IA Public Register for significant votes against management or withdrawn resolutions.",
                    "Records matched with high confidence to the curated FTSE 100 issuer alias file.",
                    "Resolution-level vote percentages and linked announcement URLs published on the register page.",
                ],
                "excluded": [
                    "Routine AGM resolutions that did not reach the register's significance threshold.",
                    "Companies not matched with sufficient confidence to the FTSE 100 issuer list.",
                    "Newer dissent cases that were never added after the IA register ceased updates in October 2025.",
                ],
                "sourceCredibilityNote": (
                    "The Investment Association Public Register was created within the UK governance and stewardship ecosystem "
                    "to track significant dissent and links back to company meeting result announcements."
                ),
            },
            "limitations": [
                "The Public Register records significant votes against management or withdrawn resolutions rather than every AGM resolution.",
                "The Investment Association stated in October 2025 that no new companies or resolutions would be added to the register.",
                "FTSE 100 inclusion relies on a maintained alias file rather than a live constituent feed.",
                "Resolution categories are assigned using rules based on source table captions and resolution text.",
            ],
            "stats": stats,
            "validation": validation,
            "summary": {
                **summary,
                "categoryBreakdown": dict(summary["categoryBreakdown"]),
            },
            "unmatchedCompanies": unmatched,
        },
        "resolutions": resolutions,
    }

    (PROCESSED_DIR / "ftse100_resolutions.json").write_text(json.dumps(resolutions, indent=2))
    (PROCESSED_DIR / "unmatched_companies.json").write_text(json.dumps(unmatched, indent=2))
    (PUBLIC_DATA_DIR / "tracker-data.json").write_text(json.dumps(payload, indent=2))
    write_csv(resolutions)


def main() -> None:
    ensure_dirs()
    lookup, _ = load_company_metadata()
    html = fetch_public_register()
    resolutions, unmatched, stats = parse_tables(html, lookup)
    validation = validate_records(resolutions)
    if validation["status"] == "fail":
        raise ValueError(json.dumps(validation, indent=2))
    write_outputs(resolutions, unmatched, stats, validation)
    print(
        json.dumps(
            {
                "included_resolutions": len(resolutions),
                "included_companies": len({item["companyName"] for item in resolutions}),
                "unmatched_companies": len(unmatched),
                **stats,
                "validation_status": validation["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
