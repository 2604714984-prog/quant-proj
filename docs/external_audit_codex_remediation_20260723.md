# External Audit Remediation Report for Codex

> 目标读者：在 `2604714984-prog/quant-proj` 上执行整改的 Codex 对话。
>
> 本文件是外审问题清单与整改合同，不是策略结果，也不授权推荐、paper trading、live trading、券商接入或自动执行。

## 1. 审计元数据与授权状态

- 审计日期：`2026-07-23`
- 审计基准：`2604714984-prog/quant-proj@35b3246e40f8315e2bbef847d995a3b6d3a3b4fc`
- 独立证据边界：`2604714984-prog/a-share-canonical-evidence-data-room@de38f03466a58b9c786ed35e2cc38abff3e9b0fe`
- 当前判定：`RESEARCH_INFRASTRUCTURE_ONLY`
- 策略候选晋级：`DENY`
- 推荐或个人资金配置：`DENY`
- Paper/live/自动执行：`DENY`

在所有 P0 问题关闭、研究选择控制补齐、真实数据证据通过独立验收之前，保持：

```text
strategy_candidate_available=false
recommendation_authorized=false
paper_trading_authorized=false
live_trading_authorized=false
automatic_execution_authorized=false
```

## 2. Codex 执行合同

开始整改前必须遵守：

1. 先确认当前 checkout 仍是主线研究仓，不是归档仓、证据室、数据镜像或上游镜像。
2. 以当前 `v2-main` 为准重新读取相关文件；不得假设审计基准提交之后没有变化。
3. 不修改 `a-share-canonical-evidence-data-room` 的证据资产，不恢复归档 manager、dispatcher、ticket、registry、旧策略 runner、broker、paper/live 或自动执行路径。
4. 不新增固定本机路径，不把 mutable 数据写回 Git，不让第二个仓库获得同一种 canonical 数据的写权限。
5. 修改必须最小、可回滚、可验证；不得为顺手整理而做无关重构。
6. 不得削弱现有 fail-closed 行为。证据不足时状态保持 `BLOCKED`，不得用 fixture 宣称真实数据问题已经关闭。
7. 每个 PR 必须明确区分事实、推断、假设、已验证结果和未验证事项。
8. 每个整改 PR 原则上只处理一个问题或一个强耦合问题组。
9. P0 未关闭前，不实现候选晋级、推荐或交易授权功能。

## 3. 仓库和数据边界

- `quant-proj`：唯一活跃主线代码仓，包含 CLI、DuckDB read/append-only writer、市场语义、回测核心和通用研究 primitives。
- `QUANT_DATA_ROOT/quant_research.duckdb`：声明的外部 mutable canonical 数据对象。本次外审没有重新读取或哈希该数据库。
- `a-share-canonical-evidence-data-room`：独立只读证据边界；其私有 Release 资产仍待独立 external receipt。
- 其他历史仓库：只读归档证据，禁止重新接入运行时。

现有系统对交易日历身份、决策/执行时序、PIT status 选择、缺失行情 fail-closed、A 股 T+1/板手数/印花税、DuckDB 事务写入和路径身份防护已有较好基础。

仍未闭合的可信链为：

```text
真实原始字节
  -> 可信 available_at / source receipt
  -> 完整 PIT universe
  -> 冻结 feature / decision artifact
  -> 无测试集泄漏的 trial ledger
  -> 重叠收益和多重检验调整
  -> 公司行动完整收益
  -> 强制成本与容量情景
  -> 候选晋级门
```

在该链条闭合前，回测输出只能作为实验性研究结果。

## 4. 整改优先级

