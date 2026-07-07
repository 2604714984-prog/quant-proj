# Paste Prompt - R17 External Audit

Use this prompt in the user-operated GitHub / GitHub connector external-audit conversation.

```text
Please perform a GitHub-connector external audit of the closed R17 batch:

WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707

Do not rely on this summary alone. Read the GitHub files and commits listed in the controller audit packet:

https://github.com/2604714984-prog/quant-proj/blob/main/reports/agent_handoff/windows_wsl2_strategy_signal_mining_batch_r17_external_audit_packet_20260707.md

Primary question:
Can R17 be accepted as CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS, with EXTERNAL_AUDIT_TRIGGER_OPEN=no and FIXES_REQUIRED=none before the next ordinary research-only task batch?

Please verify especially:
- strategy_candidate_available=false.
- R17 found no wide-prequalified strategy rows.
- Wide3068 result is NO_R17_WIDE_PROBE_ELIGIBLE_STRATEGY.
- A_Share_Monitor did not run full-frame wide3068 and did not run chunked wide3068 because no family qualified.
- medium_overlap_198_not_pass / low_vol_20 is only a positive diagnostic factor, not a candidate/readiness/recommendation signal.
- R16 factor labels remain WEAK=5, UNSTABLE=8, POSITIVE=1.
- East Money split remains 77 CROSSCHECK_PASS / 121 CROSSCHECK_DATE_GAP / 2870 CROSSCHECK_MISSING_EAST_MONEY.
- market_data product-route prep remains inactive and separated; no registry/readiness/product route changed.
- RTX 5090 400W cap revocation is power-policy only and did not authorize broader scope.
- No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, secret exposure, DB write, network ingest, schema migration, registry activation, market_data activation, or ranked actionable list was created.

Return:

VERDICT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
ACCEPTED_SCOPE:
REJECTED_OR_BLOCKED_SCOPE:
BOUNDARY_RESULT:
NEXT_TASKS:
```
