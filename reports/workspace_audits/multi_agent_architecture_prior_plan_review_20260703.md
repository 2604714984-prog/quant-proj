# Prior Multi-Agent Architecture Plan Review

Date: 2026-07-03
Reviewed file: `/Users/rongyuxu/Desktop/multi_agent_architecture_plan.md`
Current workspace: `/Users/rongyuxu/Desktop/quant proj`

## Summary

The desktop file is a prior high-level multi-agent architecture proposal. It is useful as a design reference, but it should not be implemented directly without revision.

Recommended treatment:

- Keep it as a prior architecture concept.
- Promote selected ideas into the new `quant proj` controller workspace.
- Do not deploy the ChatGPT browser bridge or shared `~/.agents/` automation until the simpler controller-workspace workflow is stable and externally reviewed.

## Useful Ideas To Preserve

1. Shared coordination layer above existing repos.
2. Project registry for A-share and US systems.
3. Explicit agent role declarations.
4. Task modes such as serial pipeline, debate, and adversarial review.
5. A strict distinction between implementation, advisory review, process review, and external audit.
6. Incremental rollout instead of modifying existing repos immediately.

## Items That Need Revision

### 1. Tool Names And Assumptions Are Stale

The old plan refers to:

- `Deep Code CLI`
- `deepcode -p`
- `GPT-5.5 Pro`
- `DeepSeek V4 Pro`
- `Claude Code + GLM 5.2`

Current observed local tools are:

- `codex-cli 0.142.5`
- `reasonix 0.53.2`

The current plan should use Reasonix as the DeepSeek-backed advisory CLI unless a separate Deep Code CLI is confirmed and intentionally installed.

### 2. Project Stage Facts Are Outdated

The old plan describes:

- A-share as Phase 3B/3C with 78 tests.
- US as Stage US-7e.

Current observed state is later and different:

- A-share has A10/P3.x, A-STRAT-1, DB-2-related local data expansion, and dirty local-market work.
- US is on `codex/duckdb-provider` with US-13 / DuckDB-provider work and dirty files.
- `market_data` and `strategy_work` are now relevant and should be in the registry.

### 3. Browser Automation Is High Risk For Phase 1

The old plan proposes Playwright automation against ChatGPT Pro web UI.

This should be deferred because:

- web UI selectors and login state can drift;
- browser automation may fail silently;
- it creates more moving parts than the current system needs;
- external audit packet handling should remain explicit until the controller workflow is proven.

Recommended replacement:

- Start with file-based handoffs and manual ChatGPT external audit.
- Add browser automation only as a later optional stage after audit.

### 4. `~/.agents/` Is Too Broad For Initial Rollout

The old plan centralizes work under `~/.agents/`.

The current safer location is:

- `/Users/rongyuxu/Desktop/quant proj`

Reason:

- project-specific and visible to the user;
- easier to audit;
- easier to keep raw-data exclusions local;
- less likely to become an invisible global dependency.

### 5. "Full Lifecycle Including Live Execution" Must Be Reframed

The old plan includes future modes for live execution code, stop-loss logic, position management, and adversarial review.

Current project boundary:

- no broker;
- no order routing;
- no auto execution;
- no live trading;
- no real buy/sell recommendations.

Recommendation:

- Keep adversarial mode only as a safety-review pattern.
- Do not create live-execution implementation tasks.
- If a future trading-related stage is ever opened, require a separate formal authorization and external audit.

## Mapping To Current Workspace Plan

| Prior plan idea | Current decision |
|---|---|
| `~/.agents/` shared workspace | Use `/Users/rongyuxu/Desktop/quant proj` controller workspace first |
| Deep Code reviewer | Use Reasonix-Advisory unless Deep Code is separately confirmed |
| ChatGPT browser bridge | Defer; manual external audit or explicit Codex thread handoff first |
| Multi-mode tasks | Keep as conceptual modes, but start with serial pipeline and read-only review |
| Project registry | Keep; implemented as `registry/projects.yaml` |
| Existing repos untouched | Keep; no direct physical migration yet |
| AGENTS.md append in each repo | Defer until workspace plan passes review |
| Auto task claiming | Defer; start with explicit human/Codex-driven stage tasks |

## Recommended Next Step

Update the external audit packet to mention the prior desktop plan as a reviewed predecessor, then ask external review to decide:

- whether to keep the old plan as reference only;
- which parts should be folded into `quant proj`;
- whether browser automation should remain out of scope for M0/M1.

## Verdict

Status: REFERENCE_ONLY_UNTIL_REVISED

The prior plan is directionally aligned with multi-agent coordination, but too automation-heavy and stale for direct implementation. The current controller-workspace plan is the safer execution path.

