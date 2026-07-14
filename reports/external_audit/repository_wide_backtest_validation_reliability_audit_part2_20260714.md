# Repository-wide Audit — Part 2

## 回测与验证可靠性审查

**范围：** 单人、单机 WSL、本地研究、约 40 万元资金。审查所有仍可能影响 P&L、策略选择、数据语义或候选状态的活跃代码；历史报告和归档仓库按 manifest、commit、入口状态和调用关系审查。高风险运行代码逐行语义审查，并补充独立小型动态复现。

## 审查对象

- `quant_research_lab`：A 股独立 R5，implementation `d074e3cb8ab1f3936a48c86a00aa4dcc21d6f158`，smoke `d5e902af4beab6826ebc34c9a940b881f25ad750`。
- `A_Share_Monitor`：latest `ab12cf99331a39a1396c7c7f885072a9f0f68c08`；回测核心审查于 active-preservation ref `1a64e70873fc8a3c3d998e509cbcf690010ffef0`。
- `US_Stock_Monitor`：latest `872f54211e56a162e713d987d904b49d2521bd25`。
- `strategy_work`：latest `a050e20ba50ada3f8bb052585c667770dac2c2c4`；statistics `a1cf3e0978e47529b8ee2e7686ea7950e0d226ed`。
- `us_stock_30w`：R2/R3 `e47d4155...` / `2e34749f...`。
- `qts` archived ref `3565b0b927e75625c77480f619b3f4700530965f`。
- `STRATEGY_VAULT` frozen archive `f0c9d4cb4d94d89054063d6a127bb54e39c62a59`。
- `market_data` 和中央数据契约：确认其不应形成另一套回测引擎。

## VERDICT

```text
PART2_OVERALL_VERDICT: REWRITE_SELECTED_COMPONENTS
CURRENT_BACKTEST_EVIDENCE: NOT_RELIABLE_FOR_STRATEGY_ACCEPTANCE
A_SHARE_R5: REWRITE_REQUIRED_BEFORE_FULL_REPLAY
A_SHARE_MONITOR_ENGINE: USABLE_WITH_LIMITATIONS_AND_PARITY_REFERENCE
US_STOCK_MONITOR_ENGINE: USABLE_WITH_FIXES_BEST_CURRENT_US_BASE
US_STOCK_30W_ENGINE: ARCHIVE_ENGINE
STRATEGY_WORK_SCANNERS: DIAGNOSTIC_ONLY
STRATEGY_WORK_STATISTICS: KEEP_WITH_FIXES_FOR_FINALISTS
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
```

不需要再建机构级通用平台。需要修复少数关键算法，每个市场冻结一个 canonical engine，其余路径降为 parity/reference/archive。

# STATIC_FINDINGS

## 1. A 股 R5：测试和 smoke 很完整，但存在会反转结论的错误

### CRITICAL — allocator 同日前视

Soft allocator 把日期 D 的概率直接配置到日期 D 的 sleeve return；hard allocator把日期 D 的 confirmed state 直接配置到日期 D 的 sleeve return。状态和概率由 D 收盘信息产生，权重应在 D+1 生效。现有测试固定了同日行为，所以 `39 passed` 和 `allocators_complete=true` 不能证明因果正确。

### CRITICAL — 缺失行情把持仓估值为 0

`event_loop._market_value()` 对缺失 symbol price 使用 `0.0`。短期停牌应携带最后已验证价格并记录 stale age；超过阈值应阻塞；退市应使用明确处置规则。不能无声归零，也不能无限期静态估值。

### CRITICAL — deterministic detector 可能永远不切换

当前 dwell 只在 `candidate == confirmed_state` 时增长。若初始 candidate 与 neutral 不同，confirmed dwell 保持 0，持续 candidate 也无法确认。应分别维护 `candidate_state/candidate_streak` 与 `confirmed_state/confirmed_dwell`。

### HIGH — 缺少容量约束

