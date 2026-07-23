# PR #126 Round 4 最新统一外部审查报告

> 本报告只审查冻结代码提交 `d46a993d95b0b3454a10134c2ef822f17483ddc6`。  
> 将本报告提交到 GitHub 所产生的后续文档提交不属于被审代码范围，也不改变本报告结论。

## 1. 冻结边界

- 仓库：`2604714984-prog/quant-proj`
- PR：`#126`
- 分支：`agent/external-audit-codex-remediation-20260723`
- 基线：`35b3246e40f8315e2bbef847d995a3b6d3a3b4fc`
- 上一轮被审代码：`62300cdff8e300a43c0fc54b0fba2df0e456511f`
- 本轮被审代码：`d46a993d95b0b3454a10134c2ef822f17483ddc6`
- GitHub Actions merge ref：`6868d8dbc19310915797c8b0dd7353a7e7bee593`
- 独立证据室：`2604714984-prog/a-share-canonical-evidence-data-room@de38f03466a58b9c786ed35e2cc38abff3e9b0fe`
- 审查日期：`2026-07-23`
- 本轮仓库代码修改：`0`
- 本轮生产数据库写入：`未执行`
- 本轮市场数据 provider 请求：`未执行`

## 2. 外审裁决

```text
external_audit_verdict=REQUEST_CHANGES
lightweight_architecture=true
fail_closed_default=true
experimental_research_infrastructure=true

code_remediation_complete=false
only_external_evidence_remaining=false
capital_grade_research_process=false

strategy_candidate_available=false
recommendation_authorized=false
paper_trading_authorized=false
live_trading_authorized=false
automatic_execution_authorized=false
```

### 结论

该项目继续满足个人量化所需的**轻量架构**，并具备明显强于普通个人回测项目的 fail-closed 基础。

但本轮审查不能接受整改台账中的：

```text
code_remediation_complete_for_available_scope=true
only_external_evidence_remaining=true
```

本轮仍发现 **8 个 HIGH、3 个 MEDIUM** 代码级问题。主要断点不是缺少更多框架，而是现有 receipts 之间仍缺少以下确定性关系：

1. GitHub 存储资产不等于权威市场数据；
2. 执行限制和 halt 事件未全部进入 typed evidence；
3. 预注册 anchor 没有承诺实际 experiment head；
4. 同一 holdout 可通过新 ledger 被拆分；
5. holdout final-stage hash 未与实际完整运行对账；
6. 统计 p 值和面板抽样单位仍可能失真；
7. 派生数据 partition 没有 transformation receipt；
8. run bundle 只能重算哈希链，不能端到端重放结果。

因此，当前系统可继续作为**实验研究基础设施**，但不能升级为可信策略候选、推荐、paper/live 或个人资金部署依据。

## 3. 仓库角色与轻量化判断

### 仓库角色

- `quant-proj`：唯一活跃主线研究/回测代码仓，同时包含唯一 DuckDB append writer。
- `QUANT_DATA_ROOT/quant_research.duckdb`：外部 mutable canonical 数据对象。
- `a-share-canonical-evidence-data-room`：独立只读证据边界，不是第二个 writer。
- 归档仓：继续只读，不应恢复旧策略、manager、dispatcher、broker 或自动执行路径。

### 轻量化：通过

当前仍保持：

- 一个主线仓；
- 一个外部数据所有者；
- 一个独立证据室；
- 一个 CLI；
- 两个运行时依赖；
- 一套 canonical writer；
- 无 manager、dispatcher、ticket、registry、代理层；
- 无 broker、paper/live、自动执行。

本报告的修复建议均可在当前边界内完成，不需要新控制面。

## 4. 本轮接受的实质改进

以下机制有明确代码和测试证据，应保留：

- 权重由冻结 feature/definition/adapter 字节经唯一 declarative adapter 计算，caller weights 已移除。
- Universe 物化执行固定 `lifecycle_eligible` 规则并覆盖完整 source partition。
- A 股执行和组合会计已强制 raw price units；拆股、分红和 terminal recovery 进入 shares/cash/NAV。
- A 股 suspension 双证据、limit regime 完整性、blocked exit 的 pre/post-open 事件边界得到强化。
- Base/adverse 成本模型和容量证据进入候选 identity，gross/retrospective/generic 继续降级。
- `SplitManifest` 受控构造、canonical save/load 和哈希重算已经实现。
- 单链内完整 multiplicity family、Holm/Bonferroni 重算、HAC/block-bootstrap 实际估计器已经实现。
- DuckDB target contract、结构化 lineage、单 writer owner、输入/路径防护仍然保持。
- 没有恢复 manager、dispatcher、registry、broker、paper/live 或自动执行路径。

