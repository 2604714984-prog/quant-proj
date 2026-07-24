# PR #126 Round 7 独立统一外审

> 本报告只审查冻结代码提交 `3f4b46bbd3ff28bb8f28a4377a6bf4f91d566824`。
> 后续用于保存本报告和机器台账的文档提交不属于被审代码范围。

## 1. 冻结边界

- Repository：`2604714984-prog/quant-proj`
- PR：`#126`，Draft / open / not merged
- Previous base：`31329dbfd7b9bb1c184a13ee7fe2e60bd0a6ba14`
- Current base：`3ec32b30f66ab496740ca7e879983a73d68857d6`
- Previous audited code head：`938aada03f819d98cbf7c9ac627a8c77326ed312`
- Current audited code head：`3f4b46bbd3ff28bb8f28a4377a6bf4f91d566824`
- Tested merge ref：`73e974500801c6806f6b7150517812ecb4d5981c`
- GitHub Actions run：`30078703327`，job `89435117886`，`completed/success`
- Audit date：`2026-07-24`

本轮建立在此前全仓逐文件外审之上，重新审查了 `938aada..3f4b46b` 的 14 个提交和全部 15 个增量文件、受影响生产函数的完整当前实现和调用链、新同步 `v2-main` 的单提交清理增量，并在 CI wheel 上执行了独立反例。

本轮外审没有项目/生产数据库写入，也没有市场数据 provider 请求。

## 2. CI 与构建物证据

已独立确认：

- PR head、base、Draft、mergeable 状态与申报一致；
- CI wheel build、checksum、artifact upload、wheel install、`pip check`、checkout 外 CLI、Ruff 和 pytest 步骤成功；
- Artifact ID：`8590893248`；
- Artifact ZIP SHA-256：`a10788da8c92d6a5af2e8a82b79c8d8a748db2fb63574b250f840843495a57fc`；
- Wheel SHA-256：`75ea5db7675deb258cbe88c5459d3fe254ad6390283732885f8beb02eaa93f13`；
- Wheel SHA 与 `SHA256SUMS` 一致；
- 抽取 wheel 后 `compileall` 通过。

证据限制：

- CI pytest step 已确认成功；连接器未完整提取日志尾部，因此精确 `274 passed` 仍以 PR 和整改台账为准；
- 审查容器没有 DuckDB 且无法联网安装，本轮未重跑完整仓库 pytest/Ruff；
- 独立反例均运行在上述 CI wheel 上，只使用最小 DuckDB import stub，不访问数据库；
- 提交者申报的本地工作树干净、数据库写入 0 和 provider 请求 0 未由本轮环境直接观察。

## 3. 裁决

```text
external_audit_verdict=REQUEST_CHANGES_FOCUSED

repository_boundary_clean=true
runtime_architecture_lightweight=true
single_canonical_writer=true
fail_closed_default=true

R6_005_return_period_code=PASS
R6_006_actual_exposure_code=PASS

historical_run_controls_complete=false
cost_stress_semantics_valid=false
historical_feature_dataset_lineage=false
feature_label_isolation_complete=false
dataset_label_join_complete=false

exploratory_research=USABLE_WITH_CAUTION
validated_historical_research=false
fast_result_pipeline=NOT_READY
capital_grade_research_process=false

code_remediation_complete=false
only_external_evidence_remaining=false

strategy_candidate_available=false
recommendation_authorized=false
paper_trading_authorized=false
live_trading_authorized=false
automatic_execution_authorized=false
```

发现计数：

```text
HIGH=4
MEDIUM_THROUGHPUT=1
BLOCKED_EXTERNAL_EVIDENCE=1
```

准确描述：

> 本轮关闭了收益区间和实际 exposure 两条关键链路，但历史运行政策、成本压力、feature→dataset 血缘，以及 feature/label 字段与 join 隔离仍有可复现缺口。

因此不能接受：

```text
code_remediation_complete_for_round6_focused_scope=true
only_external_evidence_remaining=true
```

## 4. 原 R6 finding 复判

| Finding | Round 7 状态 | 结论 |
|---|---|---|
| `R6-001` | `PARTIAL_CODE_CLOSE_ACCEPTED` | `run_controlled_stage` 已从单一成本对象派生佣金、监管费、capacity 和 slippage，portable receipt 也会重放；但 gross/adverse 语义及历史 cost case 尚未闭合。 |
| `R6-002` | `PARTIAL_CODE_CLOSE_ACCEPTED` | 每阶段保存 feature/definition/adapter 字节并重算权重，TrialConfig 也比较 definition/adapter；但 feature snapshot 尚未证明来自所声明 DatasetManifest。 |
| `R6-003` | `PARTIAL_CODE_CLOSE_ACCEPTED` | feature/label source sets 已分离并哈希字段角色；`KEY_ONLY` 和调用方自报 availability 仍可旁路。 |
| `R6-004` | `PARTIAL_CODE_CLOSE_ACCEPTED` | 最终 partition row index 必须与 SplitManifest 完全一致；但 label-side identity 可在 join 前丢失。 |
| `R6-005` | `CLOSED_CODE` | Return period 已有显式 start/end、连续 transition 和 accepted-session coverage。 |
| `R6-006` | `CLOSED_CODE` | Exposure 已由实际开收盘持仓、成交和 blocked attempts 派生。 |

