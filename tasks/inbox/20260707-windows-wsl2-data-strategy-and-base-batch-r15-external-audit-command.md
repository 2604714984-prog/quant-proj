你说得对，这次我继续用 GitHub connector 把 R14 相关文件又往下核了一轮。下面是**基于实际 GitHub 文件阅读后的最终外审结论**，不是基于你的摘要。

# 文件级核查范围

## 已核查的 GitHub 锚点

* `A_Share_Monitor` source evidence package:

  * branch: `codex/harden-a-share-research-pipeline`
  * repair audit tag: `windows-wsl2-data-chain-repair-external-audit-20260706`
  * repair package commit: `735ac8f18266a3720d1b0e729ed6b203539d758e`
  * R14 evidence commit: `dd3089e2a9c1693ea0571db37c185d6584f1bc14`
* `strategy_work` sync:

  * commit: `2bfbe33e654e7ceb76117ab7b156ff44f2d979be`
* `quant-proj` receipt:

  * commit: `61c71087cb33ac55c6f00b9aa7da12e8a111a13b`

A_Share_Monitor 从 `735ac8f...` 到 `dd3089e2...` 只有 1 个 commit，新增/修改的是 R14 证据文件和 `generate_windows_wsl2_r14_evidence.py`，包括 40,679 行 East Money gap JSON、3,069 行 survivor-bias CSV、rejection attribution CSV、chunked blocker report、manifest hardening 等。

A_Share_Monitor 从 `6bfeb816...` 到 `735ac8f...` 包含 data-chain repair package、Baostock staging rebuild package、repair script、handoff、external audit packet 和 data-chain repair manifest。

GitHub Actions / status checks 没有可用 workflow run 或 combined status 记录；所以 validation 只能按仓库报告里记录的本地命令结果核验，不能声明有远端 CI 背书。

## 已逐项读取的关键文件

我实际读取了：

* 外审包：`windows_wsl2_data_chain_repair_external_audit_packet_20260706.md`
* Dev-to-audit handoff
* `LATEST_CODEX_AUDIT_REQUEST.md`
* data-chain repair and strategy rerun report
* manifest JSON
* manifest hardening report
* East Money gap matrix markdown
* survivor-bias row-level evidence markdown
* strategy rerun rejection attribution markdown
* chunked strategy blocker recheck markdown
* `repair_wsl_staging_data_chain.py`
* `generate_windows_wsl2_r14_evidence.py`
* `strategy_search.py`
* `chunked_features.py`
* `feature_store.py`
* `test_strategy_search_smoke.py`
* `test_feature_store_memory_safety.py`
* `.gitignore`
* `strategy_work` memo
* `quant-proj` receipt

我没有逐行人工展开 40,679 行 East Money JSON 和 3,069 行 survivor CSV 的全部行，但已核对生成逻辑、markdown summary、manifest summary、compare file list 和主要统计一致性。

---

# VERIFIED VERDICT

**VERIFIED_ACCEPT_WITH_WARNINGS**

R14 源仓级数据/策略证据批次可以接受。它不是“调参找通过”，而是完成了一个可审计的数据链修复和策略重跑证据批次。

核心结论被 GitHub 文件支持：

1. `survivor_bias_fail` 已从候选拒绝原因里消失。
2. East Money crosscheck 仍是 partial coverage，不是 full-market qualification。
3. 策略 rerun 仍全部 rejected。
4. 剩余 blocker 是 strategy-quality / robustness blocker。
5. wide3068 full-frame 仍然 unsafe，chunked mode 必须继续使用。

---

# 关键核查发现

## 1. HG-EXEC 范围成立，但只限 staging

外审包明确写了用户 HG-EXEC 授权范围：允许 `A_Share_Monitor` 在 WSL2 上做 provider/network ingest 和 DB/cache rebuild，但只限 staging validation，不允许 readiness、registry、product route 变更。

外审包也明确列出 out-of-scope：readiness promotion、registry activation、product-route activation、recommendation、ticket、`PENDING_HUMAN_REVIEW`、broker/order/paper/live/auto、secret handling、`.env` read、raw DB/cache/runtime output commit、full-frame wide3068 StrategySearch rerun。

**结论：**这批网络/DB/cache 操作在 R14 包里有明确 staging HG-EXEC 范围，但这个授权不能自动延续到 R15 的 provider 扩容。R15 如果要继续抓 East Money，必须新建 task-level HG-EXEC。

