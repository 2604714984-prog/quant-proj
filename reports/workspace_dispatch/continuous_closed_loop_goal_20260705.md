# Quant-Dispatcher Continuous Closed Loop Goal

Created: 2026-07-05T05:31:00Z
Owner: Quant-Dispatcher
Status: ACTIVE

## Permanent Closed Loop Process

This section is permanent. Do not delete it when updating the current task.

Quant-Dispatcher must continuously run the following loop:

1. Import the latest user task list, ChatGPT external-audit verdict, or downstream acceptance result.
2. Classify whether it is an ordinary research/data/strategy batch or an external-audit-triggering boundary change.
3. Dispatch ordinary implementation/research tasks to fixed downstream agents and projects:
   - A_Share_Monitor fixed Codex-Dev thread
   - US_Stock_Monitor fixed Codex-Dev thread
   - market_data fixed Codex-Dev thread
   - strategy_work fixed Codex-Dev thread when available, creating and recording one if missing
   - Reasonix-DB fixed session for DB/data advisory sidecars
   - Reasonix-Strategy fixed session for strategy/research advisory sidecars
4. Quant-Dispatcher must not directly implement source-project work unless the user explicitly asks or no downstream agent is available.
5. Collect downstream outputs only as appropriate:
   - CODEX_ACCEPTANCE
   - DATA_REPORT
   - STRATEGY_REPORT
   - REASONIX_DRAFT
   Downstream Codex-Dev threads must send completion callbacks to the active dispatcher thread. On the Windows WSL2 host, the active dispatcher thread is `019f3830-4b44-7a83-944d-247a0d4dc169`. If direct thread messaging is unavailable, downstream threads must include the callback envelope in their final answer.
6. Record controller-layer evidence in quant-proj, including dispatch summaries, result summaries, acceptance records, and board updates.
7. Commit and push controller records after each meaningful dispatch/result/closeout step.
8. Updated 2026-07-07: external-audit operation is user-operated through GitHub / GitHub connector. Quant-Dispatcher must not drive Chrome/GPT Pro itself. When there is no active user task list or downstream result to process, prepare current controller status and GitHub refs/paths if useful and ask the user for the next pasted task list, verdict, or external-audit result.
9. Use controller external-audit classification immediately when:
   - the user explicitly brings an external-audit verdict or asks for packet preparation,
   - a real external-audit trigger opens, including ticket, product route, production readiness, broker/order/paper/live/auto, raw-data migration, secret handling, or Human-Gate model change, or
   - the dispatcher has no active task and needs the next user-provided task batch to continue the closed loop.
10. When external audit is requested or needed for loop continuation, Quant-Dispatcher may prepare controller records, packet paths, and GitHub refs when asked, but the user performs the GitHub / GitHub connector audit submission. Quant-Dispatcher records the pasted verdict and next-task instructions in quant-proj, commit/pushes, then continues the loop with the next task batch.
11. When waiting for downstream agents or user-provided GPT Pro results, wait in coarse intervals rather than polling tightly.

## Permanent Boundary Rules

These rules are permanent. Do not delete them when updating the current task.

- Ordinary research/data/strategy batches do not get controller external-audit packets.
- No recommendation, ticket emission, product-route activation, production readiness, broker/order path, paper trading, live trading, or auto execution is authorized by this loop.
- DB write, schema migration, bulk ingest, network ingest, readiness change, and registry activation require task-level HG-EXEC evidence and transcript before execution.
- Reasonix outputs remain draft/advisory unless Codex-Dev implements and validates them.
- Preserve blocked and non-actionable states honestly; do not convert blocked research candidates into recommendations.
- For cross-thread Codex sends, send prompt content only. Do not pass model or thinking overrides.
- Reasonix sidecars use fixed sessions with model deepseek-v4-pro and effort high.
- Reasonix fixed sessions are persistent CLI-like conversations. Keep `quant-reasonix-db`, `quant-reasonix-strategy`, and `quant-reasonix-advisory` open and reuse the same live session when possible; do not close or recreate them after each task.
- Future data-source work must source provider candidates from `https://github.com/simonlin1212` unless the user explicitly changes this policy. This source restriction does not authorize network ingest, DB writes, data-clear promotion, readiness changes, product routes, tickets, recommendations, or broker/order/paper/live/auto behavior.
- Downstream Codex-Dev completion callbacks are required for future dispatches. Callback protocol record: `reports/workspace_dispatch/downstream_completion_callback_protocol_20260706.md`.