外审不通过不意味着应回滚上述改进。

## 5. 测试与执行证据

### 已独立确认

- PR 被审 head 为 `d46a993d95b0b3454a10134c2ef822f17483ddc6`，PR 仍为 Draft；
- 被审时 PR 共 50 commits、37 changed files；
- GitHub Actions run `30005183678` 为 `completed/success`；
- CI job 成功执行 wheel build/install、`pip check`、checkout 外 `quant info`、Ruff 和 pytest；
- CI checkout 的是 merge ref `6868d8dbc19310915797c8b0dd7353a7e7bee593`；
- evidence room 当前仍为 `PUBLISHED_UNVERIFIED_EXTERNALLY / PENDING_EXTERNAL_RECEIPT`。

### 未独立确认

- 本轮未在本地 checkout 运行 pytest 或 Ruff；
- PR/ledger 报告源码和安装 wheel 均为 `260 passed`，但 connector 未独立提取完整日志尾部；
- wheel SHA-256 `fe4b8b76fbee4b42ca0142e5be71865ee12f79fc84256f2d2a404449a41465da` 没有 CI artifact 可供重新哈希；
- “数据库写入 0、provider 请求 0、工作树干净”为整改执行记录，本轮外审无法观察其本地进程；
- 测试通过证明代码满足当前测试，不证明测试合同覆盖了全部研究欺骗路径。

## 6. 量化研究完整性复判

| 控制项 | 判定 | 说明 |
|---|---|---|
| 仓库角色与单一主线 | `PASS` | `quant-proj` 仍是主线研究/回测代码仓；外部 DuckDB 是单一数据对象；证据室独立。 |
| 轻量化 | `PASS` | 一个 CLI、两个运行时依赖、单 writer、无控制面或交易执行层。 |
| 默认 fail-closed | `PASS` | 所有授权仍为 false；generic/retrospective/gross-only 被显式降级。 |
| 前视偏差 | `PARTIAL` | 时间检查较强，但 halt/limit 自由字段和 final-stage 摘要仍可绕过完整因果链。 |
| PIT 数据 | `FAIL` | typed bytes 绑定存在，但 provider trust root 和 transformation lineage 未闭合。 |
| 存活偏差 | `PARTIAL_PASS` | 完整 partition + 固定 lifecycle rule 已建立；真实权威 status/partition 仍待验。 |
| 标签跨 split | `PARTIAL_PASS` | purge/embargo 与受控 manifest 已建立；跨 fold overlap 仍可遗漏。 |
| 测试集参与选参 | `FAIL` | 可新建独立事件链/ledger；external anchor 不承诺 preregistration head。 |
| 多重检验 | `FAIL` | 单 family 重算正确，但全局 family 边界仍可被拆分。 |
| 重叠收益 | `FAIL` | HAC/bootstrap 运行真实，但面板 evaluation unit 和 p-value 校准不正确。 |
| 交易成本与流动性 | `PARTIAL_PASS` | 机制强制且有 adverse case；真实校准证据仍未验证。 |
| 公司行动/退市 | `PARTIAL_PASS` | raw 会计已实现；真实 action completeness、pay date、recovery 仍外部待验。 |
| 数据快照与血缘 | `FAIL` | 文件哈希完整，但派生分区没有 transformation receipt。 |
| 跨进程可复现 | `PARTIAL` | 可重算已提交哈希链，不能从 bundle 重算完整输入、成交与 NAV。 |
| 独立证据验收 | `BLOCKED` | EA-001/QF-014 仍为 `PENDING_EXTERNAL_RECEIPT`。 |

# 7. 详细发现

## RA4-001 — GitHub Release 传输层被当成市场数据权威来源 `[HIGH]`

**映射既有问题：** `RA3-001`、`RA3-003`、`RA3-006`

**文件/函数：**

- `src/quant_system/data/source_identity.py::capture_github_release_asset`
- `src/quant_system/data/source_identity.py::require_provider_qualified_source`
- `src/quant_system/backtest/event_loop.py::_require_candidate_sources`
- `src/quant_system/backtest/event_loop.py::run_candidate_rebalance`

