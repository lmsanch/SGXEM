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

# Composer provider (default o4-mini via Requesty; set SGXEM_COMPOSER=glm to use Fireworks GLM-5.2)
COMPOSER = os.getenv("SGXEM_COMPOSER", "glm")
if COMPOSER == "glm":
    COMPOSER_URL, COMPOSER_MODEL, COMPOSER_KEY_ENV, COMPOSER_REASONING = FW_URL, FW_MODEL, "FIREWORKS_API_KEY", False
else:
    COMPOSER_URL = "https://router.requesty.ai/v1/chat/completions"
    COMPOSER_MODEL = "openai/o4-mini"
    COMPOSER_KEY_ENV = "REQUESTY_API_KEY"
    COMPOSER_REASONING = True   # o4-mini: uses max_completion_tokens, no temperature


def load_keys() -> None:
    """Load FIREWORKS_API_KEY + REQUESTY_API_KEY from afwerk .env if not already set."""
    for env in (COMPOSER_KEY_ENV, "FIREWORKS_API_KEY"):
        if os.environ.get(env):
            continue
        for line in Path("/research/afwerk/.env").read_text().splitlines():
            if line.startswith(env + "="):
                os.environ[env] = line.split("=", 1)[1].strip().strip('"').strip("'")


def _log_tokens(stage: str, model: str, usage) -> None:
    """Best-effort token-ledger append (never breaks composition)."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import tokens
        tokens.add(stage, model, usage)
    except Exception:  # noqa: BLE001
        pass


SYSTEM = """You compose HARD questions for an open defense/geopolitical multi-hop QA benchmark.
The benchmark's whole value is that a question CANNOT be answered without doing the multi-hop
retrieval chain. A strong independent adversary will try to break each question — if it can be
answered without chaining, it is rejected. Compose so it survives.

You get a SEED (cluster, sub_topic, hop_count) and RETRIEVED PASSAGES (each: source_id, title,
source_tier, wikidata_id, text). Compose ONE natural-language {hop_count}-hop question.

HARD RULES:
- Use ONLY facts in the passages. No outside knowledge. If they don't support a genuine
  {hop_count}-hop chain, output {"rejection": true, "reason": "..."}.
- The BRIDGE ENTITY (links hop i's answer to hop i+1's passage) MUST NOT appear in the question.
- Each hop must be NECESSARY: removing any one cited passage must make the final answer
  underivable. No single passage may answer the whole question.
- Cite the EXACT source_id supporting each hop. Never invent one. Final `answer` = verbatim (or
  minimal span) from the last hop's passage.

STRUCTURAL NECESSITY (this is the bar — obey strictly):
- The answer must NOT be derivable from any SINGLE one of the cited passages. Each hop's passage
  contributes a distinct, required link; remove any one and the answer becomes underivable.
- Do NOT name the bridge entity, and do NOT echo distinctive words/identifiers that appear in the
  gold-answer passage — that lets a solver jump straight to the answer's passage and skip the chain.
- Every intermediate hop must be NECESSARY: there must be no shorter path from the question's stated
  facts to the final answer using only the passages.

SELF-CHECK BEFORE OUTPUT (mandatory, STRUCTURAL — judge using ONLY the passages, assume zero prior
knowledge of these entities): (a) could the full answer be found in a single cited passage? (b) is
any hop skippable — can you reach the answer without one of the passages? If (a) or (b) is yes,
REWRITE so every hop is required; if it still isn't genuinely {hop_count}-hop, output a rejection.

Output JSON ONLY:
{
  "question": "natural language, bridge entity hidden, no answer-leaking specifics",
  "answer": "final answer, verbatim from the gold passage",
  "answer_aliases": ["every surface form / abbreviation of the answer"],
  "hidden_bridge": "the bridge entity you hid (audit; never in the question)",
  "leak_self_check": "one line: why an adversary cannot answer this without the chain",
  "hops": [
    {"question": "sub-question", "answer": "sub-answer", "source_id": <int>, "bridge_qid": "Qxxxx"}
  ]
}
hops length MUST equal hop_count. bridge_qid = the wikidata_id of this hop's answer entity, or ""."""


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
    avoid = seed.get("avoid_answers") or []
    if avoid:
        sys_prompt += ("\n\nDIVERSITY: do NOT produce a question whose final answer is (or is "
                       "equivalent to) any of these already-used answers — pick a DIFFERENT fact:\n- "
                       + "\n- ".join(str(x)[:80] for x in avoid[:60]))
    lines = [f"SEED: cluster={seed['cluster']} sub_topic={seed['sub_topic']} hop_count={seed['hop_count']}",
             "", "RETRIEVED PASSAGES:"]
    for p in passages:
        lines.append(f"[source_id={p['source_id']}] title={p['title']!r} tier={p['source_tier']} "
                     f"wikidata_id={p['wikidata_id']}\n{p['text'][:700]}")
    user = "\n\n".join(lines)
    load_keys()
    payload = {"model": COMPOSER_MODEL,
               "messages": [{"role": "system", "content": sys_prompt},
                            {"role": "user", "content": user}]}
    if COMPOSER_REASONING:                       # o4-mini: reasoning model
        payload["max_completion_tokens"] = 14000
    else:                                        # GLM-5.2
        payload["temperature"] = 0.3
        payload["max_tokens"] = 12000
    last = ""
    for _ in range(2):                           # retry once on transient/empty
        try:
            resp = http_json(COMPOSER_URL, payload,
                             headers={"Authorization": f"Bearer {os.environ[COMPOSER_KEY_ENV]}"}, timeout=240)
            _log_tokens("compose", COMPOSER_MODEL, resp.get("usage"))
            content = resp["choices"][0]["message"].get("content", "") or ""
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
            obj = _extract_json(content)
            if obj is not None:
                return obj
            last = content[:300]
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[:200]
    return {"rejection": True, "reason": "unparseable", "raw": last}


def _extract_json(text: str) -> dict | None:
    """Extract the first complete JSON object by brace-balancing (robust to pre/post text)."""
    start = text.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
    return None


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
