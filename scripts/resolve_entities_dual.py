#!/usr/bin/env python3
"""resolve_entities_dual.py — resolve names to QIDs two ways (SGXEM-owned).

For each input: (1) Wikipedia pageprops on a title guess -> canonical enwiki title +
QID (CITABLE: has redistributable Wikipedia prose); (2) if no enwiki article, Wikidata
wbsearchentities on the raw name -> QID + label + description (DISCOVERY-ONLY: a real
entity/QID but no citable Wikipedia text, so usable as a lead/bridge but not republished).

Prints a sign-off table; writes the citable hits as a wiki_bridge entity-spec JSONL.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

WIKI_API = "https://en.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
UA = "SGXEM-DefenseBenchmark/1.0 (research; lmsanch@gmail.com)"


def api(base: str, params: dict) -> dict | None:
    url = base + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        print(f"  ! api error: {e}")
        return None


def pageprops(title: str) -> dict | None:
    d = api(WIKI_API, {"action": "query", "format": "json", "prop": "pageprops",
                       "ppprop": "wikibase_item", "redirects": "1", "titles": title})
    if not d:
        return None
    for _pid, page in d.get("query", {}).get("pages", {}).items():
        if "missing" in page:
            return None
        qid = page.get("pageprops", {}).get("wikibase_item")
        if qid:
            return {"title": page.get("title"), "qid": qid}
    return None


def wd_search(name: str) -> dict | None:
    d = api(WD_API, {"action": "wbsearchentities", "format": "json", "language": "en",
                     "search": name, "limit": 1})
    if not d or not d.get("search"):
        return None
    s = d["search"][0]
    return {"qid": s["id"], "label": s.get("label", ""), "description": s.get("description", "")}


def wd_has_enwiki(qid: str) -> str | None:
    d = api("https://www.wikidata.org/wiki/Special:EntityData/" + qid + ".json", {})
    if not d:
        return None
    ent = d.get("entities", {}).get(qid, {})
    return ent.get("sitelinks", {}).get("enwiki", {}).get("title")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--delay", type=float, default=0.3)
    a = ap.parse_args()

    spec = json.loads(a.candidates.read_text(encoding="utf-8"))
    cluster = spec.get("cluster", "")
    rows = spec["entities"]

    citable, discovery, missing = [], [], []
    print(f"{'INPUT':28s} {'STATUS':12s} {'QID':11s} LABEL — DESCRIPTION")
    print("-" * 110)
    for e in rows:
        name = e["name"]
        guess = e.get("title", name)
        sub = e.get("sub_topic", "")
        pp = pageprops(guess)
        time.sleep(a.delay)
        if pp:
            lbl = wd_search(pp["title"])  # for a description
            time.sleep(a.delay)
            desc = lbl["description"] if lbl else ""
            citable.append({"entity": pp["title"], "wikidata_id": pp["qid"], "type": e.get("type", "unknown"),
                            "domain": cluster, "related_label": sub, "cluster": cluster,
                            "sub_topic": sub, "wikipedia_title": pp["title"]})
            print(f"{name[:28]:28s} {'CITABLE':12s} {pp['qid']:11s} {pp['title']} — {desc[:55]}")
            continue
        ws = wd_search(name if name == guess else guess)
        time.sleep(a.delay)
        if ws:
            enw = wd_has_enwiki(ws["qid"])
            time.sleep(a.delay)
            if enw:
                lbl = wd_search(enw)
                citable.append({"entity": enw, "wikidata_id": ws["qid"], "type": e.get("type", "unknown"),
                                "domain": cluster, "related_label": sub, "cluster": cluster,
                                "sub_topic": sub, "wikipedia_title": enw})
                print(f"{name[:28]:28s} {'CITABLE*':12s} {ws['qid']:11s} {enw} — {ws['description'][:55]}")
            else:
                discovery.append({"name": name, "qid": ws["qid"], "label": ws["label"],
                                  "description": ws["description"], "sub_topic": sub})
                print(f"{name[:28]:28s} {'DISCOVERY':12s} {ws['qid']:11s} {ws['label']} — {ws['description'][:55]}")
        else:
            missing.append(name)
            print(f"{name[:28]:28s} {'NO-MATCH':12s} {'—':11s}")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        for r in citable:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (a.out.with_suffix(".discovery.json")).write_text(
        json.dumps({"discovery_only": discovery, "no_match": missing}, ensure_ascii=False, indent=2))
    print("-" * 110)
    print(f"CITABLE (enwiki, ingestable): {len(citable)}  |  DISCOVERY-only (QID, no enwiki): {len(discovery)}  |  NO-MATCH: {len(missing)}")
    print(f"citable spec -> {a.out}   discovery/no-match -> {a.out.with_suffix('.discovery.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
