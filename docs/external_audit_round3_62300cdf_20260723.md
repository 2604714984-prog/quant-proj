# PR #126 Round 3 统一外部复审报告

> 本报告只审查冻结代码提交 `62300cdff8e300a43c0fc54b0fba2df0e456511f`。
> 将本报告提交到 GitHub 所产生的后续文档提交不属于被审代码范围，也不改变本报告结论。

## 1. 冻结边界

- 仓库：`2604714984-prog/quant-proj`
- PR：`#126`
- 基线：`35b3246e40f8315e2bbef847d995a3b6d3a3b4fc`
- 上一轮审查 head：`e38977f0f4448479a3b7ec979928248b745fca48`
- 本轮冻结 head：`62300cdff8e300a43c0fc54b0fba2df0e456511f`
- GitHub Actions merge ref：`26aa7217d45bc19663a9e85502644c37556ded6f`
- 独立证据室：`2604714984-prog/a-share-canonical-evidence-data-room@de38f03466a58b9c786ed35e2cc38abff3e9b0fe`
- 审查日期：`2026-07-23`
- 本轮外审仓库写入：`0`
- 本轮外审市场数据 provider 请求：`0`

## 2. 外审裁决

```text
external_audit_verdict=CONDITIONAL_PASS_EXPERIMENTAL_ONLY
lightweight_architecture=true
fail_closed_default=true
experimental_research_infrastructure=true
capital_grade_research_process=false
strategy_candidate_available=false
recommendation_authorized=false
paper_trading_authorized=false
live_trading_authorized=false
automatic_execution_authorized=false
```

项目目前可以准确描述为：

> **可靠、轻量、默认失败关闭的实验研究基础设施；尚不是已经证明不会自我欺骗的端到端资金决策研究流程。**

如果 PR 继续声称“全部可靠性整改完成”，外审结论为 `REQUEST_CHANGES`。如果将 PR 准确定位为 `lightweight fail-closed research infrastructure hardening`，当前代码具有合并价值，但合并不能解释为个人资金使用获批。

## 3. 测试和执行证据

### 已独立确认

- PR head、base、Draft 状态与申报一致；
- PR 在冻结时共有 39 个 commits、33 个 changed files；
- GitHub Actions run `29985872527` 为 `completed/success`；
- CI 成功执行 wheel build、wheel install、`pip check`、checkout 外 `quant info`、Ruff 和 pytest；
- CI checkout 的是 PR merge ref `26aa7217d45bc19663a9e85502644c37556ded6f`；
- 证据室仍明确为 `PUBLISHED_UNVERIFIED_EXTERNALLY / PENDING_EXTERNAL_RECEIPT`。

### 未独立确认

- 审查环境无法 DNS 解析 `github.com`，因此没有本地 clone、Ruff 或 pytest 重跑；
- 源码和 installed wheel 各 `258 passed` 与 PR 台账一致，但完整日志尾部未由 connector 独立提取；
- wheel SHA-256 `0f1d1922e33d9435b46cd9cb35c64492c18ce8a0a4d3d21355720ec06118723a` 没有 CI artifact 可供重新计算；
- “生产 DB 写入 0、provider 请求 0、原工作树干净”属于整改执行者的本地台账声明；
- 测试通过只能证明当前测试合同通过，不能自动证明研究合同完整。

## 4. 仓库角色和轻量化判断

### 仓库角色

- `quant-proj`：唯一活跃主线研究/回测代码仓，同时拥有唯一公开 DuckDB append writer；
- 外部 `QUANT_DATA_ROOT/quant_research.duckdb`：声明的 mutable canonical 数据对象；
- `a-share-canonical-evidence-data-room`：独立只读证据边界，不拥有 canonical 数据写权限；
- 其他历史仓库：归档，只读，不应恢复旧 manager、dispatcher、registry、broker 或 paper/live 路径。

### 轻量化判定：通过

- 运行时依赖只有 DuckDB 和 pytz；
- 只有一个 CLI；
- data、research、backtest 公共 API 仍为小型显式接口；
- 没有 manager、dispatcher、ticket、registry、proxy 或 workflow engine；
- 没有第二套 canonical writer；
- 没有 broker、paper/live 或自动执行路径；
- experiment persistence 仍为 NDJSON，不是新控制面。

后续整改不需要新增服务或编排层。需要补的是少量可验证 receipt 之间的确定性等价关系。

## 5. 已接受的实质整改

以下整改有明确代码和测试证据，可以保留：