## Mutable Current Task

Current task batch: WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707 dispatched

Objective:

Continue as Quant-Dispatcher only. The R17 GitHub connector external audit returned `VERIFIED_ACCEPT_WITH_WARNINGS` and issued `WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707`. R18 is ordinary research-only strategy hypothesis expansion. It is dispatched to A_Share_Monitor for broad strategy-family expansion, market_data for inactive-boundary/manifest/overclaim support, and strategy_work for interpretation/final sync. R18 must not activate market_data routes, create recommendation/ticket/eligibility/candidate/readiness/product routes/trading paths, run full-frame wide3068, use test results to select parameters, use the shadow leaderboard as actionable ranking, use ML score as recommendation, or perform any unapproved network/DB/secret action.

- External-audit trigger opened: `no`.
- Current dispatcher thread: `019f3830-4b44-7a83-944d-247a0d4dc169`.
- GitHub / GitHub connector external-audit operation remains user-operated; Quant-Dispatcher receives pasted task lists, verdicts, and downstream acceptances.

Do not create a controller/gate loop unless a real boundary trigger opens. The new authorization permits bounded install/network/write/route-prep work only through task-level HG records. It still does not authorize local LLM/Qwen deployment, recommendation, production recommendation readiness, broker/order/paper/live/auto, secret access/output, raw-data migration into quant-proj, transformer/RL/complex ensemble start, test-performance model selection, or weak-result candidate promotion.

GPU power policy: the earlier RTX 5090 `GPU_POWER_LIMIT_WATTS=400` rule is superseded by `reports/human_gate/windows_wsl2_5090_gpu_power_cap_revocation_20260707.md`. R17 may continue under host/driver default GPU power policy while reporting observed power-limit and power-draw telemetry. Privileged power-limit changes still require separate user direction.

Current intake and controller records:

- R13 interim GPT Pro result: `reports/agent_handoff/data_strategy_batch_r13_interim_external_audit_result_20260706.md`
- R13C intake: `reports/workspace_dispatch/data_strategy_batch_r13c_20260706_intake.md`
- R13C task packet: `tasks/in_progress/data-strategy-batch-r13c-20260706/spec.md`
- R13C dispatch summary: `reports/workspace_dispatch/data_strategy_batch_r13c_20260706_dispatch_summary.md`
- Windows WSL2 dispatcher role acceptance: `reports/workspace_dispatch/windows_wsl2_dispatcher_role_acceptance_20260707.md`
- Windows WSL2 registry refresh: `reports/workspace_status/windows_wsl2_registry_refresh_20260707.md`
- Runtime clarification and DS review: `reports/workspace_dispatch/dispatcher_runtime_clarification_and_ds_review_20260707.md`
- R15 original command: `tasks/inbox/20260707-windows-wsl2-data-strategy-and-base-batch-r15-external-audit-command.md`
- R15 intake: `reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_intake.md`
- R15 task packet: `tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/spec.md`
- R15 dispatch summary: `reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_dispatch_summary.md`
- Refreshed registry: `registry/projects.yaml`
- GitHub / GitHub connector audit operation after 2026-07-07 is user-operated; Quant-Dispatcher receives pasted verdicts/task lists and does not operate Chrome/GPT Pro directly.
- Current classification: ordinary research-only data/strategy/data-base batch
- External-audit trigger opened by R15 intake: `no`
- R15 external-audit result: `reports/agent_handoff/windows_wsl2_data_strategy_batch_r15_external_audit_result_20260707.md`
- R16 intake: `reports/workspace_dispatch/windows_wsl2_strategy_discovery_batch_r16_20260707_intake.md`
- R16 task packet: `tasks/in_progress/windows-wsl2-strategy-discovery-batch-r16-20260707/spec.md`
- R16 dispatch summary: `reports/workspace_dispatch/windows_wsl2_strategy_discovery_batch_r16_20260707_dispatch_summary.md`
- R16 classification: ordinary research-only strategy discovery batch
- External-audit trigger opened by R16 intake: `no`

