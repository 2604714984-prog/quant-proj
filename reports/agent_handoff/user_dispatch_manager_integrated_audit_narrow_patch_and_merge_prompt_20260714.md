# User-Dispatch Prompt — Manager Integrated-Audit Narrow Patches and Merge Sequence

Copy the complete fenced prompt below into the current user-controlled Quant Manager conversation.

```text
RUN MANAGER_INTEGRATED_AUDIT_NARROW_PATCH_AND_MERGE_20260714

WORKSTREAM:
QUANT_MANAGER_USER_CONTROLLED_INTEGRATION_REMEDIATION

AUTHORITATIVE INTEGRATED AUDIT:
https://github.com/2604714984-prog/quant-proj/blob/71b97f6131fa211e2a5ed7e6c8d2b968a9b7bbb7/reports/external_audit/project_wide_remediation_integrated_external_audit_20260714.md

ISSUE-LEVEL AUDIT RECEIPT:
https://github.com/2604714984-prog/quant-proj/issues/26#issuecomment-4969889384

REUSE THE EXISTING UMBRELLA ISSUE:
https://github.com/2604714984-prog/quant-proj/issues/26

DO NOT CREATE A NEW PROJECT, UMBRELLA ISSUE, TASK-PACKET TREE, DISPATCHER LAYER, ACCEPTANCE LAYER,
REGISTRY, WRITER, ENGINE, SIGNATURE SYSTEM, OR RECEIPT HIERARCHY.

==================================================
CURRENT VERIFIED PR HEADS
==================================================

Verify these refs again before execution and record any movement. The currently audited heads are:

```text
quant-proj PR #27
head 16054c55e8d83757960b10338063397a9f24dfaa
current mergeable status: false — must be updated/rebased only after downstream heads settle

central-data-ingestion PR #24
head 94326205df275ebc7490a1084d0849a9000bbdee

market_data PR #5
head 47a6c6675fe0be173a5552461921d89ec6d60b09

quant_research_lab PR #6
head 4e65fbe5889d6815a8454f80d1ea96ee0802c192

US_Stock_Monitor PR #8
head 252fe19be632943389f31d025c2789aca452df74

A_Share_Monitor PR #8
head 7951e0669609d7e0bfa8325d47b14f4b954750c9
base is a repair branch, not default main
```

The previous work is not discarded. It closed most original audit findings. This task performs only
the narrow integration fixes identified by the integrated external audit.

==================================================
FROZEN STATUS
==================================================

```text
ORIGINAL_AUDIT_FINDINGS=SUBSTANTIALLY_CLOSED_IN_CODE
CURRENT_PR_SET=CHANGES_REQUIRED_BEFORE_INTEGRATED_ACCEPTANCE
PRODUCTION_DATABASE_CUTOVER=NOT_AUTHORIZED
A_SHARE_FULL_REPLAY=BLOCKED
US_REAL_DATA_REPLAY=BLOCKED_ON_ACCEPTED_DATA
RESEARCH_RESUME=BLOCKED
SYSTEM_INTAKE_READY=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

Do not write `OPEN_P0_FINDINGS=0`, `ONE_WRITER_ACTIVE=PASS`, `ONE_CLI_ACTIVE=PASS`, or
`PROJECT_CONSOLIDATED` until the gates in this prompt actually pass.

==================================================
HARD ANTI-OVERDESIGN AND SCOPE RULES
==================================================

1. Amend the existing PRs. Do not create replacement repositories or parallel implementations.
2. Use issue #26 and existing PR discussions as the task and closeout records.
3. Do not create one task file per finding.
4. No new general framework, factory, plugin system, orchestration layer, model-routing layer, or
   generic data platform.
5. No new strategy, factor family, threshold search, or result run.
6. No production provider call, production DB mutation, schema/key change, historical backfill,
   destructive operation, strategy promotion, or trading path.
7. Each implementation patch must use the file allowlist below. Scope outside it returns:
   `SCOPE_EXPANSION_REQUIRES_USER_APPROVAL`.
8. Runtime growth must be small:
   - central-data follow-up: no more than approximately +250 net runtime lines;
   - US follow-up: no more than approximately +80 net runtime lines;
   - controller follow-up: must remain net-negative versus its base;
   - A-share R5 limits are controlled by the separate user-dispatch prompt.
9. A passing CI result does not permit status overclaim. Status is derived from installed runtime and
   semantic evidence.
10. Do not merge any PR until its updated exact head receives the requested external re-review.

