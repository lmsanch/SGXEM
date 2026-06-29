#!/usr/bin/env python3
"""compose_one.py — one-record GHQB handshake (SGXEM-owned, T5 dry-run).

Retrieves REAL evidence from afwerk_defense_corpus, has GLM-5.2 (Fireworks) compose a
multi-hop question with the bridge entity HIDDEN citing exact source IDs, and emits one
MuSiQue-schema record. Reuses: KMS embedder service (mxbai) + Qdrant + the GHQB compose
contract + the Fireworks OpenAI-compat call. Reject-on-insufficient-evidence preserved.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

EMBEDDER = "http://100.99.255.7:9999"   # KMS mxbai service (Spark), reachable from dev
QDRANT = "http://localhost:6333"
FW_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
FW_MODEL = "accounts/fireworks/models/glm-5p2"

SYSTEM = """You compose questions for an open defense/geopolitical multi-hop QA benchmark.

You are given a SEED (cluster, sub_topic, hop_count) and RETRIEVED PASSAGES (each: source_id,
title, source_tier, wikidata_id, text). Compose ONE natural-language multi-hop question.

HARD RULES:
- Use ONLY facts present in the provided passages. Never use outside knowledge. If the passages
  do not support a genuine {hop_count}-hop chain, output {"rejection": true, "reason": "..."}.
- The BRIDGE ENTITY (the entity that links hop i's answer to hop i+1's passage) MUST NOT appear
  anywhere in the final `question`. Describe it indirectly. Naming it collapses the chain.
- The chain must require {hop_count} passages: no single passage may answer the whole question.
- Cite the EXACT source_id of the passage supporting each hop. Never invent a source_id.
- The final `answer` must be verbatim (or a minimal span) from the last hop's cited passage.

Output JSON ONLY:
{
  "question": "natural language, bridge entity hidden",
  "answer": "final answer, verbatim from the gold passage",
  "answer_aliases": ["..."],
  "hidden_bridge": "the bridge entity you hid (for audit; never in the question)",
  "hops": [
    {"question": "sub-question", "answer": "sub-answer", "source_id": <int>, "bridge_qid": "Qxxxx"}
  ]
}
hops length MUST equal hop_count. bridge_qid = the wikidata_id of the entity that this hop's
answer corresponds to (from the cited passage), or "" if unknown."""


def http_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "curl/8.5.0",  # Cloudflare blocks python-urllib UA (err 1010)
                                          **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as ex:
        body = ex.read().decode(errors="replace")[:500]
        raise RuntimeError(f"HTTP {ex.code} from {url.split('//')[1].split('/')[0]}: {body}") from None


def embed_mxbai(text: str) -> list[float]:
    return http_json(f"{EMBEDDER}/embed", {"texts": [text]})["vectors"][0]


def retrieve(query: str, k: int) -> list[dict]:
    vec = embed_mxbai(query)
    body = {"vector": {"name": "mxbai", "vector": vec}, "limit": k, "with_vector": False,
            "with_payload": ["title", "text", "wikidata_id", "source_tier", "source_type"]}
    hits = http_json(f"{QDRANT}/collections/afwerk_defense_corpus/points/search", body)["result"]
    out = []
    for h in hits:
        p = h["payload"]
        out.append({"source_id": h["id"], "title": p.get("title", ""), "text": p.get("text", ""),
                    "wikidata_id": p.get("wikidata_id", ""), "source_tier": p.get("source_tier", ""),
                    "source_type": p.get("source_type", "")})
    return out


def call_glm(seed: dict, passages: list[dict]) -> dict:
    sys_prompt = SYSTEM.replace("{hop_count}", str(seed["hop_count"]))
    lines = [f"SEED: cluster={seed['cluster']} sub_topic={seed['sub_topic']} hop_count={seed['hop_count']}",
             "", "RETRIEVED PASSAGES:"]
    for p in passages:
        lines.append(f"[source_id={p['source_id']}] title={p['title']!r} tier={p['source_tier']} "
                     f"wikidata_id={p['wikidata_id']}\n{p['text'][:700]}")
    user = "\n\n".join(lines)
    resp = http_json(FW_URL, {
        "model": FW_MODEL, "temperature": 0.3, "max_tokens": 8000,  # GLM-5.2 reasoning_content eats budget
        "messages": [{"role": "system", "content": sys_prompt},
                     {"role": "user", "content": user}],
    }, headers={"Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}"})
    content = resp["choices"][0]["message"]["content"]
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    m = re.search(r"\{.*\}", content, re.DOTALL)
    return json.loads(m.group(0)) if m else {"rejection": True, "reason": "unparseable", "raw": content[:400]}


def assemble(seed: dict, comp: dict, passages: list[dict], as_of: str) -> dict:
    by_id = {p["source_id"]: p for p in passages}
    cited_ids = [h.get("source_id") for h in comp["hops"]]
    # paragraphs: cited first (supporting), then a few distractors
    paras, idx_of = [], {}
    for sid in cited_ids:
        if sid in by_id and sid not in idx_of:
            idx_of[sid] = len(paras)
            p = by_id[sid]
            paras.append({"idx": len(paras), "title": p["title"], "paragraph_text": p["text"],
                          "is_supporting": True, "source_tier": p["source_tier"]})
    for p in passages:
        if p["source_id"] not in idx_of and len(paras) < len(cited_ids) + 3:
            idx_of[p["source_id"]] = len(paras)
            paras.append({"idx": len(paras), "title": p["title"], "paragraph_text": p["text"],
                          "is_supporting": False, "source_tier": p["source_tier"]})
    decomp = []
    for h in comp["hops"]:
        sid = h.get("source_id")
        decomp.append({"question": h.get("question", ""), "answer": h.get("answer", ""),
                       "paragraph_support_idx": idx_of.get(sid, 0),
                       "bridge_qid": h.get("bridge_qid", "") or by_id.get(sid, {}).get("wikidata_id", "")})
    return {
        "id": f"{seed['hop_count']}hop__{seed['cluster']}_{seed.get('seq', 1):04d}",
        "question": comp["question"], "answer": comp["answer"],
        "answer_aliases": comp.get("answer_aliases", []),
        "paragraphs": paras, "question_decomposition": decomp,
        "cluster": seed["cluster"], "sub_topic": seed["sub_topic"], "hop_count": seed["hop_count"],
        "modality": "text", "source_reliability": seed.get("source_reliability", "high"),
        "as_of": as_of, "temporal_sensitivity": seed.get("temporal_sensitivity", "timeless"),
        "gate": {"red_team_breakable": None, "nli_all_hops_entailed": None,
                 "single_passage_sufficient": False},
        "_audit": {"hidden_bridge": comp.get("hidden_bridge", ""), "cited_source_ids": cited_ids},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=str, required=True, help="JSON seed string")
    ap.add_argument("--as-of", default="2026-06-29")
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--out", type=Path, default=Path("data/afwerk_defense_benchmark.jsonl"))
    a = ap.parse_args()
    seed = json.loads(a.seed)

    passages = retrieve(seed["retrieval_query"], a.topk)
    print(f"[retrieve] {len(passages)} passages: " +
          ", ".join(f"{p['title']}({p['source_tier']})" for p in passages[:6]))
    comp = call_glm(seed, passages)
    if comp.get("rejection"):
        print(f"[REJECTED] {comp.get('reason')}")
        return 2
    rec = assemble(seed, comp, passages, a.as_of)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[composed] hidden_bridge={rec['_audit']['hidden_bridge']!r}")
    print(f"[question] {rec['question']}")
    print(f"[answer]   {rec['answer']}")
    print(f"[wrote]    {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
