#!/usr/bin/env python3
"""Resolve curated Wikipedia titles -> canonical title + Wikidata QID (SGXEM-owned).

This authors the wiki_bridge entity-spec seed list (the bridge anchors). It is NOT
the corpus QID-linker (that is afwerk/scripts/resolve_wikidata_qids.py over RELiK
NER, reused unchanged). Here we only look up each curated seed title via the
Wikipedia pageprops API to get its exact canonical title + wikibase_item QID and
confirm the article exists.

Input : a candidates JSON {cluster, entities:[{title,type,sub_topic,...}]}
Output: entity-spec JSONL compatible with wiki_bridge.build_bridge_entry, one line:
        {entity, wikidata_id, type, domain, related_label, cluster, sub_topic, wikipedia_title}
Also prints a per-sub_topic resolution report (QID density signal).
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "SGXEM-DefenseBenchmark/1.0 (research; lmsanch@gmail.com)"


def api_get(params: dict[str, str]) -> dict[str, Any] | None:
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! API error: {exc}")
        return None


def resolve_batch(titles: list[str]) -> dict[str, dict[str, Any]]:
    """Return {input_title: {canonical, qid, missing}} for up to 50 titles."""
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "redirects": "1",
        "titles": "|".join(titles),
    }
    data = api_get(params)
    out: dict[str, dict[str, Any]] = {}
    if not data:
        return out
    query = data.get("query", {})
    # Map any normalization/redirects back to the original input title.
    alias = {}
    for n in query.get("normalized", []):
        alias[n["to"]] = n["from"]
    for r in query.get("redirects", []):
        alias[r["to"]] = alias.get(r["from"], r["from"])

    pages = query.get("pages", {})
    for _pid, page in pages.items():
        canonical = page.get("title", "")
        origin = alias.get(canonical, canonical)
        missing = "missing" in page
        qid = page.get("pageprops", {}).get("wikibase_item", "") if not missing else ""
        out[origin] = {"canonical": canonical, "qid": qid, "missing": missing}
    # Also key by canonical in case alias chain didn't capture it.
    for _pid, page in pages.items():
        canonical = page.get("title", "")
        if canonical not in out:
            missing = "missing" in page
            out[canonical] = {
                "canonical": canonical,
                "qid": page.get("pageprops", {}).get("wikibase_item", "") if not missing else "",
                "missing": missing,
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()

    spec = json.loads(args.candidates.read_text(encoding="utf-8"))
    cluster = spec.get("cluster", "")
    entities = spec["entities"]
    by_title = {e["title"]: e for e in entities}
    titles = list(by_title.keys())

    resolved: dict[str, dict[str, Any]] = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        resolved.update(resolve_batch(batch))
        time.sleep(args.delay)

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    by_sub: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [resolved, total]

    for title, meta in by_title.items():
        sub = meta.get("sub_topic", "")
        by_sub[sub][1] += 1
        info = resolved.get(title)
        if not info or info["missing"] or not info["qid"]:
            failures.append(f"{title} ({sub}) -> "
                            f"{'missing' if (info and info['missing']) else 'no-QID' if info else 'unresolved'}")
            continue
        by_sub[sub][0] += 1
        rows.append({
            "entity": info["canonical"],
            "wikidata_id": info["qid"],
            "type": meta.get("type", "unknown"),
            "domain": cluster,
            "related_label": sub,
            "cluster": cluster,
            "sub_topic": sub,
            "wikipedia_title": info["canonical"],
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n=== Resolved {len(rows)}/{len(titles)} titles -> {args.out} ===")
    print("Per-sub_topic resolution (resolved/total):")
    for sub in sorted(by_sub):
        res, tot = by_sub[sub]
        pct = 100.0 * res / tot if tot else 0.0
        flag = "  <-- SPARSE" if pct < 60 else ""
        print(f"  {sub:14s} {res}/{tot}  ({pct:.0f}%){flag}")
    if failures:
        print(f"\nUnresolved ({len(failures)}):")
        for fl in failures:
            print(f"  - {fl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
