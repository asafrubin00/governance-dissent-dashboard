#!/usr/bin/env python3
"""Validate source-backed leadership profiles against the published radar."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILES_PATH = ROOT / "public" / "data" / "leadership-profiles.json"
RADAR_PATH = ROOT / "public" / "data" / "leadership-radar.json"


def main() -> None:
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    radar = json.loads(RADAR_PATH.read_text(encoding="utf-8"))
    radar_by_ticker = {company["ticker"]: company for company in radar["companies"]}
    errors: list[str] = []
    tickers = [company.get("ticker") for company in profiles.get("companies", [])]

    if len(tickers) != len(set(tickers)):
        errors.append("Duplicate leadership-profile ticker found.")
    if profiles.get("metadata", {}).get("companyCount") != len(tickers):
        errors.append("Leadership-profile metadata count does not match the company records.")

    for company in profiles.get("companies", []):
        ticker = company.get("ticker")
        radar_company = radar_by_ticker.get(ticker)
        if not radar_company:
            errors.append(f"Profile ticker is outside the radar universe: {ticker}.")
            continue
        for role_key, profile in company.get("roles", {}).items():
            radar_role = radar_company.get("roles", {}).get(role_key)
            if not radar_role:
                errors.append(f"Unsupported profile role for {ticker}: {role_key}.")
                continue
            if profile.get("name") != radar_role.get("name"):
                errors.append(f"Profile name does not match the radar for {ticker} {role_key}.")
            if len(profile.get("summary", "").strip()) < 40:
                errors.append(f"Profile summary is missing or too short for {ticker} {role_key}.")
            if not str(profile.get("sourceUrl", "")).startswith("https://"):
                errors.append(f"Profile source must use HTTPS for {ticker} {role_key}.")
            portrait_path = profile.get("portraitPath")
            if portrait_path:
                local_path = ROOT / "public" / portrait_path.lstrip("/")
                if not local_path.is_file():
                    errors.append(f"Profile portrait is missing for {ticker} {role_key}: {portrait_path}.")

    if errors:
        raise RuntimeError("; ".join(errors))

    print(f"Validated {len(tickers)} source-backed company profiles.")


if __name__ == "__main__":
    main()