**触发条件：** 调用方在任意自己控制的 GitHub 仓库或 Release 中发布市场观察、数据分区或“预注册锚点”，再调用 `capture_github_release_asset`。

**实际影响：** GitHub 只证明某个账号在某时上传了某些字节，不证明这些字节来自交易所、行情商、公告源或独立时间戳服务。当前代码仍会把该资产标记为 `PROVIDER_QUALIFIED_CAPTURE`，并可能使接口升级为 `CONTROLLED_CANDIDATE_INPUT`。自有证据可被错误地当成独立外部证据。

**代码事实：**

- `capture_github_release_asset` 接受任意 owner/repository、tag 和 asset name。
- 该函数固定写入 `provider_id='github-releases'` 和 `capture_level='PROVIDER_QUALIFIED_CAPTURE'`。
- `require_provider_qualified_source` 只检查模块 token/capture level，不检查市场数据权威身份或仓库信任根。
- 候选接口的 provider-qualified 判定直接依赖所有 `source.is_provider_qualified_capture`。

**推断：** typed row 绑定解决了“业务值是否等于资产字节”，但没有解决“谁有资格声明这些资产字节是市场事实”。

**假设：** 用户或未来 adapter 可以选择任意 GitHub Release 作为数据来源。

**最小修复：** 将 GitHub Release 降为 `TRANSPORT_CAPTURE` 或 `EXTERNAL_ARTIFACT_CAPTURE`。只有数据族专用 adapter 才能产生 `AUTHORITATIVE_PROVIDER_CAPTURE`；adapter 应固定权威域名、provider identity、subject schema 和发布时间语义。实现可用一个小型不可变 trust policy，不需要通用 registry 或控制面。

**回归测试：**

- 用户自有 GitHub Release 不得产生市场数据或预注册的 authoritative grade。
- 未知仓库、未知 provider/data-family 只能得到实验级 transport receipt。
- 只有固定权威 adapter 返回的内容才能进入 controlled candidate grade。

## RA4-002 — 涨跌停、limit regime 与 halt/no-open 声明未被 typed receipt 绑定 `[HIGH]`

**映射既有问题：** `RA3-001`、`QF-007`、`QF-009`

**文件/函数：**

- `src/quant_system/backtest/event_loop.py::ExecutionInput`
- `src/quant_system/backtest/event_loop.py::_require_candidate_typed_values`
- `src/quant_system/backtest/event_loop.py::_inputs`
- `src/quant_system/markets/a_share.py::decide_fill`

**触发条件：** 在 execution-price typed receipt 不变时修改 `up_limit`、`down_limit`、`limit_regime`，或在缺失开盘价时手工加入 `action_types=('trading_halt',)`。

**实际影响：** 可把本应涨停不可买、跌停不可卖的订单变成成交，也可把无法解释的缺失行情声明为确认停牌。这会直接改变成交、持仓和回撤，且仍可能保留 provider-qualified grade。

**代码事实：**

- execution-price typed receipt 只绑定 basis、currency、effective_at、open_price 和 symbol。
- `up_limit`、`down_limit`、`limit_regime` 不在该 receipt 的 expected values 中。
- `confirmed_no_open_event` 只要求 `action_types` 包含 `trading_halt` 或存在 terminal action。
- `trading_halt` 这个自由字符串没有对应 `TypedObservationReceipt`；ordinary corporate action 和 terminal action 才有 typed receipt。
- `is_suspended` 会与 status evidence 交叉检查，这是已接受的改进，但不能替代 limit/halt evidence。

**推断：** 当前 typed evidence 覆盖价格，但未覆盖决定“是否能成交”的全部市场状态。

**假设：** A 股使用涨跌停约束，或美股/其他市场存在无开盘、halt 情况。

**最小修复：** 新增明确的 `a_share_execution_constraints` observation，绑定 `limit_regime`、`up_limit`、`down_limit`；新增 `market_no_open_event/halt` observation，绑定事件类型、effective time、observed time 和 subject。`action_types` 应从 typed events 派生，而不是由调用方自由填写。

**回归测试：**

- 保持 provider bytes 不变，单独修改上下限或 `no_limit` 声明必须在交易前失败。
- 缺失 open 但没有 typed halt/no-open receipt 时必须保持 unexplained gap。
- typed halt receipt 的 subject、时间或来源不匹配时不得阻止或解释成交。

## RA4-003 — 外部预注册锚点早于预注册且不承诺 experiment head `[HIGH]`