==================================================
WORKSTREAM A — CENTRAL-DATA PR #24 INSTALLED SHADOW RUNTIME
==================================================

TARGET:
https://github.com/2604714984-prog/central-data-ingestion/pull/24

CURRENT HEAD:
94326205df275ebc7490a1084d0849a9000bbdee

AMEND THE EXISTING PR/BRANCH. DO NOT OPEN A SECOND CENTRAL WRITER PR.

ALLOWED FILES:

```text
pyproject.toml
.github/workflows/research-validation.yml
central_data/__init__.py
central_data/cli.py
central_data/adapters/tushare.py
central_data/backup.py
central_data/writer.py
central_data/postcheck.py
tests/test_minimal_writer.py
README.md or one concise migration note, only if necessary
```

MANDATORY FIX A1 — PACKAGE DISCOVERY

The wheel must include `central_data*`. The current package configuration only installs
`central_data_ingestion*`, while the existing console scripts still point to the legacy collector and
publisher.

Required proof:

1. build a wheel;
2. install it into a clean virtual environment with no editable install;
3. run from outside the repository root;
4. import `central_data` from site-packages;
5. execute the shadow module CLI from the installed wheel;
6. execute focused writer tests against the installed package.

Do not repoint or delete the legacy production console scripts in this code-only patch. Until explicit
owner cutover, label them:

```text
LEGACY_ACTIVE_DURING_SHADOW_MIGRATION
```

The installed new shadow path may be invoked as `python -m central_data.cli` or one explicitly named
shadow command. Do not claim one active production CLI yet.

MANDATORY FIX A2 — DURABLE PROVIDER-TO-WRITER COMMAND

The installed shadow CLI must provide one bounded command that performs:

```text
ReplayAdapter.fetch
-> attach/normalize source, retrieved_at and available_at according to the dataset config
-> normalize_rows
-> validate_rows
-> append_batch
```

Requirements:

- adapter response SHA becomes `source_sha256` automatically;
- no manually prepared `rows.json` or hand-entered source hash is required for this path;
- network remains disabled unless an explicit execution flag is supplied;
- tests use a deterministic injected transport, not a real network call;
- credentials never appear in output, exceptions, run records, or tests;
- no out-of-Git bridge script.

Keep the existing rows-file dry-run mode if it remains useful for fixtures, but it is not accepted as
the durable provider path by itself.

MANDATORY FIX A3 — ROUTINE BACKUP POLICY

For routine append-only operation:

- use one prewrite recovery point for the first mutation of the UTC/local day;
- later routine batches that day reuse the proven recovery point;
- do not include `run_id` in every routine backup filename;
- retain a small 3–7 point rotation;
- elevated schema/backfill/delete work is outside this routine writer.

Add a test proving two routine runs on the same day do not create two full DB copies.

Before any future production cutover, the cutover plan must separately prove:

```text
old writers stopped
writer lock acquired
DuckDB checkpoint/clean close policy documented
copy created
copy opened read-only and queried
restore opened and queried
```

This PR may prove that sequence on a realistic temporary copy. It must not mutate production.

MANDATORY FIX A4 — STATUS LANGUAGE

After this patch, allowed status is:

```text
MINIMAL_WRITER_INSTALLED_SHADOW_RUNTIME_READY
PRODUCTION_WRITER_CUTOVER=false
LEGACY_PRODUCTION_CLI_RETIRED=false
```

Forbidden status before owner cutover:

```text
ONE_WRITER_ACTIVE
ONE_CLI_ACTIVE
PRODUCTION_CUTOVER_COMPLETE
```

CENTRAL ACCEPTANCE TESTS:

- clean wheel install;
- installed import and module/command execution outside repository root;
- adapter-to-writer end-to-end fixture through the CLI;
- source SHA automatically bound to response bytes;
- same-day backup reuse;
- row/key/value parity;
- idempotent replay;
- conflict quarantine;
- rollback and postcommit restore;
- aggregate read-only audit;
- no legacy/private imports in `central_data`;
- production DB byte identity unchanged.

==================================================
WORKSTREAM B — US PR #8 HALT-VALUATION PRECEDENCE
==================================================

TARGET:
https://github.com/2604714984-prog/US_Stock_Monitor/pull/8

CURRENT HEAD:
252fe19be632943389f31d025c2789aca452df74

AMEND THE EXISTING PR. DO NOT CREATE ANOTHER US ENGINE OR PR.

ALLOWED FILES:

