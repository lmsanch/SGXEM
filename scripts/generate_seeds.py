#!/usr/bin/env python3
"""generate_seeds.py — plausible seed templates for the defense benchmark (SGXEM-owned, T4).

Reuses the SHAPE of afwerk sgxem/seed_generator.py (which is multimodal-only) for the
text-defense case. Each seed: {seed_id, cluster, sub_topic, bridge_type, hop_count,
retrieval_query, source_reliability, is_final_question:false, is_evidence:false, notes}.

Weighting (locked):
  cluster   : venezuela 40%, iran/taiwan/cuba/brazil 15% each
  hop_count : 2-hop 40%, 3-hop 35%, 4-hop 25%

Discovery-feed-mined seeds (Venezuela, source_reliability low/medium) are produced
separately by mine_feed_seeds.py and concatenated; those carry contested/single-source
leads whose evidence is re-grounded to a citable tier at T5.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# cluster -> sub_topic -> [(bridge_type, retrieval_query_pattern), ...]
TEMPLATES: dict[str, dict[str, list[tuple[str, str]]]] = {
    "venezuela": {
        "energy": [
            ("org_to_subunit", "PDVSA joint venture operating field Orinoco Belt production capacity"),
            ("org_to_location", "Venezuelan refinery complex location state crude processing capacity"),
            ("person_to_org", "Venezuelan oil minister PDVSA leadership petroleum ministry"),
            ("org_to_country", "Venezuela oil export intermediary shipping destination sanctions"),
        ],
        "sanctions": [
            ("entity_to_designation", "OFAC designated Venezuelan entity sanctions program SDN list"),
            ("person_to_org", "sanctioned Venezuelan official entity bank jurisdiction"),
            ("event_to_actor", "United States executive order Venezuela sanctions authority agency"),
        ],
        "factions": [
            ("person_to_org", "Venezuelan official military unit faction PSUV loyalty"),
            ("org_to_subunit", "Cartel of the Suns military officers trafficking network unit"),
            ("platform_to_operator", "Venezuelan armed forces branch command equipment capability"),
            ("person_to_role", "Venezuelan government figure office faction power structure"),
        ],
        "disaster": [
            ("event_to_actor", "Venezuela earthquake fault region civil protection response agency"),
            ("org_to_location", "Venezuelan seismic fault zone geography affected state infrastructure"),
        ],
        "opposition": [
            ("person_to_org", "Venezuelan opposition leader coalition party external recognition"),
            ("person_to_event", "Venezuelan opposition figure election primary diplomatic recognition"),
            ("person_to_role", "Venezuela opposition interim government office leadership"),
        ],
        "international": [
            ("org_to_country", "Venezuela bilateral relations agreement foreign partner cooperation"),
            ("event_to_actor", "Venezuela foreign ally military intelligence cooperation agreement"),
        ],
    },
    "iran": {
        "nuclear": [
            ("org_to_location", "Iran nuclear enrichment facility location centrifuge capacity"),
            ("treaty_to_provision", "JCPOA provision enrichment level IAEA inspection limit"),
            ("org_to_subunit", "Atomic Energy Organization of Iran facility reactor program"),
        ],
        "sanctions": [
            ("entity_to_designation", "Iran sanctioned petrochemical banking entity evasion network"),
            ("org_to_country", "National Iranian Oil Company export route sanctions evasion"),
        ],
        "proxy": [
            ("org_to_subunit", "IRGC Quds Force proxy group area of operations command"),
            ("platform_to_operator", "Iranian proxy group weapon capability region operation"),
            ("person_to_org", "IRGC commander proxy organization area of operation"),
        ],
        "maritime": [
            ("org_to_location", "Strait of Hormuz Iranian naval force posture base"),
            ("platform_to_operator", "Iranian navy vessel class capability Persian Gulf"),
        ],
    },
    "taiwan": {
        "alliance": [
            ("treaty_to_provision", "Taiwan Relations Act commitment arms sale provision"),
            ("event_to_actor", "United States Taiwan policy assurance force posture basing"),
        ],
        "pla": [
            ("org_to_subunit", "PLA theater command unit equipment cross-strait range"),
            ("platform_to_operator", "Chinese missile system operating unit rocket force range"),
            ("org_to_location", "PLA Eastern Theater Command base unit Taiwan strait"),
        ],
        "semiconductor": [
            ("org_to_subunit", "TSMC fab chip node dependency supply chain"),
            ("org_to_country", "Taiwan semiconductor industry export dependency chain"),
        ],
        "military_geography": [
            ("org_to_location", "Taiwan strait island chain amphibious feasibility basing"),
            ("platform_to_operator", "Republic of China armed forces base island defense"),
        ],
        "roc_forces": [
            ("platform_to_operator", "Republic of China navy air force vessel aircraft capability"),
        ],
    },
    "cuba": {
        "sanctions": [
            ("treaty_to_provision", "Helms-Burton Act provision entity designation enforcement"),
            ("entity_to_designation", "Cuban Assets Control Regulations embargo entity provision"),
        ],
        "intelligence": [
            ("org_to_subunit", "Cuban intelligence directorate ministry interior facility"),
            ("org_to_country", "Cuban security services foreign cooperation advisers"),
        ],
        "migration": [
            ("event_to_actor", "Cuban migration route Coast Guard operation policy"),
            ("person_to_role", "Cuba migration policy United States interdiction"),
        ],
        "cross_cluster": [
            ("org_to_country", "Cuba Venezuela bilateral agreement military intelligence cooperation"),
        ],
        "politics": [
            ("person_to_role", "Cuban government leader Communist Party office succession"),
        ],
    },
    "brazil": {
        "environment": [
            ("org_to_subunit", "Brazil environmental agency Amazon deforestation enforcement program"),
            ("event_to_actor", "Amazon deforestation international agreement enforcement agency"),
        ],
        "disaster": [
            ("event_to_actor", "Brazil flood disaster affected region military Defesa Civil response"),
            ("org_to_location", "Brazilian state disaster infrastructure damage response"),
        ],
        "defense": [
            ("platform_to_operator", "Brazil military branch equipment acquisition exercise basing"),
            ("org_to_country", "Brazil United States defense cooperation agreement exercise"),
        ],
        "economy": [
            ("org_to_subunit", "Brazil state enterprise Petrobras Vale project sector"),
            ("org_to_location", "Brazilian state enterprise facility project environmental impact"),
        ],
    },
}

CLUSTER_WEIGHT = {"venezuela": 0.40, "iran": 0.15, "taiwan": 0.15, "cuba": 0.15, "brazil": 0.15}
HOP_WEIGHT = [(2, 0.40), (3, 0.35), (4, 0.25)]


def alloc(total: int, weights: list[float]) -> list[int]:
    """Largest-remainder allocation so the parts sum exactly to total."""
    raw = [w * total for w in weights]
    base = [int(x) for x in raw]
    rem = total - sum(base)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)
    for i in order[:rem]:
        base[i] += 1
    return base


def gen_cluster(cluster: str, n: int, start_idx: int) -> list[dict]:
    subs = list(TEMPLATES[cluster].keys())
    sub_counts = alloc(n, [1 / len(subs)] * len(subs))
    seeds: list[dict] = []
    idx = start_idx
    for sub, sc in zip(subs, sub_counts):
        hops = alloc(sc, [w for _, w in HOP_WEIGHT])
        tmpls = TEMPLATES[cluster][sub]
        ti = 0
        for (hop, _), hc in zip(HOP_WEIGHT, hops):
            for _ in range(hc):
                bt, q = tmpls[ti % len(tmpls)]
                ti += 1
                seeds.append({
                    "seed_id": f"SEED-D{idx:04d}",
                    "cluster": cluster,
                    "sub_topic": sub,
                    "bridge_type": bt,
                    "hop_count": hop,
                    "retrieval_query": q,
                    "source_reliability": "high",
                    "is_final_question": False,
                    "is_evidence": False,
                    "notes": f"plausible seed; cluster={cluster} sub_topic={sub} bridge={bt} hop={hop}",
                })
                idx += 1
    return seeds


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--total", type=int, default=500)
    ap.add_argument("--out", type=Path, default=Path("data/seeds/defense_seeds.jsonl"))
    a = ap.parse_args()

    counts = alloc(a.total, [CLUSTER_WEIGHT[c] for c in CLUSTER_WEIGHT])
    seeds: list[dict] = []
    idx = 0
    for cluster, cn in zip(CLUSTER_WEIGHT, counts):
        cs = gen_cluster(cluster, cn, idx)
        seeds.extend(cs)
        idx += len(cs)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        for s in seeds:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # histogram (the T4 gate)
    from collections import Counter
    cl = Counter(s["cluster"] for s in seeds)
    hp = Counter(s["hop_count"] for s in seeds)
    print(f"=== {len(seeds)} structured seeds -> {a.out} ===")
    print("by cluster:", {k: f"{cl[k]} ({100*cl[k]/len(seeds):.0f}%)" for k in CLUSTER_WEIGHT})
    print("by hop_count:", {k: f"{hp[k]} ({100*hp[k]/len(seeds):.0f}%)" for k in (2, 3, 4)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
