# PR #126 Round 6 统一外部审查报告

> 本报告只审查冻结代码提交 `938aada03f819d98cbf7c9ac627a8c77326ed312`。  
> 后续仅用于保存本报告的文档提交不属于被审代码范围。

## 1. 冻结边界

- Repository: `2604714984-prog/quant-proj`
- PR: `#126`，Draft / open / not merged
- Base: `v2-main@31329dbfd7b9bb1c184a13ee7fe2e60bd0a6ba14`
- Previous audited code: `81403aa223ad6d11a7339fd970b65512bdc0a5c8`
- Audited code head: `938aada03f819d98cbf7c9ac627a8c77326ed312`
- CI merge ref: `7d076d51eb70cdbcfd41a1360fd4f14c3fb958df`
- GitHub Actions run: `30062113832` — `completed/success`
- Audit date: `2026-07-24`

本轮是在此前全仓逐文件审查基础上的增量外审。比较 `81403aa..938aada` 共 16 commits、15 个 changed files；全量读取所有变更生产文件、较小测试文件以及大型测试的本轮变更和关键正向路径，并对关键合同执行独立最小复现。外审没有写入项目/生产数据库，没有调用市场数据 provider，没有修改被审代码。

## 2. 仓库和数据边界

- PR head 是候选主线研究核心，不是归档仓或交易执行仓。
- Mutable canonical data 仍位于外部 `QUANT_DATA_ROOT`。
- Prospective tree 中只有 `src/quant_system/data/writer.py` 拥有 canonical 写入职责。
- Experiment ledger 是研究证据状态，不是第二 canonical writer。
- A 股 evidence room 仍是独立证据边界。
- Broker、paper/live 和自动执行不在当前范围。

Prospective tree 的拓扑已经恢复轻量：一个主线、一个数据所有者、一个证据边界，无 manager、dispatcher 或 registry。

## 3. 外审裁决

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

本轮接受 Stage 日期修复、受控 stage receipt、Family/Trial 分离、完整 ledger 恢复、纯转换、horizon return、统计估计器和 CI artifact 等整改。但独立复现确认 4 个会改变研究结论的代码问题，因此不能接受“代码已完成，只剩外部证据”。

问题计数：

```text
HIGH=4
MEDIUM=2
LOW=1
BLOCKED_EXTERNAL=3
```

## 4. 已接受且不应回滚的整改

1. Active archive、旧结果和 direct DuckDB writers 已从 prospective tree 删除；全树边界测试限制唯一 writer。
2. StagePlan 的 signal/execution 日期矛盾已修正，并加入真实 `run_controlled_stage` 五阶段测试。
3. `ControlledStageReceipt` 可序列化、加载并重新执行成交、portfolio 和 NAV；FinalRun 检查 engine、顺序和 portfolio continuity。
4. FamilyContract 与 TrialConfig 已分离；一个 family 可以登记不同 DecisionArtifact。
5. Experiment ledger 保存完整 canonical event payload，并可在新进程恢复后继续追加。
6. Transformation 改为受控纯操作；feature 与 label 分别生成后 deterministic join。
7. ReturnArtifact 不再接受外部 return mapping；SplitEvaluation 可按 horizon 复合收益并执行 Student-t、HAC 和 centered block bootstrap。
8. CI 发布了可下载 wheel artifact；artifact archive digest 和 wheel SHA 已独立验证。

# 5. P0 发现

## R6-001 — 收益归属于上一期持仓，却被标记为本期目标组合 `[HIGH]`

**文件/函数**

- `src/quant_system/backtest/event_loop.py::run_static_rebalance`
- `src/quant_system/research/splits.py::capture_return_artifact`
- `src/quant_system/research/splits.py::evaluate_split`

**触发条件**

上一执行日持有 A，本期执行日前 A 发生价格变化，而本期目标切换为 B；或存在未退出残余持仓。

**实际影响**

从上一 portfolio mark 到本期 execution 产生的损益，被 `ReturnObservation.contributors` 标记为本期 target weights，而不是实际产生损益的上一期持仓。样本、标签、策略归因和统计显著性均会错位。第一期通常只记录建仓成本，最后一个信号的后续持有收益又没有 terminal valuation。

**代码事实**

- event loop 在本期交易前保存 initial portfolio，再按本期 target weights 交易并计算 final NAV。
- ReturnArtifact 用 initial→final NAV 计算收益，却从本期 `target_weights` 生成 contributors。
- 现有真实多阶段测试每期始终持有 AAA，无法发现换仓错位。
- 独立复现：上一期持有 AAA，AAA 从 10 涨至 20，本期开盘切换到 BBB；系统输出 `return=100%`、`contributors=('BBB',)`。