| 优先级 | ID | 严重程度 | 问题 |
|---|---|---|---|
| P0 | `QF-001` | HIGH | PIT/来源身份是调用方声明，不是可信字节捕获结果 |
| P0 | `QF-015` | MEDIUM | Source revision chain 未绑定不可变的数据族、提供方和主题 |
| P0 | `QF-002` | HIGH | 任意 Python callback 可绕过信息边界，策略 SHA 未绑定实际代码 |
| P0 | `QF-003` | HIGH | Universe 完整性由调用方自证，无法发现幸存者偏差 |
| P0 | `QF-007` | HIGH | A 股 suspension 双证据不一致时可能产生不可能成交 |
| P0 | `QF-009` | HIGH | Blocked-exit 在开盘前接受已成交价格 |
| P0 | `QF-006` | HIGH | A 股公司行动、退市和复权口径未闭环 |
| P0 | `QF-008` | HIGH | 交易成本和流动性约束可省略，美股默认零成本 |
| P0 | `QF-010` | HIGH | Canonical DuckDB 目标契约、谱系和可重建性不完整 |
| P1 | `QF-012` | MEDIUM | US 终止事件现金立即进入 settled cash |
| P1 | `QF-013` | MEDIUM | Retrospective execution 没有结果证据等级或晋级限制 |
| P1 | `QF-004` | HIGH | 没有测试集访问锁、全试验台账或多重检验门 |
| P1 | `QF-005` | MEDIUM | Split 不处理测试集内部重叠收益和同日多证券面板 |
| P1 | `QF-011` | MEDIUM | Dataset identity 不完整，stage chain 可重复从零开始 |
| P2 | `QF-014` | MEDIUM | 证据室 10 个 Release 资产尚未独立验证 |
| P2 | `OP-001` | LOW | CLI 在行数上限前把整个输入读入内存 |
| P2 | `OP-002` | LOW | Wheel 默认以当前目录推导 project/data root |

---

## QF-001 — 可信来源身份未与真实字节绑定

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/data/source_identity.py::SourceIdentity.__post_init__`
- `src/quant_system/markets/universe.py::UniverseSnapshotIdentity.__post_init__`
- `src/quant_system/backtest/event_loop.py::_inputs`

**问题与触发条件**

调用方可以手工构造一个格式正确、但 `content_sha256`、`available_at`、`revision_id` 或来源 URL 不对应真实原始字节/发布时间的身份对象。

**影响**

后续 PIT、日历、公司行动、universe 和执行时序校验可在错误前提上通过；输入哈希和阶段哈希只能证明声明内部一致，不能证明声明真实。

**要求的最小解决方案**

增加唯一的可信 source-capture 入口：

- 以 `O_NOFOLLOW` 固定打开真实文件或响应字节；
- 内部计算 SHA-256；
- 记录检索时间、供应商发布时间证据和来源 URL；
- 生成 immutable capture receipt；
- 候选级入口只接受从 capture receipt 派生的身份，拒绝手工回填 identity。

**必须增加的回归测试**

- 手工构造或回填 `available_at` 的 identity 在候选入口被拒；
- 字节变化、哈希不符、来源发布时间晚于 `decision_at` 均在策略回调前失败；
- capture 期间路径替换或 symlink/hardlink 攻击失败且零写入。

---

## QF-015 — Source revision chain 缺少语义同一性

**严重程度：** `MEDIUM`，与 `QF-001` 强耦合，按 P0 处理。

**涉及文件/函数：**

- `src/quant_system/data/source_identity.py::SourceIdentity`
- `src/quant_system/data/source_identity.py::select_source_revision`

**问题与触发条件**

当前修订链校验线性、单根、哈希唯一和时间递增，但没有强制整条链的 source family、provider 和 subject 相同。语义不同的数据源可被串成结构合法的 supersedes chain。

**要求的最小解决方案**

为 `SourceIdentity` 增加不可变字段，例如：

```text
source_family_id
provider_id
subject_id
```

`select_source_revision` 必须强制整条链三者完全一致。URL 迁移只有在同一 family 的正式迁移 receipt 下允许。

**回归测试**

同链中 provider、family 或 subject 漂移必须失败；合法的同 family URL 迁移仍可选择最新可用修订。

---

## QF-002 — 任意 Python callback 可读取未来信息

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/backtest/event_loop.py::TargetWeightCallback`
- `src/quant_system/backtest/event_loop.py::run_static_rebalance`
- `src/quant_system/backtest/event_loop.py::_sha256`

**问题与触发条件**

`target_weights` 可通过闭包、全局 dataframe、文件、数据库或网络读取 execution open、未来标签或测试结果。调用方还可修改实际策略代码但继续提交旧的 definition/adapter SHA。

**影响**

`DecisionContext` 不暴露开盘价并不能形成 Python 信息流隔离；前视数据仍可进入权重，阶段身份也可与实际代码不一致。

**要求的最小解决方案**

候选级路径不接受任意 callable，改为读取冻结的 `DecisionArtifact`，至少绑定：

```text
weights
feature_snapshot_sha256
strategy_definition_sha256
strategy_adapter_sha256
decision_at
dataset_identity
split_identity
```

