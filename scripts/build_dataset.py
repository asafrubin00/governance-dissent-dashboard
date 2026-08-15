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
from bs4 import BeautifulSoup, Tag
from pypdf import PdfReader


SOURCE_URL = "https://www.theia.org/public-register"
ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = ROOT / "data" / "company_metadata.json"
SOURCE_CONFIG_PATH = ROOT / "data" / "issuer_source_config.json"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_ISSUER_DIR = ROOT / "data" / "raw" / "issuer-announcements"
RAW_DOCUMENT_DIR = ROOT / "data" / "raw" / "issuer-documents"
PUBLIC_DATA_DIR = ROOT / "public" / "data"
REQUEST_HEADERS = {"User-Agent": "FTSE100-Dissent-Tracker/2.0"}


@dataclass
class CompanyRecord:
    canonical_name: str
    sector: str
    aliases: list[str]


@dataclass
class AnnouncementPage:
    url: str
    company_name: str
    meeting_date: str
    source: str
    source_group: str
    allow_issuer_only: bool = True
    parser_hint: str | None = None


@dataclass
class ResultDocument:
    url: str
    company_name: str
    meeting_date: str
    source: str
    source_group: str
    parser_hint: str


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_ISSUER_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)


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


def load_source_config() -> tuple[list[AnnouncementPage], list[ResultDocument]]:
    if not SOURCE_CONFIG_PATH.exists():
        return [], []

    raw = json.loads(SOURCE_CONFIG_PATH.read_text())
    pages: list[AnnouncementPage] = []
    for item in raw.get("announcementSeeds", []):
        pages.append(
            AnnouncementPage(
                url=item["url"],
                company_name=item["companyName"],
                meeting_date=item["meetingDate"],
                source=item.get("source", "manual-seed"),
                source_group=item.get("sourceGroup", "Issuer announcement seed"),
                allow_issuer_only=item.get("allowIssuerOnly", True),
                parser_hint=item.get("parserHint"),
            )
        )

    documents: list[ResultDocument] = []
    for item in raw.get("resultDocumentSeeds", []):
        documents.append(
            ResultDocument(
                url=item["url"],
                company_name=item["companyName"],
                meeting_date=item["meetingDate"],
                source=item.get("source", "manual-result-document"),
                source_group=item.get("sourceGroup", "Issuer result document seed"),
                parser_hint=item["parserHint"],
            )
        )

    return pages, documents


def normalise_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip().upper())
    cleaned = cleaned.replace("P.L.C.", "PLC")
    cleaned = cleaned.replace("LIMITED", "LTD")
    cleaned = cleaned.replace("AND", "&")
    cleaned = re.sub(r"[^A-Z0-9& ]", "", cleaned)
    return cleaned


def normalise_resolution_title(value: str) -> str:
    cleaned = value.strip().upper()
    cleaned = cleaned.replace("’", "'")
    cleaned = re.sub(r"^RESOLUTION\s+\d+\s*:\s*", "", cleaned)
    cleaned = re.sub(r"^RESOLUTION\s+[A-Z]\s*:\s*", "", cleaned)
    cleaned = re.sub(r"^\d+[\.\): -]+\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^A-Z0-9&' ]", "", cleaned)
    return cleaned.strip()