---

## 2. 数据链修复结果被多文件一致支持

data-chain repair report 记录：

* snapshot: `wsl2_chain_repair_20260706_195210`
* selected symbols: `3068`
* selected delisted symbols: `80`
* eligible Baostock-delisted symbols since 2018: `162`
* delisted rows fetched: `188813`
* daily rows: `5398232`
* date range: `20180102-20260703`
* `features_daily` rows with non-empty `delist_date`: `115199`。

manifest hardening 和 manifest JSON 也记录相同核心数字：`daily=5398232`、`daily_basic=5398232`、`adj_factor=5398232`、`stk_limit=5398232`、`features_daily=5398232`、East Money crosscheck `325293` rows / `198` symbols。

**结论：**数据链修复包内部一致性较好。

---

## 3. East Money crosscheck 只能算 partial coverage

East Money gap matrix 明确显示：

* local rows: `5398232`
* local symbols: `3068`
* East Money rows: `325293`
* East Money symbols: `198`
* common pairs: `325293`
* missing East Money rows: `5066522`
* symbol coverage: `0.064537`
* row coverage: `0.060259`
* OHLCV mismatch rows: `0`
* mismatch rate on common pairs: `0.0`。

更细一点：

* `CROSSCHECK_PASS`: `77` symbols
* `CROSSCHECK_MISSING_EAST_MONEY`: `2870` symbols
* `CROSSCHECK_DATE_GAP`: `121` symbols。

**结论：**不能写“198 symbols pass”。更准确是：

```text
198 symbols have some East Money overlap.
77 symbols are full CROSSCHECK_PASS.
121 symbols have East Money coverage but date gaps.
2870 symbols lack East Money coverage.
```

R15 必须把 `198/3068` 拆成 `77 pass + 121 date-gap + 2870 missing`。

---

## 4. Survivor-bias evidence improved，但不能写 fully eliminated

survivor-bias row evidence report 显示：

* symbols audited: `3068`
* delisted symbols with pre-delist evidence: `80`
* current listed symbols with no delist date: `2988`
* unresolved survivor-bias symbol count: `0`
* rows after delist date: `0`。

文件明确解释：`CURRENT_LISTED_NO_DELIST` 对当前上市标的是 expected；关键修复证据是 historical delisted symbols 已存在，且 feature rows 位于 delist date 前或当天。

文件也明确警告：这支持 “survivor-bias evidence chain improved”，但不证明 survivor-bias risk fully eliminated，也不推动 data-clear 或 strategy readiness。

**结论：**R14 的 survivor-bias 修复是真进展，但仍必须保留 scope limitation。

---

## 5. 策略全部 rejected 的结论被支持

rejection attribution report 显示 pre/post 对比：

* `bare_minimum_r13_wide3068` 从 `parameter_instability_fail + survivor_bias_fail` 变成只剩 `parameter_instability_fail`。
* `lowvol_quality_focused_r13_wide3068` 从包含 `survivor_bias_fail` 的多重拒绝原因，变成不再包含 survivor-bias，但仍有 `cost_stress_fail`、`max_drawdown_reject`、`parameter_instability_fail`、`trade_count_too_low`、`validation_trade_count_too_low`。

Rerun report 也记录：

* bare-minimum: 1 candidate, 0 approved, 1 rejected, survivor-bias PASS, cost-stress PASS, reason `parameter_instability_fail`, test Sharpe `-0.881046`。
* low-vol-quality: 4 candidates, 0 approved, 4 rejected, survivor-bias PASS, cost-stress FAIL warning，3 个 trade-count weakness，1 个 drawdown/instability/cost-stress fail。

**结论：**R14 策略结果必须保持为 `all rejected`。不能写成 candidate recovery。

---

## 6. Chunked 路径已存在，并且 full-frame guard 有代码支持

`strategy_search.py` 中 `run(chunked=False)` 会先调用 `_raise_if_full_frame_unsafe()`；如果 `features_daily` 超阈值则抛出 `BLOCKED_FULL_FRAME_STRATEGY_SEARCH_UNSAFE`。

`_run_chunked()` 使用 `ChunkedFeatureReader`，生成 chunk artifacts，并在输出 `memory_telemetry` 中记录 `full_features_daily_loaded=False` 和 `chunked_feature_reader=True`。