哈希必须由系统从实际字节内部计算。实验级 callable 可以保留，但结果强制标记 `UNTRUSTED_EXPERIMENT`，不得晋级。

**回归测试**

- 回调闭包引用 execution open 或未来标签时候选入口失败；
- 修改适配器字节但复用旧 SHA 时失败；
- DecisionArtifact 任一字节变化都会改变输入身份；
- 失败必须发生在任何 portfolio mutation 之前。

---

## QF-003 — Universe snapshot 不能证明股票池完整

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/markets/universe.py::lifecycle_coverage_sha256`
- `src/quant_system/markets/universe.py::validate_universe_snapshot`

**问题与触发条件**

上游可用今天仍存续的证券重建历史股票池，遗漏退市或失败证券，再为不完整列表生成自洽的 member count 和哈希。

**影响**

当前校验能证明 supplied members 没有漂移，但不能证明完整来源中不存在其他应当出现的证券。幸存者偏差可完整通过。

**要求的最小解决方案**

增加唯一 universe materializer，从固定来源分区为来源中的每个证券输出：

```text
included / excluded
排除原因
source partition SHA
inclusion rule code SHA
calendar identity
PIT lifecycle evidence
```

候选 runner 只接受该物化结果，不接受调用方自制 members tuple。

**回归测试**

来源分区同时包含存续股、退市股和失败股；手工漏掉退市股的自洽 snapshot 必须失败。修改 inclusion rule 字节必须改变 snapshot identity。

---

## QF-007 — A 股 suspension 双证据冲突未 fail closed

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/backtest/event_loop.py::run_static_rebalance`
- `src/quant_system/backtest/event_loop.py::_inputs`
- `src/quant_system/backtest/event_loop.py::_fill`
- `src/quant_system/markets/a_share.py::decide_fill`

**问题与触发条件**

`StatusEvidence.suspended=True`，但 `ExecutionInput.is_suspended=False`；证券是已有持仓，并因 universe 不合格而目标置零。

**影响**

Universe 侧认为证券暂停交易，退出单却可能按独立的 false bar flag 成交，产生不可能的卖出和乐观回撤。

**要求的最小解决方案**

- 在策略回调前比较 selected suspended evidence 与 execution status；
- 冲突直接失败，或至少保守地按任一 `True` 阻塞；
- 对 `up_limit/down_limit=None` 增加显式语义，区分“该日无涨跌停制度”和“适用制度但字段缺失”。

**回归测试**

- 持仓 `status suspended=true`、bar flag=false 时必须在回调前失败且不得成交；
- 适用涨跌停制度但缺少 limit 字段时失败；
- 明确记录 no-limit regime 时仍允许正常处理。

---

## QF-009 — Blocked-exit 混淆决策时点与成交事件

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/backtest/blocked_orders.py::ExitAttempt.__post_init__`
- `src/quant_system/backtest/blocked_orders.py::_validated_attempt`
- `src/quant_system/backtest/blocked_orders.py::execute_ready_blocked_exit`

**问题与触发条件**

API 强制 `decision_at < session.open_at`，同时允许 filled attempt 携带该日开盘/成交价。调用方等价于在市场事件发生前提供已经成交的价格。

**要求的最小解决方案**

将 retry decision 和 fill event 分为两个对象：

```text
RetryDecision(decision_at, requested_session, reason)
FillEvent(execution_at, price, source, effective_at, basis)
```

成交事件必须使用 timestamped 或 retrospective basis，并绑定来源身份。原 API 降为内部或实验级。

**回归测试**

- 开盘前不可提交 filled price；
- timestamped open source 与晚到日线 source 产生不同 evidence grade；
- 填充失败或 source 时序错误时，order 和 portfolio 深层状态保持不变。

---

## QF-006 — A 股公司行动、退市和价格口径未闭环

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/backtest/event_loop.py::_inputs`
- `src/quant_system/backtest/event_loop.py::_actions`
- `src/quant_system/backtest/portfolio.py::apply_cash_distribution`
- `src/quant_system/backtest/portfolio.py::apply_terminal_action`

**问题与触发条件**

A 股发生现金分红、送转/拆并股、并购、退市或代码变更；上游使用复权价但没有声明和绑定 adjustment basis。

**影响**

显式 A 股 action 会被拒，省略 action 又可继续运行；结果可能漏记分红或退市损失，也可能在复权数据上重复调整。

