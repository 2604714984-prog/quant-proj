# 当前外审：研究可靠性与成果吞吐

> 本报告取代继续增加安全控制的审查方向。  
> 审查目标只有两项：
>
> 1. 研究结果是否能经受因果时序、PIT、样本选择、成本和统计复核；
> 2. 从一个研究假设到一个可复现结果，是否足够直接、快速和低摩擦。
>
> 不影响研究正确性、canonical 数据所有权或结果可复现性的纯防御性问题，不再作为整改主线。

## 1. 冻结边界

- 仓库：`2604714984-prog/quant-proj`
- PR：`#126`
- Base：`v2-main@31329dbfd7b9bb1c184a13ee7fe2e60bd0a6ba14`
- 上一轮完整审查 head：`857b264883bbcdaf06e47f66df4f878dfea5c475`
- 本轮被审代码 head：`81403aa223ad6d11a7339fd970b65512bdc0a5c8`
- GitHub Actions merge ref：`37da8ccaa028e5cd983054148217a836428f1cec`
- CI run：`30026809844`，`completed/success`
- 本报告提交产生的后续文档 commit 不属于被审代码范围。

本轮重新审查了 `857b264..81403aa` 的全部生产代码增量、相关测试增量和最终当前文件；未改变文件沿用上一轮逐文件审查台账。GitHub Actions 已确认 wheel build/install、`pip check`、checkout 外 CLI、Ruff 和 pytest 均成功。PR 报告 `270 passed`，本轮连接器未独立提取完整日志尾部。

## 2. 重新校准后的结论

```text
repository_shape=PASS
single_canonical_writer=PASS
fail_closed_core=PASS

research_reliability=PARTIAL_PASS
fast_result_pipeline=FAIL
capital_grade_research=false

security_scope=FREEZE
add_more_generic_receipts=false
add_manager_dispatcher_registry=false

strategy_candidate_available=false
recommendation_authorized=false
paper_trading_authorized=false
live_trading_authorized=false
automatic_execution_authorized=false
```

### 已接受的整改

以下整改有明确代码和测试证据，不应继续反复重做：

- active tree 已移除终止研究归档、一次性执行器、mutable results 和 direct DuckDB writers；
- 一个 canonical writer 和 per-target minimum grade 已建立；
- arbitrary callback result 与 controlled result 已分型；
- stage plan 已绑定 initial/final portfolio state continuity；
- ReturnArtifact 已从受控 stage/NAV 链派生；
- experiment ledger 路径已从 AppPaths 推导；
- source、calendar、execution、universe、cost、corporate action 和 split 的局部 fail-closed 明显加强；
- generic/retrospective/gross-only 不会被升级为交易授权；
- 没有新增 manager、dispatcher、registry、broker 或自动执行。

剩余问题不应再通过增加更多类型和校验层解决，而应通过压缩研究路径、消除重复运行和补齐两条关键因果关系解决。

## 3. 阻断项

### RT-001 — 特征与标签生成链不具备严格因果隔离 `[HIGH]`

**文件/函数**

- `src/quant_system/research/identity.py::_run_transformation`
- `src/quant_system/research/identity.py::_validate_partition`
- `src/quant_system/research/identity.py::execute_transformation`

**触发条件**

历史样本的 `observed_at` 早于某个特征输入的真实 `available_at`，但该输入仍早于整个 dataset 的全局 `dataset_as_of`；或者 label 程序通过中间文件携带、改写 feature 字段。

**实际影响**

未来可用信息可能进入历史特征。当前全局 as-of 检查无法证明每一行的 feature 在该行 observation/decision 时已经可用。

**代码事实**

- 当前固定执行顺序为 `raw -> feature output -> label output -> final output`；
- label 程序只读取 feature output，final 程序只读取 label output；
- feature 与 label 不是两个独立 artifact，无法独立审计或缓存；
- `_validate_partition` 仅要求名称以 `available_at` 结尾的字段不晚于全局 `dataset_as_of`；
- 没有强制 `feature_available_at <= observed_at/decision_at`；
- label 的未来区间与 feature 的因果字段没有在 join 边界隔离。

