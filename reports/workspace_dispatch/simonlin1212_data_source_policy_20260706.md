# simonlin1212 Data Source Policy

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-06
Status: ACTIVE_POLICY

## User Directive

Future data-source work for this quant workspace must source provider candidates from:

```text
https://github.com/simonlin1212
```

This applies to new provider discovery, provider-contract drafting, evidence-chain design, and future HG-EXEC-authorized fetch/import planning.

## Current Repository Snapshot

Observed via GitHub public repository listing on 2026-07-06:

```text
Agent-Staff
Hiring-Radar
SDesign
TradingAgents-astock
Vibe-Research
a-stock-data
astock-peg
awesome-mcp-servers
global-stock-data
globalpercent
investment-news
selloracle-mcp
```

## Primary Quant Data-Source Repositories

Use these first for provider/evidence contracts:

- `simonlin1212/a-stock-data`: A-share market data, adjusted price/corporate-action caveats, amount/turnover/market-cap, industry/concept, announcements/news, hot lists, limit-up/龙虎榜/解禁/margin/shareholder/dividend/ETF/options style evidence planning.
- `simonlin1212/global-stock-data`: US/global metadata, Yahoo/SEC/EDGAR/XBRL-style source planning, adjusted close, row-level crosscheck, provenance, freshness, source-hash contracts.

## Secondary Research-Only Repositories

These may be used only as research memo/enrichment structures unless separately promoted by a future approved task:

- `investment-news`
- `astock-peg`
- `TradingAgents-astock`
- `globalpercent`
- `Hiring-Radar`
- other simonlin1212 repositories not explicitly classified as primary provider repos

Secondary repositories must not introduce action language, recommendation language, ticket eligibility, product readiness, or runtime strategy promotion.

## Hard Routing Rules

- Do not introduce a new external data-source provider outside `github.com/simonlin1212` unless the user explicitly changes this policy.
- Provider code availability is not imported evidence.
- A repository endpoint existing is not data-clear.
- Network fetch capability is not product-read.
- LLM/news/announcement summaries are not data-clear evidence.
- Partial provenance, missing hashes, missing freshness, or missing row-level crosscheck cannot unlock readiness, ticket eligibility, product routes, or production recommendation readiness.
- Any future network ingest, DB write, schema migration, bulk ingest, provider-data persistence, readiness change, or registry activation still requires task-level `HG-EXEC` evidence and transcript.

## Boundary

This policy does not authorize recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, product-route activation, production readiness, broker/order/paper/live/auto behavior, raw-data migration into quant-proj, `.env` reads, key output, or secret handling.
