# Handoff: A_Share_Monitor R16

Send to WSL2 downstream thread `019f387b-617e-7273-b539-161216ae3002`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/A_Share_Monitor.

Task batch: WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-strategy-discovery-batch-r16-20260707/spec.md
Human-Gate classification: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-strategy-discovery-batch-r16-20260707/human_gate.md

Verified R15 facts:
- R15 closed as CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS.
- East Money split: 77 CROSSCHECK_PASS, 121 CROSSCHECK_DATE_GAP, 2870 CROSSCHECK_MISSING_EAST_MONEY.
- 198 common symbols are overlap evidence only.
- Survivor-bias evidence improved but did not eliminate all scope limits.
- wide3068 full-frame StrategySearch remains BLOCKED_FULL_FRAME_STRATEGY_SEARCH_UNSAFE.
- wide3068 work is chunked-only.
- All strategy reruns remain rejected.
- strategy_candidate_available=false.
- market_data contract remains RESEARCH_STAGING_ONLY_NOT_DATA_CLEAR.
- No registry/readiness/product route changed.

Primary objective:
Find and evaluate strategy hypotheses using R15's research-only data and chunked execution base. Do not tune parameters to force a pass. Do not produce recommendations, tickets, eligibility candidates, readiness, product routes, or trading paths.

Assigned tasks:
1. A-WIN-R16-1 / Strategy evidence freeze before new search.
2. A-WIN-R16-2 / Factor predictive diagnostics before strategy construction.
3. A-WIN-R16-3 / Pre-registered strategy hypothesis catalog.
4. A-WIN-R16-4 / Strategy scout run on small and medium caches.
5. A-WIN-R16-5 / Wide3068 chunked diagnostic run for eligible families.
6. A-WIN-R16-6 / Trade-count rescue diagnostics.
7. A-WIN-R16-7 / Cost-aware strategy redesign diagnostics.
8. A-WIN-R16-8 / Parameter stability and cluster selection map.
9. A-WIN-R16-9 / Regime and period attribution.
10. A-WIN-R16-10 / Strategy-family rejection taxonomy v2.
11. A-WIN-R16-11 / Research-only shadow leaderboard.

Required artifacts and validation are defined in the task packet. Use the callback envelope from the task packet.

Hard requirements:
- No full-frame wide3068 StrategySearch.
- wide3068 diagnostics must be chunked-only.
- No network/provider fetch.
- No DB/cache rebuild, schema migration, readiness change, registry activation, or raw-data migration.
- No post-hoc parameter change after test results.
- WIDE_DIAGNOSTIC_ELIGIBLE is not a candidate.
- Shadow leaderboard is not a recommendation.
- If no strategy qualifies for wide diagnostics, output NO_WIDE_DIAGNOSTIC_ELIGIBLE_STRATEGY.

Completion callback required:
After finishing, send a prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope from the task packet. If thread messaging is unavailable, include the callback envelope in your final answer.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, secret handling, DB write, network ingest, schema migration, readiness change, or registry activation.
```