**推断**

当前机制能证明转换可重复，但还不能证明特征是 point-in-time 的。串行链也迫使每次 feature 变化重新运行 label 和 final，降低迭代速度。

**假设**

真实 feature/label 数据包含不同可用时间，label 需要使用 observation 之后的收益区间。

**最小修复**

改成并行的三步：

```text
raw sources -> feature artifact
raw sources -> label artifact
(feature artifact, label artifact) -> deterministic join
```

Join 必须强制：

```text
feature_available_at <= observed_at
observed_at <= label_end_at
feature columns 不读取 label artifact
```

Feature 和 label artifact 分别缓存、分别哈希。不要新增 DAG manager；一个固定三步函数即可。

**回归测试**

- feature available_at 晚于 observed_at、但早于 dataset_as_of 时必须失败；
- label 改变不得改变 feature artifact SHA；
- feature 改变不得强制重算未变化的 label artifact；
- join 后任一 feature 字段都能追溯到 feature artifact，而非 label artifact。

---

### RT-002 — Candidate 评估重新运行了一个单独 stage，而不是评估被 holdout 检验的完整 run `[HIGH]`

**文件/函数**

- `src/quant_system/backtest/event_loop.py::run_candidate_rebalance`
- `src/quant_system/research/experiments.py::FinalRunReceipt`
- `src/quant_system/research/splits.py::ReturnArtifact`

**触发条件**

调用方提供一个通过 holdout 的完整 `FinalRunReceipt`，随后给 `run_candidate_rebalance` 传入不同的当前 `portfolio`、`stage_context` 或单一 signal session。

**实际影响**

Holdout 统计针对历史完整 run；返回的 candidate result 却来自随后重新执行的另一个单 stage。两者可以共享 strategy/data/split SHA，却不必拥有相同的 final stage、initial portfolio 或 final portfolio。

**代码事实**

- candidate 入口验证 `FinalRunReceipt`、ReturnArtifact/SplitEvaluation 和 holdout event；
- 随后又以调用方传入的 portfolio 和 stage_context 分别执行 base/adverse 单 stage；
- 没有要求当前 `stage_context.stage_index == final_run_receipt.stage_count - 1`；
- 没有要求当前 stage initial/final portfolio 与 FinalRunReceipt 最后一阶段一致；
- candidate 输出的 stage hash 是这次新运行的 hash，不是 holdout 所评估完整 run 的 final hash。

**推断**

“历史研究评估”和“下一期 prospective stage”被混在同一个函数。它既增加重复计算，也削弱结果语义。

**最小修复**

拆成两个简单入口：

```text
assess_research_run(
    final_run_receipt,
    return_artifact,
    split_evaluation,
    experiment_evidence,
    cost_stress_result,
) -> ResearchAssessment

run_prospective_stage(...) -> ControlledStageResult
```

`assess_research_run` 只验证并汇总已经执行的完整 run，不再次交易。Prospective stage 单独运行，不继承历史 holdout 的 PASS 名称。

**回归测试**

- 替换 candidate portfolio 或 stage_context 不能改变历史 `ResearchAssessment`；
- `ResearchAssessment.final_stage_hash` 必须等于 holdout/ReturnArtifact 的 final stage；
- prospective stage 不能被误标为历史 holdout 结果；
- candidate assessment 不应再次执行 base/adverse event loop。

---

### RT-003 — 没有从研究定义到结果的标准入口 `[HIGH: THROUGHPUT]`

**文件/函数**

- `src/quant_system/cli.py::_parser`
- `src/quant_system/research/__init__.py`
- `src/quant_system/backtest/__init__.py`

**触发条件**

研究者要从一个新假设开始，生成 PIT 数据、执行 stage plan、计算成本后收益和统计结果。

