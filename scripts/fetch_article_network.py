#!/usr/bin/env python3
"""fetch_article_network.py — mine a Wikipedia 'hub' article into a citable entity set (SGXEM-owned).

Given one article (e.g. Bolibourgeoisie), pull its outbound article links, resolve each to a
Wikidata QID, and tag instance-of (human / organization / other). Because every link is an
English Wikipedia article, the whole set is CITABLE (redistributable bridge anchors). Emits a
wiki_bridge entity-spec JSONL ready for the same fetch->ingest path.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

WIKI = "https://en.wikipedia.org/w/api.php"
WD = "https://www.wikidata.org/w/api.php"
UA = "SGXEM-DefenseBenchmark/1.0 (research; lmsanch@gmail.com)"
HUMAN, ORG = "Q5", {"Q43229", "Q4830453", "Q783794", "Q891723", "Q6881511"}  # org-ish classes


def api(base: str, params: dict) -> dict:
    params = {**params, "format": "json"}
    url = base + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
        return json.loads(r.read().decode())


def get_links(title: str) -> list[str]:
    out, cont = [], {}
    while True:
        d = api(WIKI, {"action": "query", "titles": title, "prop": "links",
                       "plnamespace": 0, "pllimit": "max", **cont})
        for _pid, page in d.get("query", {}).get("pages", {}).items():
            out += [l["title"] for l in page.get("links", [])]
        if "continue" in d:
            cont = d["continue"]
            time.sleep(0.2)
        else:
            break
    return out


def qids_for_titles(titles: list[str]) -> dict[str, str]:
    res = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        d = api(WIKI, {"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                       "redirects": 1, "titles": "|".join(batch)})
        for _pid, page in d.get("query", {}).get("pages", {}).items():
            q = page.get("pageprops", {}).get("wikibase_item")
            if q:
                res[page["title"]] = q
        time.sleep(0.2)
    return res


def types_for_qids(qids: list[str]) -> dict[str, tuple[str, str]]:
    """qid -> (kind, description)."""
    res = {}
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        d = api(WD, {"action": "wbgetentities", "ids": "|".join(batch),
                     "props": "claims|descriptions", "languages": "en"})
        for qid, ent in d.get("entities", {}).items():
            desc = ent.get("descriptions", {}).get("en", {}).get("value", "")
            insts = set()
            for c in ent.get("claims", {}).get("P31", []):
                try:
                    insts.add(c["mainsnak"]["datavalue"]["value"]["id"])
                except (KeyError, TypeError):
                    pass
            kind = "human" if HUMAN in insts else ("org" if insts & ORG else "other")
            res[qid] = (kind, desc)
        time.sleep(0.2)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--article", required=True)
    ap.add_argument("--cluster", default="venezuela")
    ap.add_argument("--sub-topic", default="boliburguesia")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--kinds", default="human,org", help="comma list of kinds to keep")
    a = ap.parse_args()
    keep = set(a.kinds.split(","))

    links = get_links(a.article)
    print(f"[links] {len(links)} outbound article links from '{a.article}'")
    t2q = qids_for_titles(links)
    print(f"[qid]   {len(t2q)} resolved to QIDs")
    q2t = types_for_qids(list(set(t2q.values())))

    rows = []
    for title, qid in sorted(t2q.items()):
        kind, desc = q2t.get(qid, ("other", ""))
        if kind not in keep:
            continue
        rows.append({"entity": title, "wikidata_id": qid, "type": kind, "domain": a.cluster,
                     "related_label": a.sub_topic, "cluster": a.cluster, "sub_topic": a.sub_topic,
                     "wikipedia_title": title, "description": desc})

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"[keep]  {len(rows)} entities ({dict(Counter(r['type'] for r in rows))}) -> {a.out}")
    for r in rows:
        print(f"  {r['wikidata_id']:11s} [{r['type']:5s}] {r['entity']} — {r['description'][:55]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