R5 有整数手、费用和现金约束，但没有 amount/volume/ADV participation。正式 A 股回放必须加入容量模型。

### 其他高价值修复

- 默认资金 100 万，与约 40 万账户不符；正式主配置应为 40 万，并做 20/80 万敏感性。
- universe 尚未完整处理 dated active/listing/delist/board。
- metrics 中所谓 Sharpe 实为 annual return / annual volatility，应改名或换成标准日收益 Sharpe。
- family sleeve 先平均独立策略收益，重叠证券没有净额化；可作诊断，不是证券级共享资本证据。
- selection ledger/gates 主要是同一 pipeline 的自报摘要，不是访问控制。
- train-only probabilistic detector 方向正确，但应增加 convergence、cluster occupancy 和 D+1 对齐检查。

## 2. A_Share_Monitor：市场规则成熟，但验证层仍会错误通过

### 可保留

- close-D signal / next-session open；
- 同日卖出优先；
- 最低佣金、印花税、上交所过户费；
- 100 股 lot、涨跌停、停牌；
- amount/volume capacity；
- 日期分块不拆分同一交易日。

### HIGH — 缺少 `available_date` 时返回 no-future PASS

`_no_future_leak_status_chunked()` 在字段不存在时直接返回 PASS。没有可审计时间戳只能是 `UNVERIFIED/WARNING/FAIL-CLOSED`，不能算通过。

### 其他问题

- OHLC 缺失只记 WARNING，Portfolio 可无限期携带旧价；需要 stale-session 上限和退市规则。
- stop/take 使用当日 low/high 触发次日开盘卖出，应准确命名为“日内触发、次日执行”，不是止损价成交。
- holding days 在退出判断和 trade log 中分别使用交易日与日历日。
- 默认资金 100 万；fill config 允许 10% amount 和 10% volume participation，对小盘研究过宽。建议 1% ADV 主假设，0.5%/2% stress。
- walk-forward summary 与 robustness payload 混入 test 指标。当前 grade 主要用 train/validation，但应把 selection summary 和 final holdout report 物理分离。
- evaluator 可自动输出 `PAPER`，对当前个人研究阶段没有必要。建议只保留 `REJECTED / RESEARCH_ONLY / VALIDATION_INTERESTING / FINAL_HOLDOUT_PASSED`。
- `alpha_vs_benchmark` 只是总收益差；turnover 定义需明确；Sharpe 应标注 rf=0。

## 3. US_Stock_Monitor：当前最适合成为美股 canonical engine

### 可保留

- close-D / next actual panel session open；
- 同日卖出优先和 retained-target resize；
- held symbol 缺失 close 时 fail closed；
- raw Sina central data 禁止转为 adjusted PricePanel；
- selection 主要使用 validation；
- synthetic pipeline 不冒充真实策略。

### HIGH — no-fills gate 读取全样本 fill count

Evaluator 使用 `result.n_fills == 0`，而 n_fills 来自完整 run。若 train/validation 零成交、只有 test 成交，策略可绕过 no-fills 拒绝。应分别记录 train/validation/test fills，selection 只能读 development fills。

### 其他问题

- settlement 对全历史固定 T+1，应明确为 broker/account 假设或按日期实现；若日期化，必须使用正式交易日历而非 weekday helper。
- `walk_forward()` 只是切分固定 equity curve，应改名 `temporal_fold_stability`。
- corporate action 未同步调整 volume；halt/delist 仅匹配单日；缺 delisting return。
- 5 bps cost + 5 bps slippage 对 QQQ/SPY/GLD 等流动资产可作 40 万账户基础，对小盘股需额外 ADV/cost tier。

## 4. strategy_work：统计工具值得保留，但尚未保护 canonical selection

可保留：frozen holdout、experiment ledger、artifact hash、split-boundary purge、moving-block bootstrap、HAC、PSR/DSR、CSCV-PBO。

问题：