**实际影响**

必须在 notebook 或一次性脚本中手工创建并连接大量对象：

- TransformationReceipt / DatasetManifest
- SplitManifest / SplitEvaluationPlan
- UniverseMaterialization
- DecisionArtifact
- StagePlan / ControlledStageResult
- FinalRunReceipt / ReturnArtifact / SplitEvaluation
- experiment events / ledger / anchor
- CandidateRunConfig / cost assumptions / bundle

这种调用图本身成为新的错误来源，也使可靠机制难以真正被日常使用。

**代码事实**

- 唯一 CLI 只有 `info` 和 `data inspect/query/append`；
- research 和 backtest 顶层暴露数十个低层 primitive；
- 没有一个 end-to-end reference runner；
- README 宣称一个小运行面，但研究流程没有对应入口。

**最小修复**

增加一个函数和一个 CLI 子命令，不新增框架：

```text
run_research(spec, mode="explore" | "verify")
quant research run SPEC.json --mode explore|verify
```

两个模式：

- `explore`：开发/验证集、PIT、成本和完整结果；禁止读取 final holdout；不生成 full bundle，不要求 external anchor；
- `verify`：冻结 family、解锁一次 holdout、执行完整 replay、生成 bundle 和审计 receipt。

输出固定为一个紧凑 JSON：

```text
status = PASS | FAIL | BLOCKED
dataset_sha
strategy_sha
split_sha
base/adverse metrics
failure_reason
evidence_grade
authorization=false
```

**回归测试**

- 一个小 fixture 从 spec 到结果只需一次命令；
- explore 模式不能读取 final holdout；
- verify 模式必须复用 explore 已冻结的 dataset/strategy artifacts；
- 失败结果同样生成紧凑、可复现的 terminal report。

---

### RT-004 — 同一事实被多次全量重放 `[HIGH: THROUGHPUT]`

**文件/函数**

- `TransformationReceipt.verify`
- `DatasetManifest.verify_identity`
- `CandidateRunBundle.verify`
- `serialize_candidate_run_bundle`
- `load_candidate_run_bundle`
- `replay_candidate_run_bundle`
- `_build_candidate_run_bundle`

**触发条件**

正常执行 transformation、构建 candidate、序列化 bundle、加载 bundle 并执行显式 replay。

**实际影响**

同一转换和同一 base/adverse stage 被重复运行多次。小 fixture 看不出问题，但真实多年数据会把可靠流程变成高倍重复计算。

**代码事实**

- transformation 首次执行后立即调用 `receipt.verify()`，再次运行三步转换；
- DatasetManifest 每次验证又对每个 TransformationReceipt 执行完整 replay；
- bundle 构建后立即 `bundle.verify()`，会 replay base/adverse；
- serialize 再 verify；
- load 再 verify；
- `replay_candidate_run_bundle` 先 verify，再显式 replay base/adverse。

**最小修复**

把验证拆为两级：

```text
verify_structure()   # 快：schema/hash/identity/coverage
replay()             # 慢：真正重新执行
```

策略：

- 普通 explore/run 只做结构验证；
- 首次生成 artifact 时执行一次；
- promotion/CI 明确执行一次 full replay；
- replay receipt 按 immutable input identity 缓存；
- load 默认只做结构验证，`--replay` 才重跑。

**回归测试**

- 通过 call counter 证明一次 explore 不重复执行 transformation；
- 一次 verify promotion 对每个 immutable artifact 最多 full replay 一次；
- load/inspect 不触发交易或 transformation；
- 修改任何输入 hash 后缓存失效。

---

### RT-005 — Run bundle 内嵌全部原始和派生字节，不适合真实数据规模 `[MEDIUM: THROUGHPUT]`

**文件/函数**

- `src/quant_system/backtest/event_loop.py::_bundle_artifact_payloads`
- `src/quant_system/backtest/event_loop.py::_build_candidate_run_bundle`

