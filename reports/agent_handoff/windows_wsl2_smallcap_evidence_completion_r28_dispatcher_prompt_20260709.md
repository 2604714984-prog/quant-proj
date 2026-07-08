# Dispatcher Prompt - R28 SmallCap Evidence Completion

Batch: `WINDOWS_WSL2_SMALLCAP_EVIDENCE_COMPLETION_R28_20260709`

Read:

- `tasks/in_progress/windows-wsl2-smallcap-evidence-completion-r28-20260709/spec.md`
- R27 result summary and closeout.
- A_Share_Monitor R27 SmallCap artifacts.
- R26 SmallCap evidence package.

## Execute

Run R28 as an ordinary research-only evidence-completion batch.

## Objective

Complete the missing evidence that blocked SmallCap Low Turnover from local research probe reconsideration:

1. Preserve row-level pre-trade signal matrix.
2. Preserve market-cap universe membership snapshot.
3. Rerun full leakage/timing audit.
4. Rebuild metrics from the preserved matrix.
5. Decide whether SmallCap becomes local research probe eligible or remains blocked.

## Priority

- SmallCap evidence completion is the primary task.
- US30W remote/mirror preservation is optional and must not delay SmallCap.
- pass77 and ETF must not be rerun without changed accepted evidence.

## Boundary

Research-only. No actionable output, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto path, active registry/schema change, credential output, or full-frame wide3068.

## Callback

Return the callback envelope required in the task packet, including SmallCap row-level evidence status, leakage/timing audit result, robustness status, local probe prequalification result, US30W preservation status, candidate availability, boundary result, fixes required, and next source action.