Final R15 source states:

- `A_Share_Monitor`: thread `019f387b-617e-7273-b539-161216ae3002`, completed `A-WIN-R15-1` through `A-WIN-R15-15`, commit `518081d0e110a0518f5c31adc19722e42a6b94a7`, pushed to `origin/codex/harden-a-share-research-pipeline`.
- `market_data`: thread `019f387b-e763-7c01-ae3d-6be552cdb6dc`, completed `MD-WIN-R15-1` through `MD-WIN-R15-4`, commit `fa014470b39b07ae342996d629f1b2356138111f`, pushed to `origin/main`.
- `strategy_work`: thread `019f3881-5293-74a1-8535-814bd83c8681`, completed `SW-WIN-R15-1` through `SW-WIN-R15-3`, final-sync commit `bc70517bb5740105989f404510e7b815644d3bf6`, pushed to `origin/main`.
- `US_Stock_Monitor`: `019f387b-a161-7ad0-8678-f03a099612ba`, ready but not assigned because the R15 US branch was optional and not explicitly requested.
- Future downstream handoffs must use these WSL2-visible threads and the active dispatcher callback target, or final-answer callback envelopes if thread sending is unavailable.

Final R16 source states:

- `A_Share_Monitor`: thread `019f387b-617e-7273-b539-161216ae3002`, completed `A-WIN-R16-1` through `A-WIN-R16-11`, commit `f5805d9cede3efb114fa01de810cf27a97ef7a6f`, pushed to `origin/codex/harden-a-share-research-pipeline`.
- `market_data`: thread `019f387b-e763-7c01-ae3d-6be552cdb6dc`, completed `MD-WIN-R16-1` through `MD-WIN-R16-3`, commit `3c6c95172517de6fb908d73defa72c9fa1f28f85`, pushed to `origin/main`.
- `strategy_work`: thread `019f3881-5293-74a1-8535-814bd83c8681`, completed `SW-WIN-R16-1` through `SW-WIN-R16-3`, final-sync commit `094af646175131bc60b0c9aabc7c785cba0c13a6`, pushed to `origin/main`.
- `US_Stock_Monitor`: thread `019f387b-a161-7ad0-8678-f03a099612ba`, ready but not assigned because the R16 US branch was optional and not explicitly requested.
- R16 result summary: `reports/workspace_dispatch/windows_wsl2_strategy_discovery_batch_r16_20260707_result_summary.md`
- R16 closeout: `reports/workspace_dispatch/windows_wsl2_strategy_discovery_batch_r16_20260707_closeout.md`
- GPU Phase 2 intake: `reports/workspace_dispatch/windows_wsl2_5090_gpu_numeric_diagnostics_phase2_20260707_intake.md`
- GPU Phase 2 task packet: `tasks/in_progress/windows-wsl2-5090-gpu-numeric-diagnostics-phase2-20260707/spec.md`
- GPU Phase 2 dispatch summary: `reports/workspace_dispatch/windows_wsl2_5090_gpu_numeric_diagnostics_phase2_20260707_dispatch_summary.md`
- GPU Phase 2 A-share callback: `reports/workspace_dispatch/windows_wsl2_5090_gpu_numeric_diagnostics_phase2_20260707_a_share_callback.md`
- GPU Phase 2 result summary: `reports/workspace_dispatch/windows_wsl2_5090_gpu_numeric_diagnostics_phase2_20260707_result_summary.md`
- GPU Phase 2 closeout: `reports/workspace_dispatch/windows_wsl2_5090_gpu_numeric_diagnostics_phase2_20260707_closeout.md`
- GPU Phase 2 classification: ordinary research-only numeric diagnostics batch
- External-audit trigger opened by GPU Phase 2 intake: `no`
- GPU Phase 3 intake: `reports/workspace_dispatch/windows_wsl2_5090_gpu_ml_signal_research_phase3_20260707_intake.md`
- GPU Phase 3 task packet: `tasks/in_progress/windows-wsl2-5090-gpu-ml-signal-research-phase3-20260707/spec.md`
- GPU Phase 3 dispatch summary: `reports/workspace_dispatch/windows_wsl2_5090_gpu_ml_signal_research_phase3_20260707_dispatch_summary.md`
- GPU Phase 3 result summary: `reports/workspace_dispatch/windows_wsl2_5090_gpu_ml_signal_research_phase3_20260707_result_summary.md`
- GPU Phase 3 closeout: `reports/workspace_dispatch/windows_wsl2_5090_gpu_ml_signal_research_phase3_20260707_closeout.md`
- GPU Phase 3 classification: ordinary research-only ML signal research batch if environment preconditions are met
- External-audit trigger opened by GPU Phase 3 intake: `no`
- Broad Human-Gate authorization: `reports/human_gate/windows_wsl2_broad_authorization_20260707.md`
- Broad controlled advancement task packet: `tasks/in_progress/windows-wsl2-authorized-controlled-advancement-20260707/spec.md`
- Broad controlled advancement dispatch summary: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_dispatch_summary.md`
- Broad controlled advancement result summary: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_result_summary.md`
- RTX 5090 power cap policy: `reports/human_gate/windows_wsl2_5090_gpu_power_cap_policy_20260707.md`
- Post-R15 progress summary: `reports/workspace_dispatch/windows_wsl2_post_r15_development_progress_summary_20260707.md`
- Post-R15 user-requested external audit packet: `reports/agent_handoff/windows_wsl2_post_r15_development_external_audit_packet_20260707.md`
- Post-R15 external-audit result: `reports/agent_handoff/windows_wsl2_post_r15_development_external_audit_result_20260707.md`
- R17 intake: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_intake.md`
- R17 task packet: `tasks/in_progress/windows-wsl2-strategy-signal-mining-batch-r17-20260707/spec.md`
- R17 dispatch summary: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_dispatch_summary.md`
- R17 A_Share_Monitor callback: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_a_share_callback.md`
- R17 market_data callback: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_market_data_callback.md`
- R17 result summary: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_result_summary.md`
- R17 strategy_work callback: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_strategy_work_callback.md`
- R17 closeout: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_closeout.md`
- R17 external-audit packet: `reports/agent_handoff/windows_wsl2_strategy_signal_mining_batch_r17_external_audit_packet_20260707.md`
- R17 external-audit prompt: `reports/agent_handoff/windows_wsl2_strategy_signal_mining_batch_r17_external_audit_prompt_20260707.md`
- R17 external-audit result: `reports/agent_handoff/windows_wsl2_strategy_signal_mining_batch_r17_external_audit_result_20260707.md`
- R18 intake: `reports/workspace_dispatch/windows_wsl2_strategy_hypothesis_expansion_batch_r18_20260707_intake.md`
- R18 task packet: `tasks/in_progress/windows-wsl2-strategy-hypothesis-expansion-batch-r18-20260707/spec.md`
- R18 dispatch summary: `reports/workspace_dispatch/windows_wsl2_strategy_hypothesis_expansion_batch_r18_20260707_dispatch_summary.md`
- R17 A-share resume handoff after power-policy revocation: `tasks/in_progress/windows-wsl2-strategy-signal-mining-batch-r17-20260707/handoff_a_share_resume_after_power_policy_revocation.md`
- RTX 5090 power cap revocation: `reports/human_gate/windows_wsl2_5090_gpu_power_cap_revocation_20260707.md`
- A_Share_Monitor callback: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_a_share_callback.md`
- A_Share_Monitor push callback: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_a_share_push_callback.md`
- US_Stock_Monitor callback: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_us_callback.md`
- US_Stock_Monitor push callback: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_us_push_callback.md`
- market_data callback: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_market_data_callback.md`
- market_data Codex-Audit callback: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_market_data_codex_audit_callback.md`
- market_data push callback: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_market_data_push_callback.md`
- market_data external audit packet: `reports/agent_handoff/windows_wsl2_authorized_controlled_advancement_market_data_external_audit_packet_20260707.md`
- Task-level HG records: `HG-EXEC-TASK-GPU-ENV-PHASE2-PHASE3-20260707`, `HG-EXEC-TASK-A-EAST-MONEY-COVERAGE-20260707`, `HG-EXEC-TASK-US-METADATA-REPAIR-20260707`, `HG-EXEC-TASK-MD-PRODUCT-ROUTE-PREP-20260707`

