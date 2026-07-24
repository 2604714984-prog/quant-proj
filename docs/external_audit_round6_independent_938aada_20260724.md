# PR #126 Round 6 独立外部审查报告

> 本报告只审查冻结代码提交 `938aada03f819d98cbf7c9ac627a8c77326ed312`。  
> 后续仅用于保存本报告和机器台账的文档提交不属于被审代码范围。

## 1. 冻结边界

- Repository：`2604714984-prog/quant-proj`
- PR：`#126`，Draft / open / not merged
- Base：`v2-main@31329dbfd7b9bb1c184a13ee7fe2e60bd0a6ba14`
- Previous audited head：`81403aa223ad6d11a7339fd970b65512bdc0a5c8`
- Audited code head：`938aada03f819d98cbf7c9ac627a8c77326ed312`
- GitHub Actions merge ref：`7d076d51eb70cdbcfd41a1360fd4f14c3fb958df`
- GitHub Actions run：`30062113832`，`completed/success`
- 审查日期：`2026-07-24`

本轮建立在此前逐文件完整审查之上，重新审查了 `81403aa..938aada` 的全部生产代码增量、相关测试增量和关键正向路径，并对若干研究合同进行了独立最小复现。

## 2. 独立验证证据

已确认：

- CI wheel build、`SHA256SUMS`、artifact upload、wheel install、`pip check`、checkout 外 CLI、Ruff 和 pytest 步骤全部成功；
- 已下载 CI artifact；
- wheel SHA-256 为 `0f7b925efeb9a356b4e2017ca27f320bc51aba382c6cf7d60110fbb9b37eee72`，与 artifact 内 `SHA256SUMS` 一致；
- artifact ZIP SHA-256 为 `625c596fccf40fbc9d42ec9fd0a47b95fd2567b3ce23e3af66e9fea1a966dcbb`；
- 抽取 wheel 源码后 `compileall` 通过；
- 自研 Student-t 双侧 p-value 与 SciPy 1.17.0 对照，测试网格最大绝对误差约 `1.78e-12`。

证据限制：

- CI pytest step 已确认成功，但连接器没有完整提取日志尾部，因此精确 `273 passed` 仍以 PR/整改台账为准；
- 本轮没有项目/生产数据库写入，也没有市场数据 provider 请求；
- FRED 9 行 exploratory slice 的原始快照、spec 和临时执行脚本未提交，无法从干净 clone 独立重放。

## 3. 外审裁决

```text
external_audit_verdict=REQUEST_CHANGES_FOCUSED

repository_boundary_clean=true
runtime_architecture_lightweight=true
single_canonical_writer=true
fail_closed_default=true

real_controlled_multistage_path=true
portable_stage_receipts=true
experiment_ledger_recoverable=true
bundle_execution_replay=true

historical_cost_binding=false
historical_strategy_binding=false
feature_label_causal_isolation=false
dataset_split_row_binding=false
return_horizon_semantics=false
actual_exposure_binding=false

exploratory_research=USABLE_WITH_CAUTION
fast_result_pipeline=NOT_READY
validated_research_end_to_end=false
capital_grade_research_process=false

code_remediation_complete=false
only_external_evidence_remaining=false

strategy_candidate_available=false
recommendation_authorized=false
paper_trading_authorized=false
live_trading_authorized=false
automatic_execution_authorized=false
```

准确描述：

> 本轮已经关闭真实 stage → receipt → return → statistics 的基本正向路径，项目可靠性有实质进步；但历史成本、历史策略身份、feature 因果、dataset/split 行一致性、收益区间和实际组合暴露仍有六处会改变研究结论的脱钩。

## 4. 已接受且不应回滚的整改

1. 真实 `run_controlled_stage` 多阶段链现在能够生成 `ControlledStageReceipt`、`FinalRunReceipt`、`ReturnArtifact` 和 `SplitEvaluation`。
2. `ControlledStageReceipt.verify()` 会重新执行 event-loop artifact，并核对成交、portfolio、NAV、receipt hash chain 和 core-engine identity。
3. `FamilyContract` 与 `TrialConfig` 已分离；同一 multiplicity family 可以容纳不同 DecisionArtifact。
4. `TrialRunReceipt`、`evaluate_frozen_historical_run()` 和 `replay_trial_run()` 已建立历史运行、收益和统计的可重放链。
5. Experiment ledger 已持久化完整 canonical event payload，支持跨进程恢复和追加。
6. Transformation 已改为固定纯 JSON DSL；feature、label 和 join artifacts 可分别重放。
7. CandidateRunBundle v4 会重放 base/adverse execution 和部分 qualification artifacts，并绑定 core-engine artifact。
8. TerminalAction 的 UTC/交易所本地日期问题已修复。
9. CI 已发布并验证 wheel artifact。
10. Student-t 数值实现已有独立外部金标，不作为本轮阻断项。