1. Caller-supplied weights 已移除；`capture_decision_artifact` 由冻结 feature、definition 和 declarative adapter 字节计算权重。
2. Universe 不再接受调用方 inclusion decisions；固定 `lifecycle_eligible` 规则覆盖完整 source partition。
3. A 股 raw split、现金分红和 terminal recovery 已进入 shares、average cost、pending cash 和 NAV。
4. Base/adverse regulatory fee 和 slippage 会进入两次实际组合模拟。
5. Pre-open retry intent 与 post-open `NoFillEvent` 已分离。
6. Package code SHA 和 active settings SHA 改为内部计算。
7. Persistent experiment ledger、完整 multiplicity family、HAC/block bootstrap、dataset semantic hashes 和 candidate stage identity 已接入。
8. Generic、retrospective 和 gross-only 结果均显式降级。
9. Suspension、limit regime、T+1、结算和路径身份等原有 fail-closed 未被削弱。
10. 所有授权字段继续固定为 false。

## 6. 可靠性矩阵

| 控制项 | 结论 | 说明 |
|---|---|---|
| 主线仓/数据所有者/证据边界 | PASS | 单一主线、单一数据所有者、独立证据边界。 |
| 最小系统复杂度 | PASS | 没有恢复归档控制面或交易执行层。 |
| 默认 fail-closed | PASS | 证据等级不足时降级，授权持续为 false。 |
| 决策和执行时序 | SUBSTANTIAL_PASS | 决策、执行、未成交和结算事件已明显加强。 |
| PIT 业务值数据血缘 | FAIL | Provider receipt 未证明具体业务字段从该资产解析。 |
| 存活偏差 | PARTIAL_PASS | 完整 partition 和固定规则已实现，真实 status 值仍缺 typed binding。 |
| 标签跨 split | PARTIAL_PASS | Purge/embargo primitives 存在，SplitManifest 仍可手工伪造。 |
| 测试集参与选参 | FAIL | Holdout family 可拆分或在访问后扩展。 |
| 多重检验 | FAIL | Family 边界和 anchor 仍可由调用方选择。 |
| 重叠收益 | FAIL | 估计器会运行，但 evaluation plan、样本顺序和 p-value 绑定不完整。 |
| 交易成本和流动性 | PARTIAL_PASS | Base/adverse/capacity 强制，真实校准证据仍外部待验。 |
| 公司行动 | PARTIAL_PASS | Raw 会计实现，adjusted price unit 仍不安全。 |
| 数据快照绑定 | PARTIAL | 字节哈希显著增强，partition PIT receipt 和 verified loader 尚缺。 |
| 跨进程可复现 | FAIL | 关键对象依赖进程内 token，缺 canonical run bundle。 |
| 独立证据验收 | BLOCKED | QF-014 仍缺独立 reviewer receipt。 |

## 7. 详细发现

### RA3-001 — Provider source bytes 未绑定实际业务字段 `[HIGH]`

**文件/函数**

- `data/source_identity.py::capture_github_release_asset`
- `backtest/event_loop.py::ExecutionInput`
- `backtest/event_loop.py::_require_candidate_sources`
- `markets/universe.py::StatusEvidence`
- `backtest/capacity.py::CapacityObservation`
- `data/calendar.py::AcceptedSession`
- `data/source_identity.py::CorporateActionIdentity`

**触发条件**

取得一份 `PROVIDER_QUALIFIED_CAPTURE`，随后手工构造与资产字节不一致的 open、decision price、session、status、volume、amount 或 action 字段。

**影响**

当前 grade 只证明某个 provider 资产存在，不证明回测字段由该资产解析。错误或事后修改的业务值仍可能获得 `CONTROLLED_CANDIDATE_INPUT`。

**代码证据**

- Provider adapter 返回原始 bytes 和 SourceIdentity，不返回 typed row receipt；
- Candidate gate 只检查对象携带的 source capture level；
- 行情、状态、容量、日历和 action 值由调用方独立传入。

**最小修复**

仅针对实际使用的数据族实现 `TypedObservationReceipt`：由 exact provider bytes 解析 typed row，绑定 parser code SHA、schema、row payload SHA 和 available_at。Candidate runner 只接受由该 receipt 构建的对象。

**回归测试**

- Provider bytes 中 open=10，手工提交 open=20 必须失败；
- status、volume、amount、action date/amount 与源字节不一致时必须在 portfolio mutation 前失败；
- parser code 或 schema 改变必须改变 row receipt 和 stage identity。

### RA3-002 — `SplitManifest` 可直接伪造 `[HIGH]`

**文件/函数**

