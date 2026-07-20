# SOURCES_LICENSE.md — provenance + redistribution license, per source

**Scope:** every source the AFWERK defense benchmark corpus draws on, across T1 (Wikipedia/Wikidata),
T2 (CRS reports), and T3 (OFAC + institutional — this deliverable). One row per source for the T3
additions (small, individually-varied licenses); T1/T2 tiers are large and uniform, so they're rolled
up here with a pointer to the underlying per-source registry files, which already are the one-row-per-
source ledger for those tiers.

**Citable tiers** (redistributed verbatim as `paragraphs[].paragraph_text` in the benchmark, must carry
a verified CC-BY-SA / public-domain / owned license): `wikipedia, crs, ofac, institutional, sgx_owned`.

**Discovery-only tiers** (leads only — surfaced during seed mining, re-grounded to a citable source
before any question is composed, full text never redistributed): `rss_geopolitics, news_gdelt,
rss_world_news`.

---

## 1. T3 — OFAC (new, this deliverable)

| source_id | publisher | url | license | redistribution_ok |
|---|---|---|---|---|
| `OFAC-FAQ-VENEZUELA` | U.S. Dept. of the Treasury (OFAC) | https://ofac.treasury.gov/faqs/topic/1581 | US Government work — public domain, 17 U.S.C. §105 | yes |
| `OFAC-FAQ-IRAN` | U.S. Dept. of the Treasury (OFAC) | https://ofac.treasury.gov/faqs/topic/1551 | US Government work — public domain, 17 U.S.C. §105 | yes |
| `OFAC-FAQ-CUBA` | U.S. Dept. of the Treasury (OFAC) | https://ofac.treasury.gov/faqs/topic/1541 | US Government work — public domain, 17 U.S.C. §105 | yes |
| `OFAC-SDN-LIST` | U.S. Dept. of the Treasury (OFAC) | https://www.treasury.gov/ofac/downloads/sdn.csv | US Government work — public domain, 17 U.S.C. §105 | yes, **but structured only** — registered for provenance/entity-QID anchoring; NOT chunked into narrative passages (a raw designee/alias/program table doesn't entail cleanly for MiniCheck, same rule CRS statistical appendices are dropped under) |

Narrative content acquired: FAQ Topic pages (genuine Q&A prose — legal basis, Executive Orders,
designated-entity relationships, effective dates), not the "Sanctions Programs and Country
Information" index pages, which are mostly General-License title lists (table-like, low entailment
value) and were deliberately skipped. 628,304 chars of narrative prose across the 3 FAQ pages
(Venezuela 131,889 / Iran 322,668 / Cuba 173,747).

Taiwan and Brazil have **no** OFAC sanctions program or FAQ topic page — confirmed by absence on
`ofac.treasury.gov/sanctions-programs-and-country-information`, not assumed. Not a gap; those
countries are not OFAC-sanctioned jurisdictions.

Files: `data/defense_corpus/corpus/ofac/*.txt` (+`OFAC-SDN.csv`), manifest
`data/defense_corpus/ofac_manifest.jsonl`. Script: `scripts/acquire_ofac_sources.py`.

## 2. T3 — Institutional (new, this deliverable)

| source_id | publisher | url | license | redistribution_ok |
|---|---|---|---|---|
| `INST-IRAN-ECONMON-2020` | World Bank Group | http://documents.worldbank.org/curated/en/287811608721990695/text/Iran-Economic-Monitor-Weathering-the-Triple-Shock.txt | © World Bank; document's own "Rights and Permissions" front matter: *"this work may be reproduced, in whole or in part, for noncommercial purposes as long as full attribution to this work is given"* — verified in-document, not assumed from a site-wide policy | yes (noncommercial research use, attributed) |
| `INST-BRAZIL-SCD-2023` | World Bank Group | http://documents.worldbank.org/curated/en/099072023134526692/text/BOSIB0bf484b270d508c2809049f2fffead.txt | same as above, verified in this document's own front matter | yes (noncommercial research use, attributed) |

