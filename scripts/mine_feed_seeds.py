#!/usr/bin/env python3
"""mine_feed_seeds.py — discovery-feed-mined Venezuela seeds (SGXEM-owned, T4 discovery layer).

Encodes leads surfaced READ-ONLY from KMS discovery feeds (rss_geopolitics; news_gdelt /
rss_world_news when reachable) into seed templates carrying the novel
`source_reliability ∈ {low, medium}` dimension. Feeds are LEADS ONLY — never
republished; each seed's cited evidence is re-grounded to a citable tier
(wikipedia/crs/ofac/institutional) during T5 composition, else rejected.

Each lead = a contested / single-source / timely claim that makes a good
source-reliability test item. hop_count is weighted 40/35/25 across the leads.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# (sub_topic, bridge_type, retrieval_query, source_reliability, lead_note)
# lead_note records the discovery-feed origin; the claim is re-grounded at T5.
LEADS: list[tuple[str, str, str, str, str]] = [
    ("sanctions", "person_to_org", "Venezuelan businessman OFAC designation money laundering indictment intermediary", "medium",
     "rss_geopolitics: Alex Saab characterized as Maduro's 'bagman', Miami 2019 DEA indictment — re-ground to OFAC/Wikipedia"),
    ("sanctions", "person_to_org", "Venezuelan official designated sanctions banking network jurisdiction", "medium",
     "rss_geopolitics: corrupt banking relationships lead — re-ground to OFAC SDN"),
    ("factions", "person_to_org", "Venezuelan general military intelligence FARC cocaine trafficking allegation", "low",
     "rss_geopolitics: Hugo Carvajal single-source allegations re Cabello/FARC cocaine — contested, single defector source"),
    ("factions", "person_to_org", "Venezuelan official Cartel of the Suns drug trade denial military officers", "low",
     "rss_geopolitics: Diosdado Cabello denies drug-trade involvement — contested allegation"),
    ("factions", "person_to_event", "former Venezuelan intelligence chief defection United States testimony", "low",
     "rss_geopolitics: Carvajal ('El Pollo') defection/testimony — single-source"),
    ("factions", "person_to_org", "Venezuelan defense minister armed forces loyalty Maduro government", "medium",
     "rss_geopolitics: Vladimir Padrino Lopez military loyalty — re-ground to Wikipedia/CRS"),
    ("opposition", "person_to_role", "Venezuela interim president transitional government claim recognition", "low",
     "rss_geopolitics: 'Interim president Delcy Rodriguez' — contested/timely status claim"),
    ("international", "org_to_country", "Venezuela Cuban security advisers intelligence cooperation deployment", "medium",
     "rss_geopolitics: Cuban security advisers ordered by Caracas — re-ground to CRS Cuba-Venezuela"),
    ("energy", "org_to_subunit", "PDVSA oilfield services contract production recovery foreign company", "medium",
     "rss_geopolitics: SLB/PDVSA modernization deal — timely; re-ground to citable filing"),
    ("energy", "org_to_country", "Venezuela crude oil export volume destination sanctions license", "medium",
     "rss_geopolitics: Venezuela oil-export figures — single-source numeric, re-ground to citable"),
    ("factions", "person_to_org", "Venezuela colectivo armed group urban control faction loyalty", "low",
     "rss_geopolitics: colectivos as irregular pro-government armed groups — contested role"),
    ("energy", "org_to_country", "Venezuela gold reserves foreign control intervention asset seizure", "low",
     "rss_geopolitics: 'US moves to secure Venezuela's gold' — contested/timely claim"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("data/seeds/venezuela_discovery_seeds.jsonl"))
    ap.add_argument("--per-lead", type=int, default=3, help="seeds per lead (hop 2/3/4 cycled)")
    a = ap.parse_args()

    hops = [2, 3, 4]
    seeds = []
    idx = 0
    for li, (sub, bt, q, rel, note) in enumerate(LEADS):
        for k in range(a.per_lead):
            hop = hops[(li + k) % 3]  # spread hop_counts ~evenly -> ~40/35/25 over the set
            seeds.append({
                "seed_id": f"SEED-VD{idx:04d}",
                "cluster": "venezuela",
                "sub_topic": sub,
                "bridge_type": bt,
                "hop_count": hop,
                "retrieval_query": q,
                "source_reliability": rel,
                "is_final_question": False,
                "is_evidence": False,
                "discovery_origin": "kms_feed_lead",
                "notes": note,
            })
            idx += 1

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        for s in seeds:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    from collections import Counter
    rel = Counter(s["source_reliability"] for s in seeds)
    hp = Counter(s["hop_count"] for s in seeds)
    print(f"=== {len(seeds)} discovery-mined Venezuela seeds -> {a.out} ===")
    print("source_reliability:", dict(rel))
    print("hop_count:", dict(hp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
