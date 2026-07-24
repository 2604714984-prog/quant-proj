# PR #126 Round 5 外部续审报告

> 本报告只审查冻结代码提交 `81403aa223ad6d11a7339fd970b65512bdc0a5c8`。
> 后续用于保存本报告的文档提交不属于被审代码范围。
>
> 项目当前优先级是：**可靠地、快速地产出可验证研究成果**。本报告不要求继续堆叠泛化安全框架；整改应集中在研究因果链中仍断开的少数关系。

## 1. 冻结边界

- Repository: `2604714984-prog/quant-proj`
- PR: `#126`，Draft / open / not merged
- Base: `v2-main@31329dbfd7b9bb1c184a13ee7fe2e60bd0a6ba14`
- Previous audited head: `857b264883bbcdaf06e47f66df4f878dfea5c475`
- Audited remediation head: `81403aa223ad6d11a7339fd970b65512bdc0a5c8`
- GitHub Actions merge ref: `37da8ccaa028e5cd983054148217a836428f1cec`
- Workflow run: `30026809844` — `completed/success`
- Job: `89273236139`

GitHub Actions 已确认 wheel build/install、`pip check`、checkout 外 `quant info`、Ruff 和 pytest 步骤成功。PR 报告 `270 passed`；本轮连接器未独立提取完整日志尾部，且 workflow 没有可下载 artifact，因此不独立确认精确测试数量和 wheel SHA。

## 2. 外审裁决

```text
external_audit_verdict=REQUEST_CHANGES

architecture_cleanup_substantially_complete=true
prospective_tree_lightweight=true
prospective_tree_single_writer=true
provider_default_fail_closed=true

code_remediation_complete=false
only_external_evidence_remaining=false
historical_run_evidence_valid=false
return_artifact_real_path_reachable=false
multiplicity_family_real_path_valid=false
transformation_hermetic=false
end_to_end_research_replay=false
capital_grade_research_process=false

strategy_candidate_available=false
recommendation_authorized=false
paper_trading_authorized=false
live_trading_authorized=false
automatic_execution_authorized=false
```

发现计数：

```text
HIGH=9
MEDIUM=3
BLOCKED_EXTERNAL=1
```

## 3. 已接受的整改

以下修改有实质价值，应保留：

1. Prospective tree 已移除 active terminal archives、旧研究结果和 direct DuckDB writers；全树 AST 测试限制唯一 writer。
2. Generic/transport builder 已不能生成 `PROVIDER_QUALIFIED_CAPTURE`；在没有权威 adapter 时系统正确 fail closed。
3. Arbitrary-callback 实验结果与 `ControlledStageResult` 已分型。
4. Stage 结果保存 initial/final portfolio artifacts，FinalRunReceipt 检查相邻阶段状态 SHA 连续。
5. Candidate bundle v3 已能重放 base/adverse execution，并比较 receipts、portfolio 和 NAV。
6. 成本、容量、A股 raw corporate-action 会计、split manifest 和统计估计器均比初始版本明显加强。

这些改进说明基础设施方向可用；剩余问题主要是**真实正向路径、trial→run→return 绑定、多重检验族和数据转换依赖**，不是缺少更多安全组件。

# 4. P0 阻断问题

## EX6-001 — 真实 runner 结果无法进入 ReturnArtifact `[HIGH]`

**文件/函数**

- `src/quant_system/backtest/event_loop.py::run_static_rebalance`
- `src/quant_system/research/splits.py::capture_return_artifact`
- `tests/controlled_result_fixtures.py::controlled_return_fixture`

**事实**

- `run_static_rebalance` 要求 `stage_context.stage_session == signal_session`。
- execution session 是 `calendar.next_session(signal_session)`。
- `capture_return_artifact` 又要求 `execution_session.session_date == result.stage_session`。
- 正常情况下 next session 不可能等于 signal session。
- 正向测试通过手工 fixture 将两者伪装为同一天，没有调用真实 runner。

**影响**

真实受控历史回测无法产生代码所要求的 ReturnArtifact。当前统计链通过的是 fixture 路径，不是生产路径。

**最小修复**

明确 StagePlan 的日期合同。建议 StageReceipt 同时绑定：

```text
signal_session
execution_session
```

验证 execution 是 signal 的下一 accepted session。ReturnObservation 使用 execution session，但不要求其等于 stage plan 的 signal session。

**回归测试**

- 用真实 `AcceptedSessionCalendar + run_controlled_stage` 生成至少5个连续 stages。
- 真实 chain 必须能生成 ReturnArtifact。
- signal/execution 错位、跳过 session、calendar revision 不一致必须失败。