**触发条件**

Dataset 含多个 raw partitions、feature/label outputs、转换脚本和 policy 文件。

**实际影响**

Bundle 将所有文件读取进内存并以 Base64 放入一个 JSON，产生约 33% 编码膨胀、重复存储和 64 MiB 单文件限制。真实历史数据会使结果生成和传输变慢，甚至无法构建 bundle。

**代码事实**

- raw paths、output partitions、programs、strategy bytes 和 policy 文件全部加入 payload；
- 每个文件完整读入内存；
- content 以 Base64 内嵌；
- bundle 创建后立即进行完整 replay。

**最小修复**

Bundle 改成 content-addressed manifest：

```text
sha256
byte_count
artifact_role
relative content-store URI
```

数据放在 `QUANT_DATA_ROOT/artifacts/<sha256>`。默认 bundle 只保存 manifest；需要离线归档时显式执行：

```text
quant research pack BUNDLE
```

**回归测试**

- 相同 artifact 只存一份；
- 大于 64 MiB 的 partition 不需要内嵌即可形成 bundle；
- 缺失或 hash 不符的 artifact 在 replay 前失败；
- compact manifest 大小不随原始数据总字节线性膨胀。

---

### RT-006 — 受控 adapter 与 transformation 环境限制了正常量化迭代 `[MEDIUM: PRODUCTIVITY]`

**文件/函数**

- `src/quant_system/backtest/event_loop.py::_execute_frozen_adapter`
- `src/quant_system/research/identity.py::_HERMETIC_RUNNER`
- `src/quant_system/research/identity.py::_run_hermetic_step`

**触发条件**

研究需要排名、分位数组合、行业中性、波动率缩放或使用已安装的共享数值代码。

**实际影响**

- controlled adapter 只支持一个固定的 threshold + positive_sum 合同；
- 每种新策略逻辑都可能迫使修改 shared core；
- transformation audit hook 限制 project/venv 文件访问，容易迫使 feature/label 程序成为自包含脚本；
- 三个独立子进程增加开发和运行成本。

**代码事实**

唯一 adapter schema固定为：

```json
{
  "feature_field": "scores",
  "normalization": "positive_sum",
  "transform": "threshold",
  "version": 1
}
```

Transformation 采用 `python -I`、空环境和文件访问 audit hook。

**最小修复**

不要继续建设 adapter registry 或 DSL。允许一个 branch-level、冻结的纯 adapter artifact：

```text
input: canonical feature JSON/Arrow
output: sorted target weights JSON
```

在记录了 wheel/environment SHA 的确定性进程中执行。可靠性来自冻结输入、代码、依赖环境和输出重放，不来自把研究代码当作敌对代码沙箱。

**回归测试**

- 修改 adapter 或依赖 wheel 会改变 strategy identity；
- 同一输入/环境重复执行产生相同权重；
- adapter 不接收 label artifact 或 execution price；
- 一个 rank/top-N/equal-weight 示例无需修改 shared core。

---

### RT-007 — 自研统计实现缺少外部数值金标 `[MEDIUM: RELIABILITY]`

**文件/函数**

- `src/quant_system/research/splits.py::_regularized_incomplete_beta`
- `src/quant_system/research/splits.py::_student_t_two_sided_pvalue`
- `src/quant_system/research/splits.py::evaluate_split`

**触发条件**

小样本 Student-t、极端 statistic、HAC 或 bootstrap 边界值进入最终判断。

**实际影响**

流程和 hash 均可能正确，但数值实现误差仍会改变 PASS/FAIL。继续扩展自研统计代码会增加维护成本。

**事实**

当前测试覆盖方法、范围、最小样本和篡改失败；本轮代码搜索未发现与 SciPy、R 或固定外部统计表的数值对照。

**最小修复**

二选一：

1. 使用一个成熟统计库；或
2. 保持零运行时依赖，但加入由 SciPy/R 离线生成并提交的 golden vectors，覆盖尾部、自由度和 bootstrap 案例。

