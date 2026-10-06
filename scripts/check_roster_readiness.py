#!/usr/bin/env python3
"""Check the live FTSE 100 roster without rebuilding the full product dataset."""

from __future__ import annotations

import json
import os

from build_leadership_radar import (
    EXPANSION_SOURCE_PATH,
    ROSTER_PATH,
    ROSTER_READINESS_PATH,
    SOURCE_PATH,
    build_roster_readiness,
    fetch_roster,
    write_roster_readiness,
)


def main() -> None:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    expansion = json.loads(EXPANSION_SOURCE_PATH.read_text(encoding="utf-8"))
    curated = [*source["companies"], *expansion["companies"]]
    roster = fetch_roster()
    previous = None
    if ROSTER_READINESS_PATH.exists():
        previous = json.loads(ROSTER_READINESS_PATH.read_text(encoding="utf-8"))

    report = build_roster_readiness(roster, curated, previous)
    report_changed = write_roster_readiness(report)
    current_roster = json.loads(ROSTER_PATH.read_text(encoding="utf-8")) if ROSTER_PATH.exists() else None
    roster_changed = current_roster != roster
    if roster_changed:
        ROSTER_PATH.write_text(json.dumps(roster, indent=2) + "\n", encoding="utf-8")

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"pending_count={len(report['pendingEntrants'])}\n")
            output.write(f"changed={'true' if report_changed or roster_changed else 'false'}\n")

    pending = ", ".join(row["ticker"] for row in report["pendingEntrants"]) or "none"
    departed = ", ".join(row["ticker"] for row in report["departedEvidence"]) or "none"
    print(
        f"Roster readiness: {report['status']}; verified "
        f"{report['sourceVerifiedCurrentCount']}/{report['currentRosterCount']}; "
        f"pending={pending}; departed={departed}."
    )


if __name__ == "__main__":
    main()