**映射既有问题：** `RA3-003`、`RA3-004`

**文件/函数：**

- `src/quant_system/research/experiments.py::ExperimentEvent`
- `src/quant_system/research/experiments.py::preregister_trial`
- `src/quant_system/research/experiments.py::require_adjusted_holdout_for_candidate`
- `src/quant_system/backtest/event_loop.py::run_candidate_rebalance`

**触发条件：** 提供任意在 `preregistered_at` 之前已存在的 provider-qualified source 作为 external anchor。

**实际影响：** 该 source 不可能承诺随后才创建的 trial、family、参数或 ledger head。任意无关资产都可满足 anchor 字段；代码无法证明策略和参数在 holdout 访问前已冻结。

**代码事实：**

- `preregister_trial` 要求 `external_anchor.available_at <= preregistered_at`。
- `ExperimentEvent` 只保存 external anchor SHA 和 capture level。
- 代码不解析 anchor 内容，也不验证其中包含 holdout ID、family contract 或 preregistration/ledger head。
- 候选 grade 只检查 anchor capture level 为 provider qualified。
- 当前测试 fixture 明确创建了比 preregistration 更早的 anchor。

**推断：** 这是一份“预先存在的引用”，不是对预注册状态的外部时间戳承诺。

**假设：** external anchor 的目标是证明预注册发生在 holdout access 之前。

**最小修复：** 改为两阶段：先完整登记 family 并持久化 preregistration head；再发布 `AnchorReceipt`，其内容必须包含 holdout ID、family size、参数摘要、ledger head 和 creation time；anchor availability 必须晚于 family freeze、早于首次 holdout access。

**回归测试：**

- 与 ledger head 无关的 provider-qualified 资产不得充当 anchor。
- anchor 早于 family freeze 或晚于 holdout access 时必须失败。
- 修改 family、参数或 head 后旧 anchor receipt 必须失效。

## RA4-004 — 同一 holdout 仍可通过新事件链和新 ledger 路径拆分多重检验族 `[HIGH]`

**映射既有问题：** `RA3-003`、`QF-004`

**文件/函数：**

- `src/quant_system/research/experiments.py::_validate_chain`
- `src/quant_system/research/experiments.py::preregister_trial`
- `src/quant_system/research/experiments.py::persist_experiment_ledger`
- `src/quant_system/research/experiments.py::require_adjusted_holdout_for_candidate`

**触发条件：** 对同一 dataset/split 从 `events=()` 重新开始，并为每个策略使用不同 NDJSON 路径或不同进程；最后只提交获胜链。

**实际影响：** 单条链内部的 Holm/Bonferroni 和 family 完整性是正确的，但全局试验次数仍可被低报。多个 singleton family 可把多重检验重新伪装成单次检验。

**代码事实：**

- 同一 dataset/split 只允许一个 family 的检查范围局限于调用方传入的 events tuple。
- `persist_experiment_ledger` 的 path 由调用方任意指定。
- 没有配置绑定的 canonical ledger，也没有跨 ledger 的 holdout ID 唯一约束。
- 候选入口只验证所提供 ledger 与所提供 manifest，不搜索其他 ledger。

**推断：** append-only 是局部性质；没有全局唯一边界时，失败实验仍可通过新链被遗忘。

**假设：** 个人研究会重启进程、建立多个实验文件或测试多个策略家族。

**最小修复：** 在 `QUANT_DATA_ROOT` 下固定一个 canonical experiment ledger，按 `holdout_key=hash(dataset+split+stage plan)` 建立不可重复 family contract。所有试验必须追加到该文件；首次 holdout access 后冻结该 key。这只是一个 NDJSON 文件及文件锁，不需要 manager/registry。

**回归测试：**

- 新进程尝试为同一 holdout key 创建第二个 ledger/family 必须失败。
- 两个 singleton family 不能替代一个 `family_size=2` 的合同。
- 删除或遗漏历史失败 trial 后不能匹配外部 anchor head。

## RA4-005 — completed final-stage hash 是预先提交的自由摘要，未与当前实际 stage 结果对账 `[HIGH]`

**映射既有问题：** `RA3-004`、`RA3-012`、`QF-011`

**文件/函数：**

- `src/quant_system/backtest/event_loop.py::CandidateRunConfig`
- `src/quant_system/backtest/event_loop.py::capture_candidate_run_config`
- `src/quant_system/backtest/event_loop.py::run_candidate_rebalance`
- `src/quant_system/research/experiments.py::capture_holdout_result`

