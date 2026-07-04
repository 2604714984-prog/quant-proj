# Final Publication Metadata Runbook

Status: active
Rule id: `FINAL_PUBLICATION_METADATA_V1`
Owner: `Quant-Dispatcher`

Use this whenever a ChatGPT external-audit packet is committed, tagged, and pushed.

## Purpose

The final packet file is normally written before the final tag exists, so it cannot self-embed the final tag object. To avoid relying on chat-only metadata, every final external-audit publication must have a post-tag metadata closeout file.

## Required Metadata File

Create a metadata closeout using this naming shape:

```text
reports/agent_handoff/<batch>_final_publication_metadata_<yyyymmdd>.md
```

The file must include:

- repository;
- branch;
- final tag;
- tag object;
- commit;
- tree;
- tag URL;
- packet path;
- packet manifest path;
- final current package manifest path when one exists;
- source-of-truth statement;
- Codex-Audit status;
- external-audit requested verdict choices;
- non-authorization boundary.

## Required Source Of Truth Statement

Every final metadata file must include a source-of-truth statement equivalent to:

```text
This file records the final immutable publication tuple after the final packet tag was created. The external-audit entry point remains the immutable tag below.
```

## Manifest Inclusion Rule

The final metadata file must be included in the next durable publication manifest or closeout manifest.

Preferred pattern:

1. Commit the external-audit packet and packet manifest.
2. Create and push the annotated final packet tag.
3. Read the final tag object, commit, and tree.
4. Add the final metadata closeout on `main`.
5. Add a closeout manifest that includes the metadata file, or update the next packet's final publication manifest to include it.

Do not rewrite the immutable packet tag only to add post-tag metadata. Record post-tag metadata on `main` and treat the immutable tag as the external-audit entry point.

## Verification

Before closing the stage, verify:

- final tag resolves locally;
- final tag resolves on `origin`;
- final tag object, commit, and tree are recorded;
- packet manifest verifies from a full tag archive;
- final metadata file is committed and pushed to `main`;
- final metadata file is referenced by the next closeout or publication manifest.

## Non-Authorization

Publication metadata does not authorize recommendation, buy/sell advice, HITL ticket emission, broker APIs, order routing, order submission, auto execution, paper trading, live trading, trade plans, entry prices, target weights, position sizing, allocation, DB writes, network ingest, schema migration, registry activation, readiness changes, raw-data migration, `.env` access, key output, or secret handling.