不要继续自研更多分布函数。

**回归测试**

- Student-t p-value 与金标在明确容差内一致；
- 极端 statistic 和低自由度覆盖；
- bootstrap 固定 seed 的经验 p-value有金标；
- 升级 Python 后金标仍通过。

---

### RT-008 — 市场数据可信度与预注册锚点使用了同一个等级概念 `[MEDIUM: PRODUCTIVITY]`

**文件/函数**

- `src/quant_system/data/source_identity.py::SourceIdentity`
- `src/quant_system/research/experiments.py::ExperimentAnchorReceipt`
- `src/quant_system/backtest/event_loop.py::run_candidate_rebalance`

**触发条件**

使用 GitHub commit/Release 作为预注册的外部时间承诺，同时使用交易所或数据商作为市场数据来源。

**实际影响**

GitHub 不应被视为权威市场数据源，但完全可以作为个人项目的外部预注册 commitment。当前 candidate grade 要求 anchor 为 `PROVIDER_QUALIFIED_CAPTURE`，而 provider-qualified construction 又被整体禁用，导致 controlled candidate grade实际上不可达。

**最小修复**

拆成两个正交字段：

```text
market_data_grade = GENERIC | AUTHORITATIVE_PROVIDER
commitment_grade = NONE | EXTERNAL_COMMITMENT
```

- GitHub remote commit/Release 可满足 `EXTERNAL_COMMITMENT`；
- 只有固定市场数据 adapter 可满足 `AUTHORITATIVE_PROVIDER`；
- 不需要 provider registry，只实现当前实际数据源的一条 adapter。

**回归测试**

- GitHub anchor 可证明 preregistration head，但不能提升市场数据 grade；
- 市场数据权威 receipt 不能替代 experiment anchor；
- 两项均满足时才能形成候选证据等级。

## 4. 优先级与交付策略

### PR #126 只再修两个 correctness blocker

当前 PR 已有 71 commits 和大规模变更。不要继续把所有效率优化塞入同一个 PR。

在本 PR 中只关闭：

1. `RT-001`：feature/label 因果隔离与 row-level PIT；
2. `RT-002`：历史完整 run assessment 与 prospective stage 分离。

随后以“可靠研究核心”合并；继续保持所有资金和交易授权为 false。

### 下一个小 PR 只做速度到结果

下一 PR 限定为：

1. `run_research(spec, mode)` + `quant research run`；
2. cheap verify / explicit replay；
3. content-addressed bundle manifest；
4. 一个 branch-level frozen adapter；
5. 一个真实数据源的纵向切片。

不要增加 manager、dispatcher、registry、通用 provider 平台或新的审批流程。

## 5. 推荐的日常研究路径

```text
1. quant research run spec.json --mode explore
   - PIT feature build
   - train/validation only
   - base/adverse costs
   - compact PASS/FAIL/BLOCKED report
   - no final holdout, no external anchor, no full bundle replay

2. 冻结 strategy/data/split
   - append preregistration once
   - publish Git commit/Release commitment

3. quant research run spec.json --mode verify
   - one final holdout access
   - one full controlled run
   - ReturnArtifact + statistical evaluation
   - one full replay in CI
   - compact evidence manifest

4. 外审只看 verify artifact
```

这条路径保留研究完整性，但避免每次探索都承担最终候选级证据成本。

## 6. 最终判断

当前项目的**组件拓扑已经轻量化**，但**日常研究路径仍然过重**。

最强的下一步不是再增加保护，而是：

```text
修正两条因果关系
+ 提供一个标准研究入口
+ 将昂贵重放推迟到 verify/promotion
+ 选一个真实数据源完成纵向闭环
```

在这些完成前：

```text
research_core=USABLE_WITH_CAUTION
fast_result_pipeline=NOT_READY
capital_grade_research=false
all_trading_authorizations=false
```