`chunked_features.py` 中有 `DEFAULT_SAFE_FULL_FRAME_CELLS = 100_000_000`，并通过 `TableProfile.unsafe_for_full_frame` 判断 `row_count * column_count` 是否超阈值。

chunked blocker report 显示当前 `features_daily` 为：

```text
5,398,232 rows
180 columns
971,681,760 cells
estimated memory bytes 15,546,908,160
safe full-frame cells 100,000,000
full-frame status BLOCKED_FULL_FRAME_STRATEGY_SEARCH_UNSAFE
```

它还记录 post-repair rerun telemetry 为 `full_features_daily_loaded=False`、`chunked_feature_reader=True`。

**结论：**chunked blocker 判断成立。

---

## 7. 小样本 equivalence test 已存在

`test_strategy_search_smoke.py` 包含：

* missing features 时必须走 chunked build，不允许调用 full in-memory build；
* unsafe full-frame guard 测试；
* small-cache full-frame vs chunked equivalence test，比较 label、reasons 和多个 train/validation/test numeric metrics，要求差异为 0。

`test_feature_store_memory_safety.py` 也覆盖 legacy in-memory 行为和 `build_to_store()` streaming build。

**结论：**R14 的 chunked path 不是只有报告层声明，有基础测试支撑。R15 还需要把 equivalence 从 synthetic/small 扩展到更多真实小缓存和更多策略族。

---

## 8. 数据/cache 输出确实被 .gitignore 屏蔽

`.gitignore` 排除了 `.env`、token-like 文件、`.duckdb`、`.parquet`、`data/**`、outputs、logs、recommendation tickets 等。

**结论：**原始 DB/cache/Parquet/runtime outputs 未被纳入 Git 的约束在配置层成立。

---

## 9. 一个需要修正的细节：RSS 单位

`strategy_search.py` 中 `memory_telemetry` 字段名写的是 `max_rss_bytes`，但值来自 `resource.getrusage(...).ru_maxrss`。在 Linux/WSL 下这个值通常是 kilobytes，不是 bytes。

Rerun report 用 `max RSS: 1997256 kB` / `2271128 kB`。

**结论：**这个不是外审 blocker，但 R15 必须修成统一字段：

```text
max_rss_kb
max_rss_bytes
max_rss_gb
```

不能继续把 ru_maxrss 直接命名为 bytes。

---

# FINAL VERDICT

```text
VERDICT:
VERIFIED_ACCEPT_WITH_WARNINGS

EXTERNAL_AUDIT_TRIGGER_OPEN:
no

FIXES_REQUIRED:
none before the next ordinary data/strategy batch

MANDATORY_WARNINGS_TO_CARRY_FORWARD:
1. East Money crosscheck is partial only.
2. 198 symbols have overlap, but only 77 are CROSSCHECK_PASS and 121 have date gaps.
3. Survivor-bias evidence improved; risk is not proven fully eliminated.
4. All strategies remain rejected.
5. Remaining blockers are strategy-quality/robustness blockers.
6. wide3068 full-frame remains blocked.
7. R15 must fix memory telemetry units.
8. Future provider expansion requires fresh task-level HG-EXEC.
```

---

# NEXT_BATCH

```text
WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706
```

下面是基于**彻底 GitHub 文件核查后**的下一步大任务包。

---

# A. A_Share_Monitor 数据链与数据基座任务

## A-WIN-R15-1 / East Money coverage expansion priority queue

目标：把 R14 partial coverage 拆成可执行扩容队列。

输入：

* R14 East Money gap matrix。
* 当前状态：

  * 77 `CROSSCHECK_PASS`
  * 121 `CROSSCHECK_DATE_GAP`
  * 2870 `CROSSCHECK_MISSING_EAST_MONEY`

任务：

* 生成 symbol-level priority queue。
* 对 2870 missing symbols 分类：

  * main board
  * GEM / ChiNext
  * STAR
  * delisted / historical
  * low liquidity
  * short history
  * ST-like excluded
  * mapping issue
  * provider timeout / throttling
* 输出 first 300 / next 1000 / full 3068 的扩容顺序。
* 不执行网络。
* 若需要抓取，输出：

  * `HG_EXEC_REQUIRED_FOR_EAST_MONEY_COVERAGE_EXPANSION`

