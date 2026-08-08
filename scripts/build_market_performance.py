#!/usr/bin/env python3
"""Build validated FTSE 100 market-performance series from public Yahoo chart data."""

from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
LEADERSHIP_PATH = ROOT / "public" / "data" / "leadership-radar.json"
OUTCOME_PATH = ROOT / "data" / "leadership_transition_outcomes.json"
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


def repair_scale_discontinuities(
    points: list[dict[str, float | str]],
) -> tuple[list[dict[str, float | str]], int]:
    """Align isolated GBP/GBp unit switches without smoothing genuine returns."""
    repaired: list[dict[str, float | str]] = []
    adjustment_count = 0
    for point in points:
        close = float(point["close"])
        adjusted_close = float(point["adjustedClose"])
        factor = 1.0
        if repaired:
            previous = float(repaired[-1]["adjustedClose"])
            raw_ratio = adjusted_close / previous
            if raw_ratio < 0.05 or raw_ratio > 20:
                candidates = (0.01, 1.0, 100.0)
                factor = min(
                    candidates,
                    key=lambda candidate: abs(math.log((adjusted_close * candidate) / previous)),
                )
        if factor != 1:
            adjustment_count += 1
        repaired.append({
            **point,
            "close": round(close * factor, 4),
            "adjustedClose": round(adjusted_close * factor, 4),
        })
    return repaired, adjustment_count


def extreme_discontinuities(points: list[dict[str, float | str]]) -> list[str]:
    errors = []
    for previous, current in zip(points, points[1:]):
        ratio = float(current["adjustedClose"]) / float(previous["adjustedClose"])
        if ratio < 0.05 or ratio > 20:
            errors.append(f"{previous['date']} to {current['date']} ({ratio:.2f}x)")
    return errors


def market_symbol(ticker: str) -> str:
    return MARKET_SYMBOL_OVERRIDES.get(ticker, f"{ticker}.L")


def main() -> None:
    leadership = json.loads(LEADERSHIP_PATH.read_text(encoding="utf-8"))
    outcomes = json.loads(OUTCOME_PATH.read_text(encoding="utf-8"))
    companies = {company["ticker"]: company for company in leadership["companies"]}
    historical_starts: dict[str, list[str]] = {}
    for case in outcomes["completedCases"]:
        historical_starts.setdefault(case["ticker"], []).append(case["roleStartDate"])
    errors = []
    series = []
    earliest_start = min(
        company["roles"][role].get("roleStartDate")
        for company in companies.values()
        for role in ("ceo", "chair")
        if company["roles"][role].get("roleStartDate")
    )
    period1 = int(datetime.fromisoformat(earliest_start).replace(tzinfo=timezone.utc).timestamp())
    benchmark_points, benchmark_adjustments = repair_scale_discontinuities(fetch_chart(BENCHMARK, period1))
    total_scale_adjustments = benchmark_adjustments

    for ticker, company in companies.items():
        symbol = market_symbol(ticker)
        role_dates = [
            company["roles"][role].get("roleStartDate")
            for role in ("ceo", "chair")
            if company["roles"][role].get("roleStartDate")
        ]
        company_period1 = int(datetime.fromisoformat(min([*role_dates, *historical_starts.get(ticker, [])])).replace(tzinfo=timezone.utc).timestamp())
        try:
            points, scale_adjustment_count = repair_scale_discontinuities(fetch_chart(symbol, company_period1))
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
        remaining_discontinuities = extreme_discontinuities(points)
        if remaining_discontinuities:
            errors.append(f"Extreme scale discontinuity remains for {ticker}: {remaining_discontinuities[0]}.")
        total_scale_adjustments += scale_adjustment_count
        series.append({
            "ticker": ticker,
            "companyName": company["companyName"],
            "marketSymbol": symbol,
            "scaleAdjustmentCount": scale_adjustment_count,
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
            "scaleTreatment": "Isolated approximately 100x GBP/GBp unit switches are aligned to the preceding observation before returns are calculated; corrections never smooth ordinary price movements.",
            "scaleAdjustmentCount": total_scale_adjustments,
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
