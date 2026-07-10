# Automated Research Factory S1 State Machine

Research-only lifecycle; no provider/network, DB/cache/data write, source-project change, strategy run, secret access, candidate/readiness/product/recommendation/trading path, broker, paper, live, or automatic execution is authorized.

`NEW -> HYPOTHESIS -> MODEL_SPEC -> IMPLEMENTATION -> BACKTEST -> VERIFICATION -> FAILURE_REVIEW -> LOCKED_OOS -> RESEARCH_EVIDENCE_ACCEPTED|RESEARCH_EVIDENCE_REJECTED`

`BLOCKED` is an orthogonal hold from any non-terminal state. It retains immutable refs, prior state, actor, timestamp, and reason; unblocking resumes only after rechecking those refs. `LOCKED_OOS` is irreversible and cannot be tuned or overwritten.

State obligations: HYPOTHESIS is falsifiable with predeclared criteria; MODEL_SPEC records versioned features/labels, horizon, PIT universe, time split, missing-data policy, and whole-label split purge; IMPLEMENTATION records immutable code/config/dependency refs and reproducibility command; BACKTEST records run ref, execution delay, corporate actions, costs/slippage, and raw metrics; VERIFICATION independently checks leakage, PIT, purge, reproducibility, metric integrity, and multiple testing; FAILURE_REVIEW records stable failure codes and disposition; LOCKED_OOS freezes OOS partition and refs; final states record reviewer, receipts, timestamp, and reason.

STATE.json owns intermediate lifecycle states and transition history. Routine final acceptance is a separate Luna/high read-only role; Sol handles only unresolved evidence conflict or insufficiency after one bounded Luna rework.

Transitions append from/to, actor, timestamp, reason, and immutable refs. Labels are wholly contained in one partition and overlapping windows purged. Universe membership is point-in-time, including delistings. Signals use a predeclared observation-to-fill delay. Corporate actions, fees, commissions, spread, market impact, and slippage are recorded; omission rejects evidence. Multiple-testing search space, trials, selection, and correction/holdout are recorded. strategy_candidate_available remains false.

Failure codes: DATA_GAP, PIT_VIOLATION, SURVIVORSHIP_BIAS, LABEL_LEAKAGE, SPLIT_PURGE_FAILURE, EXECUTION_DELAY_MISSING, CORPORATE_ACTION_MISSING, COST_SLIPPAGE_MISSING, REPRODUCIBILITY_FAILURE, MULTIPLE_TESTING_UNDISCLOSED, IMMUTABLE_REF_MISSING, METRIC_INTEGRITY, CONFIG_DRIFT, SCOPE_BOUNDARY_VIOLATION, OTHER_REQUIRES_REVIEW.
