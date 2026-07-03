# Reasonix Role Split Addendum

Date: 2026-07-04
Workspace: `/Users/rongyuxu/Desktop/quant proj`
Status: PLANNING_UPDATE / NEEDS_REVIEW_BEFORE_OPERATIONAL_USE

## Reason For Change

Reasonix is currently connected to DS and is expected to help with database maintenance and strategy development. Treating Reasonix as only a generic advisory reviewer is too coarse.

The workspace now splits Reasonix into three dispatchable roles:

- `reasonix_db_maintainer`
- `reasonix_strategy_researcher`
- `reasonix_advisory`

## Role Boundaries

### Reasonix-DB

Purpose:

- database maintenance diagnostics;
- schema/readiness review;
- manifest and data coverage planning;
- SQL or migration drafts;
- stale registry detection.

Default mode:

- read-only or draft-only.

Requires `human_gate` for:

- DB writes;
- schema migration;
- bulk ingest;
- physical DB movement;
- product-read registry activation;
- readiness decision changes.

Requires Codex-Dev for:

- implementation;
- tests;
- validation;
- delivery reports.

### Reasonix-Strategy

Purpose:

- strategy hypotheses;
- factor/config drafts;
- zero-candidate/rejected-result diagnosis;
- evidence-gap planning;
- overfit/data-risk critique.

Default mode:

- research draft.

Requires Codex-Dev for:

- promoting configs into A-share or US source repos;
- adding production code;
- adding tests;
- stage delivery reports.

Must not:

- output buy/sell advice;
- emit recommendation tickets;
- claim readiness without audited gates.

### Reasonix-Advisory

Purpose:

- read-only second review;
- test-gap review;
- report-overclaim review;
- boundary-leak review;
- codebase Q&A.

Must not:

- edit files unless converted into a Codex-Dev task;
- replace Codex-Audit;
- declare final external verdict.

## Dispatcher Update

Quant-Dispatcher now assigns:

- DB maintenance tasks to `reasonix_db_maintainer`;
- strategy research tasks to `reasonix_strategy_researcher`;
- second-review tasks to `reasonix_advisory`;
- implementation tasks to `codex_dev`;
- boundary-changing tasks to `human_gate` first.

## External Review Questions

1. Are Reasonix-DB and Reasonix-Strategy constrained enough to avoid unsafe writes or recommendation drift?
2. Should DB writes always require both `human_gate` and Codex-Dev validation?
3. Should strategy configs remain in `strategy_work` or task folders until Codex-Dev promotion?
4. Are these roles clear enough for Dispatcher to assign tasks from ChatGPT lists?