```text
usq/backtest/gap_policy.py
tests/test_execution_gap_policy.py
```

MANDATORY FIX:

For a held symbol with:

```text
confirmed trading_halt
and a positive but stale/indicative provider price
```

valuation must use the latest prior accepted adjusted mark, not the current provider value.

Precedence for held valuation:

```text
terminal corporate action/delisting identity
-> confirmed halt
-> valid current price
-> unexplained gap
```

Do not alter the already accepted fill rule: a confirmed halt never fills.

Required test:

```text
previous accepted close = 10
current provider price = 12
action_types contains trading_halt
resolved held valuation = 10
no fill occurs
```

Run the focused semantic tests and full existing suite. No provider/network run.

==================================================
WORKSTREAM C — A_SHARE_MONITOR DEFAULT-BRANCH CANONICALIZATION
==================================================

CURRENT PR:
https://github.com/2604714984-prog/A_Share_Monitor/pull/8

CURRENT HEAD:
7951e0669609d7e0bfa8325d47b14f4b954750c9

The current PR is based on a repair branch, not default `main`. Merging it as-is does not make the
accepted semantics the default runtime.

Manager must choose exactly one of these paths:

A. retarget/rebuild the existing PR as one narrow integration onto current `main`; or
B. change the default branch to the accepted repair line after proving no required default-branch fix
   is lost.

Do not leave two active A-share authorities.
Do not keep both an integration PR and the old repair-only PR open after the decision.

Required evidence:

- exact commit comparison between `main` and the repair line;
- accepted missing-price, period-return, PIT, test-selection and excess-return tests remain present;
- no safety fix from `main` is silently lost;
- the displaced branch receives an immutable tag/ref;
- current docs and CI identify the chosen default/canonical branch;
- no strategy research or full replay is run.

Allowed final status:

```text
A_SHARE_LEGACY_CANONICAL_BRANCH_SELECTED
```

This does not make A_Share_Monitor the future authoritative strategy engine; it only prevents unsafe
legacy execution while QRL assumes authority.

==================================================
WORKSTREAM D — TRACK THE SEPARATE QRL R5 FOLLOW-UP
==================================================

The user will independently dispatch:

```text
reports/agent_handoff/user_dispatch_codex_a_share_r5_full_replay_readiness_followup_prompt_20260714.md
```

Manager may track refs and gates only. Manager must not select A-share formulas, parameters, winners,
or allocator conclusions.

Do not merge QRL PR #6 until that follow-up is complete and independently re-reviewed.

==================================================
WORKSTREAM E — MARKET_DATA PR #5
==================================================

TARGET:
https://github.com/2604714984-prog/market_data/pull/5

CURRENT HEAD:
47a6c6675fe0be173a5552461921d89ec6d60b09

No code expansion is requested. Keep it read-only.

Merge only after the updated central-data PR proves the installed shadow writer exists. If base drift
requires a mechanical rebase, run the existing full CI and confirm no central write surface returns.

==================================================
WORKSTREAM F — QUANT-PROJ PR #27 FINAL TRUTHFUL INTEGRATION
==================================================

TARGET:
https://github.com/2604714984-prog/quant-proj/pull/27

CURRENT HEAD:
16054c55e8d83757960b10338063397a9f24dfaa
CURRENT MERGEABLE STATUS:
false

Do not repair or rebase PR #27 first. Update it last after all downstream patch heads are frozen.

ALLOWED CONTROLLER SCOPE:

```text
existing project remediation status board
existing ownership/deprecation document
existing lightweight runbooks/prompts
registry/agents.yaml and registry/model_routing.yaml historical-status clarification
one existing CI workflow
PR body and issue #26 comments
```

Required changes:

1. Replace stale PR heads with the actual new exact SHAs.
2. Replace overclaims:

```text
OPEN_P0_FINDINGS=0
ONE_WRITER_STATUS=PASS
ONE_CLI_STATUS=PASS
PROJECT_CONSOLIDATED
```

with evidence-derived states such as:

```text
ORIGINAL_AUDIT_FINDINGS_CLOSED_IN_REPAIR_BRANCHES
FULL_REPLAY_BLOCKERS_OPEN
MINIMAL_WRITER_INSTALLED_SHADOW_RUNTIME_READY
PRODUCTION_CUTOVER_NOT_AUTHORIZED
A_SHARE_DEFAULT_BRANCH_CANONICALIZATION=<actual status>
```

