# Human-Gate Classification: Research Data Fastpath Catchup

Decision date: 2026-07-07 Asia/Shanghai
Policy: `HG-POLICY-RESEARCH-DATA-FAST-PATH-20260707`

## Classification

Research-data fast path.

Per-task HG-EXEC required: `no`, provided all work remains bounded, public/no-secret, source-local, research-only, and non-actionable.

External-audit trigger open: `no`.

## Allowed

- Bounded public/no-secret research data fetch.
- Source-local research cache/staging/report/test writes or rebuilds.
- Provider/source diagnostics.
- Manifest/count/hash evidence.
- Research-only E1, East Money, and US metadata staging diagnostics.

## Not Authorized

- `.env`, key, token, credential, auth, or secret access/output.
- Raw-data migration into `quant-proj`.
- Active schema migration.
- Readiness promotion.
- Registry activation.
- Product-route activation or replacement.
- Recommendation/advice.
- `PENDING_HUMAN_REVIEW`.
- Ticket.
- Eligibility candidate.
- Strategy candidate promotion.
- Broker/order/paper/live/auto.
- Daily signal push.

## Required Controls

- Bounded scope in handoff.
- Command transcript for network/write tasks.
- Manifest/count/hash evidence.
- Validation and forbidden overclaim scan.
- Prompt-only callback to Quant-Dispatcher.