- `research/splits.py::SplitManifest`
- `research/splits.py::build_split_manifest`
- `research/splits.py::evaluate_split`
- `research/identity.py::capture_dataset_manifest`
- `backtest/event_loop.py::run_candidate_rebalance`

**触发条件**

直接实例化一份事后选择 samples 的 `SplitManifest`，并把 dataset 中登记的 SHA 填入 `manifest_sha256`。

**影响**

可以改变 label end、fold、overlap group 或测试样本，却继续声称与冻结 split 一致；purge、embargo 和重叠收益控制可被绕过。

**代码证据**

- `SplitManifest` 没有私有 token 或 `__post_init__` 重算；
- `evaluate_split` 不重算 manifest hash；
- Candidate 只比较 evaluation 中的 manifest SHA 字符串；
- Dataset manifest 哈希任意 split 文件字节，但不加载和验证样本内容。

**最小修复**

增加受控构造、canonical serializer 和 verified loader；每次 evaluation 前重算样本 payload。Dataset 应绑定 canonical split receipt，而不是任意文件裸 SHA。

**回归测试**

- 手工构造且自填摘要的 manifest 必须失败；
- 改变 entity、observed_at、label_end 或 fold 后旧摘要必须失效；
- 磁盘 split receipt 与内存样本不一致时 candidate 必须失败。

### RA3-003 — Multiplicity family 可拆分或在 holdout 后扩展 `[HIGH]`

**文件/函数**

- `research/experiments.py::preregister_trial`
- `research/experiments.py::record_holdout_result`
- `research/experiments.py::require_adjusted_holdout_for_candidate`
- `research/experiments.py::persist_experiment_ledger`

**触发条件**

先读取 family 内一个 trial 的 holdout，再补登记其他 trial；或者对同一 dataset/split/holdout 建立多个 `family_size=1` 的 family，只提交赢家。

**影响**

Holm/Bonferroni 在单个 family 内可正确重算，但全部研究尝试仍可低报，测试集参与选参和多重检验偏差仍存在。

**代码证据**

- 首个 HOLDOUT_RESULT 后仍未禁止新增 preregistration；
- family ID 和 size 由调用方选择；
- Candidate 只检查被选 family；
- external anchor 只是 64 位字符串，没有 receipt 内容验证；
- ledger path 可由调用方另开多份。

**最小修复**

由 dataset+split+stage plan 派生稳定 `holdout_id`。同一 holdout 只能有一个完整 family contract；任何 holdout access 前必须登记完整 family，首次 access 后禁止新增 trial。使用一个配置绑定的 canonical ledger，并验证 `AnchorReceipt` 确实覆盖访问前 head。

**回归测试**

- 首个 HOLDOUT_RESULT 后追加 trial 必须失败；
- 同一 holdout 创建两个 singleton family 必须失败；
- 任意 SHA 不能代替包含 head 和可信时间的 anchor receipt。

### RA3-004 — Holdout p-value/result 未绑定 evaluation 和最终 stage `[HIGH]`

**文件/函数**

- `research/experiments.py::record_holdout_result`
- `research/experiments.py::require_adjusted_holdout_for_candidate`
- `research/splits.py::evaluate_split`
- `backtest/event_loop.py::run_candidate_rebalance`

**触发条件**

对无显著性的 returns 生成 SplitEvaluation，同时手工提交有利的 raw p-value、adjusted p-value 和任意 result SHA。

**影响**

Multiplicity adjustment 可形式正确，但无法证明原始 p-value 来自该 statistic、该 returns 或完整 stage chain。

**代码证据**

- SplitEvaluation 保存 statistic、SE 和 returns SHA，但不内部计算 raw p-value；
- `record_holdout_result` 接受调用方提交 raw p-value 和 result SHA；
- Candidate 没有比较 holdout result 与 SplitEvaluation receipt 或 final stage hash。

**最小修复**

增加 `HoldoutResultReceipt`，由完整 stage-plan final hash、冻结 returns artifact、SplitEvaluation 和内部计算的 p-value 派生。外部不再直接提交 p-value 或任意 result SHA。

**回归测试**

- 弱 returns 配手工 p=0.001 必须失败；
- 改变 returns、estimator 或 final stage hash 后旧 receipt 必须失效；
- 未完成完整 stage plan 时不得生成 holdout result。

### RA3-005 — HAC/bootstrap 的样本顺序和参数未预注册 `[HIGH]`

**文件/函数**