**Why license was verified per-document rather than assumed:** `worldbank.org`'s live Terms &
Conditions ("Reproduction and Use" page) state general site content requires **prior written
permission** to redistribute — the commonly-cited "World Bank content is CC BY 4.0" claim applies
specifically to formal Open Knowledge Repository publications and datasets, not the general
marketing site, and even within Documents & Reports the license varies by individual publication
(a "Doing Business 2015" report checked during acquisition was explicitly CC BY 3.0 IGO; the two
docs used here instead carry the noncommercial-reproduction-with-attribution grant quoted above —
both explicit, both real, just not identical language). The acquisition script
(`scripts/acquire_institutional_sources.py`) fails closed: it greps each document's own front
matter for an explicit license/reproduction grant and **skips** anything without one, rather than
inheriting a blanket assumption. 355,929 chars of narrative prose across the two documents.

**Coverage gaps — documented, not silently dropped, escalate before adding:**
- **Venezuela**: World Bank's only indexed documents are pre-2003 archival reports (1960s–70s
  "economic position and prospects" memoranda) that predate the Bank's 2012 Open Access policy and
  carry no in-document license statement. Skipped. Venezuela's sanctions/geopolitical narrative is
  already well covered by CRS (T2) and the new OFAC FAQ (T3) — the gap doesn't starve the cluster.
- **Cuba**: not a World Bank member state; no modern WB documents exist to acquire.
- **Taiwan**: not a World Bank member state (per the same non-recognition status that keeps it off
  OFAC's list too); no WB country program exists.
- **IMF**: `imf.org/en/About/copyright-and-usage` returned HTTP 403 live; the legacy
  `imf.org/external/terms.htm` redirect resolves to an empty stub page. No verifiable per-document
  license text was found this session (IMF materials are typically © IMF with a narrower reuse
  policy than CC-BY, not confirmed either way here). **Excluded, escalated** — do not include IMF
  content until a human confirms the actual terms (e.g., by inspecting a specific publication's
  front matter the way the two WB docs above were checked).

Files: `data/defense_corpus/corpus/institutional/*.txt`, manifest
`data/defense_corpus/institutional_manifest.jsonl`. Script: `scripts/acquire_institutional_sources.py`.

## 3. T1 — Wikipedia / Wikidata (roll-up, pre-existing)

| tier | count (rows in `sgxem_source_registry.jsonl`) | license | redistribution_ok |
|---|---|---|---|
| `wikipedia` | 410 (incl. 134 `SC-*` supply-chain rows) | CC BY-SA 3.0/4.0 (Wikipedia) | yes, share-alike attribution required |
| `wikidata` | 148 | CC0 (Wikidata) | yes |

Full one-row-per-source ledger: `data/defense_corpus/sgxem_source_registry.jsonl` (filter
`source_type in {wikipedia, wikidata}`) and `data/defense_corpus/supply_chain_registry.jsonl` for
the 37-source supply-chain sub-cluster specifically. **Known pre-existing data-quality note**
(found while compiling this doc, not introduced by T3): ~100 `WIKI-*` source_ids appear 2–4×
each in `sgxem_source_registry.jsonl` (e.g. `WIKI-1967_Caracas_earthquake` ×4) — harmless
duplicate registrations, not a licensing issue, but worth a dedup pass if the registry is ever
used as an authoritative count rather than a license ledger.

## 4. T2 — CRS reports (roll-up, pre-existing)

| tier | count | license | redistribution_ok |
|---|---|---|---|
| `crs` | 100 | US Government work (Congressional Research Service) — public domain | yes |

Full ledger: `data/defense_corpus/crs_registry.jsonl`. Acquired via
`scripts/acquire_crs_reports.py` (EveryCRSReport.com bulk mirror). This is the T3 template this
deliverable followed.

## 5. sgx_owned

| source_id | publisher | license | redistribution_ok | note |
|---|---|---|---|---|
| `venezuelan_assets` (KMS collection, ~2.8K records) | SGX / internal | owned — internal research corpus at `/research/venezuelan_assets` (no third-party license needed; confirmed no `LICENSE`/third-party-attribution requirement in that repo) | yes | **prose only** — per the issue's explicit instruction, numeric/CSV/table chunks from this collection must be dropped before ingest (tables don't entail cleanly in MiniCheck, same rule as everywhere else in this doc). **Not yet executed**: this is a documentation/classification decision for T3; the actual prose-only filter is an ingest-time payload operation against the `venezuelan_assets` Qdrant collection, which was not run this session (see §6 blockers) — flagging so it isn't silently assumed done. |

