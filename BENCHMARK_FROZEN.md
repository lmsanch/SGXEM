# SGXEM Defense Benchmark — frozen scoring snapshot (seven-cluster set)

**Current snapshot: 2026-07-19.** Supersedes the 2026-06-30 pre-registration below — this file
had already grown from 137 (Venezuela-only) to 316 (5 clusters) between those two dates without
this doc being updated to match; that gap is now closed, and enterprise_risk + supply_chain
(built and gate-verified earlier but never merged into the canonical file) are folded in too.
**If you scored anything against the 2026-06-30 or any undocumented intermediate hash, it does
not match the current file — rescore, don't compare across snapshots.**

## What this is
360 gate-verified multi-hop QA questions across **seven clusters** (five geopolitical +
enterprise-risk + supply-chain). Every record passed: per-hop MiniCheck NLI entailment + an
**independent structural gate** (Kimi K2.6 adversary: not single-passage / not skippable,
judged from the passages with no world knowledge; DeepSeek V4 Pro judge: not forced +
well-formed) + build.py schema/defensibility + ≤2-per-answer diversity cap + near-duplicate-
question drop.

## Distribution (2026-07-19)
- records: 360
- cluster: venezuela 137 · taiwan 51 · brazil 48 · iran 45 · cuba 35 · enterprise_risk 26 · supply_chain 18
- hop_count: 2-hop 309 · 3-hop 47 · 4-hop 4
- temporal_sensitivity: timeless 285 · recency 75

## Files (the AFWERK contract — 2 files)
- `data/afwerk_defense_benchmark.jsonl`  (canonical, hashed)
- `data/afwerk_defense_benchmark.json`   (JSON-array view for eval_kms_reader_f1.py)
- `data/afwerk_defense_corpus.json`      ([{title,text}], de-duped paragraph union; supporting text verbatim = gold join key; 476 passages)

## SHA-256 (2026-07-19 snapshot)
- benchmark.jsonl : 404c1b7dfdb1ac3e9513579830223ce2d214d3cd63b628015658e4915b7245dc
- benchmark.json  : 2d4c762a926a54c8145f7c8b8c730451b408f78064ccab50a1aa6ecb568d78cb
- corpus.json     : 984e7f61bd84cc80bbd649bf5f3581923b09ba3a8d34fead639e25c0a809a5a4

## For the AFWERK agent
Derive topk/entities/nli yourself (per AFWERK_CONTRACT_ANSWERS.md). Run engine + frontier
baselines, **sliced by temporal_sensitivity × cluster**. The 75 recency questions are the
knockout axis (frozen-cutoff frontier models should fail; the retrieval-grounded stack should win).

## Notes / known gaps
- Hop mix skews 2-hop (the source compositions were 2-hop heavy; 3/4-hop gate out harder).
- A `final_curated.jsonl` cross-cluster "top picks" subset (39 questions) also exists for a
  smaller, hand-picked showcase set — separate purpose from the full 360-question benchmark,
  not part of this frozen file.

---

## Original 2026-06-30 pre-registration (historical, superseded — kept for provenance)

137 gate-verified multi-hop QA questions over the Venezuela cluster only.
- records: 137 · distinct answers: 95 · hop_count: 2-hop 114 · 3-hop 20 · 4-hop 3
- temporal_sensitivity: timeless 116 · recency 21
- SHA-256 — benchmark.jsonl: `cbdb9aaf147fc5640d6f13431ce7bceabbec0d8d731a8196df740f10eccbeaea`,
  benchmark.json: `70b21fb89d6d1366ddec12d6c0dd08c0244a96d42fe1f1b17345d56737e00646`,
  corpus.json: `f1734c3da9cc07782db763aad720d4d2af36bcca26057fb4aa249b48a902e4ac`
- Notes at the time: "Venezuela-only (breadth Iran/Taiwan/Cuba/Brazil deferred — costs ~$20-25
  + ~2-3h on GLM; add after first scores)." That breadth expansion did happen (grew the file
  to 316 between 06-30 and 07-19) but was never re-frozen with a new hash until now.