交付物：

```text
reports/workspace_dispatch/windows_wsl2_east_money_coverage_priority_queue_20260706.md
reports/workspace_dispatch/windows_wsl2_east_money_coverage_priority_queue_20260706.csv
```

---

## A-WIN-R15-2 / East Money date-gap diagnostics

目标：专门解释 121 个 `CROSSCHECK_DATE_GAP`。

任务：

* 对 121 date-gap symbols 输出：

  * local date range
  * East Money date range
  * missing dates
  * missing row count
  * gap month buckets
  * train/validation/test impact
  * likely reason: provider gap / listing-date gap / calendar gap / delist gap / unresolved
* 不补抓。
* 不把 date-gap symbols 计为 pass。

交付物：

```text
reports/workspace_dispatch/windows_wsl2_east_money_date_gap_diagnostics_20260706.md
reports/workspace_dispatch/windows_wsl2_east_money_date_gap_diagnostics_20260706.csv
```

---

## A-WIN-R15-3 / Controlled East Money HG-EXEC plan only

目标：准备未来 East Money 扩容的审批包。

任务：

* 写明：

  * provider
  * symbol batch
  * date range
  * fields
  * rate limit
  * retry policy
  * batch size
  * worker count
  * output table/path
  * row hash
  * source file hash
  * snapshot id
  * expected coverage
  * failure handling
* 不读取 `.env`。
* 不输出 token。
* 不执行网络。

交付物：

```text
reports/workspace_dispatch/hg_exec_plan_east_money_crosscheck_expansion_20260706.md
```

---

## A-WIN-R15-4 / Survivor-bias evidence hardening v2

目标：把 survivor-bias evidence 继续固化为 split-level matrix。

任务：

* 基于 3068 symbols 输出：

  * current listed
  * historical delisted
  * unresolved
  * rows after delist
  * train eligible
  * validation eligible
  * test eligible
  * missing delist evidence
  * evidence source
* 结论必须写成：

  * `SURVIVOR_BIAS_ACTIVE_REJECTION_REMOVED_WITH_REMAINING_SCOPE_LIMITS`
* 禁止写：

  * `survivor bias fully eliminated`

交付物：

```text
reports/workspace_dispatch/windows_wsl2_survivor_bias_evidence_hardening_v2_20260706.md
reports/workspace_dispatch/windows_wsl2_survivor_bias_split_matrix_20260706.csv
```

---

## A-WIN-R15-5 / Features_daily lineage and staging assumptions manifest

目标：把 `features_daily` 建成可审计 derived feature artifact。

任务：

* 为每个 source table 记录：

  * row count
  * symbol count
  * date range
  * source
  * synthetic flag
  * staging flag
* 为每类 feature 记录：

  * source table
  * derivation rule
  * availability timing
  * no-future condition
  * missingness
* 必须显式记录 staging assumptions：

  * `adj_factor = identity staging factor`
  * `stk_limit = board-level computed`
  * `suspend_d = inferred from missing daily bars`
  * East Money crosscheck partial only
* 不产生 data-clear promotion。

交付物：

```text
reports/workspace_dispatch/windows_wsl2_features_daily_lineage_manifest_20260706.json
reports/workspace_dispatch/windows_wsl2_features_daily_lineage_report_20260706.md
```

---

## A-WIN-R15-6 / Tradability evidence base

目标：把策略 rejection 和实际可交易性拆开。

任务：

* 对 wide3068 universe 输出 tradability matrix：

  * ST / *ST
  * suspension
  * limit up/down
  * one-lot affordability
  * liquidity bucket
  * turnover bucket
  * amount bucket
  * listing age
  * adjusted price availability
  * tradability status
* 按 train/validation/test 汇总 tradable universe size。
* 判断 trade-count weakness 来源：

  * signal sparsity
  * tradability filter
  * feature missing
  * cost model
  * execution rule
  * universe composition

交付物：

```text
reports/workspace_dispatch/windows_wsl2_a_share_tradability_evidence_base_20260706.md
reports/workspace_dispatch/windows_wsl2_a_share_tradability_matrix_20260706.csv
```

---

# B. Chunked StrategySearch / Backtest 工程任务

## A-WIN-R15-7 / Full-frame guard finalization

