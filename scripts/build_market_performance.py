#!/usr/bin/env python3
"""Build validated FTSE 100 market-performance series from public Yahoo chart data."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
LEADERSHIP_PATH = ROOT / "public" / "data" / "leadership-radar.json"
OUTPUT_PATH = ROOT / "public" / "data" / "market-performance.json"
MARKET_SYMBOL_OVERRIDES = {"BT.A": "BT-A.L"}
BENCHMARK = "^FTSE"


def fetch_chart(symbol: str, period1: int) -> list[dict[str, float | str]]:
    print(f"Fetching {symbol}...", flush=True)
    query = urlencode({
        "period1": period1,
        "period2": int(datetime.now(timezone.utc).timestamp()),
        "interval": "1mo",
        "events": "div,splits",
    })
    response = subprocess.run(
        [
            "curl", "--fail", "--location", "--silent", "--show-error",
            "--user-agent", "Mozilla/5.0 ProxyWarsGovernanceResearch/1.0",
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    result = json.loads(response.stdout)["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    points = []
    for timestamp, close, adj_close in zip(timestamps, quote["close"], adjusted):
        if close is None or adj_close is None or close <= 0 or adj_close <= 0:
            continue
        points.append({
            "date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
            "close": round(close, 4),
            "adjustedClose": round(adj_close, 4),
        })
    return points


def normalise(points: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    first_close = float(points[0]["close"])
    first_adjusted = float(points[0]["adjustedClose"])
    return [
        {
            **point,
            "priceReturnPct": round((float(point["close"]) / first_close - 1) * 100, 2),
            "dividendAdjustedReturnPct": round((float(point["adjustedClose"]) / first_adjusted - 1) * 100, 2),
        }
        for point in points
    ]


def market_symbol(ticker: str) -> str:
    return MARKET_SYMBOL_OVERRIDES.get(ticker, f"{ticker}.L")


def main() -> None:
    leadership = json.loads(LEADERSHIP_PATH.read_text(encoding="utf-8"))
    companies = {company["ticker"]: company for company in leadership["companies"]}
    errors = []
    series = []
    earliest_start = min(
        company["roles"][role].get("roleStartDate")
        for company in companies.values()
        for role in ("ceo", "chair")
        if company["roles"][role].get("roleStartDate")
    )
    period1 = int(datetime.fromisoformat(earliest_start).replace(tzinfo=timezone.utc).timestamp())
    benchmark_points = fetch_chart(BENCHMARK, period1)

    for ticker, company in companies.items():
        symbol = market_symbol(ticker)
        role_dates = [
            company["roles"][role].get("roleStartDate")
            for role in ("ceo", "chair")
            if company["roles"][role].get("roleStartDate")
        ]
        company_period1 = int(datetime.fromisoformat(min(role_dates)).replace(tzinfo=timezone.utc).timestamp())
        try:
            points = fetch_chart(symbol, company_period1)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, KeyError, TypeError, json.JSONDecodeError) as exc:
            errors.append(f"Unable to fetch market data for {ticker} ({symbol}): {type(exc).__name__}.")
            continue
        if len(points) < 2:
            errors.append(f"Insufficient observations for {ticker}.")
            continue
        if len({point["date"] for point in points}) != len(points):
            errors.append(f"Duplicate observation date for {ticker}.")
        if points != sorted(points, key=lambda point: point["date"]):
            errors.append(f"Unsorted observations for {ticker}.")
        series.append({
            "ticker": ticker,
            "companyName": company["companyName"],
            "marketSymbol": symbol,
            "roles": {
                role: {
                    "name": company["roles"][role].get("name", "Not applicable"),
                    "roleStartDate": company["roles"][role].get("roleStartDate"),
                }
                for role in ("ceo", "chair")
            },
            "points": normalise(points),
        })

    if errors or len(series) != len(companies) or len(benchmark_points) < 12:
        raise RuntimeError("; ".join(errors or ["Market-performance coverage is incomplete."]))

    payload = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "companyCount": len(series),
            "sourceName": "Yahoo Finance public chart endpoint",
            "sourceUrl": "https://finance.yahoo.com/",
            "frequency": "Monthly",
            "methodology": "Share-price return uses unadjusted close. Dividend-adjusted return uses Yahoo adjusted close, rebased from the first observation on or after the selected leader's role start date.",
            "limitations": "A public-data research series, not a licensed total-return index. Adjusted-close methodology and historical corrections are controlled by the data provider; currency, tax and transaction costs are excluded.",
            "validation": {"status": "pass", "errors": []},
        },
        "benchmark": {"symbol": BENCHMARK, "name": "FTSE 100 price index", "points": normalise(benchmark_points)},
        "companies": series,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(series)} company series.")


if __name__ == "__main__":
    main()
