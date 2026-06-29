# SGXEM ▸ AFWERK Defense Multi-Hop Benchmark — Agent Task Brief

**Owner of this repo's work:** a dedicated SGXEM agent (you).
**Owner of training/engine:** the AFWERK agent (separate, in `/research/afwerk`). Do **not** touch training — your job ends at producing the benchmark dataset.
**Contract between us:** you emit the benchmark in **MuSiQue JSON schema** (§4). That is the only interface. If you honor the schema, the AFWERK harnesses consume it with zero glue.

Canonical strategy docs (read these first, they are in the afwerk repo):
- `/research/afwerk/docs/strategy/afwerk_corpus_plan_defense_benchmark.md` — the WHAT (clusters, sources, sizes, paper). **This is your spec.**
- `/research/afwerk/docs/strategy/afwerk_build_plan_defense_decomposer.md` — the training half (context only; not your job).
- `/research/afwerk/docs/strategy/musique_decomposition_research_2026-06-29.md` — method survey (context).

---

## 1. Mission (one paragraph)

Build the first open, **defense/geopolitical multi-hop QA benchmark** (~1,000 gate-verified 2/3/4-hop questions over a public corpus), using SGXEM's existing **GHQB methodology**: template a question shape → retrieve real evidence from a vectorized corpus (entities bridged by **Wikidata QID**) → have an LLM compose a natural question with the **bridge entity hidden**, citing only retrieved evidence → **prove** each question is genuinely multi-hop via a defensibility gate. The benchmark serves two audiences at once: an open-source paper (breadth, reproducibility, pre-registration) and an AFWERX proposal (a Venezuela depth spine the proposer can personally validate). Everything is **open-source / public-knowledge** — capabilities, treaties, org structure, chronology; analyst OSINT reasoning, never operational targeting.

---

## 2. The methodology you are executing (so you understand WHY)

SGXEM's GHQB pipeline already implements this for the multimodal case; you are adapting it to **text-only defense**. The flow (reuse the existing code, don't reinvent):

1. **Vectorize the corpus** → Qdrant collections (text passages embedded; each point carries `entity_links` + `wikidata_id`).
2. **QID linking = the bridge anchor.** A multi-hop chain is *real* only when hop-i's answer-entity and hop-(i+1)'s passage share the **same Wikidata QID**. The QID is how you guarantee — and hide — the bridge.
3. **"Plausible" seeds** = templates specifying a question's *shape* (`cluster`, `sub_topic`, `bridge_type`, `hop_count`, `retrieval_query`). Not yet grounded.
4. **Retrieve via KMS/Qdrant** → pull the real passages + QID-linked bridge entities for each seed.
5. **Compose (transform plausible → real)** with the teacher LLM, given ONLY retrieved evidence: emit `question, answer (verbatim), hidden_bridge, hops[], required_text_sources[]` — cite **exact** source IDs, **never name the bridge entity**, **reject** rather than invent if evidence is insufficient.
6. **Defensibility gate** (the part that makes it a credible benchmark):
   - `prompts/01_generation.md` — compose + self red-team.
   - `prompts/02_red_team.md` — fresh adversarial pass: can it be answered WITHOUT chaining (world-knowledge / uniqueness / lexical-leak / distribution / format shortcuts)?
   - **For text-only defense, the `prompts/03_text_only_ablation.md` artifact-vs-text gate is replaced by: (a) MiniCheck NLI — every hop's sub-answer must be entailed by its cited passage; and (b) a single-passage-sufficiency check — no single retrieved passage may answer the whole question (else it isn't multi-hop).**
   - `build.py` — schema + rule validation (bridge entity must not leak into the question; hop-count label valid; etc.). Extend its `VALID_*` sets for the text-only/defense fields.

---

## 3. What already exists — REUSE, don't rebuild

| Asset | Path | Use |
|---|---|---|
| GHQB pipeline (retrieve + 2-stage compose) | `/research/afwerk/scripts/ghqb_pipeline.py` | adapt: swap multimodal collections for the defense text corpus; keep the compose/grounding/reject logic |
| 3 curation prompts | `/research/SGXEM/prompts/0{1,2,3}_*.md` | reuse 01/02; replace 03 with the MiniCheck + single-passage gate |
| Schema/defensibility validator | `/research/SGXEM/build.py` | extend `REQUIRED_FIELDS`/`VALID_*` for text-only defense |
| Curation loop driver | `/research/SGXEM/curation_loop.py` | the orchestration skeleton |
| QID cache (166K name→QID) | `/research/afwerk/data/sgxem_poc/wikidata_entity_cache.jsonl` | entity→QID linking backbone |
| NV-Embed-v2 recipe | Spark: `faster-qwen3-tts` venv + `PYTHONPATH=.tf442` + `HF_HOME=.hfcache` | embed the defense corpus (same retriever AFWERK uses) |
| MiniCheck NLI verifier | `/research/kms/services/triple_extraction/nli_verifier.py` (`NLIVerifier`) + AFWERK `scripts/verify_musique_triples_nli.py` pattern | the per-hop entailment gate |
| 100 multimodal SGXEM seeds | `/research/afwerk/data/sgxem_poc/sgxem_question_seeds.jsonl` | the 50–80 multimodal splice (§ corpus plan) |

---

## 4. OUTPUT CONTRACT — MuSiQue schema (non-negotiable)

Emit `data/afwerk_defense_benchmark.jsonl`, one question per line:

```json
{
  "id": "<Khop>__<cluster>_<seq>",            // e.g. "3hop__venezuela_0142"
  "question": "<natural-language, bridge entity HIDDEN>",
  "answer": "<final answer, verbatim from gold passage>",
  "answer_aliases": ["..."],
  "paragraphs": [                              // candidate set incl. distractors
    {"idx": 0, "title": "...", "paragraph_text": "...", "is_supporting": true, "source_tier": "wikipedia|crs|ofac|institutional"}
  ],
  "question_decomposition": [                  // the gold multi-hop chain
    {"question": "<sub-q, #k bridge refs>", "answer": "<sub-answer>", "paragraph_support_idx": 0, "bridge_qid": "Q12345"}
  ],
  "cluster": "venezuela|iran|taiwan|cuba|brazil",
  "sub_topic": "energy|sanctions|factions|...",
  "hop_count": 2,
  "modality": "text|audio|depth|thermal",
  "source_reliability": "high|medium|low",     // novel dimension; low = contested/single-source
  "gate": {"red_team_breakable": false, "nli_all_hops_entailed": true, "single_passage_sufficient": false}
}
```

This matches the fields AFWERK's `eval_kms_reader_f1.py` / decomposition harnesses already read (`paragraphs[].is_supporting`, `question_decomposition[]`). Keep the field names exact.

---

## 5. Task list (each task has a deliverable + acceptance gate)

> Mirrors C1–C9 in the corpus plan. Do them in order; each gate must pass before the next.

- **T1 — Corpus: Wikipedia+Wikidata backbone.** Assemble passages for all 5 clusters (Venezuela ~40%, Iran/Taiwan/Cuba/Brazil ~15% each) across the sub-topics in the corpus plan §1. Paragraph-chunk, tag each with QIDs (use the cache), embed with NV-Embed-v2, index in a new Qdrant collection `afwerk_defense_corpus`. **Gate:** passages retrievable; QID coverage >80% on entity-rich sub-topics.
- **T2 — Corpus: CRS reports.** Add ~20 CRS reports/cluster (public domain). Extract narrative prose (skip stat appendices), chunk, QID-tag, index. **Gate:** MiniCheck can verify claims against CRS passages; `source_tier="crs"` set.
- **T3 — Corpus: OFAC + institutional.** OFAC SDN + sanctions guidance (public domain); World Bank/IMF country narrative text. **Gate:** redistribution license verified per source and recorded in `SOURCES_LICENSE.md`.
- **T4 — Seeds.** Generate plausible seed templates per cluster×sub-topic, `hop_count` weighted **40/35/25** (2/3/4-hop), with `retrieval_query`. **Gate:** seed counts match the target cluster distribution.
- **T5 — Generate.** Run the adapted GHQB pipeline (teacher = **GLM-5.2**; mine AFWERK's existing Llama-70B Self-Ask traces as seed exemplars). Target ~2,000 raw compositions (expect ~50% survival). Enforce: hidden bridge, exact source-ID citation, ≥1 non-Wikipedia hop in 3+ hop chains, reject-on-insufficient-evidence. **Gate:** raw set generated; every item carries gold `question_decomposition` + `paragraphs`.
- **T6 — Gate.** Apply the defensibility gate to every raw question: 02 red-team → MiniCheck per-hop entailment → single-passage-sufficiency check → `build.py` schema/rule validation. **Gate:** ~1,000 survivors; record survival rate per cluster/sub-topic (drop sub-topics under ~30% survival — too QID-sparse).
- **T7 — Calibrate.** Hand-sample ~50 survivors; check failure modes (temporal drift, QID-sense ambiguity, trivial multi-hop, bridge leak). Tune gate thresholds. **Gate:** false-positive rate acceptable; write `GATE_CALIBRATION.md`.
- **T8 — Multimodal splice.** Run the existing multimodal GHQB over the 100 SGXEM seeds → 50–80 sensor→text questions; pass them through the same gate; label `modality`. **Gate:** multimodal items in MuSiQue schema, gated.
- **T9 — Freeze + pre-register.** Final human-approval pass; freeze `afwerk_defense_benchmark.jsonl`; compute and publish its **SHA-256 hash** (commit + timestamp) **before any model is scored**. **Gate:** hash recorded in `BENCHMARK_FROZEN.md`. Hand the frozen file path to the AFWERK agent.

(Baseline scoring — T-final — is run by AFWERK against the frozen file; you just deliver + hash it.)

---

## 6. Guardrails (do not violate)
- **Open-source / public-knowledge only.** No classified, no operational/targeting content. Capabilities, treaties, org structure, chronology.
- **License-clean redistribution.** Every redistributed passage must be CC-BY-SA / public-domain / owned. Log provenance + license per source (T3 deliverable). For paywalled figures (IISS/Jane's), cite the Wikipedia/CRS passage that quotes them, never the original.
- **Never name the bridge entity in the question** (it leaks the multi-hop). `build.py` enforces this — keep that check.
- **Pre-register before scoring** (T9). This is the single move that defeats "you tuned to your own test."
- **Don't invent facts.** Compose only from retrieved evidence; reject otherwise. The whole credibility of the set rests on this.
- **Stay in this repo + the SGXEM data dirs.** Don't modify AFWERK training code. Cross-repo reads (QID cache, NV-Embed recipe, NLIVerifier) are fine; cross-repo writes are not.

## 7. Escalate to the human when
- A sub-topic's gate survival is <30% (QID-sparse) — confirm drop/reallocate.
- A source's redistribution license is ambiguous — confirm before including.
- Venezuela source-reliability labels on contested facts — the human (domain expert) validates the `low`/`medium`/`high` calls.
- Per-cluster difficulty diverges >10 F1 in a dry run — flag for rebalancing.

---

**Definition of done:** a frozen, SHA-256-hashed `afwerk_defense_benchmark.jsonl` (~1,000 + multimodal splice) in MuSiQue schema, license-logged, gate-passed, pre-registered — handed to the AFWERK agent for baseline scoring.
