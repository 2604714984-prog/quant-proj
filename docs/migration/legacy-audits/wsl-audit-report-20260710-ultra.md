# WSL 全项目超详细审核报告（第二次扫描）

> 审核日期：2026-07-10
> 范围：`/home/rongyu/workspace/` 下所有项目
> 方法：全局敏感信息扫描 + 每项目并行逐行代码审查

---

## 第一部分：全局扫描结果

### 1.1 项目总清单（共 10 个项目，新增 FinGPT）

| # | 项目 | 大小 | 语言 | 性质 |
|---|------|------|------|------|
| 1 | A_Share_Monitor | 11G | Python | A股量化研究系统（核心） |
| 2 | US_Stock_Monitor | 187M | Python | 美股量化研究系统 |
| 3 | quant_research_lab | 1.9G | Python | 量化研究实验室 |
| 4 | us_stock_30w | 10M | Python | 美股30万策略 |
| 5 | market_data | 1.7M | Python | 统一市场数据治理层 |
| 6 | quant-proj | 6.5M | Markdown | 量化工作区调度器 |
| 7 | strategy_work | 2.8M | Python/YAML | 策略配置与研究报告 |
| 8 | STRATEGY_VAULT | <1M | Markdown | 已验证策略库 |
| 9 | global-stock-data | <1M | Markdown | 全球股票数据工具包 |
| 10 | **FinGPT** | **35M** | **Python** | **AI4Finance 外部开源项目（克隆）** |

### 1.2 敏感信息扫描

#### API Key / Token 搜索
- ❌ **无硬编码 API key 被发现**（搜索了 sk-*, ghp_*, Bearer 等模式）
- ✅ 所有 token 仅从环境变量读取（TUSHARE_TOKEN, DATA_PROVIDER_API_KEY）
- ⚠️ `save_deepseek_api_key.py` — 将 DeepSeek API key 明文保存到本地文件
- ⚠️ `deepseek_keychain.py` — 管理密钥链文件

#### 🚨 `pickle.load()` 无校验（15 个文件 — 严重安全风险）

所有文件从硬编码路径加载 pickle，**无 HMAC/checksum/签名验证**，若 pickle 文件被篡改可导致任意代码执行：

| 文件 | 行 | 路径 |
|------|----|------|
| `US_Stock_Monitor/scripts/audit_chain.py` | 20 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/cred_test.py` | 27 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/credibility_test.py` | 38 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/current_positions.py` | 11 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/deep_val2.py` | 31 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/final_opt.py` | 19 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/improve_strat.py` | 27 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/new_strategies.py` | 20 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/opt_r2.py` | 18 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/opt_r3.py` | 18 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/paper_trade.py` | 20 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/run_adaptive.py` | 16 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/run_baseline.py` | 15 | `../us_stock_30w/data/us_panel.pkl` |
| `US_Stock_Monitor/scripts/survivorship_fix.py` | 60 | `../us_stock_30w/data/us_panel.pkl` |
| `quant_research_lab/research/*.py` | 多处 | `cached_signals_full.parquet` |

#### 🚨 硬编码绝对路径（42+ 处）

**macOS 路径（已废弃，WSL2 无法运行）：**
```
A_Share_Monitor/qta/cli.py:250,296,322  →  /Users/rongyuxu/Desktop/A_Share_Monitor/...
A_Share_Monitor/scripts/expand_daily_data.py:9  →  /Users/rongyuxu/Desktop/...
A_Share_Monitor/scripts/expand_daily_v2.py:5  →  /Users/rongyuxu/Desktop/...
A_Share_Monitor/scripts/marathon_expand.py:6,9  →  /Users/rongyuxu/Desktop/...
A_Share_Monitor/scripts/expand_symbol_pool.py:11  →  /Users/rongyuxu/Desktop/...
US_Stock_Monitor/scripts/fill_us_data.py:10  →  /Users/rongyuxu/Desktop/...
US_Stock_Monitor/scripts/fill_us_nasdaq.py:9  →  /Users/rongyuxu/Desktop/...
US_Stock_Monitor/scripts/fill_us_slow.py:11  →  /Users/rongyuxu/Desktop/...
US_Stock_Monitor/scripts/fill_missing_us.py:5  →  /Users/rongyuxu/Desktop/...
market_data/collect_a_share_state.py:5  →  /Users/rongyuxu/Desktop/...
market_data/collect_us_state.py:5  →  /Users/rongyuxu/Desktop/...
```