**触发条件：** 在运行前为 `completed_final_stage_hash` 填入任意合法 SHA，并让 `HoldoutResultReceipt` 使用同一 SHA。

**实际影响：** 配置、holdout receipt 和 event 会彼此一致，但该 SHA 不必是实际完整 `StagePlan` 的最终输出。候选证据可绑定到无关或不存在的回测结果。

**代码事实：**

- `CandidateRunConfig` 在 `run_candidate_rebalance` 之前就要求 completed final-stage hash。
- `capture_holdout_result` 接受调用方提供的 final-stage hash。
- candidate runner 只比较 config 中的 hash 与 receipt 中的 hash。
- 计算出本次 base stage hash 后，代码没有要求它等于 completed final-stage hash。
- 当前测试 helper 使用 `hash('fixture-final-stage')`，没有从实际 run result 得到该值。

**推断：** 当前关闭的是摘要字段之间的漂移，不是摘要与真实完整运行之间的漂移。

**假设：** `HoldoutResultReceipt` 应代表所评估完整回测的最终 stage。

**最小修复：** 拆分“执行回测”和“评估候选”：先按完整 `StagePlan` 运行并冻结 `FinalRunReceipt`；该 receipt 从实际最后一个结果派生并验证完整 prior-stage chain。之后 `capture_holdout_result` 只接受 `FinalRunReceipt`，`CandidateRunConfig` 不再预注册未知的输出 hash。

**回归测试：**

- 任意 fixture SHA 与实际 final stage 不同必须失败。
- 未执行到 StagePlan 最后一阶段时不能生成 holdout receipt。
- 跳过、重排或替换任何中间 stage 后 final receipt 必须失效。

## RA4-006 — 所有统计方法都用标准正态 erfc 生成 p 值，block bootstrap 与小样本推断失真 `[HIGH]`

**映射既有问题：** `RA3-004`、`RA3-005`

**文件/函数：**

- `src/quant_system/research/experiments.py::capture_holdout_result`
- `src/quant_system/research/splits.py::evaluate_split`

**触发条件：** 使用 non-overlapping 小样本、HAC 小样本或 block bootstrap，然后调用 `capture_holdout_result`。

**实际影响：** 候选 PASSED/FAILED 由错误校准的 p 值决定。尤其 block bootstrap 已计算经验分布，却没有用该分布计算 p 值；`n=2` 也可以被当作标准正态 z 检验。

**代码事实：**

- `capture_holdout_result` 固定使用 `erfc(abs(statistic)/sqrt(2))`。
- 该分支不区分 non-overlapping、HAC 与 block bootstrap。
- `SplitEvaluation` 允许最少两个 returns。
- block bootstrap 只保存 bootstrap standard error，没有保存或使用经验零假设分布。

**推断：** 标准误计算已经改进，但候选门的尾部概率仍可能极度乐观。

**假设：** adjusted p-value 是候选通过的重要证据。

**最小修复：** 使用方法专属推断：小样本独立收益使用 t 分布并设最小样本门槛；HAC 规定最低样本量和预注册 bandwidth 后使用明确的渐近检验；block bootstrap 使用中心化经验分布直接计算双侧 p 值。

**回归测试：**

- `n=2` 的高 t 值不能按标准正态产生近零 p 值。
- block-bootstrap p 值必须来自 empirical distribution，而不是 erfc。
- 低于方法最小样本量时 fail closed，不得生成 PASSED receipt。

## RA4-007 — 面板样本被当作单一时间序列，且跨 fold 标签重叠被忽略 `[HIGH]`

**映射既有问题：** `RA3-005`、`QF-005`

**文件/函数：**

- `src/quant_system/research/splits.py::build_split_manifest`
- `src/quant_system/research/splits.py::build_split_evaluation_plan`
- `src/quant_system/research/splits.py::evaluate_split`

**触发条件：** 同一日期包含多个证券样本，或 selected sample IDs 横跨多个 fold 且标签区间重叠。

**实际影响：** HAC 和 moving-block bootstrap 会按 observed time、entity ID 顺序把截面股票排成伪时间序列。同日相关性、横截面聚类和跨 fold 重叠未被建模，标准误可显著偏低。

**代码事实：**

- `SplitManifest` 明确支持同日多 entity 样本。
- evaluation plan 将样本按 observed time、entity ID、label end 排序。
- HAC/bootstrap 直接对该顺序的 returns 做序列估计。
- overlapping 条件要求两个样本具有相同 fold ID，跨 fold 重叠不计入。
- 计划中没有 evaluation unit、date aggregation 或 cluster policy。