def extract_resolution_number(value: str) -> int | None:
    match = re.search(r"resolution\s+(\d+)", value, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    match = re.match(r"^(\d+)[\.\)]?\s+", value.strip())
    if match:
        return int(match.group(1))

    return None


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def parse_percent(value: str) -> float | None:
    stripped = value.replace("%", "").strip()
    if not stripped:
        return None
    try:
        return round(float(stripped), 2)
    except ValueError:
        return None


def parse_count(value: str) -> int | None:
    stripped = re.sub(r"[^0-9]", "", value)
    if not stripped:
        return None
    return int(stripped)


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

    shareholder_keywords = [
        "employee pay",
        "supplier",
        "shareaction",
        "shareholder requisitioned",
        "shareholder resolution",
        "requisitioned resolution",
        "midland clawback",
    ]
    if any(keyword in title for keyword in shareholder_keywords):
        return "shareholder-proposal", "Shareholder proposal"

    return "other-governance", "Other governance"


def management_vote_context(
    category_key: str,
    votes_for_pct: float | None,
    votes_against_pct: float | None,
) -> tuple[bool, str, float | None]:
    if category_key == "shareholder-proposal":
        return False, "against", votes_for_pct
    return True, "for", votes_against_pct


def apply_management_context(record: dict[str, Any]) -> None:
    category_key, category_label = classify_resolution(record["sourceGroup"], record["resolutionTitle"])
    is_register_requisition = (
        record.get("recordOrigin") == "ia-register"
        and "requisitioned" in record.get("sourceGroup", "").lower()
    )
    if is_register_requisition:
        management_sponsored, recommendation, dissent_pct = (
            False,
            "against",
            record.get("votesForPct"),
        )
    else:
        management_sponsored, recommendation, dissent_pct = management_vote_context(
            category_key,
            record.get("votesForPct"),
            record.get("votesAgainstPct"),
        )
    record["resolutionCategory"] = category_key
    record["resolutionCategoryLabel"] = category_label
    record["managementSponsored"] = management_sponsored
    record["managementRecommendation"] = recommendation
    record["managementDissentPct"] = dissent_pct
    record["governanceNote"] = governance_note(category_key, dissent_pct, record["resolutionTitle"])


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


def fetch_url(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=(5, 20))
    response.raise_for_status()
    return response.text


def fetch_public_register() -> str:
    return fetch_url(SOURCE_URL)


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
                "votesForCount": None,
                "votesAgainstCount": None,
                "votesWithheldCount": None,
                "totalVotesCastCount": None,
                "statementInResults": statement_in_results,
                "statementInResultsUrl": results_link,
                "updateStatement": update_statement,
                "updateStatementUrl": update_link,
                "resolutionCategory": category_key,
                "resolutionCategoryLabel": category_label,
                "governanceNote": governance_note(category_key, votes_against, resolution_title),
                "sourceUrl": SOURCE_URL,
                "recordOrigin": "ia-register",
                "recordOriginLabel": "IA Public Register",
                "officialAnnouncementUrl": results_link,
                "officialAnnouncementSource": None,
                "officialAnnouncementVerified": False,
                "officialAnnouncementStatus": "unverified",
                "updateStatementParsed": False,
                "updateStatementSummary": None,
                "updateStatementDocumentType": None,
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


def is_html_announcement_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return lowered.endswith(".html") or "regulatory-story.aspx" in lowered


def collect_announcement_pages(
    resolutions: list[dict[str, Any]],
    manual_pages: list[AnnouncementPage],
) -> list[AnnouncementPage]:
    pages_by_key: dict[tuple[str, str], AnnouncementPage] = {}
    url_dates: dict[str, set[str]] = {}

    for item in resolutions:
        for key in ["statementInResultsUrl", "updateStatementUrl"]:
            url = item.get(key)
            if not is_html_announcement_url(url):
                continue
            url_dates.setdefault(url, set()).add(item["meetingDate"])
            pair = (url, item["meetingDate"])
            if pair in pages_by_key:
                continue
            pages_by_key[pair] = AnnouncementPage(
                url=url,
                company_name=item["companyName"],
                meeting_date=item["meetingDate"],
                source="ia-linked-announcement",
                source_group=item["sourceGroup"],
            )

    for page in manual_pages:
        url_dates.setdefault(page.url, set()).add(page.meeting_date)
        pages_by_key.setdefault((page.url, page.meeting_date), page)

    pages = list(pages_by_key.values())
    for page in pages:
        if page.source == "ia-linked-announcement" and len(url_dates.get(page.url, set())) > 1:
            page.allow_issuer_only = False

    return pages


def write_raw_announcement_html(url: str, html: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    target = RAW_ISSUER_DIR / f"{digest}.html"
    target.write_text(html)
    return target


def write_raw_document(url: str, content: bytes, suffix: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    target = RAW_DOCUMENT_DIR / f"{digest}{suffix}"
    target.write_bytes(content)
    return target


def looks_like_vote_table(table: Tag) -> bool:
    text = table.get_text(" ", strip=True).lower()
    has_for_against = ("votes for" in text or "total votes for" in text or re.search(r"\bfor\b", text)) and (
        "votes against" in text or "total votes against" in text or re.search(r"\bagainst\b", text)
    )
    has_vote_structure = "total votes cast" in text or "withheld" in text or "resolution" in text
    return bool(has_for_against and has_vote_structure)


def parse_resolution_title_and_number(cells: list[str]) -> tuple[int | None, str | None, list[str]]:
    if not cells:
        return None, None, []

    first = cells[0].strip()
    if re.fullmatch(r"\d+", first):
        title = cells[1].strip() if len(cells) > 1 else None
        return int(first), title, cells[2:]

    if re.fullmatch(r"\d+[\.\)]", first):
        title = cells[1].strip() if len(cells) > 1 else None
        return int(re.sub(r"[^0-9]", "", first)), title, cells[2:]

    match = re.match(r"^resolution\s+(\d+)[\.\): -]*(.*)$", first, flags=re.IGNORECASE)
    if match:
        title = match.group(2).strip() or (cells[1].strip() if len(cells) > 1 else None)
        return int(match.group(1)), title, cells[1:]

    match = re.match(r"^resolution\s+[A-Z][\.\): -]+(.*)$", first, flags=re.IGNORECASE)
    if match:
        title = match.group(1).strip() or (cells[1].strip() if len(cells) > 1 else None)
        return None, title, cells[1:]

    match = re.match(r"^(\d+)[\.\)]?\s+(.*)$", first)
    if match:
        return int(match.group(1)), match.group(2).strip(), cells[1:]

    return None, None, []


def parse_official_vote_row(cells: list[str]) -> dict[str, Any] | None:
    resolution_number, title, body = parse_resolution_title_and_number(cells)
    if not title:
        return None

    if body and body[0].strip().lower() in {"ordinary", "special"}:
        body = body[1:]

    if any("no votes required" in part.lower() for part in body):
        return None

    total_first_layout = (
        len(body) == 6
        and (parse_percent(body[2]) or 0) <= 100
        and (parse_percent(body[4]) or 0) <= 100
        and parse_percent(body[1]) is None
        and parse_percent(body[3]) is None
    )
    if total_first_layout:
        total_votes_cast_count = parse_count(body[0])
        votes_for_count = parse_count(body[1])
        votes_for_pct = parse_percent(body[2])
        votes_against_count = parse_count(body[3])
        votes_against_pct = parse_percent(body[4])
        votes_withheld_count = parse_count(body[5])
        issued_share_capital_voted_pct = None
    else:
        votes_for_count = parse_count(body[0]) if len(body) > 0 else None
        votes_for_pct = parse_percent(body[1]) if len(body) > 1 else None
        votes_against_count = parse_count(body[2]) if len(body) > 2 else None
        votes_against_pct = parse_percent(body[3]) if len(body) > 3 else None

        total_votes_cast_count = None
        votes_withheld_count = None
        issued_share_capital_voted_pct = None

        if len(body) == 6:
            votes_withheld_count = parse_count(body[4])
            issued_share_capital_voted_pct = parse_percent(body[5])
        elif len(body) == 7:
            total_votes_cast_count = parse_count(body[4])
            issued_share_capital_voted_pct = parse_percent(body[5])
            votes_withheld_count = parse_count(body[6])
        elif len(body) >= 8:
            total_votes_cast_count = parse_count(body[4])
            issued_share_capital_voted_pct = parse_percent(body[6]) or parse_percent(body[5])
            votes_withheld_count = parse_count(body[7])

    return {
        "resolutionNumber": resolution_number,
        "resolutionTitle": title,
        "resolutionTitleNormalised": normalise_resolution_title(title),
        "votesForCount": votes_for_count,
        "votesForPct": votes_for_pct,
        "votesAgainstCount": votes_against_count,
        "votesAgainstPct": votes_against_pct,
        "votesWithheldCount": votes_withheld_count,
        "totalVotesCastCount": total_votes_cast_count,
        "issuedShareCapitalVotedPct": issued_share_capital_voted_pct,
    }


def parse_entain_vote_rows(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    text = re.sub(r"\s+", " ", main.get_text(" ", strip=True))
    start = text.find("1. To ")
    working = text[start:] if start != -1 else text
    pattern = re.compile(
        r"(?P<num>\d{1,2})\.\s*(?P<title>.+?)\s+"
        r"(?P<total>\d[\d,]*)\s+"
        r"(?P<for_count>\d[\d,]*)\s+"
        r"(?P<for_pct>\d+[\.,]\d+)\s+"
        r"(?P<against_count>\d[\d,]*)\s+"
        r"(?P<against_pct>\d+[\.,]\d+|>\d+[\.,]\d+)\s+"
        r"(?P<withheld>\d[\d,]*)"
        r"(?=\s+\d{1,2}\.\s|\s+Special Resolutions|\s+Note:|$)",
        flags=re.IGNORECASE,
    )
    rows: list[dict[str, Any]] = []
    for match in pattern.finditer(working):
        title = match.group("title").strip()
        rows.append(
            {
                "resolutionNumber": int(match.group("num")),
                "resolutionTitle": title,
                "resolutionTitleNormalised": normalise_resolution_title(title),
                "votesForCount": parse_count(match.group("for_count")),
                "votesForPct": parse_percent(match.group("for_pct").replace(",", ".")),
                "votesAgainstCount": parse_count(match.group("against_count")),
                "votesAgainstPct": parse_percent(match.group("against_pct").replace(">", "").replace(",", ".")),
                "votesWithheldCount": parse_count(match.group("withheld")),
                "totalVotesCastCount": parse_count(match.group("total")),
                "issuedShareCapitalVotedPct": None,
            }
        )
    return rows


def parse_ig_rns_vote_rows(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    preformatted = soup.find("pre")
    text = preformatted.get_text("\n") if preformatted else soup.get_text("\n")
    start = text.find("WITHHELD*")
    end = text.find("*A vote withheld", start)
    working = text[start + len("WITHHELD*"):end if end != -1 else None] if start != -1 else text
    pattern = re.compile(
        r"^\s*(?P<num>\d{1,2})\s+(?P<title>.+?)\s{2,}"
        r"(?P<for_count>\d[\d,]*)\s+"
        r"(?P<for_pct>\d+\.\d+)%?\s+"
        r"(?P<against_count>\d[\d,]*)\s+"
        r"(?P<against_pct>\d+\.\d+)%?\s+"
        r"(?P<total>\d[\d,]*)\s+"
        r"(?P<isc>\d+\.\d+)%?\s+"
        r"(?P<withheld>\d[\d,]*)\s*$",
        flags=re.IGNORECASE,
    )
    rows: list[dict[str, Any]] = []
    for line in working.splitlines():
        match = pattern.match(line)
        if match:
            rows.append(
                {
                    "resolutionNumber": int(match.group("num")),
                    "resolutionTitle": match.group("title").strip(),
                    "resolutionTitleNormalised": normalise_resolution_title(match.group("title")),
                    "votesForCount": parse_count(match.group("for_count")),
                    "votesForPct": parse_percent(match.group("for_pct")),
                    "votesAgainstCount": parse_count(match.group("against_count")),
                    "votesAgainstPct": parse_percent(match.group("against_pct")),
                    "votesWithheldCount": parse_count(match.group("withheld")),
                    "totalVotesCastCount": parse_count(match.group("total")),
                    "issuedShareCapitalVotedPct": parse_percent(match.group("isc")),
                }
            )
        elif rows and line.strip():
            rows[-1]["resolutionTitle"] += f" {line.strip()}"
            rows[-1]["resolutionTitleNormalised"] = normalise_resolution_title(rows[-1]["resolutionTitle"])
    return rows


def parse_announcement_tables(html: str, parser_hint: str | None = None) -> list[dict[str, Any]]:
    if parser_hint == "entain-agm-results":
        return parse_entain_vote_rows(html)
    if parser_hint == "ig-rns-results":
        return parse_ig_rns_vote_rows(html)

    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []

    for table in soup.find_all("table"):
        if not looks_like_vote_table(table):
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            parsed = parse_official_vote_row(cells)
            if parsed:
                rows.append(parsed)

        if rows:
            break

    return rows


def clean_pdf_text(text: str) -> str:
    cleaned = text.replace("\xa0", " ")
    cleaned = re.sub(r"Page \d+ of \d+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def parse_pdf_result_rows(text: str, parser_hint: str) -> list[dict[str, Any]]:
    cleaned = clean_pdf_text(text)
    if not cleaned:
        return []

    if parser_hint == "ihg-agm-results":
        start = cleaned.find("1 Report")
        working = cleaned[start:] if start != -1 else cleaned
        pattern = re.compile(
            r"(?P<num>\d{1,2})(?:\([a-z]\))?\s+(?P<title>.+?)\s+"
            r"(?P<for_count>\d[\d,]*)\s+"
            r"(?P<for_pct>\d+\.\d+)%?\s+"
            r"(?P<against_count>\d[\d,]*)\s+"
            r"(?P<against_pct>\d+\.\d+)%?\s+"
            r"(?P<total>\d[\d,]*)\s+"
            r"(?P<isc>\d+\.\d+)%?\s+"
            r"(?P<withheld>\d[\d,]*)"
            r"(?=\s+\d{1,2}(?:\([a-z]\))?\s+|\s+Notes:|$)",
            flags=re.IGNORECASE,
        )
        return [
            {
                "resolutionNumber": int(match.group("num")),
                "resolutionTitle": match.group("title").strip(),
                "resolutionTitleNormalised": normalise_resolution_title(match.group("title")),
                "votesForCount": parse_count(match.group("for_count")),
                "votesForPct": parse_percent(match.group("for_pct")),
                "votesAgainstCount": parse_count(match.group("against_count")),
                "votesAgainstPct": parse_percent(match.group("against_pct")),
                "votesWithheldCount": parse_count(match.group("withheld")),
                "totalVotesCastCount": parse_count(match.group("total")),
                "issuedShareCapitalVotedPct": parse_percent(match.group("isc")),
            }
            for match in pattern.finditer(working)
        ]

    if parser_hint == "hsbc-agm-results":
        start = cleaned.find("1. To receive")
        working = cleaned[start:] if start != -1 else cleaned
        working = re.sub(r"(\d)\.To\b", r"\1. To", working)
        pattern = re.compile(
            r"(?P<num>\d+)\.\s*(?P<title>.+?)\s+"
            r"(?P<for_count>\d[\d,]*)\s+"
            r"(?P<for_pct>\d+\.\d+)\s+"
            r"(?P<against_count>\d[\d,]*)\s+"
            r"(?P<against_pct>\d+\.\d+)\s+"
            r"(?P<total>\d[\d,]*)\s+"
            r"(?P<isc>\d+\.\d+%)\s+"
            r"(?P<withheld>\d[\d,]*)"
            r"(?=\s+\d+\.\s|\s+\*\s+based on|\s+2\.\s+Other|$)",
            flags=re.IGNORECASE,
        )
        return [
            {
                "resolutionNumber": int(match.group("num")),
                "resolutionTitle": match.group("title").strip(),
                "resolutionTitleNormalised": normalise_resolution_title(match.group("title")),
                "votesForCount": parse_count(match.group("for_count")),
                "votesForPct": parse_percent(match.group("for_pct")),
                "votesAgainstCount": parse_count(match.group("against_count")),
                "votesAgainstPct": parse_percent(match.group("against_pct")),
                "votesWithheldCount": parse_count(match.group("withheld")),
                "totalVotesCastCount": parse_count(match.group("total")),
                "issuedShareCapitalVotedPct": parse_percent(match.group("isc")),
            }
            for match in pattern.finditer(working)
        ]

    if parser_hint == "rio-agm-results":
        start = cleaned.find("Table 1")
        working = cleaned[start:] if start != -1 else cleaned
        pattern = re.compile(
            r"(?P<num>\d+)\.?\s+(?P<title>.+?)\s+"
            r"(?P<total>\d[\d,]*)\s+"
            r"(?P<for_count>\d[\d,]*)\s+"
            r"(?P<for_pct>\d+\.\d+)\s+"
            r"(?P<against_count>\d[\d,]*)\s+"
            r"(?P<against_pct>\d+\.\d+)\s+"
            r"(?P<withheld>\d[\d,]*)"
            r"(?=\s+\d+\.\s|\s+Resolution\s+\d+\b|\s+The results of the Rio Tinto plc polls|$)",
            flags=re.IGNORECASE,
        )
        rows: list[dict[str, Any]] = []
        for match in pattern.finditer(working):
            title = match.group("title").strip()
            if "was passed with less than" in title.lower() or "table 3" in title.lower():
                continue
            rows.append(
                {
                    "resolutionNumber": int(match.group("num")),
                    "resolutionTitle": title,
                    "resolutionTitleNormalised": normalise_resolution_title(title),
                    "votesForCount": parse_count(match.group("for_count")),
                    "votesForPct": parse_percent(match.group("for_pct")),
                    "votesAgainstCount": parse_count(match.group("against_count")),
                    "votesAgainstPct": parse_percent(match.group("against_pct")),
                    "votesWithheldCount": parse_count(match.group("withheld")),
                    "totalVotesCastCount": parse_count(match.group("total")),
                    "issuedShareCapitalVotedPct": None,
                }
            )
        return rows

    if parser_hint == "anto-agm-results":
        rows: list[dict[str, Any]] = []
        for match in re.finditer(r"\((?P<num>\d+)\)\s+Resolution withdrawn\d*", cleaned, flags=re.IGNORECASE):
            rows.append(
                {
                    "resolutionNumber": int(match.group("num")),
                    "resolutionTitle": "Resolution withdrawn",
                    "resolutionTitleNormalised": normalise_resolution_title("Resolution withdrawn"),
                    "votesForCount": None,
                    "votesForPct": None,
                    "votesAgainstCount": None,
                    "votesAgainstPct": None,
                    "votesWithheldCount": None,
                    "totalVotesCastCount": None,
                    "issuedShareCapitalVotedPct": None,
                }
            )
        return rows

    if parser_hint == "standard-agm-results":
        start = cleaned.find("1 To ")
        working = cleaned[start:] if start != -1 else cleaned
        working = re.sub(
            r"\s+General\s+emptive offer to shareholders, up to the specified amount3",
            "",
            working,
            flags=re.IGNORECASE,
        )
        pattern = re.compile(
            r"(?P<num>\d{1,2})\s+(?P<title>.+?)\s+"
            r"(?P<for_count>\d[\d,]*)\s+"
            r"(?P<for_pct>\d+\.\d+)%?\s+"
            r"(?P<against_count>\d[\d,]*)\s+"
            r"(?P<against_pct>\d+\.\d+)%?\s+"
            r"(?P<total>\d[\d,]*)\s+"
            r"(?P<isc>\d+\.\d+)%?\s+"
            r"(?P<withheld>\d[\d,]*)"
            r"(?=\s+\d{1,2}\s+To\s|\s+General\s+emptive offer|\s+\d+\s+Includes discretionary votes|$)",
            flags=re.IGNORECASE,
        )
        return [
            {
                "resolutionNumber": int(match.group("num")),
                "resolutionTitle": match.group("title").strip(),
                "resolutionTitleNormalised": normalise_resolution_title(match.group("title")),
                "votesForCount": parse_count(match.group("for_count")),
                "votesForPct": parse_percent(match.group("for_pct")),
                "votesAgainstCount": parse_count(match.group("against_count")),
                "votesAgainstPct": parse_percent(match.group("against_pct")),
                "votesWithheldCount": parse_count(match.group("withheld")),
                "totalVotesCastCount": parse_count(match.group("total")),
                "issuedShareCapitalVotedPct": parse_percent(match.group("isc")),
            }
            for match in pattern.finditer(working)
        ]

    if parser_hint == "persimmon-proxy-results":
        pattern = re.compile(
            r"RES:(?P<num>\d{3})\s+(?P<title>.+?)\s+"
            r"(?P<for_holders>\d[\d,]*)\s+(?P<for_count>\d[\d,]*)\s+(?P<for_pct>\d+\.\d+)\s+"
            r"(?P<against_holders>\d[\d,]*)\s+(?P<against_count>\d[\d,]*)\s+(?P<against_pct>\d+\.\d+)\s+"
            r"(?P<discretionary_holders>\d[\d,]*)\s+(?P<discretionary_count>\d[\d,]*)\s+(?P<discretionary_pct>\d+\.\d+)\s+"
            r"(?P<withheld_holders>\d[\d,]*)\s+(?P<withheld_count>\d[\d,]*)\s+"
            r"(?P<total>\d[\d,]*)\s+(?P<support_holders>\d[\d,]*)\s+"
            r"(?P<support_count>\d[\d,]*)\s+(?P<support_pct>\d+\.\d+)"
            r"(?=\s+RES:|$)",
            flags=re.IGNORECASE,
        )
        return [
            {
                "resolutionNumber": int(match.group("num")),
                "resolutionTitle": match.group("title").strip(),
                "resolutionTitleNormalised": normalise_resolution_title(match.group("title")),
                # Persimmon's 2017 proxy report presents direct-for and discretionary
                # votes separately, then combines them in the final support column.
                "votesForCount": parse_count(match.group("support_count")),
                "votesForPct": parse_percent(match.group("support_pct")),
                "votesAgainstCount": parse_count(match.group("against_count")),
                "votesAgainstPct": parse_percent(match.group("against_pct")),
                "votesWithheldCount": parse_count(match.group("withheld_count")),
                "totalVotesCastCount": parse_count(match.group("total")),
                "issuedShareCapitalVotedPct": None,
            }
            for match in pattern.finditer(cleaned)
        ]

    if parser_hint == "babcock-agm-results":
        start = re.search(r"\b1\.\s+Approval", cleaned)
        working = cleaned[start.start():] if start else cleaned
        working = working.split("Further information:", 1)[0]
        chunks = re.split(r"(?=\b\d{1,2}\.\s+)", working)
        data_pattern = re.compile(
            r"(?P<for_count>\d[\d,]*)\s+"
            r"(?P<for_pct>\d+\.\d+)\s+"
            r"(?P<against_count>\d[\d,]*)\s+"
            r"(?P<against_pct>\d+\.\d+)\s+"
            r"(?P<total>\d[\d,]*)\s+"
            r"(?P<withheld>\d[\d,]*)"
        )
        rows: list[dict[str, Any]] = []
        for chunk in chunks:
            header = re.match(r"(?P<num>\d{1,2})\.\s+(?P<body>.+)", chunk)
            if not header:
                continue
            data = data_pattern.search(header.group("body"))
            if not data:
                continue
            title = clean_pdf_text(
                f"{header.group('body')[:data.start()]} {header.group('body')[data.end():]}"
            )
            rows.append(
                {
                    "resolutionNumber": int(header.group("num")),
                    "resolutionTitle": title,
                    "resolutionTitleNormalised": normalise_resolution_title(title),
                    "votesForCount": parse_count(data.group("for_count")),
                    "votesForPct": parse_percent(data.group("for_pct")),
                    "votesAgainstCount": parse_count(data.group("against_count")),
                    "votesAgainstPct": parse_percent(data.group("against_pct")),
                    "votesWithheldCount": parse_count(data.group("withheld")),
                    "totalVotesCastCount": parse_count(data.group("total")),
                    "issuedShareCapitalVotedPct": None,
                }
            )
        return rows

    if parser_hint == "reckitt-agm-results":
        start = re.search(r"\b1\.\s+(?:To|That)", cleaned)
        working = cleaned[start.start():] if start else cleaned
        working = re.split(r"Resolutions?\s+\d+\s+to\s+\d+", working, maxsplit=1)[0]
        chunks = re.split(r"(?=\b\d{1,2}\.\s+)", working)
        data_pattern = re.compile(
            r"(?P<for_count>\d[\d,]*)\s+"
            r"(?P<for_pct>\d+\.\d+)%?\s+"
            r"(?P<against_count>\d[\d,]*)\s+"
            r"(?P<against_pct>\d+\.\d+)%?\s+"
            r"(?P<total>\d[\d,]*)\s+"
            r"(?:(?P<isc>\d+\.\d+)%?\s+)?"
            r"(?P<withheld>\d[\d,]*)"
        )
        rows: list[dict[str, Any]] = []
        for chunk in chunks:
            header = re.match(r"(?P<num>\d{1,2})\.\s+(?P<body>.+)", chunk)
            if not header:
                continue
            data = data_pattern.search(header.group("body"))
            if not data:
                continue
            title = clean_pdf_text(
                f"{header.group('body')[:data.start()]} {header.group('body')[data.end():]}"
            )
            rows.append(
                {
                    "resolutionNumber": int(header.group("num")),
                    "resolutionTitle": title,
                    "resolutionTitleNormalised": normalise_resolution_title(title),
                    "votesForCount": parse_count(data.group("for_count")),
                    "votesForPct": parse_percent(data.group("for_pct")),
                    "votesAgainstCount": parse_count(data.group("against_count")),
                    "votesAgainstPct": parse_percent(data.group("against_pct")),
                    "votesWithheldCount": parse_count(data.group("withheld")),
                    "totalVotesCastCount": parse_count(data.group("total")),
                    "issuedShareCapitalVotedPct": parse_percent(data.group("isc")) if data.group("isc") else None,
                }
            )
        return rows

    if parser_hint == "united-utilities-agm-results":
        start = cleaned.find("1 Receiving")
        working = cleaned[start:] if start != -1 else cleaned
        pattern = re.compile(
            r"(?P<num>\d{1,2})\s+(?P<title>.+?)\s+"
            r"(?P<for_count>\d[\d,]*)\s+"
            r"(?P<for_pct>\d+\.\d+)%?\s+"
            r"(?P<against_count>\d[\d,]*)\s+"
            r"(?P<against_pct>\d+\.\d+)%?\s+"
            r"(?P<isc>\d+\.\d+)\s+"
            r"(?P<withheld>\d[\d,]*)"
            r"(?=\s+\d{1,2}\s+[A-Z]|\s+LEI\s+-|$)",
            flags=re.IGNORECASE,
        )
        rows: list[dict[str, Any]] = []
        for match in pattern.finditer(working):
            votes_for = parse_count(match.group("for_count"))
            votes_against = parse_count(match.group("against_count"))
            title = re.sub(r"pre-\s+emption", "pre-emption", match.group("title").strip(), flags=re.IGNORECASE)
            rows.append(
                {
                    "resolutionNumber": int(match.group("num")),
                    "resolutionTitle": title,
                    "resolutionTitleNormalised": normalise_resolution_title(title),
                    "votesForCount": votes_for,
                    "votesForPct": parse_percent(match.group("for_pct")),
                    "votesAgainstCount": votes_against,
                    "votesAgainstPct": parse_percent(match.group("against_pct")),
                    "votesWithheldCount": parse_count(match.group("withheld")),
                    "totalVotesCastCount": (votes_for + votes_against) if votes_for is not None and votes_against is not None else None,
                    "issuedShareCapitalVotedPct": parse_percent(match.group("isc")),
                }
            )
        return rows

    if parser_hint in {"gsk-agm-results", "smiths-agm-results"}:
        start_match = re.search(r"\b1\s+(?:Receive|Adoption)", cleaned)
        working = cleaned[start_match.start():] if start_match else cleaned
        working = re.sub(
            r"(?:Resolution\s+)?(?:VOTES|Total votes)\s+FOR.*?VOTES\s+WITHHELD(?:\(\d\))?",
            " ",
            working,
            flags=re.IGNORECASE,
        )
        working = re.sub(
            r"(17\s+Authority for the company to make donations to political organisations)\s+"
            r"(?P<data>\d[\d,]*\s+\d+\.\d+\s+\d[\d,]*\s+\d+\.\d+\s+\d[\d,]*\s+\d[\d,]*)\s+"
            r"and incur political expenditure\s+(18\s+Authority to allot shares)",
            r"\1 and incur political expenditure \g<data> \3",
            working,
            flags=re.IGNORECASE,
        )
        working = re.sub(
            r"(15\s+Authority for Audit & Risk Committee to determine the)\s+"
            r"(?P<data>\d[\d,]*\s+\d+\.\d+\s+\d[\d,]*\s+\d+\.\d+\s+\d[\d,]*\s+\d+\.\d+%\s+\d[\d,]*)\s+"
            r"remuneration of the auditors\s+(16\s+Authority to Directors to allot shares)",
            r"\1 remuneration of the auditors \g<data> \3",
            working,
            flags=re.IGNORECASE,
        )
        pattern = re.compile(
            r"(?P<num>\d{1,2})\s+(?P<title>.+?)\s+"
            r"(?P<for_count>\d[\d,]*)\s+"
            r"(?P<for_pct>\d+\.\d+)\s+"
            r"(?P<against_count>\d[\d,]*)\s+"
            r"(?P<against_pct>\d+\.\d+)\s+"
            r"(?P<total>\d[\d,]*)\s+"
            r"(?:(?P<isc>\d+\.\d+)%\s+)?"
            r"(?P<withheld>\d[\d,]*)"
            r"(?=\s+\d{1,2}\s+[A-Z]|\s+Notes?\b|\s+\(\d\)|$)",
            flags=re.IGNORECASE,
        )
        return [
            {
                "resolutionNumber": int(match.group("num")),
                "resolutionTitle": re.sub(
                    r"pre-\s+emption",
                    "pre-emption",
                    match.group("title").strip(),
                    flags=re.IGNORECASE,
                ),
                "resolutionTitleNormalised": normalise_resolution_title(match.group("title")),
                "votesForCount": parse_count(match.group("for_count")),
                "votesForPct": parse_percent(match.group("for_pct")),
                "votesAgainstCount": parse_count(match.group("against_count")),
                "votesAgainstPct": parse_percent(match.group("against_pct")),
                "votesWithheldCount": parse_count(match.group("withheld")),
                "totalVotesCastCount": parse_count(match.group("total")),
                "issuedShareCapitalVotedPct": parse_percent(match.group("isc")) if match.group("isc") else None,
            }
            for match in pattern.finditer(working)
        ]

    return []


def validate_official_vote_rows(rows: list[dict[str, Any]], source_url: str) -> None:
    if not rows:
        raise ValueError(f"Configured AGM source produced no vote rows: {source_url}")

    resolution_keys = [
        (row["resolutionNumber"], row["resolutionTitleNormalised"])
        for row in rows
        if row["resolutionNumber"] is not None
    ]
    if len(resolution_keys) != len(set(resolution_keys)):
        raise ValueError(f"Configured AGM source produced duplicate resolution rows: {source_url}")

    for row in rows:
        for field in ("votesForPct", "votesAgainstPct", "issuedShareCapitalVotedPct"):
            value = row.get(field)
            if value is not None and not 0 <= value <= 100:
                raise ValueError(f"Configured AGM source produced an impossible {field}: {source_url}")


def extract_update_statement_summary(text: str) -> str | None:
    cleaned = clean_pdf_text(text)
    if not cleaned:
        return None

    sentences = re.split(r"(?<=[\.\?!])\s+", cleaned)
    selected: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(
            phrase in lowered
            for phrase in [
                "update statement",
                "voting outcomes of resolution",
                "shareholders",
                "votes cast were supportive",
                "supportive of resolution",
                "no further actions are necessary",
            ]
        ):
            selected.append(sentence.strip())
        if len(selected) >= 3:
            break

    if not selected:
        selected = sentences[:3]

    summary = " ".join(selected).strip()
    return summary or None


def enrich_with_update_statement_documents(
    resolutions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    pdf_urls = sorted(
        {
            item["updateStatementUrl"]
            for item in resolutions
            if item.get("updateStatementUrl") and str(item["updateStatementUrl"]).lower().endswith(".pdf")
        }
    )

    audit_rows: list[dict[str, Any]] = []
    fetched = 0
    parsed = 0
    enriched = 0

    for url in pdf_urls:
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=(5, 20))
            response.raise_for_status()
        except requests.RequestException as error:
            audit_rows.append({"url": url, "status": "fetch-failed", "error": str(error)})
            continue

        fetched += 1
        raw_path = write_raw_document(url, response.content, ".pdf")

        try:
            reader = PdfReader(str(raw_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:  # noqa: BLE001
            audit_rows.append(
                {
                    "url": url,
                    "status": "parse-failed",
                    "rawPdfPath": str(raw_path.relative_to(ROOT)),
                    "error": str(error),
                }
            )
            continue

        summary = extract_update_statement_summary(text)
        if not summary:
            audit_rows.append(
                {
                    "url": url,
                    "status": "no-summary",
                    "rawPdfPath": str(raw_path.relative_to(ROOT)),
                }
            )
            continue

        parsed += 1
        matched = 0
        for item in resolutions:
            if item.get("updateStatementUrl") != url:
                continue
            item["updateStatementParsed"] = True
            item["updateStatementSummary"] = summary
            item["updateStatementDocumentType"] = "pdf-update-statement"
            matched += 1
            enriched += 1

        audit_rows.append(
            {
                "url": url,
                "status": "parsed",
                "rawPdfPath": str(raw_path.relative_to(ROOT)),
                "matchedRecords": matched,
            }
        )

    stats = {
        "pdfDocumentsFetched": fetched,
        "pdfDocumentsParsed": parsed,
        "pdfUpdateStatementsEnriched": enriched,
    }
    return resolutions, stats, audit_rows


def enrich_with_result_documents(
    resolutions: list[dict[str, Any]],
    lookup: dict[str, CompanyRecord],
    result_documents: list[ResultDocument],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    title_lookup, number_lookup = build_record_lookups(resolutions)
    audit_rows: list[dict[str, Any]] = []
    issuer_only_records: list[dict[str, Any]] = []
    fetched = 0
    parsed = 0
    extracted_rows = 0
    verified_rows = 0

    for document in result_documents:
        try:
            response = requests.get(document.url, headers=REQUEST_HEADERS, timeout=(5, 20))
            response.raise_for_status()
        except requests.RequestException as error:
            audit_rows.append(
                {
                    "url": document.url,
                    "companyName": document.company_name,
                    "meetingDate": document.meeting_date,
                    "status": "fetch-failed",
                    "documentType": "pdf-results",
                    "error": str(error),
                }
            )
            continue

        fetched += 1
        raw_path = write_raw_document(document.url, response.content, ".pdf")

        try:
            reader = PdfReader(str(raw_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:  # noqa: BLE001
            audit_rows.append(
                {
                    "url": document.url,
                    "companyName": document.company_name,
                    "meetingDate": document.meeting_date,
                    "status": "parse-failed",
                    "documentType": "pdf-results",
                    "rawPdfPath": str(raw_path.relative_to(ROOT)),
                    "error": str(error),
                }
            )
            continue

        official_rows = parse_pdf_result_rows(text, document.parser_hint)
        validate_official_vote_rows(official_rows, document.url)
        parsed += 1
        extracted_rows += len(official_rows)
        page_matches = 0
        page_new_records = 0

        for official in official_rows:
            title_key = (
                document.company_name,
                document.meeting_date,
                official["resolutionTitleNormalised"],
            )
            existing = title_lookup.get(title_key)
            if existing is None and official["resolutionNumber"] is not None:
                official_category_key, _ = classify_resolution("", official["resolutionTitle"])
                number_key = (
                    document.company_name,
                    document.meeting_date,
                    official["resolutionNumber"],
                )
                candidate = number_lookup.get(number_key)
                if candidate is not None and (
                    candidate["resolutionCategory"] == official_category_key
                    or "withdrawn" in document.source_group.lower()
                ):
                    existing = candidate
            if existing is not None:
                existing["votesForCount"] = official["votesForCount"] or existing["votesForCount"]
                existing["votesAgainstCount"] = official["votesAgainstCount"] or existing["votesAgainstCount"]
                existing["votesWithheldCount"] = official["votesWithheldCount"] or existing["votesWithheldCount"]
                existing["totalVotesCastCount"] = official["totalVotesCastCount"] or existing["totalVotesCastCount"]
                existing["votesForPct"] = official["votesForPct"] or existing["votesForPct"]
                existing["votesAgainstPct"] = official["votesAgainstPct"] or existing["votesAgainstPct"]
                existing["issuedShareCapitalVotedPct"] = (
                    official["issuedShareCapitalVotedPct"] or existing["issuedShareCapitalVotedPct"]
                )
                existing["officialAnnouncementUrl"] = document.url
                existing["officialAnnouncementSource"] = document.source
                existing["officialAnnouncementVerified"] = True
                existing["officialAnnouncementStatus"] = "verified"
                page_matches += 1
                verified_rows += 1
                continue

            company_match = lookup.get(normalise_name(document.company_name))
            if company_match is None:
                continue

            title = official["resolutionTitle"]
            category_key, category_label = classify_resolution(document.source_group, title)
            _, _, management_dissent_pct = management_vote_context(
                category_key, official["votesForPct"], official["votesAgainstPct"]
            )
            if (management_dissent_pct or 0) < 20:
                continue
            company_slug = slugify(company_match.canonical_name)
            record = {
                "id": build_row_id(company_slug, document.meeting_date, title),
                "companyName": company_match.canonical_name,
                "companySlug": company_slug,
                "sourceCompanyName": document.company_name,
                "sector": company_match.sector,
                "meetingDate": document.meeting_date,
                "meetingYear": datetime.fromisoformat(document.meeting_date).year,
                "meetingType": "AGM",
                "sourceGroup": document.source_group,
                "resolutionTitle": title,
                "votesForPct": official["votesForPct"],
                "votesAgainstPct": official["votesAgainstPct"],
                "votesWithheldPct": None,
                "issuedShareCapitalVotedPct": official["issuedShareCapitalVotedPct"],
                "votesForCount": official["votesForCount"],
                "votesAgainstCount": official["votesAgainstCount"],
                "votesWithheldCount": official["votesWithheldCount"],
                "totalVotesCastCount": official["totalVotesCastCount"],
                "statementInResults": True,
                "statementInResultsUrl": document.url,
                "updateStatement": None,
                "updateStatementUrl": None,
                "resolutionCategory": category_key,
                "resolutionCategoryLabel": category_label,
                "governanceNote": governance_note(category_key, official["votesAgainstPct"], title),
                "sourceUrl": document.url,
                "recordOrigin": "issuer-announcement",
                "recordOriginLabel": "Issuer announcement",
                "officialAnnouncementUrl": document.url,
                "officialAnnouncementSource": document.source,
                "officialAnnouncementVerified": True,
                "officialAnnouncementStatus": "issuer-only",
                "updateStatementParsed": False,
                "updateStatementSummary": None,
                "updateStatementDocumentType": None,
            }
            issuer_only_records.append(record)
            title_lookup[title_key] = record
            if official["resolutionNumber"] is not None:
                number_lookup[(document.company_name, document.meeting_date, official["resolutionNumber"])] = record
            page_new_records += 1

        audit_rows.append(
            {
                "url": document.url,
                "companyName": document.company_name,
                "meetingDate": document.meeting_date,
                "status": "parsed",
                "documentType": "pdf-results",
                "rawPdfPath": str(raw_path.relative_to(ROOT)),
                "rowsExtracted": len(official_rows),
                "rowsMatched": page_matches,
                "rowsAdded": page_new_records,
                "parserHint": document.parser_hint,
            }
        )

    combined = resolutions + issuer_only_records
    combined.sort(key=lambda item: (item["meetingDate"], item["companyName"], item["resolutionTitle"]), reverse=True)
    stats = {
        "pdfResultDocumentsFetched": fetched,
        "pdfResultDocumentsParsed": parsed,
        "pdfResultRowsExtracted": extracted_rows,
        "pdfResultVerifiedResolutions": verified_rows,
        "pdfResultIssuerOnlyAdded": len(issuer_only_records),
        "officialVoteCountCoverage": sum(1 for item in combined if item["votesForCount"] is not None),
    }
    return combined, stats, audit_rows


def build_record_lookups(
    resolutions: list[dict[str, Any]],
) -> tuple[
    dict[tuple[str, str, str], dict[str, Any]],
    dict[tuple[str, str, int], dict[str, Any]],
]:
    title_lookup = {
        (
            item["companyName"],
            item["meetingDate"],
            normalise_resolution_title(item["resolutionTitle"]),
        ): item
        for item in resolutions
    }

    number_lookup: dict[tuple[str, str, int], dict[str, Any]] = {}
    for item in resolutions:
        number = extract_resolution_number(item["resolutionTitle"])
        if number is None:
            continue
        number_lookup[(item["companyName"], item["meetingDate"], number)] = item

    return title_lookup, number_lookup


def enrich_with_official_announcements(
    resolutions: list[dict[str, Any]],
    lookup: dict[str, CompanyRecord],
    announcement_pages: list[AnnouncementPage],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    title_lookup, number_lookup = build_record_lookups(resolutions)
    audit_rows: list[dict[str, Any]] = []
    issuer_only_records: list[dict[str, Any]] = []
    parsed_pages = 0
    extracted_rows = 0
    verified_rows = 0

    def fallback_existing(page_company: str, page_date: str, official: dict[str, Any], source_group: str) -> dict[str, Any] | None:
        category_key, _ = classify_resolution(source_group, official["resolutionTitle"])
        official_against = official.get("votesAgainstPct")
        same_date_candidates: list[dict[str, Any]] = []
        for candidate in resolutions:
            if candidate["companyName"] != page_company or candidate["meetingDate"] != page_date:
                continue
            if candidate.get("officialAnnouncementVerified"):
                continue
            same_date_candidates.append(candidate)
            if candidate["resolutionCategory"] != category_key:
                continue
            candidate_against = candidate.get("votesAgainstPct")
            if official_against is None or candidate_against is None:
                continue
            if abs(candidate_against - official_against) <= 0.2:
                return candidate

        for candidate in same_date_candidates:
            candidate_against = candidate.get("votesAgainstPct")
            if official_against is None or candidate_against is None:
                continue
            if abs(candidate_against - official_against) <= 0.2:
                return candidate
        return None

    for page in announcement_pages:
        try:
            html = fetch_url(page.url)
        except requests.RequestException as error:
            audit_rows.append(
                {
                    "url": page.url,
                    "companyName": page.company_name,
                    "meetingDate": page.meeting_date,
                    "status": "fetch-failed",
                    "error": str(error),
                }
            )
            continue

        raw_path = write_raw_announcement_html(page.url, html)
        official_rows = parse_announcement_tables(html, page.parser_hint)
        if page.source != "ia-linked-announcement":
            validate_official_vote_rows(official_rows, page.url)
        parsed_pages += 1
        extracted_rows += len(official_rows)
        page_matches = 0
        page_new_records = 0

        for official in official_rows:
            title_key = (
                page.company_name,
                page.meeting_date,
                official["resolutionTitleNormalised"],
            )
            existing = title_lookup.get(title_key)
            if existing is None:
                existing = fallback_existing(page.company_name, page.meeting_date, official, page.source_group)
            if existing is None and official["resolutionNumber"] is not None:
                official_category_key, _ = classify_resolution("", official["resolutionTitle"])
                number_key = (
                    page.company_name,
                    page.meeting_date,
                    official["resolutionNumber"],
                )
                candidate = number_lookup.get(number_key)
                if candidate is not None and (
                    candidate["resolutionCategory"] == official_category_key
                    or "withdrawn" in page.source_group.lower()
                ):
                    existing = candidate
            if existing is not None:
                existing["votesForCount"] = official["votesForCount"] or existing["votesForCount"]
                existing["votesAgainstCount"] = official["votesAgainstCount"] or existing["votesAgainstCount"]
                existing["votesWithheldCount"] = official["votesWithheldCount"] or existing["votesWithheldCount"]
                existing["totalVotesCastCount"] = official["totalVotesCastCount"] or existing["totalVotesCastCount"]
                existing["votesForPct"] = official["votesForPct"] or existing["votesForPct"]
                existing["votesAgainstPct"] = official["votesAgainstPct"] or existing["votesAgainstPct"]
                existing["issuedShareCapitalVotedPct"] = (
                    official["issuedShareCapitalVotedPct"] or existing["issuedShareCapitalVotedPct"]
                )
                existing["officialAnnouncementUrl"] = page.url
                existing["officialAnnouncementSource"] = page.source
                existing["officialAnnouncementVerified"] = True
                existing["officialAnnouncementStatus"] = "verified"
                page_matches += 1
                verified_rows += 1
                continue

            if not page.allow_issuer_only:
                continue

            company_match = lookup.get(normalise_name(page.company_name))
            if company_match is None:
                continue

            title = official["resolutionTitle"]
            category_key, category_label = classify_resolution(page.source_group, title)
            _, _, management_dissent_pct = management_vote_context(
                category_key, official["votesForPct"], official["votesAgainstPct"]
            )
            if (management_dissent_pct or 0) < 20:
                continue
            company_slug = slugify(company_match.canonical_name)
            record = {
                "id": build_row_id(company_slug, page.meeting_date, title),
                "companyName": company_match.canonical_name,
                "companySlug": company_slug,
                "sourceCompanyName": page.company_name,
                "sector": company_match.sector,
                "meetingDate": page.meeting_date,
                "meetingYear": datetime.fromisoformat(page.meeting_date).year,
                "meetingType": "AGM",
                "sourceGroup": page.source_group,
                "resolutionTitle": title,
                "votesForPct": official["votesForPct"],
                "votesAgainstPct": official["votesAgainstPct"],
                "votesWithheldPct": None,
                "issuedShareCapitalVotedPct": official["issuedShareCapitalVotedPct"],
                "votesForCount": official["votesForCount"],
                "votesAgainstCount": official["votesAgainstCount"],
                "votesWithheldCount": official["votesWithheldCount"],
                "totalVotesCastCount": official["totalVotesCastCount"],
                "statementInResults": True,
                "statementInResultsUrl": page.url,
                "updateStatement": None,
                "updateStatementUrl": None,
                "resolutionCategory": category_key,
                "resolutionCategoryLabel": category_label,
                "governanceNote": governance_note(category_key, official["votesAgainstPct"], title),
                "sourceUrl": page.url,
                "recordOrigin": "issuer-announcement",
                "recordOriginLabel": "Issuer announcement",
                "officialAnnouncementUrl": page.url,
                "officialAnnouncementSource": page.source,
                "officialAnnouncementVerified": True,
                "officialAnnouncementStatus": "issuer-only",
            }
            issuer_only_records.append(record)
            title_lookup[title_key] = record
            if official["resolutionNumber"] is not None:
                number_lookup[(page.company_name, page.meeting_date, official["resolutionNumber"])] = record
            page_new_records += 1

        audit_rows.append(
            {
                "url": page.url,
                "companyName": page.company_name,
                "meetingDate": page.meeting_date,
                "status": "parsed",
                "rawHtmlPath": str(raw_path.relative_to(ROOT)),
                "rowsExtracted": len(official_rows),
                "rowsMatched": page_matches,
                "rowsAdded": page_new_records,
            }
        )

    combined = resolutions + issuer_only_records
    combined.sort(key=lambda item: (item["meetingDate"], item["companyName"], item["resolutionTitle"]), reverse=True)
    stats = {
        "issuerAnnouncementPagesFetched": len(announcement_pages),
        "issuerAnnouncementPagesParsed": parsed_pages,
        "issuerAnnouncementRowsExtracted": extracted_rows,
        "issuerVerifiedResolutions": verified_rows,
        "issuerOnlyResolutionsAdded": len(issuer_only_records),
        "officialVoteCountCoverage": sum(1 for item in combined if item["votesForCount"] is not None),
    }
    return combined, stats, audit_rows


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
        "managementDissentPct",
        "managementSponsored",
        "managementRecommendation",
        "votesWithheldPct",
        "issuedShareCapitalVotedPct",
        "votesForCount",
        "votesAgainstCount",
        "votesWithheldCount",
        "totalVotesCastCount",
        "statementInResults",
        "statementInResultsUrl",
        "updateStatement",
        "updateStatementUrl",
        "resolutionCategory",
        "resolutionCategoryLabel",
        "governanceNote",
        "sourceUrl",
        "recordOrigin",
        "recordOriginLabel",
        "officialAnnouncementUrl",
        "officialAnnouncementSource",
        "officialAnnouncementVerified",
        "officialAnnouncementStatus",
        "updateStatementParsed",
        "updateStatementSummary",
        "updateStatementDocumentType",
    ]
    with (PROCESSED_DIR / "ftse100_resolutions.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(resolutions)


def build_summary(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    companies = sorted({item["companyName"] for item in resolutions})
    categories = Counter(item["resolutionCategoryLabel"] for item in resolutions)
    years = sorted({item["meetingYear"] for item in resolutions})
    highest = max((item["managementDissentPct"] or 0.0 for item in resolutions), default=0.0)
    remuneration_count = sum(1 for item in resolutions if item["resolutionCategory"] == "remuneration")
    director_count = sum(1 for item in resolutions if item["resolutionCategory"] == "director-election")

    return {
        "companyCount": len(companies),
        "resolutionCount": len(resolutions),
        "yearsCovered": years,
        "highestVotesAgainstPct": highest,
        "highestManagementDissentPct": highest,
        "categoryBreakdown": categories,
        "remunerationCount": remuneration_count,
        "directorElectionCount": director_count,
        "issuerVerifiedCount": sum(1 for item in resolutions if item["officialAnnouncementVerified"]),
        "issuerOnlyCount": sum(1 for item in resolutions if item["recordOrigin"] == "issuer-announcement"),
        "voteCountCoverage": sum(1 for item in resolutions if item["votesForCount"] is not None),
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
        "managementDissentPct",
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
    announcement_audit: list[dict[str, Any]],
    document_audit: list[dict[str, Any]],
) -> None:
    summary = build_summary(resolutions)
    generated_at = datetime.now(timezone.utc).isoformat()
    start_date = min((item["meetingDate"] for item in resolutions), default=None)
    end_date = max((item["meetingDate"] for item in resolutions), default=None)
    reviewed_meetings = {
        (item["companyName"], item["meetingDate"])
        for item in announcement_audit + document_audit
        if item.get("status") == "parsed"
        and item.get("rowsExtracted", 0) > 0
        and item.get("companyName")
        and item.get("meetingDate")
    }
    direct_dates = sorted(meeting_date for _, meeting_date in reviewed_meetings)
    post_register_meetings = [
        {"companyName": company_name, "meetingDate": meeting_date}
        for company_name, meeting_date in sorted(reviewed_meetings)
        if meeting_date > "2025-10-31"
    ]
    payload = {
        "metadata": {
            "title": "FTSE 100 Shareholder Dissent Tracker",
            "sourceName": "IA Public Register + official issuer announcements",
            "sourceUrl": SOURCE_URL,
            "generatedAt": generated_at,
            "refreshMode": "weekly-automated-refresh-with-editorial-source-onboarding",
            "focusStatement": "This app tracks significant shareholder dissent, not general AGM voting coverage.",
            "coverageStatement": (
                "Phase 2 combines the Investment Association Public Register with parsed issuer announcement pages "
                "and selected official result PDFs where machine-readable vote outcomes can be extracted cleanly."
            ),
            "coveragePeriod": {
                "startDate": start_date,
                "endDate": end_date,
            },
            "directIssuerMeetingCoverage": {
                "reviewedMeetingCount": len(reviewed_meetings),
                "startDate": direct_dates[0] if direct_dates else None,
                "endDate": direct_dates[-1] if direct_dates else None,
                "postRegisterMeetingCount": len(post_register_meetings),
                "postRegisterMeetings": post_register_meetings,
                "interpretation": "Reviewed meetings include complete official vote tables even when no resolution crossed the 20% publication threshold.",
            },
            "sourceLayers": [
                {
                    "name": "Investment Association Public Register",
                    "role": "Historical significant-dissent register and base resolution feed",
                },
                {
                    "name": "Official issuer announcements",
                    "role": "Issuer-level verification and vote-count enrichment from company-linked HTML results pages and selected result PDFs",
                },
            ],
            "methodology": {
                "included": [
                    "Resolutions listed on the IA Public Register for significant votes against management or withdrawn resolutions.",
                    "Records matched with high confidence to the curated FTSE 100 issuer alias file.",
                    "Official issuer announcement pages linked from the register or added as manual issuer seeds where parsable.",
                    "Selected official AGM result PDFs where vote tables can be extracted with high confidence.",
                    "For board-opposed shareholder proposals, support for the proposal is reported as dissent against management; raw for and against percentages remain separately disclosed.",
                ],
                "excluded": [
                    "Routine AGM resolutions that did not reach the tracker’s significance threshold.",
                    "Companies not matched with sufficient confidence to the FTSE 100 issuer list.",
                    "PDF-only issuer result documents that have not yet been added to the parser layer.",
                ],
                "sourceCredibilityNote": (
                    "The Investment Association Public Register sits inside the UK governance and stewardship ecosystem, "
                    "while the issuer-announcement layer pulls directly from company-linked official meeting result pages and issuer-published AGM result documents."
                ),
            },
            "limitations": [
                "The IA Public Register records significant votes against management or withdrawn resolutions rather than every AGM resolution.",
                "The Investment Association stated in October 2025 that no new companies or resolutions would be added to the register.",
                "Issuer-announcement enrichment covers configured HTML result pages and selected stable PDF layouts; new issuer formats require editorial parser review before publication.",
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
    (PROCESSED_DIR / "issuer_announcement_audit.json").write_text(json.dumps(announcement_audit, indent=2))
    (PROCESSED_DIR / "issuer_document_audit.json").write_text(json.dumps(document_audit, indent=2))
    (PUBLIC_DATA_DIR / "tracker-data.json").write_text(json.dumps(payload, indent=2))
    write_csv(resolutions)


def main() -> None:
    ensure_dirs()
    lookup, _ = load_company_metadata()
    source_config, result_documents = load_source_config()
    html = fetch_public_register()
    resolutions, unmatched, ia_stats = parse_tables(html, lookup)
    announcement_pages = collect_announcement_pages(resolutions, source_config)
    resolutions, issuer_stats, announcement_audit = enrich_with_official_announcements(
        resolutions,
        lookup,
        announcement_pages,
    )
    resolutions, pdf_result_stats, pdf_result_audit = enrich_with_result_documents(
        resolutions,
        lookup,
        result_documents,
    )
    resolutions, document_stats, document_audit = enrich_with_update_statement_documents(resolutions)
    for resolution in resolutions:
        apply_management_context(resolution)
    resolutions = [
        resolution
        for resolution in resolutions
        if (resolution.get("managementDissentPct") or 0) >= 20
        or "withdraw" in resolution["resolutionTitle"].lower()
    ]
    validation = validate_records(resolutions)
    if validation["status"] == "fail":
        raise ValueError(json.dumps(validation, indent=2))

    stats = {
        **ia_stats,
        **issuer_stats,
        **pdf_result_stats,
        **document_stats,
        "issuerVerifiedResolutions": sum(
            1 for resolution in resolutions if resolution["officialAnnouncementVerified"]
        ),
        "issuerOnlyResolutionsAdded": sum(
            1 for resolution in resolutions if resolution["recordOrigin"] == "issuer-announcement"
        ),
        "officialVoteCountCoverage": sum(
            1 for resolution in resolutions if resolution["votesForCount"] is not None
        ),
    }
    write_outputs(
        resolutions,
        unmatched,
        stats,
        validation,
        announcement_audit,
        pdf_result_audit + document_audit,
    )
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