---

## EX6-002 — ControlledStageResult / FinalRunReceipt 可被手工伪造 `[HIGH]`

**文件/函数**

- `ControlledStageResult.verify_controlled_result`
- `capture_final_run_receipt`
- `tests/controlled_result_fixtures.py`
- `tests/test_experiment_receipts.py`

**事实**

- `verify_controlled_result` 只验证私有 token、grade、SHA 格式、portfolio artifact 和 finite NAV。
- 它没有从 input identity、execution receipts 和 StageContext 重算 receipt chain 与 stage hash。
- 测试使用 `object.__new__` 和 `_CONTROLLED_STAGE_TOKEN` 直接制造 controlled results。

**影响**

任意现金路径可以被包装为 FinalRunReceipt、ReturnArtifact、SplitEvaluation 和 HoldoutResultReceipt。

**最小修复**

建立可重算的 `ControlledStageReceipt`：保存 canonical input artifact、canonical execution receipt payloads、stage context、initial/final portfolio。验证时内部重算：

```text
input_identity
receipt_hashes
stage_hash
final_nav
portfolio continuity
```

FinalRunReceipt 只接受经 verified loader 验证的持久 stage receipts。不要把 Python 私有 token 当成证据权限边界。

**回归测试**

- `object.__new__ + 私有 token + 手工 stage_hash` 必须失败。
- 修改任一 receipt、input identity、NAV 或 portfolio 后旧 receipt 失效。
- 候选正向测试不得使用手工 controlled-result fixture。

---

## EX6-003 — FinalRun/Return evidence 未绑定预注册候选 `[HIGH]`

**文件/函数**

- `FinalRunReceipt`
- `CandidateRunConfig`
- `run_candidate_rebalance`
- `tests/test_event_loop.py::_run_candidate_rebalance`

**事实**

FinalRunReceipt 当前没有绑定每阶段的：

```text
trial_id
DecisionArtifact SHA
DatasetManifest SHA
UniverseMaterialization SHA
cost/config SHA
engine artifact SHA
```

Candidate gate 分别验证 CandidateRunConfig 和 FinalRunReceipt，但没有证明 FinalRunReceipt 的历史 stages 执行了该 CandidateRunConfig。正向测试用独立 synthetic cash path 为另一个 DecisionArtifact 提供显著性证据。

**影响**

策略A可以借用策略B或任意 synthetic cash chain 的 holdout 结果。

**最小修复**

增加 ordered per-stage `TrialRunReceipt`，每个 stage 绑定上述 trial/data/strategy/universe/cost identities。FinalRunReceipt 保存有序 stage receipt SHA，并在 holdout capture 时按 trial 全量核对。

**回归测试**

- 相同 StagePlan、不同 DecisionArtifact 必须失败。
- 不同 dataset/universe/cost/max_positions 不得复用同一历史资格。
- 每阶段 feature snapshot 变化必须体现在有序 receipt 中。

---

## EX6-004 — 资格 StagePlan 与当前 candidate StageContext 可不同 `[HIGH]`

**文件/函数**

- `capture_candidate_run_config`
- `run_candidate_rebalance`
- candidate 正向测试 helper

**事实**

- CandidateRunConfig 与 FinalRunReceipt 的 plan SHA 会比较。
- `stage_context.plan_sha256` 没有与它们比较。
- 测试使用5日历史 FinalRunReceipt，却用单阶段 StageContext 执行候选。
- CandidateRunConfig 只有一个 signal/decision artifact，无法描述真实多阶段历史运行。

**影响**

一个计划的 holdout 结果可授权另一个执行计划。

**最小修复**

拆成两个明确入口：

```text
evaluate_frozen_historical_run
apply_qualified_strategy_stage
```

历史入口接受完整 ordered per-stage config；prospective 入口消费独立资格 receipt，并显式绑定新的运行计划。

**回归测试**

- 历史资格阶段不得接受不匹配的 StageContext。
- prospective execution 必须显式声明资格 receipt 与新 plan 的关系。
- 多阶段历史运行不能由一个 decision_at/DecisionArtifact 代表。

---

## EX6-005 — 真实 multi-trial multiplicity family 不可构造 `[HIGH]`

**文件/函数**

- `preregister_trial`
- `CandidateRunConfig`
- `tests/test_experiment_receipts.py::_preregister`

**事实**

- family 内所有 trial 被要求共享相同 `candidate_run_config_sha256`。
- CandidateRunConfig 又绑定 strategy/decision artifact 和参数。
- 不同 trial 必然拥有不同 config SHA。
- family_size=2 测试使用固定假 SHA，而不是两个真实 CandidateRunConfig。

