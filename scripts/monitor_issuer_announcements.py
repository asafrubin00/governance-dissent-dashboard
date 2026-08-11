#!/usr/bin/env python3
"""Detect new earnings-related links on official issuer pages for editorial review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "announcement_monitor_sources.json"
LEADERSHIP_PATH = ROOT / "data" / "leadership_sources.json"
LEADERSHIP_EXPANSION_PATH = ROOT / "data" / "leadership_sources_expansion.json"
SNAPSHOT_PATH = ROOT / "data" / "announcement_monitor_snapshot.json"
QUEUE_PATH = ROOT / "data" / "announcement_review_queue.json"
STATUS_PATH = ROOT / "public" / "data" / "announcement-monitor.json"
USER_AGENT = "ProxyWarsGovernanceResearch/1.0 (+source-monitor; review-only)"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def canonical_url(value: str) -> str:
    parsed = urlparse(value)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", ""))


def candidate_id(ticker: str, url: str) -> str:
    digest = hashlib.sha256(f"{ticker}|{canonical_url(url)}".encode()).hexdigest()[:16]
    return f"{ticker.lower()}-{digest}"


def validate_config(config: dict[str, Any], queue: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = config.get("sources", [])
    tickers = [source.get("ticker") for source in sources]
    if len(tickers) != len(set(tickers)):
        errors.append("Duplicate monitored ticker found.")
    leadership = json.loads(LEADERSHIP_PATH.read_text(encoding="utf-8"))
    expansion = json.loads(LEADERSHIP_EXPANSION_PATH.read_text(encoding="utf-8"))
    leadership_tickers = {
        company["ticker"] for company in [*leadership["companies"], *expansion["companies"]]
    }
    if set(tickers) != leadership_tickers:
        errors.append("Monitored tickers do not exactly match the source-verified leadership cohort.")
    keyword_groups = config.get("keywordGroups", {})
    if set(keyword_groups) != {"earnings", "succession"}:
        errors.append("Monitor keyword groups must contain earnings and succession.")
    if any(not keywords for keywords in keyword_groups.values()):
        errors.append("Announcement-monitor keyword groups cannot be empty.")
    for source in sources:
        if not source.get("ticker") or not source.get("companyName"):
            errors.append("Monitor source is missing a ticker or company name.")
        if not str(source.get("url", "")).startswith("https://"):
            errors.append(f"Monitor URL must use HTTPS for {source.get('ticker', '[unknown]')}.")
        for fallback_url in source.get("fallbackUrls", []):
            if not str(fallback_url).startswith("https://"):
                errors.append(f"Monitor fallback URL must use HTTPS for {source.get('ticker', '[unknown]')}.")
    queue_ids = [item.get("id") for item in queue.get("candidates", [])]
    if len(queue_ids) != len(set(queue_ids)):
        errors.append("Duplicate announcement review-queue ID found.")
    allowed_statuses = {"pending", "dismissed", "promoted"}
    for item in queue.get("candidates", []):
        if item.get("status") not in allowed_statuses:
            errors.append(f"Unsupported review status for {item.get('id', '[unknown]')}.")
        if not item.get("url") or not item.get("ticker"):
            errors.append(f"Review candidate is missing a URL or ticker: {item.get('id', '[unknown]')}.")
        if not set(item.get("signalTypes", [])).issubset(keyword_groups):
            errors.append(f"Review candidate has an unsupported signal type: {item.get('id', '[unknown]')}.")
    return errors


def fetch_candidates(
    source: dict[str, Any],
    keyword_groups: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], str]:
    session = requests.Session()
    session.mount(
        "https://",
        HTTPAdapter(
            max_retries=Retry(
                total=2,
                connect=2,
                read=2,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("GET",),
            )
        ),
    )
    errors = []
    response = None
    for url in [source["url"], *source.get("fallbackUrls", [])]:
        try:
            response = session.get(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-GB,en;q=0.8",
                },
                timeout=(7, 20),
            )
            response.raise_for_status()
            break
        except requests.RequestException as error:
            errors.append(f"{url}: {error}")
            response = None
    if response is None:
        raise requests.RequestException("; ".join(errors))
    soup = BeautifulSoup(response.text, "html.parser")
    source_host = urlparse(response.url).netloc.lower().removeprefix("www.")
    matches: dict[str, dict[str, str]] = {}

    for link in soup.find_all("a", href=True):
        title = clean_text(link.get_text(" ", strip=True))
        href = urljoin(response.url, link["href"])
        host = urlparse(href).netloc.lower().removeprefix("www.")
        haystack = f"{title} {href}".lower().replace("-", " ").replace("_", " ")
        signal_types = sorted(
            group
            for group, keywords in keyword_groups.items()
            if any(keyword in haystack for keyword in keywords)
        )
        if not title or len(title) < 6 or not signal_types:
            continue
        if host != source_host and not host.endswith(f".{source_host}") and not source_host.endswith(f".{host}"):
            continue
        url = canonical_url(href)
        matches[url] = {"title": title[:240], "url": url, "signalTypes": signal_types}

    return sorted(matches.values(), key=lambda item: item["url"]), response.url


def failure_category(error: Exception) -> str:
    message = str(error).lower()
    if "403" in message or "401" in message:
        return "access-blocked"
    if "timed out" in message or "timeout" in message:
        return "timeout"
    if "ssl" in message or "certificate" in message:
        return "tls-error"
    if "404" in message:
        return "not-found"
    if "429" in message:
        return "rate-limited"
    return "fetch-error"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Record current links without adding them to the editorial queue.",
    )
    args = parser.parse_args()
    now = datetime.now(timezone.utc).isoformat()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    errors = validate_config(config, queue)
    if errors:
        raise RuntimeError("; ".join(errors))

    existing_queue_ids = {item["id"] for item in queue["candidates"]}
    source_health: list[dict[str, Any]] = []
    new_candidate_count = 0

    fetch_results: dict[str, tuple[list[dict[str, Any]], str] | Exception] = {}
    with ThreadPoolExecutor(max_workers=min(20, len(config["sources"]))) as executor:
        futures = {
            executor.submit(fetch_candidates, source, config["keywordGroups"]): source["ticker"]
            for source in config["sources"]
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                fetch_results[ticker] = future.result()
            except Exception as error:
                fetch_results[ticker] = error

    for source in config["sources"]:
        ticker = source["ticker"]
        previous = snapshot["sources"].get(ticker, {"seenIds": []})
        seen_ids = set(previous.get("seenIds", []))
        try:
            result = fetch_results[ticker]
            if isinstance(result, Exception):
                raise result
            candidates, resolved_url = result
            current_ids = {candidate_id(ticker, item["url"]) for item in candidates}
            new_items = [] if args.baseline or not previous.get("lastSuccessAt") or not previous.get("matchedLinkCount") else [
                item for item in candidates if candidate_id(ticker, item["url"]) not in seen_ids
            ]
            for item in new_items:
                item_id = candidate_id(ticker, item["url"])
                if item_id in existing_queue_ids:
                    continue
                queue["candidates"].append({
                    "id": item_id,
                    "ticker": ticker,
                    "companyName": source["companyName"],
                    "title": item["title"],
                    "url": item["url"],
                    "signalTypes": item["signalTypes"],
                    "detectedAt": now,
                    "status": "pending",
                    "reviewNote": "Keyword match only; verify the official announcement before adding any analytical evidence.",
                })
                existing_queue_ids.add(item_id)
                new_candidate_count += 1
            snapshot["sources"][ticker] = {
                "companyName": source["companyName"],
                "configuredUrl": source["url"],
                "resolvedUrl": resolved_url,
                "lastSuccessAt": now,
                "lastError": None,
                "matchedLinkCount": len(candidates),
                "seenIds": sorted(seen_ids | current_ids),
            }
            source_health.append({
                "ticker": ticker,
                "status": "active" if candidates else "reachable-no-matches",
                "matchedLinkCount": len(candidates),
                "matchedLinkCountBySignal": {
                    group: sum(group in item["signalTypes"] for item in candidates)
                    for group in config["keywordGroups"]
                },
            })
        except Exception as error:
            snapshot["sources"][ticker] = {
                **previous,
                "companyName": source["companyName"],
                "configuredUrl": source["url"],
                "lastAttemptAt": now,
                "lastError": str(error)[:300],
            }
            source_health.append({
                "ticker": ticker,
                "status": "unavailable",
                "failureCategory": failure_category(error),
                "error": str(error)[:240],
            })

    snapshot["lastRunAt"] = now
    queue["updatedAt"] = now
    queue["candidates"].sort(key=lambda item: item["detectedAt"], reverse=True)
    active_count = sum(item["status"] == "active" for item in source_health)
    reachable_count = sum(item["status"] != "unavailable" for item in source_health)
    unavailable_by_category = {
        category: sum(item.get("failureCategory") == category for item in source_health)
        for category in sorted({item.get("failureCategory") for item in source_health if item.get("failureCategory")})
    }
    status = {
        "metadata": {
            "generatedAt": now,
            "mode": "baseline" if args.baseline else "monitor",
            "publicationRule": "Detection creates a typed review candidate only. Nothing is added to warning or succession evidence without source verification.",
            "sourceCount": len(config["sources"]),
            "activeSourceCount": active_count,
            "reachableSourceCount": reachable_count,
            "unavailableSourceCount": len(source_health) - reachable_count,
            "unavailableSourceCountByCategory": unavailable_by_category,
            "newCandidateCount": new_candidate_count,
            "pendingCandidateCount": sum(item["status"] == "pending" for item in queue["candidates"]),
            "pendingCandidateCountBySignal": {
                group: sum(
                    item["status"] == "pending" and group in item.get("signalTypes", [])
                    for item in queue["candidates"]
                )
                for group in config["keywordGroups"]
            },
            "validation": {"status": "pass", "errors": []},
        },
        "sources": source_health,
    }
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    QUEUE_PATH.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(
        f"Monitored {len(source_health)} issuers: {active_count} active, "
        f"{reachable_count} reachable, {len(source_health) - reachable_count} unavailable, "
        f"{new_candidate_count} new review candidates."
    )


if __name__ == "__main__":
    main()