GPU Phase 2 dispatch state:

- `A_Share_Monitor`: thread `019f387b-617e-7273-b539-161216ae3002`, assigned `GPU-P2-1` through `GPU-P2-9`, returned `BLOCKED_CUDA_PYTHON_UNAVAILABLE`.
- `market_data`, `strategy_work`, and `US_Stock_Monitor` are not assigned in this batch.
- GPU visible through WSL `nvidia-smi`: NVIDIA GeForce RTX 5090, driver `610.47`, reported memory `32607 MiB`.
- Python CUDA numeric libraries unavailable in A_Share_Monitor `.venv`: `torch`, `cupy`, `numba`, `jax`, `jaxlib`, `tensorflow`, `pycuda`, and `triton` all absent per callback.

GPU Phase 3 dispatch state:

- `A_Share_Monitor`: intended owner thread `019f387b-617e-7273-b539-161216ae3002`; handoff prepared but not sent because environment precondition remains unmet.
- Fresh non-mutating check confirms GPU visible through WSL `nvidia-smi`: NVIDIA GeForce RTX 5090, driver `610.47`, reported memory `32607 MiB`.
- Python CUDA/ML libraries unavailable in A_Share_Monitor `.venv`: `torch`, `cupy`, `numba`, `jax`, `jaxlib`, `tensorflow`, `pycuda`, `triton`, `xgboost`, `sklearn`, and `cuml` absent.