**推断**

当前收益数值可能来自真实 NAV，但时间归属和证券归属不一定对应被检验 sample。

**最小修复**

明确定义 execution-to-next-execution 收益期：第 t 个 DecisionArtifact 形成的执行后持仓，由第 t+1 个 execution mark 结束，收益归属于第 t 个实际持仓/权重。ReturnObservation 保存 interval start/end、opening exposure、closing holdings、外部现金流和成本。FinalRun 增加 terminal valuation。

**回归测试**

- 交替 AAA/BBB 的真实三阶段测试；AAA 在切换前上涨，收益必须归给上一期 AAA。
- blocked exit 和残余持仓必须进入 exposure receipt。
- 第一期建仓成本和后续持有收益分开；最后一期有 terminal mark 或明确排除。

---

## R6-002 — 历史 TrialConfig 未绑定实际策略定义、特征快照和 DatasetManifest `[HIGH]`

**文件/函数**

- `src/quant_system/research/experiments.py::TrialConfig`
- `src/quant_system/research/experiments.py::evaluate_frozen_historical_run`
- `src/quant_system/backtest/event_loop.py::ControlledStageReceipt`
- `src/quant_system/backtest/event_loop.py::DecisionArtifact`

**触发条件**

TrialConfig 声明策略 A 的 definition/参数，但历史 stage receipts 实际来自策略 B；或 DecisionArtifact 只携带与真实 DatasetManifest 无关的 dataset identity 字符串。

**实际影响**

策略 A 可以借用策略 B 的历史收益、p-value 和 holdout 结果。当前 replay 能证明已提交 weights 产生这些成交，不能证明 weights 由 TrialConfig 声明的 definition、feature 和 dataset 生成。

**代码事实**

- TrialConfig 保存 `definition_sha256` 和 parameters。
- 历史评估比较 stage plan、split、ordered decision/universe SHA、dataset/cost/engine 标签，但没有比较 definition、parameters 或 max_positions 与 stage replay 的实际策略配置。
- Stage receipt 没有保存可重新执行的历史 feature/definition/adapter artifact 集合。
- 历史评估不接收并验证 DatasetManifest，也不证明 feature snapshot 由该 dataset partition 产生。
- 独立复现把 TrialConfig definition 改为 `f`×64，而实际 stage definition 为另一 SHA；历史评估仍成功。

**最小修复**

在 run-level manifest 保存每阶段可重放 DecisionArtifact payload：feature、definition、adapter、decision_at、dataset/split identity 和来源 receipt。历史评估重新执行 feature→weights，并比较 stage weights；同时传入并验证 DatasetManifest，feature snapshot 必须由其 partition/TransformationReceipt 产生。至少立即比较 stage replay 中的 definition、adapter 和 max_positions 与 TrialConfig。

**回归测试**

- 只改变 TrialConfig definition 或 threshold 必须失败。
- 相同 weights、不同 definition/feature bytes 不得共用历史资格。
- 替换 DatasetManifest、partition 或 feature snapshot 后旧 TrialRunReceipt 失效。

---

## R6-003 — 历史阶段只绑定成本摘要，未证明执行使用对应成本和容量 `[HIGH]`

**文件/函数**

- `src/quant_system/backtest/event_loop.py::run_controlled_stage`
- `src/quant_system/backtest/event_loop.py::ControlledStageReceipt`
- `src/quant_system/research/experiments.py::evaluate_frozen_historical_run`

**触发条件**

传入某个非零 ExecutionCostAssumptions SHA，但 portfolio 使用零佣金/零税费、slippage=0 或不同 capacity policy。

**实际影响**

零成本历史收益可以声称绑定现实成本假设，并进入统计和 holdout；历史 adverse case 也没有作为完整收益路径被评估。

**代码事实**

- `run_controlled_stage` 接收裸 `cost_assumptions_sha256`，同时独立接收 portfolio costs、capacity policy 和 slippage。
- 函数没有从实际成本对象计算该 SHA，也没有核对 replay artifact 中的真实成本设置。
- 历史评估只检查 receipt 成本 SHA 等于 TrialConfig 成本 SHA。
- 独立复现使用非零成本假设 SHA，但 replay 中 commission、tax、slippage 均为 0；评估仍成功。
- 仓库真实多阶段测试同样传入非零成本 identity，但 portfolio 为零成本且未传 slippage。

**最小修复**

`run_controlled_stage` 接受实际 ExecutionCostAssumptions/CostStressCase，内部配置 portfolio、capacity 和 slippage，并从对象计算 identity。历史验证保存 base 与 adverse 两条完整 FinalRun/ReturnArtifact，或明确用 adverse 作为晋级门。

