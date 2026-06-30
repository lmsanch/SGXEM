# SGXEM Defense Benchmark — frozen scoring snapshot (Venezuela depth spine)

**Pre-registered 2026-06-30** (hashes computed BEFORE any model is scored).

## What this is
137 gate-verified multi-hop QA questions over the Venezuela cluster (the AFWERK depth
spine). Every record passed: per-hop MiniCheck NLI entailment + an **independent
structural gate** (Kimi K2.6 adversary: not single-passage / not skippable, judged from
the passages with no world knowledge; DeepSeek V4 Pro judge: not forced + well-formed) +
build.py schema/defensibility + ≤2-per-answer diversity cap + near-duplicate-question drop.

## Distribution
- records: 137 · distinct answers: 95
- cluster: venezuela 137
- hop_count: 2-hop 114 · 3-hop 20 · 4-hop 3
- temporal_sensitivity: timeless 116 · recency 21

## Files (the AFWERK contract — 2 files)
- `data/afwerk_defense_benchmark.jsonl`  (canonical, hashed)
- `data/afwerk_defense_benchmark.json`   (JSON-array view for eval_kms_reader_f1.py)
- `data/afwerk_defense_corpus.json`      ([{title,text}], de-duped paragraph union; supporting text verbatim = gold join key; 103 passages)

## SHA-256 (pre-registration anchors)
- benchmark.jsonl : cbdb9aaf147fc5640d6f13431ce7bceabbec0d8d731a8196df740f10eccbeaea
- benchmark.json  : 70b21fb89d6d1366ddec12d6c0dd08c0244a96d42fe1f1b17345d56737e00646
- corpus.json     : f1734c3da9cc07782db763aad720d4d2af36bcca26057fb4aa249b48a902e4ac

## For the AFWERK agent
Derive topk/entities/nli yourself (per AFWERK_CONTRACT_ANSWERS.md). Run engine + frontier
baselines, **sliced by temporal_sensitivity × cluster**. The 21 recency questions are the
knockout axis (frozen-cutoff frontier models should fail; the retrieval-grounded stack should win).

## Notes / known gaps
- Venezuela-only (breadth Iran/Taiwan/Cuba/Brazil deferred — costs ~$20-25 + ~2-3h on GLM; add after first scores).
- Hop mix skews 2-hop (the source compositions were 2-hop heavy; 3/4-hop gate out harder).
