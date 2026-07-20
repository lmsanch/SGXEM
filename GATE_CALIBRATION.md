# GATE_CALIBRATION.md — T7 gate review

**Scope:** hand-review of the T6 defensibility gate that produced `data/afwerk_defense_benchmark.jsonl`
(360 records, frozen per `BENCHMARK_FROZEN.md`). This document does **not** modify the benchmark, the
gate code, or the frozen files — it documents what the gate actually does today, what a 50-record
manual audit found, and what would need to change if a re-gate is ever authorized.

**Method:** stratified random sample of 50 records from the final 360 (`random.seed(7)`/`random.seed(99)`,
oversampling 4-hop [4/4 included], 3-hop [18/47], and recency [22/75] records since those are where
failure modes are most likely, plus cluster coverage including the two smallest clusters,
`enterprise_risk` and `supply_chain`). Every sampled record was read in full (question, all hops,
supporting passages, gate dict) and cross-checked against real Wikidata for every `bridge_qid`. No paid
API calls were made — MiniCheck/Kimi/DeepSeek were not re-invoked; the review is manual reading by this
agent plus free Wikidata `wbgetentities` lookups (~50 read-only HTTP calls, no cost). `build.py` was run
against the full 360-record file to confirm the schema/bridge-leak check still holds structurally.

## 1. What "the gate" actually is (read from code, not docs)

The issue references `prompts/03_nli_single_passage.md` and implies there are tunable "NLI
entailment-probability cutoff" and "single-passage-sufficiency cutoff" values to calibrate. Neither is
accurate for the pipeline that actually built the 360-record file:

- `prompts/02_red_team.md` and `prompts/03_text_only_ablation.md` (no `03_nli_single_passage.md` exists
  under any name) are **not used by the current gate at all**. `grep` confirms they're referenced only
  by `curation_loop.py`, the legacy cross-modal (thermal/audio/depth) pipeline from the repo's initial
  commit. The MuSiQue defense-benchmark gate (T5/T6/T7) has its own, separate, inline prompts.
