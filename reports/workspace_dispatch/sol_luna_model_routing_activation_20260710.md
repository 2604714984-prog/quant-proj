# Sol / Luna Collaboration Routing Activation

Status: `CONFIGURED_LEAN`

## Active topology

- Quant-Manager: current task `019f4c70-cac3-7211-8e04-47b8b51c819e`,
  `gpt-5.6-sol` / high. Owns hard decomposition, scope, dependencies, and the
  two allowed evidence exceptions.
- Quant-Dispatcher: task `019f4ca0-2054-77e3-9559-7005c0f9b565`,
  `gpt-5.6-luna` / medium. Owns queue, bounded packets, callbacks, and stall
  detection; it is not a second coordinator or reviewer.
- Executors: `gpt-5.6-luna` / medium.
- Final acceptance: separate read-only `gpt-5.6-luna` / high.

The path is Manager -> Dispatcher -> Executor -> automated gate -> Luna
acceptance. A red deterministic gate returns to Luna. Sol is used only when
evidence is still insufficient after one bounded Luna evidence rework or when
deterministic checks cannot reconcile conflicting evidence. Final ownership
then returns to Luna.

## Simplification

The durable workflow uses one task packet and only two result records:

1. one execution gate record;
2. one Luna acceptance record.

There is no routine Sol second review, no replay of full task history, and no
separate escalation/ruling manifest chain. The gate still binds expected
commands, callback, artifact hashes, and real Git refs. The Luna record carries
accept/rework/escalate and, if Sol was needed, binds the narrow ruling before a
final Luna decision.

## BaoStock recovery exercised by the new path

- stalled executor `019f4c95-9fac-7ff3-ad69-cca5fb8d1400` was interrupted and
  archived without commit or push;
- preserved worktree:
  `/home/rongyu/workspace/.wt-baostock-fundamental-smoke-20260710`;
- recovery executor: `019f4cac-2637-7052-8fb2-a88c43b44be6`;
- formal task packet:
  `tasks/backlog/A_SHARE_BAOSTOCK_FUNDAMENTAL_SMOKE_CODE_20260710`;
- two attempted precommit acceptance tasks were correctly blocked by host
  process-spawn error 1312 and made no changes. The lean path does not require
  a duplicate precommit model review: a green deterministic run permits an
  immutable branch commit, then Luna accepts the validated execution record;
- the first implementation commit was superseded after two deterministic gaps
  (clean-worktree binding and nonzero logout-result handling). Luna completed
  the bounded rework at commit `6ea528568de57da85eec3b12aec37a7a444ae5a3`;
  the automated gate reran all packet commands in a clean committed worktree,
  and fresh read-only Luna acceptance task
  `019f4cc3-e022-7f21-9f4d-0b3e036b7bf3` returned findings=none. Sol was not
  used for the rework or acceptance.

Family 68 stays frozen. The code retains `pubDate`, `statDate`, `roeAvg`,
`gpMargin`, `CFOToNP`, `liabilityToAsset`, and `YOYAsset`, with
`gpMargin=query_profit_data`. `strategy_candidate_available=false` remains
unchanged.

## Controller validation

```text
model routing validation: PASS
focused routing/gate/acceptance pytest: 27 passed
task packet validation: PASS
TOML/YAML/JSON parse: PASS
git diff --check: PASS
```

Boundary remains research-only: no provider execution, recommendation/advice,
candidate promotion, readiness/product-route activation, broker/order/paper/
live/auto, raw-data migration, or secret access/output.