**回归测试**

- 非零成本 identity + 零成本执行必须在执行前失败。
- 逐笔 commission/tax/slippage 与 CostStressCase 对账。
- gross-only 结果不能被标为 net validation。

---

## R6-004 — RT-001 仍可通过共享 raw bytes 和未覆盖字段引入前视 `[HIGH]`

**文件/函数**

- `src/quant_system/research/identity.py::replay_pure_transformation_artifacts_bytes`
- `src/quant_system/research/identity.py::_pure_step_bytes`
- `src/quant_system/research/identity.py::_validate_partition`
- `src/quant_system/research/identity.py::_row_pit_enforced`

**触发条件**

同一 raw source 同时包含历史特征和未来标签；feature spec 把未来标签列重命名为 score，同时输出一个无关但合格的 `safe_feature_available_at`。

**实际影响**

Receipt 得到 `row_pit_enforced=true`，输出确定且可重放，但特征仍使用未来信息。Discovery 和未来 provider-qualified validation 都会受影响。

**代码事实**

- feature 和 label steps 接收同一组 `raw_bytes`。
- 投影/rename 没有字段级 provenance 与 availability 映射。
- `_row_pit_enforced` 只要求存在任意 `*feature_available_at` 和 observed_at/decision_at。
- `_validate_partition` 不证明每个 feature column 对应哪个 source field/availability field。
- DatasetManifest 不逐行核对 partition sample_id/observed_at/label_end_at 与 SplitManifest。
- 独立复现将 `future_label=123` 重命名为 score，另附安全 availability 字段；输出 `score=123` 且 `row_pit_enforced=true`。

**最小修复**

分离 `feature_raw_sources` 与 `label_raw_sources`，feature step 不得读取 label raw bytes。候选级 feature artifact 强制 sample_id、decision_at/observed_at 和唯一 max_feature_available_at，并验证 `max_feature_available_at <= decision_at < label_end_at`。若允许 rename，spec 必须声明每个输出 feature 的 source field 和 availability field。DatasetManifest 逐行对账 SplitManifest。

**回归测试**

- Feature 读取 label-only source 或 future label 字段时失败。
- 一个安全 availability 字段不能掩盖另一个无 provenance feature。
- Partition 与 SplitManifest 的 sample/time 任一不一致时失败。

# 6. 吞吐和发布问题

## R6-005 — Stage receipts 重复内嵌共享日历并多次 replay `[MEDIUM]`

每个 stage receipt 的 replay artifact 重复保存整份 calendar；构造、capture、FinalRun、ReturnArtifact 和 TrialRun 又多次调用 replay。独立测量：6 sessions 约 32,979 bytes，50 sessions 约 122,365 bytes，200 sessions 约 427,767 bytes。由于每个 stage 都保存 N-session calendar，整个 N-stage run 呈 O(N²) 存储增长（推断）。

**最小修复：** 使用共享 RunContextManifest，calendar/dataset/universe/engine/cost 只保存一次；stage 只引用共享 SHA。拆分 `verify_structure()` 与显式 `replay()`，Discovery 不重放，Validation/CI 每个 immutable stage 最多 replay 一次。

## R6-006 — 没有标准 research runner 和 repo-contained vertical slice `[MEDIUM]`

当前 CLI 只有 `info` 和 `data inspect/query/append`；active tree 没有当前策略 spec 或正式 exploratory report。用户报告的 FRED 切片仅验证 generic transformation，并未形成可复核策略回测、ReturnArtifact 和紧凑报告。

**最小修复：** 下一独立小 PR 增加 `run_research(spec, mode='explore'|'verify')` 和一个 CLI 子命令，只实现一个窄数据源和一个简单策略，输出固定 PASS/FAIL/BLOCKED JSON。不要新增 manager、registry 或 provider platform。

## R6-007 — CI artifact 的 SHA256SUMS 路径不可直接校验 `[LOW]`

CI 执行 `sha256sum dist/*.whl | tee dist/SHA256SUMS`；artifact 解压后 wheel 位于根目录，但清单仍引用 `dist/...`。实际 wheel SHA 正确，直接 `sha256sum -c SHA256SUMS` 仅因路径错误失败。

**最小修复：** `(cd dist && sha256sum *.whl > SHA256SUMS)`，并增加下载后直接校验测试。

# 7. 独立复现摘要

