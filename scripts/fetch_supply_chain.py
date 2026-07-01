#!/usr/bin/env python3
"""fetch_supply_chain.py — fetch FULL Wikipedia article plaintext for the supply-chain corpus.

Unlike wiki_bridge (one-paragraph summary), this pulls the full article via the Wikipedia
extracts API so passages carry trade/exporter/logistics/risk specifics — needed for genuine
2-3 hop supply-chain chains. Writes SC-*.txt + source_registry rows (source_type=wikipedia,
CC BY-SA). Then chunk with SmartChunker (text_ingestion) -> ingest, same as the CRS path.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://en.wikipedia.org/w/api.php"
UA = "SGXEM-DefenseBenchmark/1.0 (research; lmsanch@gmail.com)"


def fetch_extract(title: str, max_chars: int) -> str:
    params = {"action": "query", "format": "json", "prop": "extracts", "explaintext": "1",
              "redirects": "1", "titles": title}
    url = API + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
            data = json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001
        print(f"  ! {title}: {exc}"); return ""
    for _pid, page in data.get("query", {}).get("pages", {}).items():
        txt = page.get("extract", "") or ""
        txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
        return txt[:max_chars]
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entities", type=Path, required=True)
    ap.add_argument("--corpus-dir", type=Path, required=True)
    ap.add_argument("--max-chars", type=int, default=14000)
    ap.add_argument("--delay", type=float, default=0.4)
    a = ap.parse_args()
    sc_dir = a.corpus_dir / "corpus" / "supply_chain"
    sc_dir.mkdir(parents=True, exist_ok=True)
    registry = a.corpus_dir / "sgxem_source_registry.jsonl"

    rows = [json.loads(l) for l in a.entities.read_text().splitlines() if l.strip()]
    reg_rows, got = [], 0
    for e in rows:
        title = e["entity"]
        sid = "SC-" + re.sub(r"[^A-Za-z0-9]", "_", title)
        out = sc_dir / f"{sid}.txt"
        if out.exists():
            got += 1; continue
        txt = fetch_extract(title, a.max_chars)
        time.sleep(a.delay)
        if len(txt) < 400:
            print(f"  skip {title} (too short)"); continue
        out.write_text(f"# {title}\n\n{txt}\n", encoding="utf-8")
        reg_rows.append({"source_id": sid, "title": title, "publisher": "Wikipedia",
                         "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                         "source_type": "wikipedia", "domain": "supply_chain",
                         "license_or_access_note": "CC BY-SA 4.0 (Wikipedia)", "s3_uri": "N/A",
                         "local_path": str(out.resolve()), "modality_relevance": [], "status": "downloaded"})
        got += 1
        print(f"  [{got}] {sid} ({len(txt)} chars) {title}", flush=True)

    with registry.open("a", encoding="utf-8") as f:
        for r in reg_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nDONE: {got} supply-chain articles -> {sc_dir} (+{len(reg_rows)} registry rows)")
    # also emit a supply-chain-only registry for chunking
    (a.corpus_dir / "supply_chain_registry.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reg_rows), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