目标：让 wide3068 无法误跑 full-frame。

任务：

* 保留并测试 `BLOCKED_FULL_FRAME_STRATEGY_SEARCH_UNSAFE`。
* 对以下情况必须 fail closed：

  * row_count * column_count > threshold
  * config 指向 wide3068
  * chunked 未启用
  * features_daily 已存在但过大
* 不允许 OOM-driven validation。
* 增加测试覆盖真实 metadata profile，而不是只测 synthetic tiny table。

交付物：

```text
reports/workspace_dispatch/windows_wsl2_full_frame_strategy_guard_20260706.md
tests/test_strategy_search_full_frame_guard.py
```

---

## A-WIN-R15-8 / Memory telemetry unit normalization

目标：修复 `max_rss_bytes` 命名不准。

任务：

* 将 telemetry 输出改为：

  * `max_rss_kb`
  * `max_rss_bytes`
  * `max_rss_gb`
  * `source_unit`
* 所有 R15 run report 使用统一单位。
* 说明 `/usr/bin/time -v` 与 `resource.getrusage().ru_maxrss` 在 WSL/Linux 下的单位。
* 回填解释 R14 `1997256` / `2271128` 应视为 kB。

交付物：

```text
reports/workspace_dispatch/windows_wsl2_memory_telemetry_normalization_20260706.md
tests/test_memory_telemetry_units.py
```

---

## A-WIN-R15-9 / Metadata-only table profiling

目标：减少 `ChunkedFeatureReader.table_profile()` 对大表读取 `ts_code/trade_date` 的依赖。

当前代码为了 profile 会读取 `ts_code`、`trade_date` 两列到 pandas。对 5.4M rows 还能接受，但未来更大数据会变成新瓶颈。

任务：

* 优先从 metadata JSON / parquet metadata / precomputed manifest 获取：

  * row count
  * column count
  * min/max date
  * symbol count
  * date count
* 若缺 metadata，再使用 bounded scan。
* 不允许为了 profile 读取全量 feature columns。
* 输出 profile source：

  * `METADATA`
  * `PARQUET_FOOTER`
  * `BOUNDED_SCAN`
  * `FULL_TWO_COLUMN_SCAN_FALLBACK`

交付物：

```text
qta/research/chunked_table_profile.py
reports/workspace_dispatch/windows_wsl2_metadata_only_table_profile_20260706.md
tests/test_chunked_table_profile.py
```

---

## A-WIN-R15-10 / Chunked feature reader hardening

目标：巩固 chunked reader。

任务：

* 支持 date range
* 支持 split boundary
* 支持 column projection
* 支持 chunk inventory
* 支持 missingness summary
* 支持 warmup rows 标识
* 明确不读 future split 数据
* 输出 chunk artifact：

  * `chunk_plan.json`
  * `chunk_inventory.csv`
  * `chunk_reader_validation.md`

交付物：

```text
qta/research/chunked_features.py
reports/workspace_dispatch/windows_wsl2_chunked_feature_reader_hardening_20260706.md
tests/test_chunked_feature_reader.py
```

---

## A-WIN-R15-11 / Chunked backtest equivalence expansion

目标：把 chunked execution 从 smoke 证明扩展到更多真实小缓存。

任务：

* 在 synthetic cache、50-symbol clean cache、mini cache 上分别跑：

  * full-frame
  * chunked
* 对比：

  * label
  * reasons
  * total return
  * Sharpe
  * drawdown
  * trade count
  * orders
  * positions
  * cost stress
  * survivor bias
  * parameter instability
* 如果不一致，输出 root cause。

交付物：

```text
reports/workspace_dispatch/windows_wsl2_chunked_equivalence_expansion_20260706.md
reports/workspace_dispatch/windows_wsl2_chunked_vs_full_metrics_diff_20260706.csv
tests/test_chunked_strategy_equivalence_real_cache.py
```

---

# C. Strategy-quality 任务

## A-WIN-R15-12 / Strategy rejection research agenda

目标：把 all rejected 转成研究路线，不是调参找通过。

任务：

* 汇总 blockers：

  * parameter instability
  * cost stress
  * trade-count weakness
  * max drawdown
  * negative validation/test
  * concentration risk
  * benchmark underperformance not evaluated