**推断：** 估计器真实运行，但未必对应研究数据的抽样单位。

**假设：** 股票截面研究会同时包含多个证券，并使用重叠 forward returns。

**最小修复：** 在 `SplitEvaluationPlan` 中冻结 evaluation unit。个人日频截面策略最简单的路径是先形成每日组合收益，再对一日一个 return 做 HAC/block bootstrap；若保留 security-level 样本，必须实现按日期聚类或 two-way clustering。非独立 fold 不得在同一 evaluation 中混合。

**回归测试：**

- 同日多证券输入不能直接进入普通一维 HAC。
- 跨 fold 的重叠标签必须被检测，或计划必须限制为一个 fold。
- 改变 entity 排序不应改变统计结果；按日聚合结果应保持稳定。

## RA4-008 — DatasetManifest 只并列保存 parser/code 与 partition hash，没有证明这些代码产生了该分区 `[HIGH]`

**映射既有问题：** `RA3-006`、`QF-011`

**文件/函数：**

- `src/quant_system/research/identity.py::DatasetManifest`
- `src/quant_system/research/identity.py::capture_dataset_manifest`
- `src/quant_system/research/identity.py::DatasetManifest.verify_identity`

**触发条件：** 提交任意 provider-qualified partition bytes，同时提供任意 parser、feature、label 和 policy 文件。

**实际影响：** 代码能证明所有文件没有改变，但不能证明 partition 是由声明的 parser/feature/label 代码从声明的原始 source 生成。事后修改标签、删除不利样本或混入未来修订的数据仍可能被包装成自洽 manifest。

**代码事实：**

- `capture_dataset_manifest` 分别计算 parser、feature、label、policy 与 partition 文件 SHA。
- `verify_identity` 重新哈希这些文件并核对 partition source content SHA/available time。
- 代码不执行 parser/feature/label，也没有 `TransformationReceipt` 绑定输入 source、代码、配置和输出 partition。
- `source_snapshot_sha256s` 仍是摘要列表，而不是可逐项验证的原始 source receipt 对象。

**推断：** 数据快照绑定已加强，但数据生成血缘尚未形成可重放关系。

**假设：** feature/label partition 是本地派生数据，而非权威 provider 直接发布的最终研究表。

**最小修复：** 新增最小 `TransformationReceipt`：raw source receipt 列表、parser/feature/label code SHA、config、schema、row count、output partition SHA 和 execution time。`DatasetManifest` 接受 `TransformationReceipt`，而不是并列的裸文件哈希。

**回归测试：**

- 同一代码/输入下替换 partition bytes 必须失败。
- 同一 partition 配上不同代码但无重放证明必须失败。
- 输出包含 source available time 晚于 dataset as-of 的记录时 fail closed。

## RA4-009 — CandidateRunBundle 只能重算已提交的哈希链，不能独立重放研究输入和组合结果 `[MEDIUM]`

**映射既有问题：** `RA3-007`

**文件/函数：**

- `src/quant_system/backtest/event_loop.py::CandidateRunBundle`
- `src/quant_system/backtest/event_loop.py::CandidateRunBundle.verify`
- `src/quant_system/backtest/event_loop.py::serialize_candidate_run_bundle`
- `src/quant_system/backtest/event_loop.py::load_candidate_run_bundle`
- `src/quant_system/data/source_identity.py::_capture_payload`

**触发条件：** 在新进程中只有 `CandidateRunBundle` JSON，没有原始 source receipts、数据分区、策略字节和初始 portfolio。

**实际影响：** 新进程可以重算 receipt chain，但不能重新计算 base input identity、成交、final NAV 或 source values。整体字段可被一起替换并重新计算自哈希；同一 GitHub asset 重取时 `retrieved_at` 又会改变 source receipt。

**代码事实：**

- bundle 保存 identity hash、source receipt SHA 列表和 canonical execution receipt payload。
- verify 从已提交的 input identity 和 receipt payload 重算 stage hash。
- bundle 不保存或定位完整 source payload、dataset partitions、strategy bytes、初始 portfolio、marks 或 final NAV。
- SourceIdentity capture payload 包含 `retrieved_at`；GitHub adapter 每次使用当前时间。

**推断：** 当前实现是跨进程的哈希链校验器，不是端到端研究重放包。

