# R21 Development-First Amendment - A_Share_Monitor

Controller: Quant-Dispatcher
Created: 2026-07-08 Asia/Shanghai
Batch: `WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708`
Target repo: `/home/rongyu/workspace/A_Share_Monitor`
Target thread: `019f387b-617e-7273-b539-161216ae3002`
Branch: `codex/task-packet-r20-v2-20260708`

## Required Reads

- `/home/rongyu/workspace/quant-proj/docs/development_first_research_policy_20260708.md`
- `/home/rongyu/workspace/quant-proj/reports/agent_handoff/windows_wsl2_r21_development_first_dispatcher_amendment_20260708.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-feature-materialization-and-strategy-delta-r21-20260708/spec.md`

## Objective

Continue R21 under the development-first amendment. The prior A-share callback is not sufficient as final materialization-lane completion because it ended at limitation preservation and skipped diagnostics. Continue with actual row/field work and limitation-aware diagnostics.

Do not expand safety policy work.
Do not ask for another architecture/gate review.
Do not stop for ordinary warnings.

## Hard Stops

Stop only for:

1. Secret, credential, key, token, auth, or `.env` access or output.
2. Broker/order/paper/live/auto execution or daily signal push.
3. Product route, readiness, active registry, or production adapter activation.
4. Actionable investment advice or ticket claim.
5. Test-result parameter selection.
6. Non-public, paywalled, auth-required, or anti-abuse-bypassing provider access.

Everything else is a warning and research should continue.

## Required Work

ETF lane:

- Materialize ETF amount/NAV/premium/turnover for the 30-symbol ETF universe if possible.
- If unavailable, produce field-level unavailable evidence.
- Then run limitation-aware ETF delta diagnostics.

A-share lane:

- Materialize PEG/event/funds/hot-money feature rows for the 77-symbol pass-only universe.
- If rows validate, run new-feature-only delta diagnostics.
- If rows do not validate, skip with reason, not more policy reports.

Global/news/macro lane:

- Materialize date-indexed context/regime rows where possible.
- Never use them as direct signals.

## Required Output

End with:

- data rows or field-level unavailable evidence;
- limitation-aware ETF delta diagnostics;
- A-share validated rows or concrete row-validation failure reasons;
- new-feature-only delta diagnostics if validated rows exist;
- failure-memory updates;
- concrete next experiments.

## Boundary

Research-only. No actionable output, recommendation/advice, candidate promotion, readiness promotion, route activation, daily signal push, raw-data migration into controller, active schema/registry activation, full-frame wide3068, test-result parameter selection, non-public/auth-required provider access, or credential output.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708
WORKSTREAM: R21_DEVELOPMENT_FIRST_AMENDMENT_A_SHARE_CONTINUATION
TARGET_REPO: /home/rongyu/workspace/A_Share_Monitor
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
ETF_FIELD_STATUS:
A_SHARE_FEATURE_STATUS:
GLOBAL_NEWS_MACRO_STATUS:
DATA_ROWS:
STRATEGY_DIAGNOSTICS:
FAILURE_MEMORY_UPDATE:
NEXT_EXPERIMENTS:
WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