* 每类 blocker 输出：

  * hypothesis
  * pre-registered diagnostic
  * allowed config changes
  * forbidden post-hoc tuning
  * expected interpretation

交付物：

```text
reports/workspace_dispatch/windows_wsl2_strategy_rejection_research_agenda_20260706.md
```

---

## A-WIN-R15-13 / Cost-stress decomposition

目标：解释 cost stress fail，不通过降低成本模型来找通过。

任务：

* 输出：

  * turnover
  * average holding days
  * trade count
  * gross return
  * net return
  * cost per trade
  * slippage sensitivity
  * commission sensitivity
  * stamp tax sensitivity
  * break-even cost level
* 判断 failure 来源：

  * turnover too high
  * edge too weak
  * holding period too short
  * liquidity/tradability insufficient
  * cost model interaction

交付物：

```text
reports/workspace_dispatch/windows_wsl2_cost_stress_decomposition_20260706.md
reports/workspace_dispatch/windows_wsl2_cost_stress_decomposition_20260706.csv
```

---

## A-WIN-R15-14 / Parameter instability surface

目标：解释 `parameter_instability_fail`。

任务：

* 输出 low-vol / quality / defensive momentum 参数网格稳定面。
* 记录：

  * train metric
  * validation metric
  * test metric
  * rank stability
  * turnover
  * cost stress
  * drawdown
  * trade count
* 不选择 best parameter 作为 candidate。
* 只判断是否存在稳定区域。

交付物：

```text
reports/workspace_dispatch/windows_wsl2_parameter_instability_surface_20260706.md
reports/workspace_dispatch/windows_wsl2_parameter_instability_surface_20260706.csv
```

---

## A-WIN-R15-15 / Pre-registered broad strategy family diagnostics

目标：广泛开发策略族，但禁止调参找通过。

策略族：

```text
low_vol_quality
defensive_momentum
drawdown_controlled_momentum
liquidity_quality
low_turnover_quality
sector_neutral_low_vol
tradability_filtered_quality
benchmark_relative_defensive
volatility_regime_filtered
cost_aware_low_turnover
```

任务：

* 每个策略族先写 pre-registration。
* 固定：

  * signal definition
  * features
  * universe
  * split
  * cost model
  * expected failure modes
* 先跑 mini/small cache diagnostics。
* wide run 必须 chunked 且满足前置条件。
* 不根据 test 结果反向改参数。

交付物：

```text
reports/workspace_dispatch/windows_wsl2_pre_registered_strategy_family_plan_20260706.md
```

---

# D. market_data 数据基座任务

## MD-WIN-R15-1 / A-share wide feature research data-base contract

目标：把 R14/R15 A-share wide features 定义成 research-only data base artifact。

状态标签建议：

```text
RESEARCH_FEATURE_AVAILABLE
RESEARCH_FEATURE_CROSSCHECK_PARTIAL
SURVIVOR_BIAS_EVIDENCE_IMPROVED
STRATEGY_INPUT_RESEARCH_READY_WITH_WARNINGS
NOT_PRODUCT_READY
```

必须禁止：

```text
product_read_allowed=true
production_recommendation_data_ready=true
ticket_eligibility=true
broker/live/auto=true
```

交付物：

```text
market_data/reports/codex_dev/windows_wsl2_a_share_wide_feature_data_base_contract_20260706.md
market_data/tests/test_windows_wsl2_a_share_research_data_base_contract.py
```

---

## MD-WIN-R15-2 / Cross-repo evidence bridge

目标：把 A_Share_Monitor 证据映射到 market_data 合约。

输入：

* East Money gap matrix
* survivor-bias evidence
* features lineage
* tradability matrix
* rejection attribution
* chunked blocker

输出：

* evidence present
* evidence partial
* evidence missing
* cannot promote reasons

交付物：

```text
market_data/reports/codex_dev/windows_wsl2_a_share_data_evidence_bridge_20260706.md
market_data/reports/codex_dev/windows_wsl2_a_share_data_evidence_bridge_20260706.json
```

---

## MD-WIN-R15-3 / Negative overclaim regression tests

目标：防止研究数据基座被误写成产品路径。

负例：

* partial East Money 被写成 full coverage
* 198 overlap 被写成 198 pass
* survivor-bias active rejection removed 被写成 risk eliminated
* features_daily exists 被写成 strategy valid
* all rejected 被写成 candidate available
* chunked pass 被写成 readiness
* positive validation Sharpe 被写成 ticket
* research feature contract 被写成 product route