**影响**

诚实的 Holm/Bonferroni family 无法包含多个不同策略或参数。

**最小修复**

拆分：

```text
FamilyContract:
  dataset/split/holdout/stage/evaluation/cost/alpha/family_size

TrialConfig:
  strategy/feature/parameters
```

Anchor 冻结有序 TrialConfig SHA 集合。

**回归测试**

- 两个真实、不同 DecisionArtifact 的 family_size=2 必须成功登记和批量评估。
- freeze 后增加 trial 或更换任一 TrialConfig 必须失败。
- 禁止使用没有实际 CandidateRunConfig 对象的固定 SHA fixture。

---

## EX6-006 — 收益未绑定 label horizon 与样本构成 `[HIGH]`

**文件/函数**

- `SplitSample`
- `evaluate_split`
- overlap/horizon tests

**事实**

- SplitSample 保存 `observed_at` 和 `label_end_at`。
- evaluate_split 只取 observed date 集合，并读取每日期一个 portfolio return。
- 它没有按 `observed_at → label_end_at` 构造复合收益。
- 五日标签测试实际使用单日 synthetic returns。
- 同日选择1只或100只证券会消费相同 portfolio return。

**影响**

被校正的重叠标签和实际被检验收益不是同一个 estimand。

**最小修复**

ReturnObservation/ReturnArtifact 绑定：

```text
start_session
end_session
compound_net_return
contributor set
weights or portfolio aggregate receipt
```

**回归测试**

- 五日 label 必须使用真实5日复合净NAV收益。
- 改变 label_end_at 必须改变 return/evaluation identity。
- 同日 selected contributors 变化且聚合 receipt 不匹配时失败。

---

## EX6-007 — Experiment ledger 可换 data root 重开，且无法恢复事件 `[HIGH]`

**文件/函数**

- `persist_experiment_ledger`
- `ExperimentLedgerReceipt.verify_current_bytes`

**事实**

- Ledger 路径来自当前进程的 `QUANT_DATA_ROOT`。
- 换一个 data root 可以创建另一份空 ledger。
- 当前测试只证明旧 receipt 在 root 切换后失效，未证明第二 root 不能新建 family。
- NDJSON 只保存 event index/hash，不保存完整 ExperimentEvent payload。

**影响**

同一 holdout 可跨 root/机器重新开始；新进程又无法从原 ledger 恢复历史链。

**最小修复**

- 绑定不可变 project/data-owner identity，而非仅环境路径。
- 持久化完整 canonical event payload。
- 提供 verified loader。
- holdout key 从冻结 dataset/split/stage/evaluation family contract 派生。

**回归测试**

- 第二进程/第二 root 不得为同一 holdout key 建新 family。
- 只凭 ledger 可恢复全部 events 并合法追加。
- 删除失败 trial 后 anchor head 校验失败。

---

## EX6-008 — Python audit-hook 不是 hermetic sandbox `[HIGH]`

**文件/函数**

- `research/identity.py::_HERMETIC_RUNNER`
- `_run_hermetic_step`
- transformation tests

**事实**

本轮独立复现：Python `open()` 被 hook 阻止，但 `ctypes.CDLL(None).open/read` 可以读取未声明文件。Audit hook 不能阻止本地 syscall、native extension、`/proc` 等旁路。

**影响**

TransformationReceipt 不能证明输出只依赖声明的 raw sources。

**最小修复**

为快速产出，优先选择最小受控方案之一：

1. 受控纯函数/DSL：输入 immutable bytes，输出 immutable bytes；或
2. OS级 sandbox：只读 bind mounts、空 root/cwd、禁网 namespace/seccomp/container。

不要继续扩展 Python audit-hook 规则列表。

**回归测试**

- ctypes libc open/read、mmap、`/proc`、native extension、未声明数据库读取必须失败。
- runtime/interpreter image 变化必须改变 transformation identity。

---

## EX6-009 — Bundle v3 只重放 execution，不重放研究资格 `[HIGH]`

**文件/函数**

- `CandidateRunBundle.verify`
- `_replay_bundle_case`
- `_bundle_artifact_payloads`

**事实**

- artifact payloads 只做自SHA校验，没有 role/path/expected-field 映射。
- replay 不读取这些 payloads。
- replay 直接使用内嵌 weights、universe snapshot 和 execution inputs。
- 它不重算 feature→weights、universe materialization、dataset transformation、ReturnArtifact、SplitEvaluation、FinalRunReceipt 或 experiment family。