```text
REPRO-R6-001
stage0 contributors=('AAA',), return=0.0
stage1 contributors=('BBB',), return=1.0  # 盈利实际来自前期 AAA
stage2 contributors=('AAA',), return=0.0

REPRO-R6-002
evaluate_frozen_historical_run succeeded
TrialConfig definition = f*64
actual stage definition = 2c74c9ba...f6f9c5
mismatch=True

REPRO-R6-003
declared cost SHA = 6c401ef3...
actual commission/tax/slippage = 0
historical evaluation succeeded

REPRO-R6-004
row_pit_enforced=True
future_label=123 -> score=123
```

数值实现附加核对：Student-t p-value 对 SciPy 测试网格最大绝对误差约 `4.31e-14`；HAC mean standard error 在测试序列上与 statsmodels 匹配到机器精度，因此本轮不将自研 Student-t/HAC 数值实现列为阻断项。

# 8. 量化完整性矩阵

| 控制项 | 判定 |
|---|---|
| 前视偏差 | `FAIL` — R6-004 |
| PIT 数据 | `FAIL` — 字段级 provenance/availability 未闭合 |
| 存活偏差 | `PARTIAL_PASS` — 机制有，真实 authoritative universe 未验 |
| 标签跨 split | `PARTIAL_PASS` — purge/horizon 有，partition 与 split rows 未逐行绑定 |
| 测试集参与选参 | `PASS_MECHANISM / EVIDENCE_BLOCKED` |
| 多重检验 | `PASS_MECHANISM`，但真实收益绑定受 R6-001/002 影响 |
| 重叠收益 | `PASS_ESTIMATOR / FAIL_INPUT_SEMANTICS` |
| 交易成本 | `FAIL_HISTORICAL_BINDING` — R6-003 |
| 流动性 | `PARTIAL` — 机制存在，真实绑定/校准待验 |
| 公司行动/退市 | `PARTIAL_PASS` — 会计机制较强，真实完整性待验 |
| 数据快照 | `PARTIAL` — bytes可重放，字段级信息集未闭合 |
| 策略身份 | `FAIL_HISTORICAL_BINDING` — R6-002 |
| 跨进程复现 | `PARTIAL_PASS` |
| 单一 writer | `PASS` |
| 研究吞吐 | `FAIL` |

# 9. 外部证据阻断

- `B6-001 BLOCKED_EXTERNAL_PROVIDER`：没有 authoritative provider adapter；public capture 正确停留在 GENERIC/TRANSPORT，因此 validation/candidate grade 暂不可达。
- `B6-002 BLOCKED_EXTERNAL_CALIBRATION`：真实成本、流动性、公司行动、退市和完整 PIT universe 未独立验收。
- `EA-001 BLOCKED_EXTERNAL_EVIDENCE`：A 股 evidence room 仍为 `PUBLISHED_UNVERIFIED_EXTERNALLY / PENDING_EXTERNAL_RECEIPT`。

FRED slice 没有被误标为候选，但其原始/派生资产不在本轮可访问范围，台账哈希未独立验证。

# 10. 最小整改顺序

## 当前 PR 只修 P0

1. R6-001：收益期和实际持仓归属。
2. R6-002：TrialConfig ↔ DecisionArtifact/feature/dataset 的真实绑定。
3. R6-003：实际成本/capacity/slippage ↔ 成本 identity。
4. R6-004：feature/label raw source 隔离和字段级 PIT provenance。

不要再增加安全或治理抽象。

## 下一小 PR 做速度

1. 共享 RunContextManifest；
2. cheap structural verify / explicit replay；
3. `run_research(spec, explore|verify)` + CLI；
4. 一个真实数据源、一个简单策略、一个紧凑 terminal report。

# 11. CI 与 artifact 证据

已独立确认：

- GitHub Actions run `30062113832` completed/success；
- wheel build/upload、install、pip check、外部 CLI、Ruff、pytest步骤成功；
- artifact id `8584900000` 对应 head `938aada...`；
- artifact ZIP SHA：`625c596fccf40fbc9d42ec9fd0a47b95fd2567b3ce23e3af66e9fea1a966dcbb`；
- wheel SHA：`0f7b925efeb9a356b4e2017ca27f320bc51aba382c6cf7d60110fbb9b37eee72`。

未独立确认：日志尾部精确 `273 passed`、提交者本地 87/273 测试、provider 请求数、FRED资产、生产校准和 EA-001 receipt。

# 12. 合并与授权建议

- PR 继续 Draft。
- 关闭 R6-001 至 R6-004 后冻结新代码 head 做聚焦复审。
- P1 吞吐优化不要继续塞入当前 PR。
- Provider、生产校准和 EA-001 完成前 validated/candidate 保持 BLOCKED；exploratory research 可继续。
- 所有资金和交易授权继续为 false。