交付物：

```text
market_data/tests/test_windows_wsl2_data_base_overclaim_regression.py
```

---

## MD-WIN-R15-4 / Research data-base manifest schema draft

目标：以后每个数据基座 artifact 都有统一 schema。

字段：

```text
dataset_id
source_repo
source_commit
machine_mode
raw_source
derived_artifact
row_count
symbol_count
date_range
crosscheck_status
survivor_bias_status
feature_lineage_status
tradability_status
strategy_use_allowed
product_use_allowed
registry_activation_allowed
readiness_allowed
broker_live_auto_allowed
```

交付物：

```text
market_data/reports/codex_dev/research_data_base_manifest_schema_draft_20260706.md
market_data/reports/codex_dev/research_data_base_manifest_schema_draft_20260706.json
```

---

# E. strategy_work 任务

## SW-WIN-R15-1 / Broad R15 strategy memo

目标：同步 verified R14 facts 和 R15 plan。

必须记录：

* 77 pass / 121 date-gap / 2870 missing
* survivor-bias evidence improved, not eliminated
* all strategies rejected
* data-chain blocker reduced
* strategy-quality blocker remains
* chunked required
* no recommendation/ticket/readiness

交付物：

```text
strategy_work/reports/a_share/windows_wsl2_r15_broad_data_strategy_research_memo_20260706.md
strategy_work/reports/SUMMARY.md
```

---

## SW-WIN-R15-2 / Strategy-quality blocker roadmap

目标：从 rejected attribution 生成策略研究路线图。

交付物：

```text
strategy_work/reports/a_share/windows_wsl2_strategy_quality_blocker_roadmap_20260706.md
```

---

## SW-WIN-R15-3 / Final sync after source acceptances only

前置：

* A_Share_Monitor R15 callback
* market_data R15 callback
* strategy family plan available

交付物：

```text
strategy_work/reports/planning/windows_wsl2_data_strategy_batch_r15_final_sync_20260706.md
```

---

# F. quant-proj controller 侧任务

## QP-WIN-R15-1 / R15 intake and source receipt

目标：记录 R15 是 ordinary data/strategy batch，不是 controller/gate review。

交付物：

```text
quant-proj/reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_intake.md
```

---

## QP-WIN-R15-2 / R15 result summary and closeout

前置：

* A_Share_Monitor callback
* market_data callback
* strategy_work callback

交付物：

```text
quant-proj/reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_result_summary.md
quant-proj/reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_closeout.md
```

---

# Optional US branch

如果你想把 R15 做得更广，可以带 US，但不要抢 A 股主线：

```text
US-WIN-R15-1 / US metadata blocker continuation
US-WIN-R15-2 / US second-source HG-EXEC plan only
```

仍禁止无 HG-EXEC 的 provider/network execution。

---

# Unified validation requirements

每个源仓至少要求：

```text
py_compile: PASS
focused pytest: PASS
agent_safety_check.py: PASS
git diff --check: PASS
JSON parse: PASS where applicable
forbidden overclaim scan: PASS
```

A_Share_Monitor 额外要求：

```text
no full-frame wide StrategySearch
chunked mode required for wide3068
no OOM-driven validation
no recommendation/ticket/readiness wording
memory telemetry units normalized
```

market_data 额外要求：

```text
no product_read_allowed=true
no production_recommendation_data_ready=true
no broker/live/auto=true
no registry activation
no readiness change
```

strategy_work 额外要求：

```text
no placeholder final sync
no candidate promotion
no ranked actionable list
no buy/sell/advice wording
```

---

# Unified callback envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
KEY_RESULTS:
WARNINGS:
BLOCKERS:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```

---

# Stop conditions

任何源仓遇到以下情况必须停止：

```text
FULL_FRAME_WIDE_STRATEGY_SEARCH_ATTEMPTED
OOM_OR_MEMORY_PRESSURE_UNBOUNDED
NETWORK_PROVIDER_FETCH_REQUIRED_WITHOUT_HG_EXEC
DB_SCHEMA_CHANGE_REQUIRED_WITHOUT_HG_EXEC
REGISTRY_OR_READINESS_CHANGE_REQUIRED
PRODUCT_ROUTE_ACTIVATION_REQUIRED
SECRET_OR_ENV_ACCESS_REQUIRED
STRATEGY_RESULT_BEING_PROMOTED_TO_TICKET_OR_RECOMMENDATION
EAST_MONEY_PARTIAL_COVERAGE_WRITTEN_AS_FULL_COVERAGE
SURVIVOR_BIAS_IMPROVED_WRITTEN_AS_ELIMINATED
```

---

# Dispatcher-ready R15 prompt

```text
WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706