## 6. Discovery-only (never redistributed)

| tier | source | policy |
|---|---|---|
| `rss_geopolitics` | KMS discovery feed | leads only (see `scripts/mine_feed_seeds.py`) — a lead may only enter a question after its claim is re-grounded to a citable tier (wikipedia/crs/ofac/institutional) at T5 composition; the feed text itself is never quoted or stored as a `paragraphs[]` entry |
| `news_gdelt` | KMS discovery feed | same discovery-only policy |
| `rss_world_news` | KMS discovery feed | same discovery-only policy |

These are explicitly excluded from the citable-tier acceptance gate; `build.py`'s
`CITABLE_TIERS` set does not include them, so a record citing one directly would already fail
schema validation.

## 7. Escalations open for human review

1. **IMF narrative text** — excluded, license unverified this session (§2). Resolve by checking a
   specific IMF publication's own front matter the way the two WB documents were checked, or get
   an explicit answer from IMF's rights office.
2. **Venezuela / Cuba / Taiwan institutional coverage** — genuinely absent (not skipped for
   convenience); confirm this is acceptable given CRS/OFAC already carry Venezuela's narrative
   weight, or explicitly deprioritize institutional-tier balance for those three clusters.
3. **`venezuelan_assets` prose-only filter** — classification done (sgx_owned, confirmed
   ownership), but the actual ingest-time filter dropping numeric/CSV chunks has not been run.

---

## 8. Not done this session — real blocker, not a scope cut

The **ingest step** (SmartChunker → QID enrichment via the 275,943-entry Wikidata cache → NV-Embed-v2
embedding → upsert into the `afwerk_defense_corpus` Qdrant collection, `source_tier` stamped via
`scripts/set_source_tier.py`) was **not run**. The canonical Qdrant instance (dev-box `localhost:6333`,
per `scripts/create_defense_collection.py`'s own comment — the old Spark-side `100.115.144.22` target
is decommissioned) is currently unreachable: `docker ps` shows the `qdrant` container up with **~95GB
RSS**, and every REST/`qdrant_client` request against it returns `Connection reset by peer`. This
looks like the instance is memory-pressured or wedged, not a config issue on this end (verified via
both raw `curl` and the Python `qdrant_client`, several retries, several minutes apart). Restarting
production-adjacent shared infrastructure wasn't something to do unilaterally mid-task — flagging for
a deliberate call instead.

**What's real and ready:** 6 new sources (4 OFAC, 2 institutional), 984,233 chars of license-clean
narrative prose, registered in `sgxem_source_registry.jsonl` in the exact schema T1/T2 used, ready to
chunk/embed/ingest the moment Qdrant is healthy again — no further acquisition work is on the critical
path.

**Next steps to actually merge this into the frozen benchmark (none of which this task performed):**
1. Get the dev-box Qdrant instance healthy (restart/investigate the 95GB RSS condition) — or point
   `--host`/`QDRANT_HOST` at wherever the team decides is canonical if that comment is now stale.
2. Run the T1/T2 ingest path unmodified against the new `corpus/ofac/*.txt` and
   `corpus/institutional/*.txt` files (SmartChunker → QID → NV-Embed → upsert, `--recreate` **not**
   set).
3. Run `scripts/set_source_tier.py` to stamp `source_tier=ofac` / `source_tier=institutional` on the
   new points.
4. Run the MiniCheck NLI gate on the new tiers (mirror `scripts/nli_gate_crs.py` — an
   `nli_gate_ofac_institutional.py` swapping `--source-type`) and report survival rate.
5. Only then — as a separate, reviewable step, explicitly **not** performed by this task per its own
   constraints — fold gate-verified OFAC/institutional questions into
   `data/afwerk_defense_benchmark.jsonl` and re-freeze with a new SHA-256 in `BENCHMARK_FROZEN.md`.
