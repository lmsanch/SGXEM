#!/usr/bin/env python3
"""acquire_institutional_sources.py — World Bank narrative country reports (SGXEM-owned, T3).

Source: World Bank Documents & Reports (documents.worldbank.org), reached via the public
search API (search.worldbank.org/api/v3/wds). Pulls narrative "Economic Monitor" /
"Systematic Country Diagnostic" reports (prose analysis, not statistical annexes/tables —
same narrative-only rule the CRS/OFAC acquisitions already follow) and verifies the
license printed in EACH document's own "Rights and Permissions" front matter before
registering it — do not assume a blanket WB license, license varies per publication.

IMF was evaluated and excluded (see SOURCES_LICENSE.md): imf.org's live copyright page
returned HTTP 403 and no per-document license text was found; ambiguous, escalated to
human rather than guessed at.

worldbank.org's general marketing site (country "Overview" pages) is explicitly EXCLUDED:
its own Terms & Conditions ("Reproduction and Use") state redistribution requires prior
written permission — that is NOT the same grant as the CC BY / noncommercial-reproduction
notice printed inside individual Documents & Reports publications used here.

Writes:
  <corpus>/corpus/institutional/INST-<ID>.txt
  <corpus>/institutional_manifest.jsonl
  appends registry rows to <corpus>/sgxem_source_registry.jsonl (source_type=institutional)

Only documents whose own front matter contains an explicit reproduction/license grant are
kept; anything else is skipped and printed as a warning (fail closed on license ambiguity).
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

UA = "SGXEM-DefenseBenchmark/1.0 (research; lmsanch@gmail.com)"

# cluster -> (source_id, title, txturl, publisher)
# Selected via search.worldbank.org/api/v3/wds; narrative "Economic Monitor" / "Systematic
# Country Diagnostic" report types (not indicator tables). Venezuela/Cuba/Taiwan have no
# current entry: Venezuela's only WB docs are pre-2003 archival reports (predate the Bank's
# 2012 Open Access policy, no in-document license statement — excluded, not guessed at);
# Cuba is not a World Bank member (no modern coverage exists); Taiwan is not a WB member
# (no WB country program at all). Documented as a coverage gap, not silently dropped.
DOCS = {
    "iran": (
        "INST-IRAN-ECONMON-2020",
        "Iran Economic Monitor: Weathering the Triple-Shock (Fall 2020, 7th ed.)",
        "http://documents.worldbank.org/curated/en/287811608721990695/text/"
        "Iran-Economic-Monitor-Weathering-the-Triple-Shock.txt",
    ),
    "brazil": (
        "INST-BRAZIL-SCD-2023",
        "Brazil Systematic Country Diagnostic Update (July 2023)",
        "http://documents.worldbank.org/curated/en/099072023134526692/text/"
        "BOSIB0bf484b270d508c2809049f2fffead.txt",
    ),
}

LICENSE_MARKERS = re.compile(
    r"(creative commons|CC BY|reproduced.{0,40}for noncommercial purposes|"
    r"free to copy, distribute)", re.IGNORECASE)


def fetch(url: str, timeout: int = 60) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! fetch failed {url}: {exc}", flush=True)
        return None


def clean(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    return re.sub(r"\n{3,}", "\n\n", text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", type=Path, required=True)
    ap.add_argument("--min-chars", type=int, default=1500)
    ap.add_argument("--delay", type=float, default=0.5)
    a = ap.parse_args()

    inst_dir = a.corpus_dir / "corpus" / "institutional"
    inst_dir.mkdir(parents=True, exist_ok=True)
    registry_path = a.corpus_dir / "sgxem_source_registry.jsonl"
    manifest_path = a.corpus_dir / "institutional_manifest.jsonl"

    manifest, reg_rows = [], []

    for cluster, (sid, title, url) in DOCS.items():
        raw = fetch(url)
        time.sleep(a.delay)
        if not raw:
            print(f"  ! {cluster}: fetch failed, skipping")
            continue
        # front-matter license check (first ~120 lines = cover + rights/permissions page);
        # join with spaces (not \n) since these PDFs->txt wrap narrow columns with
        # hyphenation, splitting phrases like "reproduced, in whole or in part," across lines
        head = " ".join(raw.splitlines()[:120])
        m = LICENSE_MARKERS.search(head)
        if not m:
            print(f"  ! {cluster}: no explicit license/reproduction grant found in front "
                  f"matter — SKIPPED (fail closed, escalate before including)")
            continue
        license_note = f"World Bank — copyright; document front matter states: {m.group(0)!r} " \
                        f"(reproduction permitted for noncommercial/attributed research use — verified in-document)"
        prose = clean(raw)
        if len(prose) < a.min_chars:
            print(f"  ! {cluster}: only {len(prose)} chars, below min-chars, skipping")
            continue
        out = inst_dir / f"{sid}.txt"
        out.write_text(f"# {title}\n\n{prose}\n", encoding="utf-8")
        rec = {"source_id": sid, "title": title, "url": url, "cluster": cluster,
               "source_type": "institutional", "license_or_access_note": license_note}
        manifest.append(rec)
        reg_rows.append({
            "source_id": sid, "title": title, "publisher": "World Bank Group",
            "url": url, "source_type": "institutional", "domain": cluster,
            "license_or_access_note": license_note,
            "s3_uri": "N/A", "local_path": str(out), "modality_relevance": [],
            "status": "downloaded"})
        print(f"  [{cluster}] {sid} ({len(prose)} chars) {title} — license verified in-doc", flush=True)

    with manifest_path.open("w", encoding="utf-8") as f:
        for m2 in manifest:
            f.write(json.dumps(m2, ensure_ascii=False) + "\n")
    existing = registry_path.read_text(encoding="utf-8").splitlines() if registry_path.exists() else []
    with registry_path.open("a", encoding="utf-8") as f:
        for rr in reg_rows:
            f.write(json.dumps(rr, ensure_ascii=False) + "\n")
    print(f"\nDONE: {len(manifest)} institutional sources -> {inst_dir}")
    print(f"manifest: {manifest_path}  (+{len(reg_rows)} registry rows, {len(existing)} pre-existing)")
    print("\nCoverage gaps (documented, not silently dropped): Venezuela (only pre-2003 archival "
          "WB reports, no in-document license), Cuba (not a WB member), Taiwan (not a WB member), "
          "IMF (403 on live copyright page, no verifiable per-doc license found this session).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