- A/US 普通 candidate gate 不要求通过这些工具；“仓库有统计函数”不等于策略通过了它们。
- PBO 用 `periods // n_blocks`，尾部 observations 被静默丢弃。
- PBO 只接 return matrix，没有 decision/label-end dates，20/40/60 日重叠标签可能跨 CSCV block 泄漏。
- holdout SHA 只检查格式，没有绑定并验证实际 holdout artifact。
- PSR/DSR 没有强制 Sharpe 的频率语义，annualized Sharpe 配 daily observations 会夸大证据。
- factor/regime scanners 是 close-D 到 close-D+h 的 forward-return diagnostics，没有 next-open、订单、现金、lot、停牌和真实 fill，应永久标记 `HYPOTHESIS_DIAGNOSTIC_ONLY`。
- 多个 scanner 使用当前 symbol master 的 ST/退市名称过滤历史，存在 current-status/survivor-style bias。

## 5. 归档路径

- `us_stock_30w` 旧引擎此前已证实期初空仓、成本未正确扣除、specialist 不忠实、无真实 allocator；R3 只输出 DB blocker。结论：归档引擎，保留失败记录。
- `qts` 保持 archived/reference-only。
- `STRATEGY_VAULT` 已冻结为非活动历史档案，保持禁用。

# DYNAMIC_REPRODUCTIONS

这些是独立小型确定性样本，不代表市场收益。

1. **Detector deadlock**：连续 10 日 non-neutral candidate，confirmed state 始终 neutral，dwell 始终 0。
2. **Allocator look-ahead**：A/B 隔日轮流 +5%/-5%，当日 state 总指向当日赢家：同日配置 terminal factor `2.6533`；权重延迟一日后 `0.3774`。
3. **Missing price**：100 股、价格 10 的 market value 为 1000；缺失价格后当前函数返回 0。
4. **Sharpe 命名**：同一 20 期 synthetic equity，annual-return/vol 为 `-0.0696`，标准 daily Sharpe 为 `+0.2291`。
5. **US fill leak**：相同 development metrics 下，full-run n_fills=1 不触发 no-fills，n_fills=0 才拒绝；test-only fill 可间接影响状态。
6. **PBO remainder**：123 observations、10 blocks，只使用 120，静默丢弃 3。

# OVERENGINEERING_FINDINGS

- R5 有 39 个测试和多层 smoke/gate，却漏掉权重生效日这一核心不变量。
- strategy_work 有高级统计，但未接入真实 selection。
- 多套引擎重复实现同一概念，却缺一个简单 cross-engine golden fixture。
- 大量 external audit 反复审 packet，而 canonical data snapshot 和 canonical engine 尚未冻结。
- test/holdout 被反复“diagnostic”查看，实际降低独立性。

可靠性应来自少数不可绕过的算法不变量，不是 gate 数量。

# 40 万个人账户的最小可靠标准

必须有：

1. after-close signal、next-session execution；
2. 现金/持仓/费用逐日对账；
3. A 股 lot、最低佣金、印花税、涨跌停、停牌；
4. US adjusted total return、split/dividend、明确 settlement；
5. missing/stale/delist policy；
6. train+validation 选择，一次真正 untouched final holdout；
7. crossing-label purge；
8. 40 万主资金，20/80 万敏感性；
9. A 股 1% ADV 主假设，0.5%/2% stress；
10. 流动 US ETF/大盘股 5–10 bps 基础，小盘另设 tier；
11. total return、CAGR、标准 Sharpe、max DD、turnover、exposure、trade count、cost；
12. 每市场一组 engine fixtures + 一个 accepted real snapshot smoke；
13. 只有 final finalists 才使用 DSR/PBO 和外审。

不需要：L2 order book、多券商 routing、多租户权限、每次参数扫描做 PBO、每次普通回测外审、同一市场多套长期并存引擎、普通 evaluator 预先输出 paper/live 状态。

# KEEP / SIMPLIFY / ARCHIVE

## KEEP