- The real gate is three independent checks, run in this order:
  1. **`scripts/verify_hops_nli.py`** — per-hop entailment via `NLIVerifier` (MiniCheck-Flan-T5-Large,
     `/research/kms/services/triple_extraction/nli_verifier.py`). It calls the MiniCheck model's
     `.score()` and takes its **binary `pred_labels`** output directly as `supported`. The model does
     return a `probability` field, but **the codebase never thresholds on it** — there is no
     configurable "entailment-probability cutoff" anywhere in this repo. Whatever decision boundary
     MiniCheck's own pretrained classification head uses is the de facto cutoff, and it was never
     touched or tuned by SGXEM.
  2. **`scripts/verify_redteam.py`** — two Fireworks-hosted LLMs, each called once per record with an
     inline system prompt (not a `prompts/*.md` file): Kimi-K2.6 as adversary (`single_passage`,
     `skippable`, both boolean) and DeepSeek-V4-Pro as judge (`forced_link`, `quality_ok`, both
     boolean). **`single_passage_sufficient` is a raw LLM true/false judgment** — again, no numeric
     cutoff exists to tune.
  3. **`build.py`** — schema + the one genuinely programmatic check in the whole gate: the **bridge-leak
     regex/substring check** (no hop's answer text may appear verbatim in the question). Confirmed
     passing 360/360 on today's frozen file.
  4. **`scripts/curate.py`** — diversity, not defensibility: `--per-answer` (default **2**, i.e. at most
     2 shipped questions per distinct normalized answer) and `--qsim` (default **0.85** token-Jaccard,
     drop a question if it overlaps ≥85% with one already kept). These are the **only two numeric knobs
     in the entire pipeline**, and every batch (`run_breadth.sh`, `run_supply_chain.sh`,
     `run_enterprise_risk.sh`, `run_regen.sh`, ...) invoked `curate.py` with these hardcoded defaults —
     there's no record of a sweep or deliberate tuning pass.

**Bottom line on "calibration":** there was no deliberate threshold-tuning step, because there are no
continuous thresholds to tune in the current implementation — entailment and single-passage-sufficiency
are opaque binary LLM/model judgments, not scored cutoffs. The only tunable numbers (`per-answer=2`,
`qsim=0.85`) were run at their code-default values, not calibrated against any labeled set. This should
be stated plainly rather than backfilled with a tuning narrative that didn't happen.

## 2. Failure modes — findings from the 50-record sample

### Bridge leak — not found; gate check confirmed working
`build.py`'s exact-substring check passed 0 violations on the full 360 file, and manual reading of all
50 sampled questions found no leaks (paraphrased or literal) of a non-final hop's answer into the
question text.

### Trivial multi-hop (world-knowledge shortcut) — found, structural gap, ~10% of sample
The adversary LLM (Kimi-K2.6) is **explicitly instructed to ignore its own world knowledge**: "assume
you have never heard of any of them and know nothing beyond these passages." That's by design for
testing chain-necessity, but it means the gate **cannot and does not** test whether a real, generally
informed solver could skip a hop using common knowledge — the exact "world-knowledge shortcut" axis that
the old (unused) `prompts/02_red_team.md` axis 1 was built for.
In the sample, ~5/50 (~10%) records have an opening hop resolvable from very well-known facts without
the cited passage, e.g.:
- `3hop__taiwan_0030`: "What entity is described as the U.S. military's 'pacing challenge'?" → China —
  no passage needed by an informed reader.
- `3hop__iran_0210`: "Which country was targeted by Hamas-led attacks on October 7, 2023?" → Israel.
- `2hop__taiwan_0125`: "What government did the United States recognize from 1913 until the end of
  1978?" → ROC/Taiwan, a well-known fact to anyone versed in Taiwan history.
In every case only the *opening* hop was shortcut-able; the *final* hop (a specific figure, date, or
title) still required the cited passage, so none of these were fully breakable — this is a soft/partial
finding, not a hard false positive. No fully-trivial (entirely guessable) question was found.

### QID-sense ambiguity — found, and the most severe finding in this review
This turned out to be much bigger than "ambiguity." I extracted all 108 `bridge_qid` values from the
50-record sample and looked each one up on live Wikidata. Roughly **80% do not identify the stated
answer entity** — some are a systematic-but-wrong pattern (a person's answer given their *country's*
QID, e.g. Maduro → `Q717` Venezuela, Raúl Castro → `Q241` Cuba, Díaz-Canel → `Q241` Cuba), and a
meaningful fraction are outright nonsense with zero semantic relation to the answer:
- `sugar` → `Q133097697` = "Cuban Government"
- `PdVSA` → `Q2480` = "1976" (a year)
- `CITGO` → `Q59037861` = a Nature journal article title
- `rice` → `Q503799` = "Hercules beetle" (an insect species)
- `$345 million` → `Q1144618` = "familial Mediterranean fever" (a disease)
- `War risk insurance` → `Q23406` = "Red Sea"
- `Cliver Antonio Alcalá Cordones` → `Q295790` = a *different* Venezuelan politician (Carlos Andrés
  Pérez)
- `CISADA` and `passing a joint resolution...` both map to the same wrong `Q10225` = "Indian National
  Congress" (an Indian political party)

**Root cause, from `scripts/compose_one.py` line 126:** `bridge_qid = the wikidata_id of this hop's
answer entity, or ""` — this is a literal instruction in the composer LLM's prompt. GLM-5.2 is asked to
*recall* a QID from memory, with no verification step. Line 287 falls back to the **cited passage's own**
resolved QID when the LLM leaves the field blank — which explains the "person mapped to their country"
pattern (the passage is a Wikipedia country article; its QID gets reused). The repo has a real,
working QID resolver (`scripts/resolve_entities_dual.py`, Wikipedia pageprops + Wikidata
`wbsearchentities`) — it is simply never called on `bridge_qid`.

**Practical impact is limited but the framing gap is real:** `grep -rl bridge_qid /research/afwerk` returns
nothing — the field is not consumed anywhere in the AFWERK scoring/eval pipeline (scoring uses
`paragraphs[].paragraph_text` / `paragraph_support_idx` as the gold join key, not QIDs). So this does not
corrupt Joint-F1 or any shipped score. But `TASKS_AFWERK_defense_benchmark.md`'s locked decision #1 states
"QID enrichment is mandatory... a chain is real only when hop-i answer-entity QID ==
hop-(i+1) passage QID" — **that check was never implemented**, and the field it depends on is ~80% wrong
in this sample. `bridge_qid` today is inert, decorative, and unreliable metadata, not a verified bridge
anchor. If it's ever wired into scoring or a future gate, it needs the existing resolver run against it
first.

### Temporal drift — checked, not found as fabrication; one real precision gap
Several sampled questions reference events dated into 2026 (a "2026 Strait of Hormuz crisis," a "US/Israel
military operation against Iran" beginning February 2026, a "United States intervention in Venezuela in
2026"). These read as suspiciously speculative at first glance, so each was checked against its actual
supporting passage. All are grounded in real citable-tier sources (dated CRS reports — e.g. "Effects of
Iran Conflict on Natural Gas Prices," June 11, 2026, and "The Arab Gulf States, the Iran Conflict, and
U.S. Relations" — plus live-updated Wikipedia summaries), not hallucinated by the composer. No fabricated
"future history" was found in the sample.
The real gap: **`as_of` is not a per-fact verified date.** All 360 records carry the identical
`as_of: "2026-06-29"` — confirmed programmatically. It is simply the generation-batch timestamp
(`compose_one.py`), not a fact-specific validity date extracted from the source. `temporal_sensitivity`
(`timeless`/`recency`, 285/75 in the shipped file) is similarly just a batch label — `compose_recency.py`
always stamps `recency`, `compose_one.py` defaults to `timeless` — neither is independently verified.
This is a labeling-precision issue, not a currently-observed drift (the window since generation is short,
~3 weeks as of 2026-07-20), and the 75 recency records are deliberately the intended stress-test axis per
`BENCHMARK_FROZEN.md`, not a defect. But if this benchmark is reused months from now, nothing re-checks
whether a "recency" fact has gone stale.

### Near-duplicate / diversity-cap leakage — found, minor, explains itself
`curate.py`'s `qsim=0.85` token-Jaccard threshold only catches near-identical phrasing. Two concrete
pairs from the sample ask the same underlying fact with the same answer but score well below the
dedup threshold: `2hop__venezuela_0562` vs `2hop__venezuela_0553` (Jaccard 0.625) and
`2hop__venezuela_0557` vs `2hop__venezuela_0551` (Jaccard 0.423) — both Chevron-GL-amendment and
both Delcy-Rodríguez-24th-VP respectively. Across the full 360, **141/360 (39%) records share a
normalized answer with at least one other record** — expected and by design given the explicit
`per-answer=2` cap (most SGXEM batches intentionally ship 2 paraphrases per fact), not a bug. One answer
("12") appears 3× in the shipped file, exceeding the nominal cap of 2 — but this is a norm-collision on a
short numeric string across three *unrelated* facts (an Australian mineral-output share and two separate
OFAC license counts), not real semantic duplication. Cause: `--per-answer` is enforced **per curate.py
run**, and `emit_benchmark.py` merges multiple independent per-batch curated files without re-running the
cap globally — so the "at most 2" guarantee holds per-batch, not strictly for the final merged 360-file.

## 3. False-positive-rate estimate

Defining a false positive as a shipped record that should not have passed the gate (genuinely
breakable/single-passage-answerable, or containing a leaked bridge):

- **Hard defensibility failures (leak, fully single-passage-answerable, fully breakable):** 0/50 (0%)
  found in this sample. `build.py`'s programmatic bridge-leak check independently confirms 0/360.
- **Soft/partial risk (opening-hop world-knowledge shortcut, chain still non-trivial overall):** ~5/50
  (~10%), reflecting a real, untested gap in the adversary's design (it's deliberately blinded from
  world knowledge) rather than individual bad records.
- **Metadata-only unreliability (bridge_qid), not a benchmark-correctness issue:** ~80/108 hop-QIDs
  (~74%) wrong in the sample, but the field is unused downstream, so it does not inflate the
  benchmark-correctness FPR.

## 4. Is the current gate trustworthy as-is?

**For its stated purpose (shipping genuinely multi-hop, non-leaked, passage-grounded questions): yes,
with caveats.** The hard failure modes named in the issue (bridge leak, full single-passage
sufficiency) were not found in 50 samples, and the two structural checks that matter most
(NLI entailment, bridge-leak regex) hold up. The "calibration" framing in the issue doesn't match the
implementation, though — there's nothing numeric to tune, and that should be said plainly rather than
papered over.

**Two things are not trustworthy as documented and would need a real fix, not just doc updates, before
being relied on:**
1. `bridge_qid` cannot be treated as a verified "bridge anchor" per the epic's locked decision — it
   isn't one. Low cost to fix (the resolver already exists) but **would require re-running composition
   or a post-hoc resolve-and-patch pass over the 360 records**, which is a decision for Luis since it
   touches the frozen file.
2. The adversary's world-knowledge blindness means "trivial multi-hop via general knowledge" is a gap
   the gate cannot see, evidenced by ~10% of the sample. Closing it would mean adding a genuine
   text-only-ablation step (an *un*-blinded strong model, given the passages, asked whether the full
   *original* question — not just chain-necessity — has an obvious answer) — which is exactly what the
   old, currently-unused `prompts/03_text_only_ablation.md` was for. This would require re-running that
   check over the full 360+ pool (or the `t5_raw/*.gated.jsonl` pool before final curation) to find out
   how many additional records it would cut — not something to do without sign-off, since it could
   shrink the frozen benchmark.

Neither finding invalidates today's 360-record file for its current use; both are worth a deliberate
decision before the benchmark is extended or re-frozen.
