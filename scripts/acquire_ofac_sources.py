#!/usr/bin/env python3
"""acquire_ofac_sources.py — fetch public-domain OFAC narrative content (SGXEM-owned, T3).

Source: ofac.treasury.gov FAQ Topic pages (US Government work, public domain, 17 U.S.C. §105).
These pages carry genuine narrative Q&A prose about a country sanctions program (legal basis,
Executive Orders, designated-entity relationships, dates) — unlike the "Sanctions Programs and
Country Information" index pages, which are mostly link lists of General License titles and do
not entail cleanly for MiniCheck (same "skip tables/indices, keep narrative prose" rule the CRS
acquisition already follows).

Also registers (but does NOT chunk into narrative passages) the OFAC SDN list itself — a
structured entity/alias/program table, kept for provenance and future QID/entity-anchoring use,
consistent with the rule that tabular data isn't NLI-gate material.

Writes:
  <corpus>/corpus/ofac/OFAC-FAQ-<CLUSTER>.txt      one prose file per cluster FAQ topic page
  <corpus>/corpus/ofac/OFAC-SDN.csv                raw SDN list (structured, NOT chunked)
  <corpus>/ofac_manifest.jsonl                     {source_id,title,url,cluster,...}
  appends registry rows to <corpus>/sgxem_source_registry.jsonl (source_type=ofac)

Only three OFAC-administered clusters have a dedicated country sanctions program + FAQ topic
page: Venezuela, Iran, Cuba. Taiwan and Brazil are not OFAC-sanctioned jurisdictions — no
FAQ topic page exists for them (confirmed by absence, not assumed).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://ofac.treasury.gov"
UA = "SGXEM-DefenseBenchmark/1.0 (research; lmsanch@gmail.com)"

# cluster -> (FAQ topic id, human title, country program page slug)
FAQ_TOPICS = {
    "venezuela": (1581, "Venezuela Sanctions FAQ Topic Page", "venezuela-related-sanctions"),
    "iran": (1551, "Iran Sanctions FAQ Topic Page", "iran-sanctions"),
    "cuba": (1541, "Cuba Sanctions FAQ Topic Page", "cuba-sanctions"),
}

SDN_CSV_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
LICENSE_NOTE = "US Government work (OFAC / U.S. Dept. of the Treasury) — public domain, 17 U.S.C. §105"


def fetch(url: str, timeout: int = 30) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! fetch failed {url}: {exc}", flush=True)
        return None


def html_to_prose(raw: str) -> str:
    # drop scripts/styles/nav/table outright — same rule as CRS acquisition
    raw = re.sub(r"(?is)<(script|style|table|nav|footer)[^>]*>.*?</\1>", " ", raw)
    m = re.search(r"(?is)<main[^>]*>(.*)</main>", raw)
    body = m.group(1) if m else raw
    body = re.sub(r"(?i)</(p|div|h[1-6]|li)>", "\n", body)
    text = re.sub(r"(?s)<[^>]+>", " ", body)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", type=Path, required=True)
    ap.add_argument("--min-chars", type=int, default=1500)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--skip-sdn", action="store_true", help="skip the ~5.6MB SDN CSV download")
    a = ap.parse_args()

    ofac_dir = a.corpus_dir / "corpus" / "ofac"
    ofac_dir.mkdir(parents=True, exist_ok=True)
    registry_path = a.corpus_dir / "sgxem_source_registry.jsonl"
    manifest_path = a.corpus_dir / "ofac_manifest.jsonl"

    manifest, reg_rows = [], []

    for cluster, (topic_id, title, page_slug) in FAQ_TOPICS.items():
        sid = f"OFAC-FAQ-{cluster.upper()}"
        out = ofac_dir / f"{sid}.txt"
        url = f"{BASE}/faqs/topic/{topic_id}"
        raw = fetch(url)
        time.sleep(a.delay)
        if not raw:
            print(f"  ! {cluster}: fetch failed, skipping")
            continue
        prose = html_to_prose(raw.decode("utf-8", errors="replace"))
        if len(prose) < a.min_chars:
            print(f"  ! {cluster}: only {len(prose)} chars, below min-chars, skipping")
            continue
        out.write_text(f"# {title}\n\n{prose}\n", encoding="utf-8")
        rec = {
            "source_id": sid, "title": title, "url": url, "cluster": cluster,
            "source_type": "ofac", "license_or_access_note": LICENSE_NOTE,
        }
        manifest.append(rec)
        reg_rows.append({
            "source_id": sid, "title": title, "publisher": "U.S. Department of the Treasury (OFAC)",
            "url": url, "source_type": "ofac", "domain": cluster,
            "license_or_access_note": LICENSE_NOTE,
            "s3_uri": "N/A", "local_path": str(out), "modality_relevance": [],
            "status": "downloaded"})
        print(f"  [{cluster}] {sid} ({len(prose)} chars) {title}", flush=True)

    # SDN list — structured reference data, registered but NOT chunked as narrative passages
    if not a.skip_sdn:
        sdn_out = ofac_dir / "OFAC-SDN.csv"
        raw = fetch(SDN_CSV_URL, timeout=60)
        time.sleep(a.delay)
        if raw:
            sdn_out.write_bytes(raw)
            sid = "OFAC-SDN-LIST"
            rec = {
                "source_id": sid, "title": "Specially Designated Nationals and Blocked Persons List (SDN)",
                "url": SDN_CSV_URL, "cluster": "cross-cluster", "source_type": "ofac",
                "license_or_access_note": LICENSE_NOTE,
                "note": "structured entity/alias/program table — registered for provenance + future "
                        "QID/entity-anchoring use; NOT chunked into narrative passages for the NLI gate "
                        "(tables don't entail cleanly, same rule as CRS statistical appendices)",
            }
            manifest.append(rec)
            reg_rows.append({
                "source_id": sid, "title": rec["title"], "publisher": "U.S. Department of the Treasury (OFAC)",
                "url": SDN_CSV_URL, "source_type": "ofac", "domain": "cross-cluster",
                "license_or_access_note": LICENSE_NOTE,
                "s3_uri": "N/A", "local_path": str(sdn_out), "modality_relevance": [],
                "status": "downloaded-structured-not-chunked"})
            print(f"  [cross-cluster] {sid} ({len(raw)} bytes, structured CSV, not chunked)", flush=True)
        else:
            print("  ! SDN CSV fetch failed", flush=True)

    with manifest_path.open("w", encoding="utf-8") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    existing = registry_path.read_text(encoding="utf-8").splitlines() if registry_path.exists() else []
    with registry_path.open("a", encoding="utf-8") as f:
        for rr in reg_rows:
            f.write(json.dumps(rr, ensure_ascii=False) + "\n")
    print(f"\nDONE: {len(manifest)} OFAC sources -> {ofac_dir}")
    print(f"manifest: {manifest_path}  (+{len(reg_rows)} registry rows, {len(existing)} pre-existing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
