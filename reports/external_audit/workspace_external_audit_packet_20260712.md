# Quant Research Workspace External Audit Packet

Date: 2026-07-12
Owner: `2604714984-prog`
Audit mode: GitHub file and history review
System boundary: research-only; no recommendation, candidate promotion, readiness activation, broker, paper, live, or automatic trading

## Executive summary

This workspace is a multi-repository quantitative-research system for A-share and US-market data engineering, preregistration, backtesting, statistical validation, evidence lineage, and controller-enforced acceptance. It is not a trading product.

The current canonical conclusions are deliberately negative and fail-closed:

- `NO_CURRENT_STRICTLY_VALIDATED_A_SHARE_STRATEGY_EVIDENCE`
- `NO_CURRENT_STRICTLY_VALIDATED_US30W_FOUR_ETF_STRATEGY_EVIDENCE`
- `strategy_candidate_available=false`

These conclusions are not placeholders. They are the accepted result of methodology-correct recomputation, prospective preregistration, multiplicity correction, source qualification, point-in-time checks, and independent acceptance. Negative and blocked outcomes are retained as valid research evidence.

## What is being delivered

GitHub now contains the review-relevant source code, tests, schemas, task/controller contracts, research reports, hashes, and reproducibility instructions from the WSL workspace. Large or sensitive runtime material is intentionally excluded:

- credentials, tokens, `.env` files, and private authorization/HG records;
- raw DuckDB/SQLite databases, Parquet caches, provider payloads, and licensed data;
- virtual environments, logs, temporary DuckDB spill files, browser/session state, and build caches;
- identifiers held only in private manifests;
- files exceeding GitHub's practical limits.

These exclusions are part of the security and provenance design, not missing audit evidence. The repository manifest identifies the exact GitHub refs used for review.

## Architecture and repository responsibilities

| Repository | Responsibility | Audit role |
|---|---|---|
| `quant-proj` | Controller contracts, task packets, human gates, routing policy, automated-research-factory state machine | Entry point for this audit |
| `strategy_work` | Preregistration, methodology, statistical validation, adjudication, research lineage | Canonical strategy evidence |
| `A_Share_Monitor` | A-share ingestion, feature engineering, guarded backtest/data utilities | A-share implementation evidence |
| `US_Stock_Monitor` | US data contracts, SEC/PIT utilities, guarded research framework | US implementation evidence |
| `us_stock_30w` | Fixed-capital US strategy specifications and validation artifacts | US30W evidence |
| `market_data` | Source registry, metadata contracts, central warehouse tooling | Shared data engineering |
| `quant_research_lab` | Isolated experimental and statistical research | Non-canonical sandbox |
| `STRATEGY_VAULT` | Boundary-hardened archive of strategy material | Private archive |
| `qts` | Frozen prototype retained for selective salvage | Private archived reference |
| `quant` | Frozen legacy system | Private archived reference |
| `RD-Agent`, `FinGPT` | Forked upstream projects containing isolated local hardening work | Non-canonical reference forks |
| `global-stock-data` | Unmodified external reference | Upstream only; no local claim |
| `quant-project-shared-reports` | Human-readable cross-project reports | Private reviewer briefing |

## Governance model

The controller uses explicit role separation:

- Sol handles hard research decomposition and evidence conflicts.
- Luna handles bounded implementation and routine independent acceptance.
- Deterministic tests run before human/model acceptance.
- Provider/network/database actions require a task-specific durable authorization.
- Missing evidence becomes `BLOCKED` or `RESEARCH_EVIDENCE_REJECTED`; it is never silently promoted.

The core contracts are under `runbooks/automated_research_factory/`, including the artifact contract, state machine, and strategy-card schema. Evidence identities are expected to pin code, configuration, data, universe, split plan, and result hashes.

## Recent work relevant to this audit

### Repository-wide audit and remediation

A workspace-wide static audit, risk-based semantic review, and dynamic reproduction pass identified and then drove fixes for:

- secret-like paths and unsafe serialization;
- point-in-time leakage and revision handling;
- missing whole-label purge and embargo controls;
- hard-coded workstation paths;
- dirty-worktree execution risk;
- database overwrite and schema drift risk;
- retired trading/runtime entry points;
- CI dependency and portability gaps.

Dedicated security/integrity branches for the first-party repositories are listed in the machine-readable manifest. External upstream repositories were never pushed to their upstream owners; local changes are preserved only in owner-controlled forks.