**要求的最小解决方案**

二选一，且不得在同一运行中混用：

1. 支持 A 股 rich corporate-action identities；或
2. 强制数据集声明 `raw/qfq/hfq/total_return` 口径、调整因子来源及 `available_at`，并对 action 日做完整性核对。

没有 matching action/adjustment receipt 时 fail closed。

**回归测试**

- A 股样本存在分红、拆股或退市但无匹配证据时失败；
- raw 与 adjusted 模式混用时失败；
- 同一公司行动重复应用时失败且状态不变；
- 退市证券不能通过 universe omission 消失。

---

## QF-008 — 候选级成本和容量不是强制项

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/backtest/costs.py::TransactionCostModel`
- `src/quant_system/backtest/portfolio.py::Portfolio.us`
- `src/quant_system/backtest/event_loop.py::run_static_rebalance`
- `src/quant_system/backtest/capacity.py::assess_capacity`

**问题与触发条件**

`Portfolio.us()` 默认零成本，`slippage_bps=0`，`capacity_policy=None`。已有 capacity 只覆盖可选的前一日 volume/amount cap。

**影响**

净收益被系统性高估，尤其影响高换手、小盘、事件驱动和低流动性策略。

**要求的最小解决方案**

增加版本化 `ExecutionCostAssumptions`。候选级运行必须显式绑定：

```text
commission
bid_ask_spread
market_impact
regulatory_fees
capacity policy
currency/FX assumptions
base/adverse stress cases
```

零成本只允许 `gross_only=true`，并永久禁止候选晋级。

**回归测试**

- 候选运行未提供成本或容量证据时失败；
- 成本 assumption 任一变化改变输入身份；
- base/adverse 成本后结果同时写入冻结 artifact；
- gross-only 结果不能进入候选状态。

---

## QF-010 — Canonical DuckDB 合同和谱系不完整

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/data/writer.py::_ensure_metadata`
- `src/quant_system/data/writer.py::_validate_inputs`
- `src/quant_system/data/writer.py::append_rows`
- `src/quant_system/data/__init__.py`

**问题与触发条件**

不同调用方可对同一 target 使用不同 natural keys；公共 `append_rows` 只要求任意格式正确的 source SHA；metadata 不保存结构化来源、schema hash、代码/config SHA；目标表必须预先存在。

**影响**

同一 canonical 表可能拥有不一致的去重语义；数据来源和 schema 无法完整追溯；当前活跃树无法从零证明可重建外部数据库。

**要求的最小解决方案**

在现有 DuckDB 中增加最小 `_quant_meta.target_contracts`：

```text
target
ordered_natural_keys
schema_sha256
canonical_owner
contract_version
```

Ingest receipt 还应绑定 structured SourceIdentity、代码/config SHA。候选研究启动时绑定只读 DB 或 partition snapshot manifest。

不得新增第二个数据仓库、第二套 writer 或 manager/registry 控制面。

**回归测试**

- 同一 target 第二次改变 keys 或 schema 时失败；
- 裸 source SHA 不能进入受控 writer；
- DB/partition snapshot 漂移使研究启动失败；
- 迁移、回放和幂等 replay 继续保持 fail closed。

---

## QF-012 — US terminal recovery 现金时序过早

**严重程度：** `MEDIUM`

**涉及文件/函数：**

- `src/quant_system/backtest/event_loop.py::TerminalAction`
- `src/quant_system/backtest/portfolio.py::apply_terminal_action`

**问题与触发条件**

退市、并购或代码变更包含非零现金 recovery，而现实付款或结算日晚于 effective session。

**影响**

组合可在实际到账前再投资，现金可用性和收益被高估。

**要求的最小解决方案**

为 terminal action 增加 payment/settlement date 和 accepted settlement sessions。现金先进入 `PendingCash`，到期才进入 settled cash。

**回归测试**

付款日前 recovery 不能资助买单；payment date、settlement sessions 和 source identity 必须进入输入身份。

---

## QF-013 — Retrospective execution 没有证据等级

**严重程度：** `MEDIUM`

**涉及文件/函数：**

- `src/quant_system/backtest/event_loop.py::_inputs`
- `src/quant_system/backtest/event_loop.py::_identity`
- `src/quant_system/backtest/event_loop.py::StaticRebalanceResult`

**问题与触发条件**