Authorized controlled advancement dispatch state:

- `A_Share_Monitor`: thread `019f387b-617e-7273-b539-161216ae3002`, completed GPU environment enablement plus Phase 2/3 resume and A-share East Money bounded probe at pushed commit `a1d57f55a94382e20bfd4a184ad21c42bf9bde37`.
- `US_Stock_Monitor`: thread `019f387b-a161-7ad0-8678-f03a099612ba`, completed US metadata repair / bounded US staging at pushed commit `9264773852daf46b4abf09f347f571c5f118d634`.
- `market_data`: thread `019f387b-e763-7c01-ae3d-6be552cdb6dc`, completed product-read route/readiness preparation at pushed commit `64840aa60e520cb7f0aa17078b941e0c4bc1586e`; Codex-Audit PASS; user-operated GitHub / GitHub connector external audit verdict pending before any activation.

R13C / WSL2 hard execution rule:

- Do not run 3068-symbol full-frame pandas strategy search.
- Add fail-closed guard for unsafe full-frame `StrategySearch.run()`.
- Implement chunked feature reading and chunked backtest state handling.
- Prove full-frame vs chunked equivalence on small cache before wide3068 dry run.

Next dispatcher actions:

1. Collect A_Share_Monitor R18 callback.
2. Collect market_data R18 callback.
3. Collect strategy_work R18 final sync after source callbacks.
4. Prepare R18 result summary and closeout after all downstream callbacks are accepted.
5. Keep market_data product-route activation blocked unless a separate activation task and audit verdict are provided.