- `research/splits.py::build_split_manifest`
- `research/splits.py::evaluate_split`
- `research/experiments.py::ExperimentEvent.parameters_json`
- `backtest/event_loop.py::run_candidate_rebalance`

**触发条件**

看到 returns 后改变 selected IDs 的顺序/子集、HAC bandwidth、block length 或 bootstrap replicates。

**影响**

HAC 和 bootstrap 依赖顺序与参数；研究者仍可在测试集上选择更有利的标准误。同日多证券样本还可能被错误地作为一条时间序列。

**代码证据**

- Manifest 最终按 sample_id 哈希排序，不按 observed_at；
- Evaluation 按调用方 selected IDs 顺序消费 returns；
- 估计器参数没有与 preregistration 结构化对账；
- Candidate 不验证 `parameters_json` 与实际 evaluation plan 一致。

**最小修复**

增加 holdout 前冻结的 `SplitEvaluationPlan`：ordered sample IDs、evaluation unit、method、bandwidth/block length、replicates 和 panel aggregation/clustering policy。Evaluation 使用 sample_id→return 映射并按规范时间顺序取值。

**回归测试**

- 同一 sample-return 映射仅改变输入顺序时结果必须相同；
- Holdout 后改变估计器参数或样本集合必须失败；
- 同日面板样本必须使用明确聚合或聚类政策。

### RA3-006 — Dataset partition 缺 PIT source receipt `[HIGH]`

**文件/函数**

- `research/identity.py::DatasetManifest`
- `research/identity.py::capture_dataset_manifest`
- `backtest/event_loop.py::run_candidate_rebalance`

**触发条件**

哈希本地 partition 和 semantic 文件，并自行填写合法 `source_snapshot_sha256s`；其余 runtime sources 使用 provider-qualified receipt。

**影响**

Partition 可包含未来修订数据或 decision-at 后才可获得的数据，却仍可能满足 `has_captured_semantics` 并进入 controlled grade。

**代码证据**

- Source snapshots 是裸 SHA 字符串；
- Partition 只绑定字节哈希，无 SourceIdentity、available_at、provider 或 parser identity；
- Controlled grade 只要求 runtime source、decision artifact source 和 captured semantics。

**最小修复**

Dataset manifest 保存每个 source snapshot/partition 的 typed source receipt、available_at、provider qualification、parser/schema identity 和 dataset as-of，并逐分区验证。

**回归测试**

- Partition available_at 晚于 dataset as-of 时失败或降级；
- 无 source receipt 的 partition 不能获得 controlled grade；
- parser/schema 漂移必须改变 dataset identity。

### RA3-007 — Receipt 无法跨进程稳定重放 `[HIGH]`

**文件/函数**

- `data/source_identity.py::SourceIdentity`
- `backtest/event_loop.py::DecisionArtifact`
- `markets/universe.py::UniverseMaterialization`
- `research/identity.py::DatasetManifest`
- `research/splits.py::SplitEvaluation`
- `research/experiments.py::persist_experiment_ledger`

**触发条件**

进程 A 完成运行后退出；进程 B 只凭磁盘文件和摘要尝试恢复相同研究证据。

**影响**

关键对象依赖模块内 object token，公开 API 没有 canonical save/load/verify。Provider adapter 又把当前下载时间写入 receipt，同一 immutable asset 重取会改变 identity。Experiment ledger 只保存 event hash，不能恢复 event payload。

**最小修复**

提供 canonical run-bundle JSON/NDJSON 和 verified loaders，保存完整 receipt payload。把稳定 source identity 与 acquisition audit 分开，或复用 persisted receipt。无需新增 manager。

**回归测试**

- 子进程 A 保存 bundle，子进程 B 加载后得到相同 input/stage hash；
- 再次下载同一 immutable asset 不改变稳定 source identity；
- 任一 receipt 字段或底层文件篡改必须在加载时失败。

### RA3-008 — A 股复权价可进入现金/股数引擎 `[HIGH]`

**文件/函数**

- `markets/a_share.py::AShareAdjustmentReceipt`
- `backtest/event_loop.py::_require_a_share_adjustment_receipt`
- `backtest/event_loop.py::_decision_price`
- `backtest/event_loop.py::_fill`
- `backtest/event_loop.py::_marks`

**触发条件**

非公司行动交易日使用 qfq、hfq 或 total-return 作为 decision/open/mark 价格。

**影响**

复权价不是原始可成交现金单位。当前 sizing、现金和 NAV 未按 adjustment factor 转回 raw units，可能产生错误股数和回报。

**代码证据**