# 5. 六个 correctness blocker

## R6-001 — 历史 stage 的成本身份可与实际执行成本脱钩 `[HIGH]`

**文件/函数**

- `src/quant_system/backtest/event_loop.py::run_controlled_stage`
- `src/quant_system/backtest/event_loop.py::ControlledStageReceipt.verify`
- `src/quant_system/research/experiments.py::TrialConfig`
- `src/quant_system/research/experiments.py::evaluate_frozen_historical_run`

**触发条件**

用零佣金、零滑点或不同 capacity policy 运行历史 stage，同时向 `run_controlled_stage` 传入另一套格式正确的 `cost_assumptions_sha256`。

**实际影响**

历史成交和 NAV 可按便宜的真实参数计算，却被 TrialConfig、FamilyContract 和 DatasetManifest 标记为使用另一套更保守的成本政策。Holdout 绩效因此可能被高估。

**代码事实**

- `run_controlled_stage` 接受成本摘要字符串；实际 portfolio costs、capacity policy 和 slippage 由其他参数决定；
- stage receipt 重放真实 execution artifact，但没有从实际执行参数重算成本 identity；
- 历史评估只比较 stage receipt 的成本 SHA 与 TrialConfig 成本 SHA。

**最小修复**

`run_controlled_stage` 接受完整 `ExecutionCostAssumptions` 和明确的 base/adverse case，由函数内部唯一派生 portfolio cost model、slippage、capacity、FX 和监管费；receipt 保存 canonical cost payload，验证时从实际 replay 参数重算 identity。不得继续接受独立自由 SHA。

**回归测试**

- 实际 commission、tax、slippage 或 capacity 与声明 assumptions 不一致时失败；
- 只改变实际成本参数必须改变 stage/TrialRun identity；
- 逐笔费用与成本 receipt 对账。

## R6-002 — 历史策略定义与每阶段 DecisionArtifact 没有可验证关系 `[HIGH]`

**文件/函数**

- `src/quant_system/research/experiments.py::TrialConfig`
- `src/quant_system/research/experiments.py::evaluate_frozen_historical_run`
- `src/quant_system/backtest/event_loop.py::ControlledStageReceipt`
- `src/quant_system/backtest/event_loop.py::apply_qualified_strategy_stage`

**触发条件**

TrialConfig 声明策略定义 A，但 ordered stage receipts 实际来自定义/adapter B，只把 B 的 DecisionArtifact SHA 列入 TrialConfig。

**实际影响**

历史 holdout 结果可以属于策略 B，而 holdout event 和 prospective candidate 被标为策略 A。相同权重但不同 definition、feature 或 adapter 也可能共用历史资格。

**代码事实**

- TrialConfig 同时保存一个 `definition_sha256` 和 ordered DecisionArtifact SHA 列表，但没有校验推导关系；
- ControlledStageReceipt 没有保存可重新执行的历史 DecisionArtifact payload；
- 历史评估比较 ordered artifact SHA，却不比较 stage replay 中实际 definition/adapter 与 TrialConfig。

**最小修复**

TrialConfig 固定共享 `strategy_definition_sha256` 与 `strategy_adapter_sha256`；每个 ControlledStageReceipt 显式保存并验证二者，或保存可重放 DecisionArtifact payload。历史每个 stage 必须与 TrialConfig 策略身份一致。

**回归测试**

- 只改变 TrialConfig definition 或 adapter 时失败；
- 同权重、不同 definition/feature bytes 不得共用历史资格；
- fresh-process replay 从 per-stage DecisionArtifact artifacts 重新计算权重。

## R6-003 — Feature 与 label 仍可从同一 raw 文件读取未来标签 `[HIGH]`

**文件/函数**

- `src/quant_system/research/identity.py::replay_pure_transformation_artifacts_bytes`
- `src/quant_system/research/identity.py::_pure_step_bytes`
- `src/quant_system/research/identity.py::_validate_partition`

**触发条件**

