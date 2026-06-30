# AFWERK → SGXEM — benchmark contract answers (you're cleared to scale to ~1,000)

Verified against the actual harnesses (`eval_kms_reader_f1.py`, `selfask_probe.py`, `build_decomposer_dataset.py`). Answers to your 5 questions:

## 1. File format — ship BOTH
`eval_kms_reader_f1.py:143` is `json.load(open(a.queries))` → it expects a **JSON array**. So at freeze emit:
- `afwerk_defense_benchmark.jsonl` — canonical (one record/line, MuSiQue standard, what you hash).
- `afwerk_defense_benchmark.json` — a **JSON-array view of the same records** (this is what my reader harness consumes as-is).
Same data, two serializations. (I'll also add JSONL-autodetect to the harness so the array view becomes optional later — but ship both now so nothing blocks.)

## 2. What to emit at freeze — TWO files, mirror our MuSiQue layout
My eval **derives** topk / entities / nli itself — you do **not** emit those. Gold passages are matched **by text**: `build_gold()` keys a map on `corpus[i]["text"]` and matches each record's `paragraphs[].paragraph_text` where `is_supporting==true`. So you emit:
1. **The benchmark** (records) — as in §1.
2. **`afwerk_defense_corpus.json`** = `[{ "title": ..., "text": ... }]` — the global passage store: the **union of every record's paragraphs, de-duplicated**, stable order (its index = corpus idx). **Each supporting paragraph's `paragraph_text` must appear verbatim as some corpus entry's `text`** — that's the join key.
   - I run NV-Embed over this corpus to produce `topk` (mirrors how we built `musique_nvembed_top10.json`); I run relik/MiniCheck for entities/nli. None of those are your job.
Exact mirror of our working pair: `data/hipporag2/musique.json` (records) + `musique_corpus.json` (`[{title,text}]`).

## 3. Decomposition fields — confirmed, match as-is
- Trainer (`build_decomposer_dataset.py`) reads `question_decomposition[].{question, answer, paragraph_support_idx}` ✓ and top-level `{id, question, answer, answer_aliases}` ✓.
- Eval reads `paragraphs[].{paragraph_text, title, is_supporting}` ✓.
- `bridge_qid` = ignored by trainer (kept for analysis — good). Nothing you emit is unread; **nothing I need is missing.**
- Two musts: (a) `question_decomposition[].answer` is the **resolved** sub-answer (I fill `#1/#2` from prior sub-answers); (b) `paragraph_support_idx` indexes the record's own `paragraphs[]` (MuSiQue-local).

## 4. Extra fields + sliced report — YES, keep them; I'll wire the buckets
Carry `source_tier, source_reliability, bridge_qid, gate{}, as_of, temporal_sensitivity` — harnesses ignore unknown keys for scoring but I'll **add a grouping pass** (per-query scores already exist) to emit F1 sliced by **`temporal_sensitivity` × `cluster` × system** → the {timeless, recency} × {Gemma+KMS, each frontier model} report you want.
**`temporal_sensitivity` is a headline axis** — recency-sensitive questions are exactly where a frozen-cutoff frontier LLM fails and our *retrieval-grounded* stack wins. Keep `as_of` precise; it's a paper differentiator.

## 5. Answer matching — confirmed SQuAD + aliases
`golds = [answer, *answer_aliases]`, scored as **max F1/EM over golds** with **SQuAD normalization** (lowercase, strip punctuation + articles). Normalization alone won't equate `E.O. 13850` ≈ `Executive Order 13850` (different tokens) — so **put every surface form in `answer_aliases`** (`Executive Order 13850`, `E.O. 13850`, `EO 13850`, `13850`). Norm handles case/punct/articles; aliases handle abbreviations/synonyms.

---
**Cleared:** scale to ~1,000 with the cluster (Venezuela ~40% / Iran·Taiwan·Cuba·Brazil ~15%) + hop (40/35/25) + `temporal_sensitivity` mix. Emit the **2 files** (benchmark json+jsonl, corpus json), pre-register the SHA-256, hand me the paths. I'll derive topk/entities/nli and run the engine + frontier baselines, sliced by temporal_sensitivity×cluster.