- Action day 已强制 raw，这是正确改进；
- 非 action day 仍允许 adjusted basis；
- `_decision_price` 对无 action 的 adjusted basis 原样返回；
- `_fill` 和 `_marks` 不读取 adjustment factor。

**最小修复**

最轻量且最安全的方案：portfolio/execution/cash engine 只接受 raw executable prices；qfq/hfq/total-return 只允许进入 feature snapshot。

**回归测试**

- Candidate execution 使用 adjusted basis 且无 raw conversion receipt 时必须失败；
- Raw 与明确 factor conversion 路径必须产生相同股数、现金和 NAV。

### RA3-009 — Calendar revision rows 未逐行检查 capture level `[MEDIUM]`

**触发条件**

Revision identity source 为 provider-qualified，但其中一个 AcceptedSession.source 为 generic/manual。

**影响**

美股结算日可能依赖未受信 revision row，却仍被整体判断为 provider-qualified。

**最小修复和测试**

把预验证的 revision rows 全部加入 provider qualification；provider-qualified aggregate + generic row 必须降级或失败。

### RA3-010 — 下一次 retry 未强制晚于上一 no-fill observed time `[MEDIUM]`

**触发条件**

上一 no-fill 证据晚到，下一交易日 retry instruction 时间早于该证据 `observed_at`。

**影响**

系统可在尚不知道上一次未成交时记录下一次重试，形成因果倒序。

**最小修复和测试**

第 N+1 个 retry instruction 必须满足 `decision_at > 第 N 个 no_fill_event.observed_at`。晚到证据跨过下一 open 时，预先生成的 retry 必须失败。

### RA3-011 — Ingest lineage 未保存 capture level，owner 仍为调用方标签 `[MEDIUM]`

**文件/函数**

- `data/writer.py::_source_identity_json`
- `data/writer.py::_bind_target_contract`
- `cli.py::main`

**影响**

数据库 receipt 无法直接判断 generic/provider-qualified；canonical owner 虽首次绑定后不可变，但不是实际权限边界。

**最小修复和测试**

Metadata 显式保存 capture level；target contract 规定最低 grade；owner 从配置或包常量派生。Generic/provider-qualified 必须可区分，不符合最低 grade 的 batch 必须失败。

### RA3-012 — 运行参数和完整 stage 完成状态未逐项对账 `[MEDIUM]`

**触发条件**

Holdout 后改变 max_positions 或未结构化绑定的运行配置，或者只执行 stage plan 的一部分。

**影响**

Stage hash 会记录实际参数，但 PASSED holdout evidence 不一定针对同一完整配置和完整计划。

**最小修复和测试**

增加小型 `CandidateRunConfig` receipt，绑定 max_positions、成本、universe、decision、split plan 和完整 StagePlan。HoldoutResult 只接受 final stage。改变配置或未到 final stage 必须失败。

## 8. 最小收口架构

继续保持单仓、单数据所有者和单证据边界。只需要六类小对象：

1. `TypedObservationReceipt`：provider bytes → typed market row；
2. Canonical `SplitManifest` + `SplitEvaluationPlan`；
3. `HoldoutResultReceipt`：final stage + returns + estimator → 内部 p-value；
4. 一个 canonical experiment NDJSON + `AnchorReceipt`；
5. 一个 canonical run bundle + verified loaders；
6. A 股 portfolio/execution engine raw-only。

这些是数据和证据关系，不是 manager、registry 或 workflow system。

## 9. 再审关闭条件

再次申请“可靠个人量化研究流程”外审前，至少需要：

- Typed provider row receipts 覆盖实际使用的数据族；
- Source snapshots/partitions 均有 PIT available_at 和 parser identity；
- SplitManifest 无法手工伪造；
- Evaluation plan 在 holdout 前冻结；
- p-value/result 自动来自冻结 evaluation 和 final stage chain；
- 同一 holdout 无法拆成多个 singleton family；
- 任何 holdout result 后无法新增 preregistration；
- Receipt bundle 可在新进程加载并重放相同 stage hash；
- A 股 execution/portfolio 只使用 raw price units；
- QF-014 获得独立 reviewer receipt；
- 真实成本、公司行动、universe 和执行证据另行验收。

## 10. 最终建议

- 维持 PR Draft；
- 如果 PR 声称全部整改完成，则继续 `REQUEST_CHANGES`；
- 如果改名为基础设施强化，可以合并，但不得升级策略或资金授权；
- 不新增 manager、dispatcher、registry、第二套 writer 或 broker 路径；
- 下一轮只修复本报告列出的证据连接，不做无关重构。