Verified R14 facts:
- A_Share_Monitor R14 evidence commit: dd3089e2a9c1693ea0571db37c185d6584f1bc14
- A_Share_Monitor repair package commit: 735ac8f18266a3720d1b0e729ed6b203539d758e
- strategy_work sync: 2bfbe33e654e7ceb76117ab7b156ff44f2d979be
- quant-proj receipt: 61c71087cb33ac55c6f00b9aa7da12e8a111a13b

Verified R14 conclusions:
- Survivor-bias active rejection disappeared from candidate rejection reasons.
- East Money crosscheck remains partial:
  77 CROSSCHECK_PASS symbols,
  121 CROSSCHECK_DATE_GAP symbols,
  2870 CROSSCHECK_MISSING_EAST_MONEY symbols.
- All strategy reruns remain rejected.
- Remaining blockers are strategy-quality and robustness blockers:
  parameter instability, cost stress, trade-count weakness, drawdown, negative validation/test behavior.
- wide3068 full-frame remains blocked.
- chunked StrategySearch/backtest remains required.
- R14 memory telemetry unit naming needs normalization.

Goal:
Run a broad data/strategy development batch plus corresponding research data-base tasks.
Do not tune parameters to find a pass.
Do not create recommendation, ticket, readiness, registry activation, product route, or trading path.
Do not redesign controller/gates.

Dispatch A_Share_Monitor:
- A-WIN-R15-1 East Money coverage expansion priority queue
- A-WIN-R15-2 East Money date-gap diagnostics
- A-WIN-R15-3 Controlled East Money HG-EXEC plan only
- A-WIN-R15-4 Survivor-bias evidence hardening v2
- A-WIN-R15-5 Features_daily lineage and staging assumptions manifest
- A-WIN-R15-6 Tradability evidence base
- A-WIN-R15-7 Full-frame guard finalization
- A-WIN-R15-8 Memory telemetry unit normalization
- A-WIN-R15-9 Metadata-only table profiling
- A-WIN-R15-10 Chunked feature reader hardening
- A-WIN-R15-11 Chunked backtest equivalence expansion
- A-WIN-R15-12 Strategy rejection research agenda
- A-WIN-R15-13 Cost-stress decomposition
- A-WIN-R15-14 Parameter instability surface
- A-WIN-R15-15 Pre-registered broad strategy family diagnostics

Dispatch market_data:
- MD-WIN-R15-1 A-share wide feature research data-base contract
- MD-WIN-R15-2 Cross-repo evidence bridge
- MD-WIN-R15-3 Negative overclaim regression tests
- MD-WIN-R15-4 Research data-base manifest schema draft

Dispatch strategy_work:
- SW-WIN-R15-1 Broad R15 strategy memo
- SW-WIN-R15-2 Strategy-quality blocker roadmap
- SW-WIN-R15-3 Final sync after source acceptances only

Dispatch quant-proj:
- QP-WIN-R15-1 R15 intake and source receipt
- QP-WIN-R15-2 R15 result summary and closeout after callbacks

Optional US:
- US-WIN-R15-1 US metadata blocker continuation
- US-WIN-R15-2 US second-source HG-EXEC plan only

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, or secret handling.
Future network/provider fetch, DB/cache rebuild, schema/readiness/registry changes require separate task-level HG-EXEC evidence and transcript.
```

---

# 最终边界说明

这次结论是**已用 GitHub connector 做文件级核查后的结论**。
它不是基于你口头摘要。

R14 可以作为 verified source-level evidence 进入 R15。
R15 的方向不是“让策略过关”，而是：

```text
把 partial data evidence 做厚；
把 survivor-bias 证据继续固化；
把 chunked execution 做稳；
把全部 rejected 的原因拆成可研究的策略开发路线；
把 market_data 数据基座合约补上。
```
