#!/usr/bin/env python3
"""verify_redteam.py — independent adversary + quality judge gate (SGXEM-owned).

Two DIFFERENT model families judge each GLM-5.2-composed record (a model is blind to its
own failure modes, so self-judging is weak):
  • ADVERSARY  = Kimi K2.6 (kimi-k2p6): can the question be answered WITHOUT the multi-hop
    chain (world-knowledge / uniqueness / lexical-leak / format shortcut)? -> breakable
  • JUDGE      = DeepSeek V4 Pro (deepseek-v4-pro): is any hop FORCED/contrived, and is the
    item well-formed (answer specific + correct, natural analyst reasoning)? -> forced/quality
A record is GREEN only if: nli_all_hops_entailed AND not breakable AND not forced AND
quality_ok AND not single_passage_sufficient. Concurrent over records; each record = 2 calls.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose_one import _extract_json  # noqa: E402

FW_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
ADVERSARY = "accounts/fireworks/models/kimi-k2p6"
JUDGE = "accounts/fireworks/models/deepseek-v4-pro"

ADVERSARY_SYS = """You judge whether a question is a GENUINE multi-hop question — i.e. whether it
STRUCTURALLY requires combining several passages. You are given the QUESTION, its ANSWER, the hop
chain, and the SUPPORTING PASSAGES.

CRITICAL: judge using ONLY these passages and the chain's logic. Do NOT use any outside or world
knowledge about the entities — assume you have never heard of any of them and know nothing beyond
these passages. (We are NOT testing whether a well-read model already knows the answer; we are
testing whether the chain is logically necessary.)

Decide:
- single_passage: can the full ANSWER be found in ONE single supporting passage by itself (no
  combining)? true/false.
- skippable: can you reach the final answer WITHOUT using one of the cited passages — i.e., is some
  hop redundant or is there a shorter path through the passages? true/false.
Output JSON ONLY: {"single_passage": <bool>, "skippable": <bool>, "reason": "..."}"""

JUDGE_SYS = """You are a strict quality judge for a multi-hop QA benchmark. Given the QUESTION,
ANSWER, and hop chain, assess:
- forced_link: is ANY hop's connection contrived, vague, or not a natural analyst reasoning step
  (chain stitched together rather than genuine)? true/false.
- quality_ok: is the item well-formed — answer specific and clearly correct from the chain, question
  fluent and unambiguous, genuinely requiring all hops? true/false.
Be strict. Output JSON ONLY: {"forced_link": <bool>, "quality_ok": <bool>, "reason": "..."}"""


def call(model: str, sys_p: str, user: str) -> dict | None:
    body = json.dumps({"model": model, "temperature": 0.2, "max_tokens": 4000,
                       "messages": [{"role": "system", "content": sys_p},
                                    {"role": "user", "content": user}]}).encode()
    for _ in range(3):                            # retry to avoid fail-closing on API noise
        req = urllib.request.Request(FW_URL, data=body, method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "curl/8.5",
                                              "Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                content = json.load(r)["choices"][0]["message"].get("content", "") or ""
            obj = _extract_json(content)
            if obj is not None:
                return obj
        except Exception:  # noqa: BLE001
            continue
    return None                                   # None = genuine no-response (caller decides)


def gate_one(rec: dict) -> dict:
    decomp = rec.get("question_decomposition", [])
    chain = " | ".join(f"hop{i+1}: {h.get('question')} -> {h.get('answer')}" for i, h in enumerate(decomp))
    sup = [p for p in rec.get("paragraphs", []) if p.get("is_supporting")]
    pass_txt = "\n\n".join(f"[passage {i+1}] {p.get('title','')}: {(p.get('paragraph_text') or '')[:700]}"
                           for i, p in enumerate(sup))
    base = f"QUESTION: {rec.get('question')}\nANSWER: {rec.get('answer')}\nHOP CHAIN: {chain}\nhop_count: {rec.get('hop_count')}"
    adv = call(ADVERSARY, ADVERSARY_SYS, base + "\n\nSUPPORTING PASSAGES:\n" + pass_txt)
    jud = call(JUDGE, JUDGE_SYS, base)
    no_resp = adv is None or jud is None
    adv = adv or {}
    jud = jud or {}
    single = bool(adv.get("single_passage", True))
    skippable = bool(adv.get("skippable", True))
    return {
        "single_passage": single,
        "breakable": single or skippable,                       # structural: not genuinely multi-hop
        "forced_link": bool(jud.get("forced_link", True)),
        "quality_ok": bool(jud.get("quality_ok", False)),
        "adv_reason": adv.get("reason", "no-response"),
        "judge_reason": jud.get("reason", "no-response"),
        "no_response": no_resp,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if "FIREWORKS_API_KEY" not in os.environ:
        for line in Path("/research/afwerk/.env").read_text().splitlines():
            if line.startswith("FIREWORKS_API_KEY"):
                os.environ["FIREWORKS_API_KEY"] = line.split("=", 1)[1].strip().strip('"')

    recs = [json.loads(l) for l in a.inp.read_text().splitlines() if l.strip()]
    idxs = [i for i, r in enumerate(recs) if not r.get("rejection")]
    print(f"adversary=Kimi-K2.6 judge=DeepSeek-V4-Pro on {len(idxs)} records (workers={a.workers})", flush=True)

    res = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(gate_one, recs[i]): i for i in idxs}
        for n, fut in enumerate(as_completed(futs), 1):
            res[futs[fut]] = fut.result()
            if n % 25 == 0:
                print(f"  {n}/{len(idxs)}", flush=True)

    n_green = 0
    for i in idxs:
        r = recs[i]; v = res.get(i, {})
        g = r.setdefault("gate", {})
        g["red_team_breakable"] = v.get("breakable", True)
        g["single_passage_sufficient"] = v.get("single_passage", True)
        au = r.setdefault("_audit", {})
        au["forced_link"] = v.get("forced_link", True)
        au["quality_ok"] = v.get("quality_ok", False)
        au["adv_reason"] = v.get("adv_reason", "")
        au["judge_reason"] = v.get("judge_reason", "")
        au["no_response"] = v.get("no_response", False)
        green = (g.get("nli_all_hops_entailed") is True and g.get("red_team_breakable") is False
                 and g.get("single_passage_sufficient") is False and au["forced_link"] is False
                 and au["quality_ok"] is True)
        au["green"] = green
        n_green += 1 if green else 0

    a.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
    print(f"[gate] all-green (nli+kimi+deepseek): {n_green}/{len(idxs)} -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