**假设：** “可复现”意味着新进程可从保存证据重新计算结果，而不只是重算哈希公式。

**最小修复：** 把 bundle 改为 immutable artifact manifest：保存或引用全部 receipt payload、策略/数据文件、初始 portfolio 和运行配置，加载后重新计算 input identity、stage receipts 和 NAV。将稳定 source identity 与本次 acquisition audit 分离，或持久化并复用原始 receipt。

**回归测试：**

- 仅凭 bundle 和其声明的 artifacts，新进程必须重算相同成交、NAV 和 stage hash。
- 删除任一底层 artifact 或改变初始 portfolio 时重放失败。
- 再次获取相同不可变资产不应改变稳定内容 identity。

## RA4-010 — Typed parser identity 未覆盖 canonicalization helper 的代码语义 `[MEDIUM]`

**映射既有问题：** `RA3-001`

**文件/函数：**

- `src/quant_system/data/source_identity.py::_typed_parser_code_sha256`
- `src/quant_system/data/source_identity.py::_decode_provider_observations`
- `src/quant_system/data/source_identity.py::_canonical_observation_value`

**触发条件：** 修改 canonicalization 或校验 helper，而不修改 `_decode_provider_observations` 函数体。

**实际影响：** 业务值规范化语义已改变，但 parser SHA 保持不变；旧 receipt 会错误地声称使用了同一 parser。

**代码事实：**

- `_typed_parser_code_sha256` 只对 `_decode_provider_observations` 的源码求哈希。
- `_decode_provider_observations` 调用 canonicalization、stable ID 等 helper。
- 这些 helper 的源码不在 parser digest 中。

**推断：** parser identity 覆盖的是入口函数文本，不是完整解析语义闭包。

**假设：** 未来会演进数字、时间和 canonicalization 规则。

**最小修复：** 对整个 parser 模块或不可变 parser artifact 求哈希，或显式包含所有 helper 和 schema version；避免依赖局部函数的 `inspect.getsource` 摘要。

**回归测试：**

- canonicalization helper 的任何语义变化必须改变 parser identity。
- 安装 wheel 与源码树应计算同一 parser artifact SHA。

## RA4-011 — Canonical writer 的最低证据等级是全局 GENERIC_CAPTURE，未按 target 固定 `[MEDIUM]`

**映射既有问题：** `RA3-011`、`QF-010`

**文件/函数：**

- `src/quant_system/data/writer.py::MINIMUM_WRITE_CAPTURE_LEVEL`
- `src/quant_system/data/writer.py::_ensure_metadata`
- `src/quant_system/data/writer.py::_bind_target_contract`
- `src/quant_system/cli.py::main`

**触发条件：** 先向某 canonical target 写入 generic capture，之后再写 provider-qualified 数据，或研究读取时忽略 metadata grade。

**实际影响：** metadata 已能区分 grade，但同一业务表仍可混合实验级和外部合格数据。消费者若只查询业务表，无法从行本身判断证据等级。

**代码事实：**

- `MINIMUM_WRITE_CAPTURE_LEVEL` 固定为 `GENERIC_CAPTURE`。
- target contracts 不保存 minimum capture level。
- CLI append 通过 `capture_source_file` 产生 generic capture。
- ingest metadata 已保存 capture level，canonical owner 也已固定，这是实质改进。

**推断：** 单 writer 权限边界已改善，但 canonical 数据质量合同仍是全局最低门槛。

**假设：** 某些 target 未来应只允许 provider-qualified 或 transformation-qualified 数据。

**最小修复：** 在 target contract 中增加 `minimum_capture_level/data_grade` 并在首次建约时固定；实验/staging target 可允许 generic，研究 canonical target 必须要求相应受控 grade。

**回归测试：**

- provider-only target 拒绝 generic batch。
- target 已绑定 grade 后不得降低。
- 查询/快照 manifest 必须能证明所用分区满足 target grade。

# 8. 少数派判断、乐观/悲观框架与最强反驳

## 无背景判断

忽略项目已有投入，仅看当前代码：它适合作为严格的研究实验台，不适合作为“结果通过即可以投钱”的自动证据门。

## 少数派完整逻辑

很多个人项目的问题是约束太少；本项目现在的相反风险是 receipt 数量增加，但最关键的等价关系仍未建立。继续增加 receipt 类型不会自然提高可信度。应优先证明：

