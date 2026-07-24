# 当前外审：Round 6

> 当前有效外审报告：`docs/external_audit_round6_938aada_20260724.md`  
> 机器可读台账：`docs/external_audit_round6_ledger_938aada_20260724.json`

## 冻结边界

- 被审代码：`938aada03f819d98cbf7c9ac627a8c77326ed312`
- Base：`v2-main@31329dbfd7b9bb1c184a13ee7fe2e60bd0a6ba14`
- CI merge ref：`7d076d51eb70cdbcfd41a1360fd4f14c3fb958df`
- GitHub Actions run：`30062113832` — success

本文件及 Round 6 报告/台账的后续文档 commit 不属于被审代码范围。

## 当前裁决

```text
external_audit_verdict=REQUEST_CHANGES_FOCUSED

repository_boundary=PASS
single_canonical_writer=PASS
runtime_architecture_lightweight=PASS
fail_closed_default=PASS

exploratory_research=CONDITIONAL_PASS
validated_historical_research=FAIL
fast_result_pipeline=FAIL
capital_grade_research_process=false

code_remediation_complete=false
only_external_evidence_remaining=false

strategy_candidate_available=false
recommendation_authorized=false
paper_trading_authorized=false
live_trading_authorized=false
automatic_execution_authorized=false
```

## 当前 P0

1. `R6-001`：收益区间由上一期持仓产生，却归给本期 target weights。
2. `R6-002`：历史 TrialConfig 未绑定实际 definition、feature snapshot 和 DatasetManifest。
3. `R6-003`：历史阶段的成本 SHA 可与实际零成本/不同 capacity、slippage 脱钩。
4. `R6-004`：feature 和 label 共用 raw bytes，字段级 PIT provenance 仍可被绕过。

这四项均已通过独立最小复现触发。关闭后冻结新代码 head，再做聚焦复审。

## 已接受的整改

- Prospective tree 已恢复单主线、单 writer 和只读 evidence boundary；
- Stage signal/execution 日期关系已修复；
- ControlledStageReceipt、FinalRun、Family/Trial、完整 ledger、纯转换和 horizon statistic 均有实质改进；
- CI wheel artifact 已下载并独立验证；
- 不需要新增 manager、dispatcher、registry、ticket 或其他治理层。

## 下一阶段边界

当前 PR 只修 R6-001 至 R6-004。吞吐优化应放入下一独立小 PR：共享 RunContext、cheap verify/explicit replay、`run_research(spec, explore|verify)` 和一个真实窄 vertical slice。

Provider-qualified 数据、生产成本/流动性/公司行动/退市校准，以及 `EA-001` 独立 reviewer receipt 继续保持外部证据阻塞，不得由 fixture 关闭。