**WSL2 路径（本机，但无法移植）：**
```
quant_research_lab/paper_trader/auto_daily.py:17  →  /home/rongyu/workspace/A_Share_Monitor
quant_research_lab/paper_trader/gen_dashboard.py:7  →  /home/rongyu/workspace/quant_research_lab/...
quant_research_lab/research/rigorous_val.py:3  →  /home/rongyu/workspace/quant_research_lab
quant_research_lab/research/sweep_fast.py:4  →  /home/rongyu/workspace/quant_research_lab
quant_research_lab/research/opt_sweep.py:4  →  /home/rongyu/workspace/quant_research_lab
quant_research_lab/research/final_combos.py:2  →  /home/rongyu/workspace/quant_research_lab
quant_research_lab/research/prod_validate.py:15  →  /home/rongyu/workspace/A_Share_Monitor
strategy_work/analysis/a_share_full_cache_factor_scanner.py:14-15  →  /home/rongyu/workspace/...
strategy_work/analysis/a_share_negative_pe_recovery_audit.py:14  →  /home/rongyu/workspace/...
A_Share_Monitor/scripts/run_r30_strategy_factory.py:25  →  /home/rongyu/workspace/us_stock_30w
A_Share_Monitor/scripts/run_s2_feature_source_design.py:28  →  /home/rongyu/workspace/us_stock_30w/...
```

#### 🚨 裸 `except:`（40+ 处 — 静默吞噬错误）

| 文件 | 行 | 代码 |
|------|----|------|
| `A_Share_Monitor/scripts/expand_daily_data.py` | 30,100,115 | `except: pass` |
| `A_Share_Monitor/scripts/expand_symbol_pool.py` | 42 | `except:` |
| `A_Share_Monitor/scripts/marathon_expand.py` | 37,61,110,134 | `except: / except: pass` |
| `US_Stock_Monitor/scripts/auto_trader.py` | 77 | `except: continue` |
| `US_Stock_Monitor/scripts/sina_tracker.py` | 73 | `except: continue` |
| `US_Stock_Monitor/scripts/ibkr_bridge.py` | 86 | `except: continue` |
| `US_Stock_Monitor/scripts/evidence_trader.py` | 80 | `except: continue` |
| `US_Stock_Monitor/scripts/fill_us_nasdaq.py` | 251 | `except: pass` |
| `US_Stock_Monitor/scripts/fill_us_tencent.py` | 69 | `except: return 0.0` |
| `market_data/collect_us_state.py` | 24,28,35,52 | `except: pass` |
| `market_data/collect_a_share_state.py` | 55,72,88 | `except: pass` |
| `market_data/dump_schema.py` | 26 | `except:` |
| `FinGPT/` | 多处 | `except:` |

#### 🚨 `requests.get/post` 无超时（约 20 处）

| 文件 | 行 | 风险 |
|------|----|------|
| `A_Share_Monitor/scripts/deepseek_audit.py` | 330 | 无超时的 HTTP POST — 可能永久挂起 |
| `FinGPT/fingpt/FinGPT_RAG/*.py` | 多处 | 无超时 — 爬虫可能永久阻塞 |
| `US_Stock_Monitor/scripts/auto_trader.py` | 32 | 有 `timeout=10` ✅ |
| `US_Stock_Monitor/scripts/sina_tracker.py` | 28 | 有 `timeout=15` ✅ |

#### 🚨 `.env` / `.gitignore` 覆盖检查

| 项目 | 有 `.env`? | 有 `.gitignore`? | 有 `.env.example`? |
|------|-----------|-----------------|-------------------|
| A_Share_Monitor | no | YES | YES |
| US_Stock_Monitor | no | YES | YES |
| **STRATEGY_VAULT** | no | **NO** | **NO** |
| **global-stock-data** | no | **NO** | **NO** |
| market_data | no | YES | no |
| quant-proj | no | YES | no |
| quant_research_lab | no | YES | no |
| strategy_work | no | YES | no |
| us_stock_30w | no | YES | no |
| FinGPT | no | YES | **YES** |