执行开盘价来自收盘后日线，basis 为 `retrospective_daily_bar_open_fill`。当前 identity 会变化，但结果对象没有可见 evidence grade 或晋级限制。

**影响**

回溯重建结果容易被误解为实时可执行证据。

**要求的最小解决方案**

结果显式计算和保存 evidence grade，例如：

```text
TIMESTAMPED_EXECUTION
RETROSPECTIVE_EXECUTION
CONFIRMED_NO_OPEN
MIXED_RETROSPECTIVE
```

任何 retrospective 或晚到证据使运行不可晋级，只能作为回溯研究。

**回归测试**

相同 receipts、不同 basis 必须生成不同 grade；retrospective-only 结果不能进入候选状态。

---

## QF-004 — 测试集访问和多重检验不可审计

**严重程度：** `HIGH`

**涉及文件/函数：**

- `src/quant_system/research/__init__.py`
- `src/quant_system/research/identity.py::dataset_identity_sha256`
- `src/quant_system/research/splits.py`

**问题与触发条件**

反复观察测试结果后调整特征、参数、市场、样本期、持有期或成本，只保留最终赢家。

**影响**

无法检测 test-set tuning、研究者自由度和多重检验；可复现的单个回测仍可能是选择偏差产物。

**要求的最小解决方案**

增加简单 append-only experiment receipt，而不是 manager/registry：

```text
trial_id
preregistered definition/data/split SHA
全部尝试参数
holdout access event
结果与状态
multiplicity family id
```

最终 holdout 只允许一次解锁；失败 trial 不得删除；候选晋级必须保存多重检验调整。

**回归测试**

- 定义改变后再次访问已锁 holdout 被拒；
- 删除失败 trial 后 manifest 校验失败；
- 无 multiplicity adjustment 的候选晋级失败。

---

## QF-005 — Split 未控制测试集内部重叠收益

**严重程度：** `MEDIUM`

**涉及文件/函数：**

- `src/quant_system/research/splits.py::_validate_time_axis`
- `src/quant_system/research/splits.py::purged_embargo_train_mask`
- `src/quant_system/research/splits.py::walk_forward_masks`

**问题与触发条件**

每日样本使用 5/20 日 forward return，或同一 `observed_at` 下有多个股票样本。

**影响**

测试样本高度相关，名义样本数、t 值和 Sharpe 显著性可能被高估；严格唯一时间轴又不能直接表达面板样本。

**要求的最小解决方案**

引入带下列字段的 split manifest：

```text
sample_id
entity_id
observed_at
label_end_at
fold_id
overlap_group
```

评估必须选择非重叠测试子样本，或使用 HAC/块 bootstrap，并报告 effective N。

**回归测试**

每日 5 日标签必须产生 overlap flag；未修正显著性不得晋级；同日多证券通过稳定 sample ID 合法进入 split。

---

## QF-011 — Dataset identity 和阶段链不完整

**严重程度：** `MEDIUM`

**涉及文件/函数：**

- `src/quant_system/research/identity.py::dataset_identity_sha256`
- `src/quant_system/backtest/event_loop.py::run_static_rebalance`
- `src/quant_system/backtest/event_loop.py::_hashes`

**问题与触发条件**

特征/标签代码、universe、split 或公司行动政策改变但复用 generic config IDs；连续回测的每个阶段都使用默认零 `prior_stage_hash`。

**影响**

Dataset ID 可能无法区分语义变化；阶段可遗漏、重排或断链而不被整体 manifest 发现。

**要求的最小解决方案**

Dataset manifest 必须绑定：

```text
source snapshots
universe snapshot
feature code SHA
label code SHA
split manifest SHA
calendar/action/cost policy SHA
partition hashes
```

除显式 genesis 外，后续阶段必须提供前一 stage hash，并记录 stage index/session。

**回归测试**

任一语义 artifact 变化改变 dataset ID；第二阶段使用零 prior hash、跳过或重排 session 必须失败。

---

## QF-014 — Evidence room Release 尚未独立验收

**严重程度：** `MEDIUM`

**涉及对象：**

- `a-share-canonical-evidence-data-room/README.md`
- `a-share-canonical-evidence-data-room/MANIFEST.sha256`
- Release `a-share-canonical-evidence-20260712`

**问题与触发条件**

研究直接依赖 README 中关于行数、证券数和跨 split 标签清除的声明，但 Release 资产尚无独立验证 receipt。

**要求的最小解决方案**

