# Automated Research Factory S1 Artifact Contract

Artifacts are immutable research evidence only. Each envelope contains artifact_id, artifact_type, schema_version, created_at, owner, state, parent ids, content_sha256, immutable code/config/data/universe/split/run/review refs, and boundary flags. Every reference carries a nonempty kind, non-placeholder immutable object id, and non-placeholder full SHA-256; mutable aliases, all-one-character digest placeholders, and extra path fields are invalid. Evidence identities and reasons must contain non-whitespace text. A path never substitutes for a hash, commit, or immutable object id; corrections append a linked artifact.

Required evidence covers hypothesis/model spec; exact code/config and reproducibility command; point-in-time universe including delistings; time-ordered partitions with whole-label split purge; label horizon; execution delay; corporate actions; fees/commissions/spread/market impact/slippage; raw and aggregate metrics; multiple-testing trials and correction or untouched holdout; independent verification receipts; reviewer, timestamp, failure codes, and disposition.

Missing evidence is BLOCKED or RESEARCH_EVIDENCE_REJECTED, never a promotable warning. Accepted evidence does not imply candidate, recommendation, readiness, product, or trading status; strategy_candidate_available=false. No recommendation, readiness, product, broker, paper, live, or automatic authorization is granted. Every final envelope sets false: strategy_candidate_available, readiness_promoted, product_route_activated, recommendation_runtime_enabled, broker_api_allowed, paper_trading_allowed, live_trading_allowed, auto_execution_allowed.

RESEARCH_EVIDENCE_ACCEPTED requires an immutable review, reviewer and decision timestamp, nonempty basis, independent verification receipts, and immutable metrics, reproducibility, and multiple-testing evidence. RESEARCH_EVIDENCE_REJECTED requires an immutable review, reviewer and decision timestamp, nonempty reason, and at least one stable failure code; supporting evidence refs are retained when present. BLOCKED retains prior state, actor, timestamp, reason, and immutable review ref.

This contract authorizes no recommendation, no readiness promotion, no product-route activation, no broker access, no paper trading, no live trading, and no automatic execution.

STATE.json owns intermediate lifecycle states; this card is a terminal/hold summary. Routine final acceptance is separate Luna/high read-only. Sol handles only unresolved evidence conflict or insufficiency after one bounded Luna rework.

Family66 replay/pilot is deferred until the S1 automated gate is green and separate Luna/high acceptance is green. No external side effect is authorized. Retain rejected and blocked records with immutable refs.