- R5 import-safe 架构和 T+1 event-loop 骨架；
- A_Share_Monitor 的成本/fill/capacity 市场规则；
- US_Stock_Monitor 的 chronological engine 和 raw/adjusted fail-closed；
- strategy_work 的 purge、block bootstrap、HAC 和 experiment-ledger 思路；
- 所有失败记忆。

## SIMPLIFY

- 每市场只保留一个 canonical engine；
- candidate labels 缩为 4 个；
- selection summary 与 holdout report 分开；
- advanced statistics 只用于 finalists；
- strategy_work 只做 hypothesis/diagnostics/statistics，并调用 canonical engines；
- smoke gate 缩为 10–15 个真正会失败的不变量。

## ARCHIVE

- `us_stock_30w` engine/specialist/allocator；
- qts active references；
- R2/R3/R4 失败 DS engines；
- diagnostic scanners 的历史输出；
- R5 parity 完成后的 A_Share_Monitor legacy engine。

# TARGET_DESIGN

```text
A_SHARE CANONICAL
  quant_research_lab R5
  + 修复 allocator / detector / valuation / metrics / capacity
  + 移植 A_Share_Monitor 已验证市场规则

US CANONICAL
  US_Stock_Monitor
  + development-fill gate
  + settlement/calendar
  + corporate-action/delist
  + liquidity tiers

SHARED VALIDATION ONLY
  split_contract.py
  metrics.py
  robustness.py
  research_statistics.py

strategy_work
  preregister hypotheses
  diagnostic scans
  final-stage statistics
  calls canonical engines
```

不要建立跨 A/US 的超级通用引擎；只共享 split、metrics、statistics。

# FIXES_REQUIRED

## P0 — 任何 full replay 和新大规模策略搜索前

1. R5 allocator D+1 生效；
2. R5 missing/stale/delist policy；
3. deterministic detector candidate streak；
4. R5 A 股 capacity、40 万主配置和成本一致性；
5. A_Share no-future 缺字段改为 UNVERIFIED/FAIL；
6. US no-fills 改为 development fills；
7. 冻结每市场一个 canonical engine；
8. 加入 adversarial tests。

## P1

9. 统一标准 metrics；
10. 修复 US settlement/calendar/corporate actions；
11. 修复 PBO remainder、purged CSCV、holdout binding、Sharpe frequency；
12. scanner 永久 diagnostic-only；
13. A 股 R5 与 legacy engine 做一个 golden-fixture parity；
14. accepted DB snapshot 到位后做一次 real-data smoke。

## P2 — final finalists only

experiment ledger、purged/embargoed final validation、DSR/PSR/PBO/HAC、一次 final holdout、一次外审，然后才讨论系统接入。

# 为什么策略开发一直拖沓

顺序错误比策略本身更关键：在 canonical snapshot 和 engine 之前大量搜索；多套引擎结果不可比；forward-return diagnostics 被当成准回测；高级统计没有接入 selection；修复后增加更多 packet/gate；holdout 反复查看；缺少 stop rule。

新周期应固定为：

```text
一个 snapshot
+ 每市场一个 engine
+ 每个 family 最多 4–6 个预注册 variants
+ validation 决策
+ 一次 final holdout
+ 接受或淘汰
```

# NEXT_ACTION

1. 暂停新的 full replay 和大规模策略搜索；
2. Part 1 数据库最小化继续并行；
3. 立即执行 P0 backtest-correctness patch；
4. P0 外审通过后冻结 canonical engines；
5. Manager 发布 accepted immutable DB snapshot；
6. 做 real snapshot smoke；
7. 再进入精简策略研究周期；
8. 第三部分可开始设计流程，但 P0 前不得启动新全量研究。

# BOUNDARY_RESULT

```text
PASS_RESEARCH_ONLY_BOUNDARY
NO_STRATEGY_ACCEPTANCE
SYSTEM_INTAKE_READY=false
STRATEGY_CANDIDATE_AVAILABLE=false
```
