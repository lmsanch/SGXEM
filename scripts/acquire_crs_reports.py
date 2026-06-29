#!/usr/bin/env python3
"""acquire_crs_reports.py — fetch public-domain CRS reports per cluster (SGXEM-owned, T2).

Source: EveryCRSReport.com bulk listing (US Government work, public domain). Selects
the most recent N reports whose title matches each cluster keyword, downloads the
full-text HTML, strips tables/markup to narrative prose (statistical tables don't
entail cleanly for MiniCheck), and writes:
  <corpus>/corpus/crs/CRS-<number>.txt           one prose file per report
  <corpus>/crs_manifest.jsonl                    {source_id,title,url,date,cluster,...}
  appends registry rows to <corpus>/sgxem_source_registry.jsonl

Prose files are then chunked by SmartChunker (afwerk sgxem/text_ingestion.py),
recorded, ingested, QID-enriched, NV-Embedded — identical to the T1 path.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://www.everycrsreport.com/"
UA = "SGXEM-DefenseBenchmark/1.0 (research; lmsanch@gmail.com)"
CLUSTER_KEYWORDS = {
    "venezuela": ["venezuela"],
    "iran": ["iran"],
    "taiwan": ["taiwan"],
    "cuba": ["cuba"],
    "brazil": ["brazil"],
}


def fetch(url: str, timeout: int = 30) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! fetch failed {url}: {exc}", flush=True)
        return None


def html_to_prose(raw: str) -> str:
    # drop scripts/styles and statistical tables outright
    raw = re.sub(r"(?is)<(script|style|table)[^>]*>.*?</\1>", " ", raw)
    # keep only the report body if a content container is present
    m = re.search(r'(?is)<div[^>]*class="[^"]*(?:report|content|body)[^"]*"[^>]*>(.*)</div>', raw)
    body = m.group(1) if m else raw
    # block-level tags -> newlines so paragraphs survive
    body = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n", body)
    text = re.sub(r"(?s)<[^>]+>", " ", body)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, required=True, help="EveryCRSReport reports.csv")
    ap.add_argument("--corpus-dir", type=Path, required=True)
    ap.add_argument("--per-cluster", type=int, default=20)
    ap.add_argument("--min-chars", type=int, default=1500)
    ap.add_argument("--delay", type=float, default=0.5)
    a = ap.parse_args()

    crs_dir = a.corpus_dir / "corpus" / "crs"
    crs_dir.mkdir(parents=True, exist_ok=True)
    registry_path = a.corpus_dir / "sgxem_source_registry.jsonl"
    manifest_path = a.corpus_dir / "crs_manifest.jsonl"

    rows = list(csv.DictReader(a.csv.open(encoding="utf-8")))
    manifest, reg_rows = [], []

    for cluster, kws in CLUSTER_KEYWORDS.items():
        cands = [r for r in rows if any(k in r["title"].lower() for k in kws)]
        cands.sort(key=lambda r: r.get("latestPubDate", ""), reverse=True)
        got = 0
        for r in cands:
            if got >= a.per_cluster:
                break
            num = r["number"]
            sid = f"CRS-{num}"
            out = crs_dir / f"{sid}.txt"
            if out.exists():
                got += 1
                continue
            hpath = r.get("latestHTML", "")
            if not hpath:
                continue
            raw = fetch(BASE + hpath)
            time.sleep(a.delay)
            if not raw:
                continue
            prose = html_to_prose(raw)
            if len(prose) < a.min_chars:
                continue
            url = BASE + hpath
            out.write_text(f"# {r['title']}\n\n{prose}\n", encoding="utf-8")
            rec = {"source_id": sid, "title": r["title"], "url": url,
                   "crs_number": num, "date": r.get("latestPubDate", ""),
                   "cluster": cluster, "source_type": "crs",
                   "license_or_access_note": "US Government work (CRS) — public domain"}
            manifest.append(rec)
            reg_rows.append({
                "source_id": sid, "title": r["title"], "publisher": "Congressional Research Service",
                "url": url, "source_type": "crs", "domain": cluster,
                "license_or_access_note": "US Government work (CRS) — public domain",
                "s3_uri": "N/A", "local_path": str(out), "modality_relevance": [],
                "status": "downloaded"})
            got += 1
            print(f"  [{cluster}] {sid} ({len(prose)} chars) {r['title'][:60]}", flush=True)
        print(f"=== {cluster}: {got} reports ===", flush=True)

    with manifest_path.open("w", encoding="utf-8") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    existing = registry_path.read_text(encoding="utf-8").splitlines() if registry_path.exists() else []
    with registry_path.open("a", encoding="utf-8") as f:
        for rr in reg_rows:
            f.write(json.dumps(rr, ensure_ascii=False) + "\n")
    print(f"\nDONE: {len(manifest)} CRS reports -> {crs_dir}")
    print(f"manifest: {manifest_path}  (+{len(reg_rows)} registry rows, {len(existing)} pre-existing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