---

## 第二部分：逐项目深度审查

---

### 项目 1: A_Share_Monitor（11G — A股核心系统）

#### 架构总览
```
qta/
├── backtest/       # 回测引擎（engine, broker_sim, cost_model, fill_model, metrics, order, portfolio, risk_model, trade_log）
├── config/         # 配置加载
├── data/           # 数据层（tushare_client, universe, quality, sync, adjustments, calendar...）
│   └── local_market_db/  # DuckDB 接入（akshare/baostock/tushare fetcher, schema, db, query, migrations...）
├── features/       # 特征工程（feature_store, fundamentals, market_regime, price_volume, technical）
├── guardrails/     # 安全门控（recommendation_guard）
├── manual_review/  # 人工审核
├── observation/    # 观测系统
├── ops/            # 运维
├── recommendation/ # 推荐系统（a10_core_universe, a11_hitl, micro_hitl）
├── reports/        # 报告生成
├── research/       # 策略研究（evaluator, strategy_search, walk_forward, robustness, candidate_registry...）
├── review/         # 交易复盘（trade_review）
├── strategies/     # 策略模板
├── trading/        # 交易（manual_fill）
├── utils/          # 工具
├── cli.py          # CLI 入口
├── __main__.py     # Python -m 入口
└── strategy_validation.py  # 策略验证
```

**测试覆盖：** ~120+ 个测试文件 ✅

#### 安全审查
| 发现 | 严重程度 | 位置 |
|------|---------|------|
| CLI 硬编码 macOS DuckDB 路径 | 🚨 严重 | `qta/cli.py:250,296,322` |
| 脚本硬编码 macOS/WSL2 路径 | 🚨 严重 | `scripts/expand_daily_data.py:9`, `expand_daily_v2.py:5`, `marathon_expand.py:6` 等 |
| bare `except: pass` 在数据扩展脚本中 | 🟠 高 | `scripts/marathon_expand.py:37,61,110,134` |
| 同步脚本中 bare `except:` | 🟠 高 | `scripts/expand_symbol_pool.py:42` |
| requests 无超时（deepseek_audit.py） | 🟡 中 | `scripts/deepseek_audit.py:330` |
| **正面：** guardrails 模块存在且被测试覆盖 | ✅ | `qta/guardrails/recommendation_guard.py` |
| **正面：** 无硬编码 token | ✅ | 仅从环境变量读取 TUSHARE_TOKEN |

#### 量化正确性审查
| 发现 | 严重程度 | 说明 |
|------|---------|------|
| 回测引擎正确实现 T+1 available_qty | ✅ | `qta/backtest/engine.py` |
| 涨跌停/停牌处理 | ✅ | `qta/backtest/broker_sim.py`, `fill_model.py` |
| 成本模型完整（佣金+印花税+滑点） | ✅ | `qta/backtest/cost_model.py` |
| train/validation/test 区分 | ✅ | `qta/research/evaluator.py`, `walk_forward.py` |
| 特征工程使用 adjusted prices | ✅ | `qta/features/feature_store.py` |
| 策略评级限制正确 | ✅ | 仅 rejected/research/observation/paper_trading_candidate |
| 但 WS 使用预缓存信号 | ⚠️ 已知 | `qta/research/walk_forward.py` 需要审查 |
| outputs/ 有大量历史研究数据积累 | ⚠️ 混乱 | ~7 轮策略搜索产出（R13 多次运行） |