独立审查者以只读权限下载全部 10 个资产，校验 `MANIFEST.sha256`，执行附带验证命令，并返回绑定下列内容的 receipt：

```text
release tag
repo commit/tree
reviewer identity
asset hashes
command output hashes
zero-write attestation
```

该工作不得授予 evidence room 或审查进程 canonical DB 写权限。

**回归/验收条件**

任一资产缺失、哈希不符或验证命令失败，receipt 必须失败；在 receipt 完成前保持 `strategy_candidate_available=false`。

---

## OP-001 — CLI 大文件捕获不是流式的

**严重程度：** `LOW`

**涉及文件/函数：**

- `src/quant_system/cli.py::_capture_bytes`
- `src/quant_system/cli.py::_rows`

**问题**

整个 JSON/JSONL 文件先读入内存，之后才执行 writer 的行数上限检查。

**要求的最小解决方案**

JSONL 采用流式哈希和解析，同时执行字节/行上限；JSON array 设置明确字节上限。失败时数据库零写入。

**回归测试**

超过字节或行上限的输入在受限内存下稳定失败，数据库和 metadata 均保持不变。

---

## OP-002 — Wheel 写入可能使用意外数据根

**严重程度：** `LOW`

**涉及文件/函数：**

- `src/quant_system/paths.py::_default_project_root`
- `src/quant_system/paths.py::AppPaths.discover`

**问题**

非源码 wheel 找不到 checkout 的 `pyproject.toml` 时回退 `Path.cwd()`，随后默认数据根为当前目录的 sibling `quant-data`。

**要求的最小解决方案**

从 wheel 执行写入时强制显式 `QUANT_DATA_ROOT` 或配置。只读 `info/query` 可保留默认发现，但输出必须明确数据根是否受绑定。

**回归测试**

Wheel 未显式提供数据根时，`append --execute` 必须失败；dry-run 输出 `UNBOUND_DATA_ROOT` 或等价状态。

---

## 5. 建议整改波次

### P0-A：可信来源与策略输入边界

- `QF-001` + `QF-015`
- `QF-002`
- `QF-003`

### P0-B：市场执行和收益完整性

- `QF-007`
- `QF-009`
- `QF-006`
- `QF-008`

### P0-C：Canonical 数据契约

- `QF-010`

### P1-A：结算和证据等级

- `QF-012`
- `QF-013`

### P1-B：研究选择和统计完整性

- `QF-004`
- `QF-005`
- `QF-011`

### P2：证据验收和操作安全

- `QF-014`
- `OP-001`
- `OP-002`

## 6. 每个整改 PR 的统一关闭条件

- 修改局限于解决问题所需的最小文件集合；
- 不削弱现有 fail-closed；
- 不恢复归档控制面或交易执行路径；
- 不新增硬编码数据路径；
- 不创建第二套 canonical writer；
- 新增正向和负向回归测试；
- PR 描述列出实际运行的测试，未运行的测试不得写成已通过；
- 涉及真实数据时附 snapshot/asset SHA、来源 URL、`available_at` 证据、只读验证输出哈希、数据库写入次数和 provider request 次数；
- 原始数据或外部证据不可访问时保持 `BLOCKED`，不得用 fixture 宣布关闭。

## 7. 全局验证命令

每个代码整改至少运行并记录：

```bash
python -m ruff check .
python -m pytest -q -o pythonpath=
python -m pip wheel --no-deps . --wheel-dir dist
python -m pip install --force-reinstall dist/*.whl
python -m pip check
```

还必须运行该问题的定向测试。若 CI、依赖或外部数据不可用，应明确记录阻断原因。

## 8. 重新申请候选资格外审的完成标准

只有同时满足以下条件，才可以重新进行候选资格外审：

1. 所有 P0 问题关闭并有负向回归测试；
2. Trial ledger 能证明失败试验未被删除，最终 holdout 未参与选参；
3. 多重检验和重叠收益处理写入冻结结果 artifact；
4. Universe 能从完整来源分区重建并包含历史退市/失败证券；
5. A 股和美股的公司行动、退市、现金结算、缺失数据和成本均有完整 evidence；
6. 每次运行绑定 data、universe、feature、label、split、strategy、cost、calendar 和 source snapshot；
7. Evidence room Release 获得独立 external receipt；
8. 没有新增第二套 canonical writer，没有恢复归档控制面，没有引入 broker/paper/live/自动执行。