3. Mark `registry/agents.yaml` as historical/advisory or remove it from current routine-policy
   authority. It must not contradict the simplified `AGENTS.md` and dispatcher runbook.
4. Keep the routine flow:

```text
one issue -> one PR -> focused CI -> short closeout
```

5. Rebase/update PR #27 after downstream changes so it becomes mergeable.
6. Controller PR must remain net-negative in active runtime/policy surface.

==================================================
QRL GENERATED-ARTIFACT POLICY
==================================================

Manager must verify the updated QRL PR does not require committed smoke Parquet/CSV binaries as source
code evidence.

Expected policy:

- CI generates smoke Parquet/CSV in temporary workflow storage;
- Git tracks JUnit, concise JSON gate/manifest, and hashes only;
- existing historical commits remain immutable;
- no history rewrite is required;
- new large generated runops artifacts are not added to the PR.

==================================================
RE-REVIEW AND MERGE SEQUENCE
==================================================

After all narrow patches are pushed:

1. Post one concise issue #26 comment containing every exact new head and CI URL.
2. Request one integrated external re-review against those heads.
3. Do not merge until that review returns no blocking findings.
4. Then merge in this order:

```text
1. central-data-ingestion PR #24
2. market_data PR #5
3. US_Stock_Monitor PR #8
4. quant_research_lab PR #6
5. A_Share_Monitor canonical/default-branch integration
6. quant-proj PR #27 last
```

5. Verify default-branch SHAs and required CI after each merge.
6. Do not perform production DB cutover as part of the merge sequence.

==================================================
PRODUCTION DATABASE CUTOVER REMAINS A SEPARATE USER DECISION
==================================================

After code merges, prepare only a cutover proposal containing:

```text
pre-cutover DB identity/hash
legacy writers stopped proof
installed minimal CLI proof
read-only preflight audit
backup/restore/open/query proof
one bounded shadow append
rollback commands
expected writer/CLI after cutover
```

Return:

```text
STATUS=WAITING_FOR_EXPLICIT_USER_CUTOVER_APPROVAL
```

Do not execute production write, provider fetch, schema migration, or destructive action without a
fresh explicit user instruction.

==================================================
FINAL ACCEPTANCE STATES
==================================================

PATCH_HEADS_READY requires:

- central clean-wheel installed shadow runtime;
- provider-to-writer CLI fixture;
- daily backup reuse;
- US halt valuation precedence;
- QRL follow-up complete;
- A_Share default-branch decision complete;
- all exact-head CI green;
- controller status truthful.

MERGE_READY requires an external re-review of those exact heads.

PROJECT_CODE_CONSOLIDATED may be used only after all approved merges land on their default branches.

RESEARCH_RESUME remains false until:

- production/read-only central snapshot callback is separately accepted;
- QRL full replay receives a fresh user dispatch;
- no strategy result has been viewed or promoted prematurely.

==================================================
BOUNDARY
==================================================

Authorized:

- the narrow source/test/CI/document changes above;
- updates to existing PRs and issue #26;
- clean-wheel and temporary DuckDB tests;
- rebases required for mergeability.

Not authorized:

- production database cutover or write;
- real provider/network fetch;
- schema/key change or backfill;
- new research or parameter search;
- strategy candidate/readiness promotion;
- recommendation, broker, order, paper, live, or auto execution;
- secret exposure.

==================================================
CONCISE MANAGER CALLBACK
==================================================

BATCH: MANAGER_INTEGRATED_AUDIT_NARROW_PATCH_AND_MERGE_20260714
STATUS:
ISSUE_26_COMMENT_URL:
CENTRAL_PR_HEAD:
CENTRAL_CLEAN_INSTALL_STATUS:
CENTRAL_PROVIDER_TO_WRITER_STATUS:
CENTRAL_DAILY_BACKUP_STATUS:
MARKET_DATA_PR_HEAD:
QRL_PR_HEAD:
QRL_EXTERNAL_REVIEW_STATUS:
US_PR_HEAD:
US_HALT_VALUATION_STATUS:
A_SHARE_CANONICAL_DEFAULT_STATUS:
CONTROLLER_PR_HEAD:
CONTROLLER_MERGEABLE_STATUS:
EXACT_HEAD_CI_URLS:
INTEGRATED_REVIEW_STATUS:
MERGE_STATUS:
PRODUCTION_DB_CUTOVER: NOT_AUTHORIZED
RESEARCH_RESUME: false
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
FIXES_REQUIRED:
NEXT_ACTION:
```