#### 配置审查
| 文件 | 发现 |
|------|------|
| `pyproject.toml` | ✅ 依赖定义清晰 |
| `.gitignore` | ✅ 完善（排除 data/**, outputs/**, *.db, *.parquet, *token*）|
| `.env.example` | ✅ 只含 `TUSHARE_TOKEN=` |
| `config/data/a_share_tushare_local_db.yaml` | ✅ 明确配置 |
| `config/strategies/examples/ma_momentum_example.yaml` | ✅ 策略模板示例 |

---

### 项目 2: US_Stock_Monitor（187M — 美股核心系统）

#### 🚨 关键发现：代码分两个完全不同的质量层级

**层级 1 — usq/ 包（高质量，有测试覆盖）：**
```
usq/
├── backtest/    # engine, cost_model, fill_model, settlement, metrics, corporate_action_adjuster
├── config/      # loader, schema
├── data/        # provider_base, synthetic_provider, csv_provider, data_store, market_calendar, corporate_actions...
├── features/    # feature_store, fundamentals, price_volume, technical, market_regime
├── guardrails/  # recommendation_guard, observation_guard, review_guard, feedback_guard, safety...
├── research/    # strategy_search, evaluator, walk_forward, robustness, candidate_registry...
├── observation/ # ledger, tracker, policy
├── review/      # queue, ledger
├── feedback/    # outcome_ledger, backlog
├── iteration/   # task_queue, evidence_gap, experiment_drafts
├── recommendation_guardrail/  # blocked_reasons, preflight, policy
├── recommendation_rfc/        # schema_draft, guardrail_draft
├── recommendation_ticket_rfc/ # policy, workflow, schema_draft
├── reports/
├── utils/
├── cli.py, __main__.py
```

**层级 2 — scripts/ 目录（遗留脚本，质量参差不齐，🚨 包含危险代码）：**

40+ 个遗留脚本，其中：

#### 🚨 🚨 🚨 `ibkr_bridge.py` — 最高风险文件

```python
from ib_insync import IB, Stock, MarketOrder
# ...
ib.connect('127.0.0.1', 7497, clientId=1)  # 连接到 IBKR TWS 纸面交易端口
contract = Stock(symbol, 'SMART', 'USD')
ib.placeOrder(contract, MarketOrder(action, qty))  # 🚨 真实市价单
```

**风险等级：CRITICAL**
- `ib_insync` 可以连接到真实的 Interactive Brokers TWS/Gateway
- 端口 7497 = TWS 纸面交易端口（也可配置为 7496 = 实盘！）
- `MarketOrder` 会立即执行 — 无价格保护
- `--execute` 标志本应受保护，但解析脆弱

#### 🚨 🚨 `evidence_trader.py` — 自动化执行脚本

- 每日自动运行，管理投资组合状态
- 使用 `CAPITAL_PER = 19090`（无说明的 "half of GOOGL proceeds"）
- 有 `assert_recommendation_runtime_disabled()` 吗？**没有**
- 用 `trading_days_s1 = int((TODAY - s1_last).days * 5/7)` — 忽略美国节假日

#### 测试覆盖
~120 个测试文件 ✅（包括 guardrail, safety, settlement 测试）

---

### 项目 3: quant_research_lab（1.9G — 量化研究实验室）

#### 文件结构
```
paper_trader/     # 纸面交易引擎（engine.py, auto_daily.py, auto_paper.py, gen_dashboard.py）
quant_lab/        # 量化实验室（backtest/, factors/, data/, agents/）
research/         # 研究脚本（master_research.py, deep_validate.py, prod_validate.py, etc.）
demos/            # 演示脚本
outputs/          # 大量研究输出文件
```

#### 🚨 关键发现
| 发现 | 严重程度 | 位置 |
|------|---------|------|
| 硬编码绝对路径（A_SHARE_ROOT, STATE_DIR 等） | 🚨 严重 | `auto_daily.py:17`, `gen_dashboard.py:7-8`, `rigorous_val.py:3`, `sweep_fast.py:4`, `final_combos.py:2`, `prod_validate.py:15` |
| 预计算特征使用 future data（look-ahead） | 🚨 严重 | `research/` 下所有加载 `cached_signals_full.parquet` 的脚本 |
| 信号逻辑与 US_Stock_Monitor 脚本重复 | 🚨 严重 | 与 `US_Stock_Monitor/scripts/` 重复 |
| paper_trader 引擎缺少 guardrail 断言 | 🟠 高 | `paper_trader/engine.py` |
| 裸 `except:` 在关键路径中 | 🟠 高 | - |
| 大量 output 文件（logs, reports, dashboard） | ⚠️ 混乱 | `outputs/` 目录 |

---

### 项目 4: market_data（1.7M — 最健壮的模块）

#### 文件结构
```
adapters/
├── a_share_adapter.py    # A 股 DB 适配器 — 只读，fail-closed
├── us_stock_adapter.py   # 美股 DB 适配器 — 读取被阻断！
├── access_gate.py        # 产品访问门控 — 严格 fail-closed
├── registry.py           # 注册表加载与验证
    #   ├── 固定 A 股快照 ID: local_17b656b7acaebc19963a32d8
    #   ├── 固定 A 股范围: 50 只标的, 86,817 行
    #   ├── 美股统一 DB 状态: UNQUALIFIED_LOCAL_ROWS_PRESENT
    #   ├── 美股产品读取: BLOCKED (MISSING_CROSSCHECK_MANIFEST_READINESS)
    #   └── 所有运行时标志必须为 false
catalog/
├── market_data_registry.yaml   # 产品注册表
├── product_read_policy.yaml    # 读取策略
└── source_boundaries.yaml      # 数据源边界
tests/
reports/agent_handoff/          # 审计交接档案
```

#### 评分
| 维度 | 评分 | 说明 |
|------|------|------|
| **安全性** | ✅ 优秀 | fail-closed 设计，所有产品读取需验证，运行时标志全部 false |
| **架构** | ✅ 优秀 | 清晰的适配器模式，注册表验证 |
| **代码质量** | ✅ 良好 | 有类型注解，有测试，import 相对路径 |
| **⚠️ 问题** | `collect_a_share_state.py` 和 `collect_us_state.py` — macOS 遗留产物，硬编码 macOS 路径，bare `except: pass` |

---

### 项目 5: us_stock_30w（10M — 美股 30 万策略）

#### 文件结构
```
config/           # 账户/回测/数据/市场/策略/研究 配置
scripts/          # shell 脚本（run_all.sh, run_pipeline.sh, run_daily.sh）
outputs/          # 研究输出
reports/          # 策略报告（US30W-R22-001/002/003）
```

#### 🚨 关键发现
| 发现 | 严重程度 | 位置 |
|------|---------|------|
| 合成/真实数据标注矛盾 | 🚨 严重 | `config/data/us_data_41k.yaml` 说 `provider: synthetic, allow_network: false`，但执行使用真实 yfinance |
| 绝对路径引用 | 🟠 高 | A_Share_Monitor 脚本通过硬编码路径引用 `us_stock_30w/data/us_panel.pkl` |

---

### 项目 6: quant-proj（6.5M — 任务调度器）

**无代码文件**（纯 Markdown/YAML）
- `AGENTS.md` — 定义了 6 条硬规则
- `registry/projects.yaml` — 完整的多项目管理注册表
- `registry/agents.yaml` — Agent 角色定义
- `runbooks/` — 运行手册（human_gate, task_dispatch, task_packet_validation, recorded_execution_mode）
- `tasks/` — 任务板 + 进行中任务
- `reports/` — 审计交接档案

**评分：** ✅ 优秀的项目管理框架，安全边界定义清晰。无代码问题。

---

### 项目 7: strategy_work（2.8M — 策略配置）

#### 文件结构
```
analysis/          # 分析脚本（4 个 Python 文件）
configs/           # 策略配置 YAML
reports/           # 策略报告
```

#### 🚨 关键发现
| 发现 | 严重程度 | 位置 |
|------|---------|------|
| 所有 4 个分析脚本都硬编码了绝对路径 | 🚨 严重 | `analysis/a_share_full_cache_factor_scanner.py:14-15` — `/home/rongyu/workspace/A_Share_Monitor/data/cache/daily.parquet` 等 |

---

### 项目 8: STRATEGY_VAULT（<1M — 已验证策略）

**发现：** ✅ 结构良好，有 4 个策略报告（US_AdaptiveQuality, US_QualityLowVol, US_50_50_Combo, CN_LowTurnover），各有 report.md + reproduce.sh。无代码文件。CN-01 标注「RETRACTED — 待修复」。

---

### 项目 9: global-stock-data（<1M — 数据工具包）

**发现：** ✅ 独立开源项目（simonlin1212/global-stock-data），非本项目代码。SKILL.md 是 8 层数据架构工具包。

---

### 项目 10: FinGPT（35M — 外部开源项目）

**发现：** ✅ 来自 AI4Finance-Foundation/FinGPT（Apache 2.0 许可证）的外部克隆。非本项目的代码。无需审查，但应注意其存在（35MB）。

---

## 第三部分：🛑 最高优先级安全问题（Top 10）

| 优先级 | 问题 | 影响 | 建议修复 |
|--------|------|------|---------|
| **🔴 P0** | `ibkr_bridge.py` 包含实盘 IBKR 执行代码（ib_insync, MarketOrder, port 7497） | 可导致真实交易风险 | 删除此文件或添加编译时功能标志；添加 import-time guard `assert not on_production()` |
| **🔴 P0** | 15 个文件无校验地使用 `pickle.load()` | 任意代码执行风险 | 添加 pickle 校验和验证或迁移到安全格式 |
| **🔴 P0** | 42+ 个文件硬编码 macOS/WSL2 绝对路径 | 全部无法移植 | 使用 `Path(__file__).resolve().parents[n]` 或 `MARKET_HOME` env var |
| **🔴 P1** | 8+ 个副本的信号逻辑（Adaptive+Quality） | 维护噩梦，增加 bug 风险 | 重构到单个 `signal_library.py` |
| **🔴 P1** | `evidence_trader.py` 无 guardrail 断言，自动执行 | 可能绕过保护门控 | 添加 `assert_recommendation_runtime_disabled()` 在启动时 |
| **🟠 P1** | 未来函数 / look-ahead bias（10+ 个脚本预计算特征） | 收益严重高估 | 在回测循环中滚动/扩展构建特征 |
| **🟠 P2** | 40+ 处 `bare except: pass / continue` | 静默吞噬所有错误 | 替换为具体异常处理 + 日志 |
| **🟠 P2** | `collect_a_share_state.py` / `collect_us_state.py` — macOS 遗留，bare except, 无测试 | 在 WSL2 中崩溃 | 删除或重构 |
| **🟠 P2** | requests 无超时（约 20 处） | 网络问题可永久挂起 | 添加 `timeout=30` |
| **🟡 P3** | 合成/真实数据标注不一致（us_data_41k.yaml） | 误导审计 | 使 config provider 匹配实际执行 |

---

## 第四部分：量化策略业绩汇总（最佳可验证估计）

| 策略 | Market | Full Sharpe | OOS Sharpe | Max DD | 状态 |
|------|--------|-------------|------------|--------|------|
| Adaptive+Quality | US | 0.788 | 0.720 | -11.0% | 已验证 |
| Quality+LowVol | US | 0.897 | 0.565 | -7.2% | 已验证 |
| 50/50 Combo | US | 0.984 | — | -7.1% | 已验证 |
| CN LowTurnover (v1) | A | 0.98 | — | — | ❌ 撤销（未来函数） |
| CN LowTurnover (v2) | A | -0.13 train | 0.68 test | — | 弱信号 |
| 低换手小盘 | US | — | IR=-0.00 | — | ❌ 无效 |
| RSI-2 均值回归 | US | — | — | — | ❌ 不可行 |

---

## 第五部分：文件级详细清单（所有 Python 源文件，带行数）

> 仅列出各项目自有代码（排除 .venv, __pycache__, site-packages, 数据文件）

### A_Share_Monitor — 自有 Python 文件（~100+ 文件）
```
qta/__init__.py
qta/__main__.py
qta/cli.py                                          # CLI 入口
qta/strategy_validation.py                          # 策略验证
qta/config/__init__.py + loader.py + schema.py      # 配置层
qta/utils/__init__.py + hashing.py + io.py + logging.py + time.py
qta/backtest/__init__.py + engine.py + broker_sim.py + cost_model.py + fill_model.py + metrics.py + order.py + portfolio.py + risk_model.py + trade_log.py
qta/data/__init__.py + adjustments.py + calendar.py + coverage_report.py + data_store.py + quality.py + snapshot_manifest.py + sync.py + synthetic.py + tushare_client.py + universe.py
qta/data/local_market_db/  (22 个文件)              # 本地 DuckDB 接入层
qta/features/__init__.py + feature_store.py + fundamentals.py + market_regime.py + moneyflow.py + price_volume.py + technical.py
qta/guardrails/__init__.py + recommendation_guard.py
qta/manual_review/  (5 个文件)
qta/observation/  (4 个文件)
qta/ops/  (5 个文件)
qta/recommendation/a10_core_universe/  (12 个文件)  # 核心推荐系统
qta/recommendation/a11_hitl/  (2 个文件)
qta/recommendation/micro_hitl/  (11 个文件)         # 微账户 HITL
qta/reports/__init__.py + report_generator.py + charts.py
qta/research/  (18 个文件)                          # 策略研究
qta/review/trade_review/  (11 个文件)               # 交易复盘
qta/strategies/  (6 个文件)                         # 策略模板
qta/trading/manual_fill/  (9 个文件)                # 手动成交
scripts/  (46 个脚本)                               # 实用脚本
tests/  (~120 个测试文件)                           # 测试
```

### US_Stock_Monitor — 自有 Python 文件（~120+ 文件）
```
usq/__init__.py + __main__.py + cli.py
usq/backtest/  (9 个文件)
usq/config/  (3 个文件)
usq/data/  (18 个文件)
usq/features/  (6 个文件)
usq/guardrails/  (8 个文件)
usq/recommendation_guardrail/  (6 个文件)
usq/recommendation_rfc/  (3 个文件)
usq/recommendation_ticket_rfc/  (6 个文件)
usq/observation/  (6 个文件)
usq/review/  (6 个文件)
usq/feedback/  (7 个文件)
usq/iteration/  (7 个文件)
usq/external_research/  (7 个文件)
usq/research/  (9 个文件)
usq/reports/  (2 个文件)
usq/utils/  (5 个文件)
scripts/  (40 个遗留脚本)
  ├── auto_trader.py (248 LOC)     ⚠️ 缺少 guardrail
  ├── ibkr_bridge.py (193 LOC)     🚨 IBKR 实盘代码
  ├── evidence_trader.py (252 LOC) ⚠️ 自动化执行
  ├── sina_tracker.py              ⚠️ 裸 except
  ├── paper_trade.py (233 LOC)     ⚠️
  └── (35 个更多)
tests/  (~120 个测试文件)
```

### quant_research_lab — 自有 Python 文件（~30 个文件）
```
paper_trader/  (9 个文件)
quant_lab/  (12 个文件)
research/  (9 个文件)
demos/  (4 个文件)
```

### market_data — 自有 Python 文件（~10 个文件）
```
__init__.py, __main__.py
adapters/  (4 个文件)
catalog/  (3 个 YAML)
collect_a_share_state.py  ⚠️ macOS 遗留
collect_us_state.py       ⚠️ macOS 遗留
dump_schema.py
tests/
```

### 其余项目（us_stock_30w, strategy_work, STRATEGY_VAULT, global-stock-data, quant-proj, FinGPT）
- 见各项目章节

---

## 第六部分：项目治理评分卡

| 项目 | 有 Guardrails | 有测试 | 有 AGENTS.md | 路径可移植 | 代码可维护 |
|------|-------------|-------|-------------|-----------|-----------|
| A_Share_Monitor | ✅ | ✅ ~120 | ✅ | ❌ macOS 路径 | ⚠️ 中等 |
| US_Stock_Monitor (usq/) | ✅ | ✅ ~120 | ✅ | ✅ 相对路径 | ✅ 良好 |
| US_Stock_Monitor (scripts/) | ❌ | ❌ | N/A | ❌ 硬编码 | ❌ 差 |
| quant_research_lab | ❌ | ❌ | ❌ | ❌ 硬编码 | ❌ 差 |
| market_data | ✅ fail-closed | ✅ | ❌ | ✅ 环境变量 | ✅ 良好 |
| us_stock_30w | ❌ | ❌ | ✅ | ⚠️ 部分 | ⚠️ 中等 |
| quant-proj | ✅ 治理层 | N/A | ✅ | ✅ | ✅ 良好 |
| strategy_work | ❌ | ❌ | ❌ | ❌ 硬编码 | ⚠️ 中等 |
| STRATEGY_VAULT | N/A（静态） | N/A | ✅ | ✅ | ✅ |
| global-stock-data | N/A（外部） | ❌ | ✅ SKILL.md | ✅ | ⚠️ 有曾经修复过的 bug |

---

*审核完成。共审查 10 个项目、~400+ Python 源文件、50+ YAML 配置、数百个 Markdown 文档。发现 42+ 个硬编码路径、15 个 pickle 加载点、40+ 处裸 except、8+ 份信号逻辑副本、1 个文件含实盘 IBKR 代码。报告文件：42KB。*
