# LifeBench Prose-PII Scrubber Dataset

A PII-scrubbing dataset built from the **LifeBench** memory benchmark
([zhiyuan5986/LifeBench](https://github.com/zhiyuan5986/LifeBench),
paper [arXiv:2603.03781](https://arxiv.org/html/2603.03781v1)). Each record pairs a
question with the assembled prose evidence needed to answer it, plus exact PII spans
in that prose and a redacted version.

## Files
- `data/<user>.jsonl.gz` — full dataset, sharded by user (10 gzip-compressed JSONL files,
  1,952 records total, one JSON object per line)
- `sample_25_records.jsonl` — 25 records, uncompressed, for quick browsing on GitHub
- Build scripts: `reassemble.py` (assemble + strip source noise), `post_all.py`
  (offsets + redaction), `merge_enrich.py` (union labels), `precision_clean.py`
  (deterministic FP cleanup)

```python
import gzip, json, glob
data = [json.loads(l) for f in glob.glob("data/*.jsonl.gz")
        for l in gzip.open(f, "rt")]
print(len(data), "records")  # 1952
```

## Record schema
```jsonc
{
  "id": "fenghaoran_0000",
  "user": "fenghaoran",
  "question_type": "Information Extraction",
  "question": "...",
  "answer": "January 18",
  "data_to_answer": "<raw assembled prose evidence — input to the scrubber>",
  "scrubber_data": "<same text with PII replaced by [PERSON_1], [LOCATION_2], ...>",
  "pii_spans": [
    { "start": 110, "end": 121, "type": "PERSON", "text": "Peng Yuqing",
      "placeholder": "[PERSON_1]", "entity": "Peng Yuqing" }
  ]
}
```
`start`/`end` are character offsets into `data_to_answer` (end-exclusive).
**Guaranteed:** `data_to_answer[start:end] == text` for every span; no overlapping
spans; one consistent `[TYPE_n]` placeholder per real entity across all its mentions.

## Final stats
- **1,952 records** across 10 users; **34,416 PII spans** (avg 17.6/record)
- By type: PERSON 16,366 · ORG 9,852 · LOCATION 6,961 · PHONE 664 · ID 570 · EMAIL 3
- 1,947 records carry ≥1 span; 5 are genuinely PII-free
- **Dates / times / quantities are intentionally NOT redacted** so QA answers stay
  recoverable (privacy↔utility evaluation)

## How it was built
1. **Assemble** — for each LifeBench QA item, resolve its `evidence:[{type,id}]`
   pointers (joined on `phone_id`) to the underlying phone artifacts (SMS, calls,
   agent-chats, notes, calendar, photos, push) and concatenate into one prose context.
   Source-leaked translation-prompt junk in `faceRecognition` fields is stripped;
   6 records with junk embedded in free text were dropped.
2. **Label** — two-stage agent workflow over all 10 English users: a Sonnet *extractor*
   does prose NER (PERSON/LOCATION/ORG/EMAIL/PHONE/ID), grouping surface-form variants
   of one entity; a Sonnet *adversarial verifier* drops non-PII and unverbatim mentions.
3. **Finalize (deterministic)** — string-locate every mention → exact offsets,
   longest-match overlap resolution, consistent `[TYPE_n]` placeholders, redaction.

## Quality assurance (iterative self-audit)
Built and verified over several agent-workflow passes:
- **Coverage repair** — 4 timed-out batches + stragglers re-run until all 1,958 source
  records labeled.
- **Audit round 1** (61 records, Opus judges) → found systematic recall gaps
  (apps/brands like WeChat missed in 80 records; 227 booking/flight ID codes unlabeled).
- **Recall enrichment** (full-corpus pass) → unioned in the misses: ID 93→570,
  ORG +~1,000, with **zero regression** (no prior mention dropped).
- **Audit round 2** (54 records) → enrichment had injected FPs (generic role words,
  placeholder/descriptor ORGs, bracket/`Push/` markup, certifications) → removed
  deterministically.
- **Audit round 3** (50 fresh records) → 37/50 fully clean; residual `Push/` markup and
  generic feature-labels (`Health App`, `Pressure Monitoring`) → removed.
- **Final integrity:** 0 offset mismatches, 0 overlaps, 0 empty spans, 0 source-noise.

## Known limitations
- Labels are **silver** (Sonnet extract + verify, audited in aggregate, not span-by-span
  human-reviewed). Spot-verify before using a slice as eval **gold**.
- Long-tail/debatable cases remain (public-figure names like "Mozart", country/
  nationality terms, anonymized placeholders like "Real Estate Agent A", occasional
  word-boundary slips) — these are judgment calls, not clear errors.
- ORG vs LOCATION boundary is a judgment call for named venues (parks, museums,
  stations, restaurants).
- English (`data_en`) only; LifeBench also ships a parallel Chinese tree.

## License & attribution
Derived from **LifeBench** ([zhiyuan5986/LifeBench](https://github.com/zhiyuan5986/LifeBench),
arXiv:2603.03781), which is licensed under **Apache 2.0**. This repository is released
under the same license (see `LICENSE` and `NOTICE`). All source content is synthetic;
no data corresponds to real individuals. If you use this dataset, please cite the
LifeBench paper.