## 5. 详细发现

### R7-001 — 成本假设可以把非 gross、非 adverse 的经济结果标记为 gross/adverse `[HIGH]`

**文件/函数**

- `src/quant_system/backtest/costs.py::CostStressCase.total_rate_proxy`
- `src/quant_system/backtest/costs.py::ExecutionCostAssumptions.__post_init__`
- `src/quant_system/backtest/event_loop.py::apply_qualified_strategy_stage`

**触发条件**

- `gross_only=True`，但 `minimum_commission > 0`；
- adverse 的最低佣金更低或 FX 更有利，只用略高的 rate proxy 满足检查。

**实际影响**

结果可被标记 `GROSS_ONLY`，实际却收费；更严重的是 adverse case 对小额订单可能比 base 更便宜并产生更高 NAV，使压力测试方向反转。

**代码事实**

- `total_rate_proxy` 不包含 `minimum_commission` 和 `fx_to_base`；
- gross-only 只检查该 proxy；
- adverse 只比较 aggregate proxy，没有逐组件比较；
- candidate 输出分别乘 base/adverse 的 `fx_to_base`。

**独立复现**

```text
GROSS_ONLY_WITH_MINIMUM_ACCEPTED True 5.0 5.0
ADVERSE_STAGE_BETTER_THAN_BASE 99900.0 99980.2 True
base cost on gross 1000 = 100.0
adverse cost on gross 1000 = 0.2
```

**事实**：冻结 CI wheel 接受并执行了上述假设。

**推断**：当前 `gross_only` 和 `adverse` 标签不保证通常的经济含义。

**假设**：项目期望 gross-only 零费用，adverse 对所有支持的交易都不比 base 更便宜。

**最小修复**

- gross-only 要求 commission rate、minimum commission、regulatory fee、spread 和 impact 全部为 0；
- adverse 对各成本组件逐项不优于 base，包括 minimum commission；
- 当前 long-only 单币模型中，要求 adverse FX 不比 base 更有利；
- 若实际 adverse replay 仅因更便宜假设而优于 base，fail closed。

**回归测试**

- gross-only + nonzero minimum commission 被拒；
- 代表性小额和大额订单上 adverse cost 均不低于 base；
- adverse FX-adjusted NAV 不得仅因更有利 FX 改善。

### R7-002 — 历史 TrialConfig 未绑定 `max_positions` 和被评价的 cost case `[HIGH]`

**文件/函数**

- `src/quant_system/research/experiments.py::TrialConfig`
- `src/quant_system/research/experiments.py::evaluate_frozen_historical_run`
- `src/quant_system/backtest/event_loop.py::ControlledStageReceipt`

**触发条件**

历史 stage 以 `max_positions=None` 执行，但 TrialConfig 声称 `max_positions=1`；或历史链使用 adverse，而 trial contract 未声明 cost case。

**实际影响**

Holdout p-value 可来自不同持仓约束或未指定成本场景。Prospective gate 对当前 stage 的检查不能修复历史证据。

**代码事实**

- TrialConfig 保存 `max_positions`，但历史评估未与 stage replay 对账；
- Stage receipt 保存 `cost_case`，TrialConfig 没有历史 cost case；
- replay artifact 已包含 `max_positions`，这是遗漏的 equality check，不是缺失数据。

**独立复现**

```text
MAX_POSITIONS_IMPACT_ACCEPTED 1 ('AAA', 'BBB') 0.017573437412390598
ADVERSE_AS_BASE_CONTRACT_ACCEPTED 07329f806fd3dabc7ee543fe299bbb4b440f6ee3eb6ffdd5f2cfd1d02ba4eaf8
```

**事实**：声称最多一个持仓的 trial 接受了实际同时持有 AAA、BBB 的五阶段历史。

**推断**：历史资格未承诺完整执行政策。

**假设**：`max_positions` 和 base/adverse 选择是预注册 run control。

**最小修复**

- `ControlledStageReceipt` 显式暴露 `max_positions`，每阶段与 TrialConfig 对账；
- TrialConfig 增加 `historical_cost_case`；
- 一个 TrialRunReceipt 内 cost case 必须统一；若 base/adverse 都作为晋级证据，生成两份独立 TrialRunReceipt。