```text
权威源字节
  = typed业务值
  -> 派生分区确由声明代码产生
  -> 完整回测 final stage
  -> 冻结收益与统计检验
  -> 同一全局试验族
```

## 乐观框架

已有的时序、市场语义、成本、公司行动、数据哈希和 fail-closed 基础较强。若仅补本报告列出的关系，项目可以在不增加服务和控制面的情况下达到较高个人研究标准。

## 悲观框架

若用“更多字段都有 SHA”代替“字段之间可重算”，系统会生成非常完整但仍可自洽伪造的证据。其危险性高于简单回测，因为命名为 controlled/provider-qualified 的结果更容易获得人工信任。

## 对本结论的最强反驳

所有 authorization 均为 false，`strategy_candidate_available` 也始终为 false，因此当前不会自动触发资金操作。

该反驳对即时资金安全成立，但不能关闭研究完整性问题。用户目标是防止人工被漂亮回测误导，而不仅是防止程序自动下单。当前 `CONTROLLED_CANDIDATE_INPUT` 命名仍可能影响人工决策，所以代码合同必须继续收口。

# 9. 最小整改顺序

## P0-R4：关闭可直接伪造候选证据的路径

1. `RA4-001`：区分 GitHub transport 与权威 provider。
2. `RA4-002`：typed 绑定 limit/halt/no-open 事件。
3. `RA4-003` + `RA4-004`：真实 anchor head + 单一 canonical experiment ledger。
4. `RA4-005`：`FinalRunReceipt` 必须来自实际完整 stage chain。
5. `RA4-006` + `RA4-007`：方法专属 p 值和明确面板 evaluation unit。
6. `RA4-008`：`TransformationReceipt`。

## P1-R4：可复现性和数据合同收尾

1. `RA4-009`：完整 artifact manifest 和端到端 replay。
2. `RA4-010`：完整 parser artifact identity。
3. `RA4-011`：per-target data grade。

不需要新增 manager、dispatcher、registry 或第二个数据仓库。

# 10. PR 和授权建议

- PR 应继续保持 Draft。
- 不能以“代码整改完成，只剩外部证据”合并。
- 若要先合并已有价值，应将定位改为：`lightweight fail-closed research infrastructure hardening`。
- 合并不能解释为策略候选、推荐或资金部署获批。
- 完成 P0-R4 后重新冻结新的代码 head 外审。
- QF-014/EA-001 仍需独立 reviewer receipt；代码修复不能替代外部证据验收。

# 11. 文件审查台账

上一轮已读取完整 PR 文件集合；本轮对 `62300cdff8e300a43c0fc54b0fba2df0e456511f..d46a993d95b0b3454a10134c2ef822f17483ddc6` 的 26 个变更文件重新读取当前代码、测试和证据路径。其余文件由 compare 证明本轮未变。

## 本轮重新读取并分析

```text
docs/external_audit_round3_62300cdf_20260723.md
docs/external_audit_round3_ledger_62300cdf_20260723.json
docs/external_audit_round3_remediation_ledger_20260723.json
src/quant_system/backtest/__init__.py
src/quant_system/backtest/blocked_orders.py
src/quant_system/backtest/capacity.py
src/quant_system/backtest/event_loop.py
src/quant_system/cli.py
src/quant_system/data/__init__.py
src/quant_system/data/calendar.py
src/quant_system/data/source_identity.py
src/quant_system/data/writer.py
src/quant_system/markets/a_share.py
src/quant_system/markets/universe.py
src/quant_system/research/__init__.py
src/quant_system/research/experiments.py
src/quant_system/research/identity.py
src/quant_system/research/splits.py
tests/test_data_cli.py
tests/test_data_writer.py
tests/test_event_loop.py
tests/test_execution_semantics.py
tests/test_experiment_receipts.py
tests/test_public_api_boundaries.py
tests/test_research_splits_identity.py
tests/test_source_capture.py
```

## 上一轮已读、本轮 compare 确认未变

```text
docs/external_audit_codex_remediation_20260723.md
docs/external_audit_remediation_ledger_20260723.md
src/quant_system/backtest/costs.py
src/quant_system/backtest/portfolio.py
src/quant_system/config.py
src/quant_system/paths.py
tests/test_accepted_calendar.py
tests/test_backtest_core.py
tests/test_config.py
tests/test_markets_a_share.py
tests/test_paths.py
```

所有测试文件的本轮执行证据均来自成功的 GitHub Actions；本轮外审未在本地重复运行测试。