**影响**

Bundle 是 execution replay package，不是 end-to-end research replay package。

**最小修复**

使用 role-indexed artifact manifest，按角色重建：

```text
DecisionArtifact
UniverseMaterialization
DatasetManifest/TransformationReceipt
TrialRun/FinalRun
ReturnArtifact/SplitEvaluation
Experiment family/anchor
```

最后重新运行 candidate qualification gate。

**回归测试**

- 替换 feature/definition/dataset artifact，即使重算 envelope SHA 也必须失败。
- 新进程能够重算 weights、historical returns、p-value、fills、NAV 和资格状态。
- 缺失任一 artifact/receipt 时 fail closed。

# 5. P1 问题

## EX6-010 — Ledger/lock 路径身份保护不足 `[MEDIUM]`

Ledger 与 lock 未使用 `O_NOFOLLOW`、single-link regular-file、inode/device 前后检查和 post-close identity。复用 canonical writer 已有的 pinned-file helper；不要新建第二套实现。

## EX6-011 — TerminalAction 混用 UTC 日期和交易所本地日期 `[MEDIUM]`

构造阶段使用 UTC date，后续使用 exchange-local session date。构造阶段只校验类型；在拥有 exchange/session 的校验路径统一使用本地 session date。

## EX6-012 — Receipt 未绑定 exact core engine/package artifact `[MEDIUM]`

FinalRunReceipt 和 bundle 未绑定 event-loop/portfolio/market-policy 的精确代码或可安装 artifact。绑定 source-tree/package manifest、Python/runtime identity；CI 应发布可下载的 source/wheel artifact及SHA。

# 6. 外部阻断

## EA-001 — A股 evidence-room 仍待独立 reviewer receipt `[BLOCKED_EXTERNAL_EVIDENCE]`

Evidence-room README 仍标记：

```text
publication_status=PUBLISHED_UNVERIFIED_EXTERNALLY
verification_status=PENDING_EXTERNAL_RECEIPT
```

这不能用 fixture 或代码测试关闭。独立 reviewer 需只读下载 Release 资产、校验 manifest、运行验证命令并发布绑定身份、commit/tree、asset hashes、output hashes 和零写证明的 receipt。

# 7. 面向 Codex 的整改合同

项目目标是可靠且快速产出研究成果。Codex 下一轮应遵守：

1. **不要新增 manager、dispatcher、registry、ticket、代理层或通用权限框架。**
2. **不要继续增加不建立新等价关系的 receipt 类型。**
3. 第一优先是让真实 event-loop 正向链完整运行：

```text
real controlled stages
→ verified stage receipts
→ FinalRun
→ label-horizon ReturnArtifact
→ SplitEvaluation
→ multi-trial family
→ qualification
```

4. 删除或停止使用 `tests/controlled_result_fixtures.py` 作为候选正向证据；fixture 只能测试单一小函数。
5. 每个关键正向测试必须由真实 calendar、真实 `run_controlled_stage`、真实 costs/capacity 和真实 receipts 产生。
6. FamilyContract 与 TrialConfig 分开，至少用两个实际不同策略/参数完成一个 family_size=2 测试。
7. Historical qualification 与 prospective execution 分开，避免在一个入口里混用两个 StagePlan。
8. 转换依赖优先使用受控纯函数；不能把 Python audit-hook 声称为 hermetic。
9. 保持所有 authorization 为 false；真实 provider 和 EA-001 外部证据继续标记 BLOCKED。
10. 完成后冻结新代码 head，并在台账列出：finding→commit、真实正向测试、命令输出、数据库写入和 provider 请求。

## 推荐原子提交顺序

```text
1. fix stage signal/execution semantics and real controlled chain
2. make ControlledStageReceipt fully recomputable
3. bind TrialRun/FinalRun/ReturnArtifact to trial config
4. split historical qualification from prospective execution
5. split FamilyContract from TrialConfig and persist full ledger events
6. bind label horizon and contributor set to returns
7. replace audit-hook sandbox with pure/OS-isolated transform
8. upgrade bundle to qualification replay
9. ledger path identity, terminal local date, engine artifact binding
```

# 8. 最终状态

PR #126 应继续保持 Draft。当前不能接受：

```text
code_changes_complete_for_reported_findings=true
only_external_evidence_remaining=true
```

准确状态为：

```text
architecture_cleanup_substantially_complete=true
several_fail_closed_mechanisms_improved=true
core_research_evidence_graph_still_invalid=true
code_level_findings_remaining=true
external_evidence_remaining=true
```