Raw source 同时包含历史特征和未来 label；feature spec 直接选择或重命名未来 label，同时输出一个较早的 `feature_available_at`。

**实际影响**

`row_pit_enforced=true` 的 partition 仍可包含直接标签泄漏。当前检查证明的是一个 availability 字段合格，不证明 feature value 来自该时间前可用的输入。

**代码事实**

- feature step 与 label step 接收完全相同的 `raw_bytes`；
- DSL 支持投影、rename 和 constant fields，但没有 feature-only、label-only 或 key-only 字段角色；
- `_validate_partition` 不追踪每个 feature value 的输入字段和 source availability。

**最小修复**

为 raw sources 和字段增加最小 role contract：`FEATURE_INPUT`、`LABEL_INPUT`、`KEY_ONLY`。Feature step 只能读取 feature-role 字段/来源；label step 只能读取 label-role 字段。Availability 必须从实际使用的 source/typed field 派生，不能由常量自报。

**回归测试**

- feature spec 选择、重命名或计算 label-only 字段时失败；
- 早期 constant 覆盖真实晚到 availability 时失败；
- 同一 raw container 中未来 label 不得进入 feature artifact。

## R6-004 — Dataset partition 与 SplitManifest 没有逐行对账 `[HIGH]`

**文件/函数**

- `src/quant_system/research/identity.py::capture_dataset_manifest`
- `src/quant_system/research/identity.py::DatasetManifest.verify_identity`
- `src/quant_system/research/splits.py::SplitManifest`

**触发条件**

Transformation partition 包含一组 sample/entity/observed_at，而 SplitManifest 包含另一组样本、实体或日期。

**实际影响**

训练/标签数据与 purge/holdout 样本定义可以是两套不同集合。样本删除、移动日期、改变标签窗口或事后排除失败股票可隐藏在二者之间。

**代码事实**

- DatasetManifest 分别固定 partition、TransformationReceipt 和 SplitManifest 的 hash；
- 构建和验证过程没有提取 partition 中的 `(sample_id, entity_id, observed_at, label_end_at)` 与 SplitManifest 精确比较。

**最小修复**

Transformation 输出强制包含 canonical row index：`sample_id/entity_id/observed_at/label_end_at`。DatasetManifest 构建时生成 row-index receipt，并要求它与 SplitManifest 完整 row index 精确一致；缺失、额外、重复或时点不一致均 fail closed。

**回归测试**

- 任一 sample/entity/time/fold 不一致时失败；
- 删除失败样本或增加额外 partition 行时失败；
- row-index receipt 进入 dataset identity 和 replay bundle。

## R6-005 — 被检验收益区间没有明确经济起点和完整覆盖 `[HIGH]`

**文件/函数**

- `src/quant_system/research/splits.py::ReturnObservation`
- `src/quant_system/research/splits.py::capture_return_artifact`
- `src/quant_system/research/splits.py::evaluate_split`

**触发条件**

Label horizon 为 start→end，但 ReturnArtifact 只包含区间端点；或 feature observed_at 是信号日，实际交易从下一 accepted session 才开始。

**实际影响**

统计评估可能遗漏中间交易期、包含 start 前收益，或者把 feature observation time 误当成可投资收益起点。HAC/Bootstrap 校正的 horizon 可能不是实际被检验的经济区间。

**代码事实**

- ReturnObservation 只记录当前 execution end，没有显式 `period_start_session`；
- initial NAV 来自上一 stage final state，但该状态日期未进入 observation；
- evaluate_split 按 observation end date 选择区间，只检查端点，不证明完整 accepted-session/period chain。

**最小修复**

ReturnObservation 增加 `period_start_session` 与 `period_end_session`，由连续 portfolio transitions 派生。SplitSample 或 evaluation plan 明确区分 `feature_observed_at`、`decision_at`、`return_start_session` 和 `label_end_session`。聚合要求 period chain 无缺口、无重叠。

**回归测试**

- 缺少 horizon 中间 accepted session 或 transition 时失败；
- next-open 策略使用明确 return-start 约定；
- start 前收益被包含时失败。

## R6-006 — ReturnArtifact contributors 来自目标权重，而不是实际经济持仓 `[HIGH]`

**文件/函数**

- `src/quant_system/research/splits.py::capture_return_artifact`
- `src/quant_system/backtest/event_loop.py::run_static_rebalance`
- `src/quant_system/backtest/event_loop.py::_order`