### A-share evidence

- Families 40-65 remain superseded pending methodology-correct recomputation.
- Family 66 was rejected: 16/48 gates passed and 44/1,604 cross-split signal dates were purged.
- Family 67 was preregistered before outcomes and rejected: 6/23 gates passed.
- Family 68 has no strategy result. Its methodology amendment and data engineering are useful, but it remains blocked by primary-document tie-out, full-universe PIT identity, sample-size requirements, and future holdout/forward intervals.
- A bounded BaoStock engineering smoke produced 30 bundles, 180 source-document records, and 1,200 normalized facts. It remains secondary structured evidence; primary-document tie-out is 0/30.

### US30W four-strategy evidence

US31, US36, US41, and US46 are retrospective negative evidence:

- 0/8 Holm-adjusted comparator tests passed;
- 0/4 interval gates passed;
- 2016-2025 remains discovery-only and cannot rescue the failed 2005-2015 interval;
- later corporate-action data improvements may improve infrastructure but cannot reopen these four specifications.

Any future derivative must have a genuinely new economic hypothesis, a new lineage identifier, and a new outcome-blind preregistration.

### Data/source qualification

Bounded route studies were single-use and fail-closed. Official source surfaces were only partially qualified. Corporate-action `available_at` remains incomplete for the strict US30W contract. The third-party TuShare replay/token experiment is suspended and is not qualified evidence; no accepted provider ingestion or database write resulted from it.

## Canonical evidence entry points

- Strategy adjudication: `strategy_work` branch `codex/strategy-lineage-final-evidence-20260712`, commit `b95323d428ddcf275334b1b7d6d8b415d66818f9`.
- External-audit evidence snapshot: `strategy_work` Draft PR #10.
- A-share external-audit implementation snapshot: `A_Share_Monitor` Draft PR #6.
- Controller factory contracts: `quant-proj` branch `codex/sol-luna-collaboration-routing-20260710`, commit `13b13a3757f446f97b2b9e3d8e39c98ca247a4b5`.
- Repository-wide manifest: `workspace_external_audit_repository_manifest_20260712.json` beside this packet.

## Reproduction and validation expectations

Reviewers should begin with the repository manifest, then inspect the two Draft PRs and the named evidence branches. Each first-party repository contains its own tests and CI workflow. Important validation classes include:

- Python compilation, Ruff, focused/full Pytest;
- JSON parsing and schema invariants;
- SHA-256 sidecar verification;
- `git diff --check`;
- negative boundary scans for secret/trading/promotion language;
- exact remote-ref verification after publication.

Tests that require a separately pinned sibling repository or external research engine explicitly skip when that artifact is absent in an isolated GitHub runner; they execute normally when the pinned artifact is present. A skip is not treated as positive strategy evidence.

## Known limitations and residual risks

1. Several repositories are private. The auditor must be added as a collaborator before GitHub-only review can cover them.
2. Runtime databases and provider payloads are not uploaded. Their identities are represented by manifests and hashes, but raw-data inspection requires a separately approved secure data-room process.
3. Some historical research artifacts predate stable global trial identifiers and complete code/config/data/output hashes. The methodology therefore carries explicit multiplicity debt or remains blocked.
4. The central warehouse is infrastructure, not a substitute for PIT primary-document evidence.
5. `qts` and `quant` are archived and should be reviewed as historical references, not current engines.
6. Forked `RD-Agent` and `FinGPT` branches are local hardening evidence, not endorsements of upstream research claims.

## Questions for the external reviewer

Please focus on:

1. Whether the fail-closed evidence state machine prevents unsupported promotion.
2. Whether PIT, revision, corporate-action, whole-label purge, embargo, and survivorship controls are sufficient and correctly tested.
3. Whether global and within-family multiplicity controls are conservative enough given incomplete legacy trial identity.
4. Whether the separation among controller, executor, acceptance, provider authorization, and strategy evidence is enforceable in code and CI.
5. Whether any uploaded source/report still exposes credentials, private identifiers, licensed payloads, or a hidden trading path.
6. Which blocked data dependencies can be resolved using independently auditable official sources without weakening the frozen methodology.

## Audit boundary

This packet requests a research-process, code, test, provenance, and evidence-lineage review. It does not request investment advice, strategy promotion, portfolio construction, broker integration, or execution authorization.
