#!/usr/bin/env python3
"""Fetch local NASA FIRMS thermal anomaly records for SGXEM curation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path


BASE = Path(__file__).parent
ARTIFACTS = BASE / "artifacts"
FIRMS_DIR = ARTIFACTS / "firms_source"
DEFAULT_SOURCE = "VIIRS_SNPP_NRT"
DEFAULT_BBOX = "-125,24,-66,50"
DEFAULT_DAYS = 3


def load_local_env(path: Path = BASE / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def build_url(map_key: str, source: str, bbox: str, day_range: int, start_date: str) -> str:
    return (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/{source}/{bbox}/{day_range}/{start_date}"
    )


def fetch_csv(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "SGXEM/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"FIRMS HTTP {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"FIRMS request failed: {exc}") from exc


def write_metadata(path: Path, args: argparse.Namespace, row_count: int, source_url: str) -> None:
    metadata = {
        "source": args.source,
        "bbox": args.bbox,
        "day_range": args.days,
        "start_date": args.date,
        "row_count": row_count,
        "csv_path": str(path.relative_to(BASE)),
        "source_url_without_key": source_url.replace(os.environ["NASA_FIRMS_MAP_KEY"], "<NASA_FIRMS_MAP_KEY>"),
        "redistribution_status": "redistributable",
    }
    metadata_path = path.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--bbox", default=DEFAULT_BBOX, help="west,south,east,north")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output-dir", type=Path, default=FIRMS_DIR)
    return parser.parse_args()


def main() -> int:
    load_local_env()
    args = parse_args()
    map_key = os.environ.get("NASA_FIRMS_MAP_KEY")
    if not map_key:
        print("ERROR: set NASA_FIRMS_MAP_KEY or add it to local .env", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    safe_bbox = args.bbox.replace(",", "_").replace("-", "m")
    output_path = args.output_dir / f"firms_{args.source.lower()}_{safe_bbox}_{args.date}_{args.days}d.csv"
    url = build_url(map_key, args.source, args.bbox, args.days, args.date)

    csv_text = fetch_csv(url)
    output_path.write_text(csv_text, encoding="utf-8")
    row_count = max(0, len(csv_text.splitlines()) - 1)
    write_metadata(output_path, args, row_count, url)
    print(f"wrote {output_path} ({row_count} data rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