**触发条件**

非目标持仓因停牌、跌停、容量限制或未成交无法退出，但其市值继续进入 portfolio NAV。

**实际影响**

统计评估把完整 portfolio return 归因给 target-weight contributors，却漏掉真实仍持有并影响风险/收益的证券。样本集合与被检验组合不一致。

**代码事实**

- contributors 只来自 `result.target_weights` 中非零权重；
- event loop 允许 held nonmember 因 market block 留在最终 portfolio；
- 完整 NAV 包含这些残余持仓。

**最小修复**

对 daily portfolio evaluation，exposure receipt 从实际 initial/final positions、trades、blocked orders 和 marks 派生。更简单的做法是统计单位明确为 `portfolio-date`，不再用目标证券列表冒充实际组合成分；若做 security-level estimand，则保存真实 exposure weights。

**回归测试**

- blocked exit 留存持仓时 exposure receipt 包含该证券；
- 实际持仓集合与 selected contributors 不一致时失败；
- 净收益与逐证券 exposure/P&L reconciliation 对账。

# 6. 非阻断但应在下一小 PR 处理的吞吐问题

## R6-007 — Transformation config 被哈希但未影响输出 `[MEDIUM]`

`config_bytes` 只被解析为 JSON object，未参与 feature、label 或 join。应删除 config，或允许 spec 显式引用有限 typed keys；未使用 key 应失败。

## R6-008 — FRED exploratory slice 不是仓库内可重放 vertical slice `[MEDIUM: THROUGHPUT]`

整改台账记录了 raw/feature/label/partition hashes 和9行结果，但 active tree 没有 FRED spec、adapter、固定 artifact reference 或 compact report。下一小 PR 应增加一个标准 research runner 和可从干净 clone 重放的 exploratory spec。

## R6-009 — 构建、序列化和加载路径重复执行昂贵 replay `[MEDIUM: THROUGHPUT]`

拆分 `verify_structure()` 与显式 `replay()`；普通 explore/load 只做 hash/schema/coverage，promotion/CI 对每个 immutable identity 只 full replay 一次并保存 ReplayReceipt。

## R6-010 — Bundle Base64 内嵌所有数据，规模线性膨胀 `[MEDIUM: THROUGHPUT]`

下一小 PR 改为 content-addressed manifest：`role/sha256/byte_count/relative artifact URI`。需要离线单包时显式 pack。

# 7. 外部证据边界

## E6-001 — Provider、生产成本校准、独立 anchor 和 A股 evidence-room 验收仍开放 `[BLOCKED_EXTERNAL_EVIDENCE]`

- 当前 FRED slice 正确标记为 `EXPLORATORY_GENERIC_CAPTURE`，不能作为 candidate evidence；
- provider-qualified market observations 尚不可得；
- 真实成本、流动性、公司行动和退市完整性未做生产校准；
- `QF-014/EA-001` 独立 reviewer receipt 仍未提供。

这些属于外部证据阻塞，不替代上述六个代码 correctness blocker。Discovery lane 不必等待外部证据，但任何候选、推荐和资金授权继续保持 `false`。

# 8. 最短整改顺序

## 当前 PR 只再关闭六项

1. 实际成本参数与成本 identity 统一派生；
2. TrialConfig definition/adapter 与每阶段 DecisionArtifact 绑定；
3. Feature/label source-field role 隔离；
4. Partition row index 与 SplitManifest 精确对账；
5. 显式 return period start/end 和完整覆盖；
6. 实际 exposure receipt，而非 target-weight contributors。

六项关闭后应尽快冻结新 head 复审并合并。不要继续在本 PR 添加吞吐优化或新通用证据类型。

## 下一小 PR 专门恢复成果速度

- `run_research(spec, mode='explore'|'verify')`；
- `quant research run`；
- structural verify 与 explicit replay 分离；
- content-addressed bundle manifest；
- 一个仓库内可重放的真实 exploratory vertical slice；
- 旧外审文档归档，只保留最新报告和机器台账。

明确禁止新增 manager、dispatcher、registry、ticket、代理层或第二 writer。

# 9. 最终结论

```text
research_core=SUBSTANTIALLY_IMPROVED_BUT_NOT_YET_VALIDATED
exploratory_use=ALLOWED_WITH_EXPLICIT_EXPLORATORY_LABEL
candidate_promotion=DENY
capital_allocation=DENY
paper_live_auto_execution=DENY
```
