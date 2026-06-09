#!/usr/bin/env python3
"""Report SGXEM text sources that need distractor hardening."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curation-log", type=Path, default=BASE / "curation_log.jsonl")
    parser.add_argument("--output", type=Path, default=BASE / "text_source_hardening_report.md")
    args = parser.parse_args()

    failures = []
    for row in read_jsonl(args.curation_log):
        haystack = json.dumps(row).upper()
        if "ADD_DISTRACTORS" in haystack or "UNIQUENESS" in haystack:
            failures.append(row)

    grouped = defaultdict(list)
    for row in failures:
        candidate = row.get("candidate") or {}
        source = row.get("text_source") or candidate.get("text_source") or "UNKNOWN"
        entity = row.get("bridge_entity") or candidate.get("bridge_entity") or "UNKNOWN"
        grouped[(source, entity)].append(row.get("artifact_id", "UNKNOWN"))

    lines = [
        "# SGXEM Text Source Hardening Report",
        "",
        f"curation_log: `{args.curation_log}`",
        f"uniqueness_or_distractor_failures: {len(failures)}",
        "",
    ]
    if grouped:
        lines.extend(["| text_source | bridge_entity | artifacts |", "|---|---|---|"])
        for (source, entity), artifacts in sorted(grouped.items()):
            lines.append(f"| {source} | {entity} | {', '.join(sorted(set(artifacts)))} |")
    else:
        lines.append("No uniqueness/distractor failures found.")

    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