**回归测试**

- 两持仓的无约束历史不能满足 `max_positions=1`；
- adverse stage chain 不能满足 base TrialConfig；
- 改变 `max_positions` 或 cost case 改变 TrialRunReceipt identity。

### R7-003 — 历史 feature snapshot 可借用任意 DatasetManifest identity `[HIGH]`

**文件/函数**

- `src/quant_system/backtest/event_loop.py::capture_decision_artifact`
- `src/quant_system/backtest/event_loop.py::_verify_historical_decision_binding`
- `src/quant_system/research/experiments.py::evaluate_frozen_historical_run`
- `src/quant_system/backtest/event_loop.py::apply_qualified_strategy_stage`

**触发条件**

创建任意 feature snapshot 文件，附上一个有效 DatasetManifest 的 identity 字符串，再生成历史 stages。

**实际影响**

未来修改、独立生成或与 PIT partition 无关的 feature snapshot，可借用另一冻结数据集的 PIT identity。策略字节与权重会正确重放，但 dataset→feature 的血缘边不存在。

**代码事实**

- `capture_decision_artifact` 接受裸 `dataset_identity_sha256` 和任意 feature 文件；
- 历史评估不接收 DatasetManifest 或 FeatureSnapshotReceipt；
- Prospective gate 比较的是 identity 字符串相等，不证明 feature 由 partitions 产生；
- 现有测试也独立构造 DatasetManifest 和 feature snapshot。

**独立复现**

```text
ARBITRARY_FEATURE_SNAPSHOT_ACCEPTED_FOR_DATASET
```

冻结 DatasetManifest identity 接受了与 manifest feature-code/partition 无推导关系的 feature snapshot。

**最小修复**

增加一个很小的 `FeatureSnapshotReceipt`：由已验证的 DatasetManifest/TransformationReceipt 和确定性 as-of selector 生成。`capture_decision_artifact` 接收该 receipt，而不是裸 dataset SHA；历史评估加载并验证有序 feature snapshot receipts。

**回归测试**

- 任意 feature bytes + 有效 dataset identity 被拒；
- partition、transformation、selector 或 snapshot 任一变化使旧 TrialRunReceipt 失效；
- fresh-process replay 从 dataset artifacts 重建各期 feature snapshot，再重算权重。

### R7-004 — 字段角色和 join keys 仍允许 feature 泄漏及错误 label 归属 `[HIGH]`

**文件/函数**

- `src/quant_system/research/identity.py::_pure_step_bytes`
- `src/quant_system/research/identity.py::replay_pure_transformation_artifacts_bytes`
- `src/quant_system/research/identity.py::_validate_partition`
- `src/quant_system/research/identity.py::capture_dataset_manifest`

**触发条件**

- 将 label 值声明为 `KEY_ONLY`，feature step 读取它；
- 晚到 source 配一个自报的较早 `feature_available_at`；
- join 只按 `sample_id`，label artifact 不携带 `entity_id`。

**实际影响**

`row_pit_enforced=true` 和最终 partition/split row equality 可同时通过，但 feature 含未来 label，或 AAA 的样本附上 BBB 的 label。

**代码事实**

- `KEY_ONLY` 同时允许 feature 与 label transforms 读取，且不限于固定身份字段；
- `raw_field_roles` 由调用方声明，feature availability 从输出字段检查，不由实际使用的 source/field 派生；
- `join_jsonl` 接受任意 keys，不要求两侧携带完整 canonical identity；
- DatasetManifest 只比较最终 joined row index。

**独立复现**

```text
KEY_ONLY_LABEL_LEAK_ACCEPTED True ... future_label=0.75
LATE_FEATURE_SOURCE_ACCEPTED_AS_PIT source_available=2021 observed=2020 row_pit_enforced=True
WRONG_ENTITY_LABEL_JOIN_ACCEPTED final_entity=AAA raw_label_entity=BBB
```

**最小修复**

- `KEY_ONLY` 限定为固定 canonical identity 字段，且不得成为模型 feature；
- feature/label 两侧都必须携带完整 canonical join identity；
- join keys 固定为该 identity；
- `sample_id` 从 entity/time/fold/horizon 重算，不信任 raw sample_id；
- `max_feature_available_at` 从实际使用输入派生，不接受游离的 availability 字段。

**回归测试**

- label-only 字段即使声明 KEY_ONLY，也不能被 feature spec 选取；
- 晚到 feature source 不能靠早期自报字段变成 PIT-valid；
- feature AAA 与 label BBB 即使 sample_id 相同也失败；
- 缺少 canonical entity/time keys 的 join spec 被拒。

### R7-005 — Daily portfolio evaluation 混淆模型样本与实际 portfolio contributors `[MEDIUM_THROUGHPUT]`

**文件/函数**

