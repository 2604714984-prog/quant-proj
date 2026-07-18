# Execution Task — Shadow and Paper Activation

Date: 2026-07-18
Repository: `2604714984-prog/quant-proj`
Status: `BLOCKED_UNTIL_SHADOW_ELIGIBLE`

## Start gate

Do not start implementation until the Manager provides an exact accepted strategy state:

```text
VALIDATION=PASS
HOLDOUT=PASS
CAPITAL_FEASIBILITY=PASS
SHADOW_ELIGIBLE=true
STRATEGY_DEFINITION_SHA256=<frozen>
STRATEGY_CODE_SHA256=<frozen>
INPUT_CONTRACT_SHA256=<frozen>
```

This task does not authorize real-money trading.

## Objective

Build the smallest external execution-validation lane:

```text
frozen quant-proj target artifact
-> one-way export adapter
-> live-data Shadow ledger
-> vn.py paper_account or equivalent simulator
-> exact reconciliation report
```

The execution lane must not import strategy logic or change target construction.

## Architecture boundary

Keep execution outside the research core.

Allowed shape:

```text
quant-proj generates immutable target artifact
external adapter validates and maps instrument/order fields
simulator receives orders
receipts return to reconciliation only
```

Forbidden:

```text
vn.py dependency inside quant_system research or backtest modules
strategy parameter changes
broker gateway
real-money order
automatic order retry
new database platform
new dispatcher or Agent framework
```

## Shadow stage

Run on current market data without order submission.

Minimum evidence:

```text
20 accepted sessions
at least one scheduled rebalance event
zero missed scheduled runs
zero stale-input use
zero target identity drift
zero duplicate target artifacts
zero nonfinite or unsupported values
```

Required daily aggregate record:

```text
run_id
strategy_definition_sha256
input_identity
signal_timestamp
target_timestamp
target_count
gross_target_value
cash_target
rejection_counts
stale_input_status
order_submission=false
```

Do not publish securities or target weights in public Git evidence.

## Paper stage

Use VeighNa only as an execution-side reference or simulator. The official project includes a local `paper_account` module that matches orders using real-time gateway quotes.

Paper acceptance requires:

```text
one complete scheduled rebalance
one-to-one target/order mapping
one-to-one order/receipt mapping
zero duplicate orders
zero out-of-scope symbols
zero unauthorized retries
cash and positions reconcile after every session
restart and recovery test passes
manual stop control test passes
```

Record observed simulator limitations. Do not infer live liquidity or alpha from paper fills.

## Order policy for paper validation

Freeze before the first paper order:

```text
order type
price construction
submission window
partial-fill handling
cancellation policy
rejection policy
restart behavior
manual stop behavior
```

No order-policy optimization based on paper outcomes.

## Exit gate

Return one of:

```text
PAPER_OPERATIONAL_PASS
PAPER_OPERATIONAL_FAIL
PAPER_INPUT_BLOCKED
```

A PASS permits only a fresh external review and user decision about a later real-money pilot.

## Compliance boundary

Before any later automated live submission, the Manager must obtain confirmation from the selected broker regarding:

```text
API availability and permissions
programmatic-trading reporting requirements
account and market-data permissions
order and rate limits
```

Do not infer compliance from a simulator or from vn.py gateway availability.

## Callback

```text
STATUS:
START_GATE_EVIDENCE:
STRATEGY_ID:
SHADOW_SESSION_COUNT:
SHADOW_REBALANCE_COUNT:
SHADOW_MISSED_RUNS:
SHADOW_IDENTITY_DRIFT_COUNT:
PAPER_REBALANCE_COUNT:
TARGET_ORDER_MISMATCH_COUNT:
ORDER_RECEIPT_MISMATCH_COUNT:
DUPLICATE_ORDER_COUNT:
RECONCILIATION_STATUS:
RESTART_RECOVERY_STATUS:
MANUAL_STOP_STATUS:
REAL_MONEY_AUTHORIZED:false
NEXT_ACTION:EXTERNAL_REVIEW_OR_CLOSE
```