- `src/quant_system/research/splits.py::SplitEvaluationPlan`
- `src/quant_system/research/splits.py::evaluate_split`
- `src/quant_system/research/splits.py::ReturnObservation`

**触发条件**

Cross-sectional holdout 包含 AAA、BBB 两个模型样本，但冻结 top-N 策略实际只持有 AAA。

**实际影响**

合法 portfolio run 被拒，因为 contributors 必须等于所有 selected sample entities。若只选择实际持仓样本，又会让预注册样本集依赖 holdout 输出。

**代码事实**

- 唯一 evaluation unit 为 `daily_portfolio`；
- selected sample IDs 被汇总为 expected entity contributors；
- 每个 ReturnObservation contributor set 必须完全相等。

**独立复现**

```text
TOPN_PORTFOLIO_EVALUATION_REJECTED ValueError ReturnArtifact contributor set differs from selected samples ('AAA',)
```

**最小修复**

将模型样本 SplitManifest 与按日期/horizon 预注册的 `PortfolioEvaluationSchedule` 分开。实际 exposure receipt 继续用于审计，但不要求等于全部模型样本实体。Security-level inference 如需要，应作为另一 evaluation unit。

### E7-001 — 外部证据继续阻塞 `[BLOCKED_EXTERNAL_EVIDENCE]`

真实 provider、生产成本/流动性校准、独立 anchor 和 A 股 evidence-room reviewer receipt 仍未提供。该项正确保持 BLOCKED，不应由 fixture 或代码测试关闭。

## 6. 完整性复判

| 控制项 | 判定 | 说明 |
|---|---|---|
| 仓库边界 | `PASS` | active archive/direct writers 已清理 |
| 单一 canonical writer | `PASS` | prospective tree 仍只有中央 writer |
| 最小运行时复杂度 | `PASS` | 一个 CLI、两个 runtime dependencies、无控制面 |
| 前视偏差 | `FAIL` | feature availability/role/join contract 可绕过 |
| PIT 数据 | `FAIL` | feature snapshot 未由 DatasetManifest 派生 |
| 存活偏差 | `PARTIAL_PASS` | complete-universe 机制较强；真实 provider 待验 |
| 标签跨 split | `PARTIAL` | 最终 row-index 对账，但 label-side join identity 不完整 |
| 测试集参与选参 | `PARTIAL_PASS` | family/ledger/anchor 机制较强；独立 anchor 待验 |
| 多重检验 | `PASS_MECHANISM` | multi-trial family 和校正可复算 |
| 重叠收益 | `PASS_MECHANISM` | interval chain 已修复；model sample/portfolio unit 需拆分 |
| 交易成本 | `FAIL` | gross/adverse invariant 与 historical scenario contract 不完整 |
| 流动性 | `PARTIAL_PASS` | capacity 实际进入 stage；真实校准待验 |
| 公司行动/退市 | `PARTIAL_PASS` | raw accounting 机制较强；真实完整性待验 |
| 策略身份 | `PARTIAL` | definition/adapter 绑定；feature→dataset 关系缺失 |
| 跨进程复现 | `PARTIAL_PASS` | stage/trial/bundle replay 明显增强 |
| 快速成果管线 | `NOT_READY` | 标准 runner/vertical slice 留待后续小 PR |
| 外部证据 | `BLOCKED` | provider/calibration/anchor/EA-001 未完成 |

## 7. 最短整改顺序

当前 PR 只做三个小修复组：

1. **Run contract**
   - 对账 TrialConfig.max_positions；
   - 增加 historical_cost_case；
   - 修复 gross-only/adverse 的 componentwise invariants。
2. **Feature lineage**
   - 增加由 DatasetManifest/TransformationReceipt 派生的 FeatureSnapshotReceipt；
   - 历史每阶段重放 dataset→snapshot→weights。
3. **Transformation identity**
   - KEY_ONLY 限定为固定身份字段；
   - 两侧携带完整 canonical identity；
   - 固定 join keys 并重算 sample_id；
   - availability 从实际使用输入派生。

完成后再次冻结 head 外审。不要在当前大 PR 加吞吐优化。

下一小 PR 保留：R6-007 config cleanup、R6-008 research runner/vertical slice、R6-009 structural verify vs explicit replay、R6-010 content-addressed bundle，并加入 R7-005 的 portfolio evaluation schedule 拆分。

明确禁止新增 manager、dispatcher、registry、ticket、代理层或第二 writer。

## 8. 最终授权

```text
research_core=SUBSTANTIALLY_IMPROVED_BUT_NOT_VALIDATED
exploratory_use=ALLOWED_WITH_EXPLICIT_EXPLORATORY_LABEL
candidate_promotion=DENY
capital_allocation=DENY
paper_live_auto_execution=DENY
```
