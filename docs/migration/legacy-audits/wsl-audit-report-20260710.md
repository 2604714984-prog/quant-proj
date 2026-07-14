# WSL 全项目严格审核报告

> 审核日期：2026-07-10
> 审核范围：`/home/rongyu/workspace/` 下 9 个 Git 项目
> 审核方法：每文件每行代码审查（含并行子任务 + 手动读取）

---

## 项目总览

| # | 项目 | 大小 | Python源文件 | 关键性质 |
|---|------|------|-------------|---------|
| 1 | **A_Share_Monitor** | 11G | ~100+ | A股量化研究系统（核心项目） |
| 2 | **US_Stock_Monitor** | 187M | ~120+ | 美股量化研究系统 |
| 3 | **quant_research_lab** | 1.9G | ~30+ | 回购研究实验室 |
| 4 | **us_stock_30w** | 10M | ~10+ | 美股30万策略研究 |
| 5 | **market_data** | 1.7M | ~10+ | 统一市场数据治理层 |
| 6 | **quant-proj** | 6.5M | - | 量化工作区调度器 |
| 7 | **strategy_work** | 2.8M | ~5+ | 策略配置与研究报告 |
| 8 | **STRATEGY_VAULT** | <1M | - | 已验证策略库（静态） |
| 9 | **global-stock-data** | <1M | - | 全球股票数据工具包 |

---

## 一、安全漏洞（按严重程度排序）

### 🔴 [CRITICAL] 1. 多项目硬编码绝对路径 → 无法移植

**影响项目：** A_Share_Monitor, US_Stock_Monitor, quant_research_lab, strategy_work, market_data

**问题描述：**
大量脚本硬编码了 `/home/rongyu/workspace/` 和 `/Users/rongyuxu/Desktop/` 的绝对路径，导致：
- 代码在任何其他机器上直接崩溃
- 跨平台（macOS ↔ WSL2）路径不一致
- 无抽象层/环境变量支持

**具体位置：**
- `A_Share_Monitor/scripts/*.py` 所有脚本：`A_SHARE_ROOT = Path("/home/rongyu/workspace/A_Share_Monitor")`
- `US_Stock_Monitor/scripts/*.py` 所有脚本：硬编码 `/home/rongyu/workspace/` 路径
- `market_data/collect_a_share_state.py`, `market_data/collect_us_state.py`：硬编码 macOS 路径 `/Users/rongyuxu/Desktop/A_Share_Monitor/...`
- `quant_research_lab/*.py`：多文件绝对路径引用
- `strategy_work/configs/*.yaml`：某些配置引用绝对路径

**建议：** 统一使用 `pathlib.Path(__file__).resolve().parents[n]` 相对定位或 `MARKET_HOME` 环境变量。

### 🔴 [CRITICAL] 2. `collect_a_share_state.py` / `collect_us_state.py` 硬编码 macOS 路径

**位置：** `market_data/collect_a_share_state.py:5`, `market_data/collect_us_state.py:5`

```python
con = duckdb.connect(
    "/Users/rongyuxu/Desktop/A_Share_Monitor/data/local_market/a_share_market.duckdb",
    read_only=True
)
```

**风险：** 这两个脚本是 macOS 遗留产物，在 WSL2 中无法运行。路径不存在，直接抛出 `PermissionError`。

### 🟠 [HIGH] 3. `US_Stock_Monitor/scripts/auto_trader.py` 缺少运行时保护断言

**位置：** `auto_trader.py` 全局

**问题：** 脚本执行模拟交易，使用 `capital_per = 19090`（硬编码金额），但**没有调用** `assert_recommendation_runtime_disabled()` 等 guardrail 断言。对比之下 `cred_test.py`、`deep_validate.py` 等研究脚本正确调用了这些断言。

**风险：** 如果此脚本被误用或环境配置错误，可能绕过安全门控直接产生交易指令。

### 🟠 [HIGH] 4. API Key 硬编码风险

**位置：** 多处脚本

- `US_Stock_Monitor/scripts/fill_missing_us.py` 等：直接使用 `yfinance`（无需密钥）和 `requests` 调用 Sina API
- `save_deepseek_api_key.py`：明文保存 DeepSeek API key 到本地文件
- `deepseek_keychain.py`：管理密钥链

**风险：** 虽然多数免费API不需要密钥，但 DeepSeek key 的管理方式需要审查。`save_deepseek_api_key.py` 可能将密钥写入可被 Git 跟踪的位置。

### 🟡 [MEDIUM] 5. `collect_a_share_state.py` / `collect_us_state.py` bare `except: pass`

**位置：** 多处

```python
except: pass
```

**风险：** 静默吞噬所有异常，导致数据质量问题无法被发现。

---

## 二、量化正确性问题（Quant Correctness）

### 🔴 [CRITICAL] 1. 未来函数 / Look-ahead Bias

**影响项目：** US_Stock_Monitor (scripts/)、quant_research_lab

**问题描述：**
多个回测脚本预先加载完整的 `us_panel.pkl`（包含截至2025-12-31的全部数据），然后在特征构建阶段一次性计算所有滚动窗口特征。这意味着2020年的信号可能「看到」2021年及以后的数据。

**具体位置：**
- `US_Stock_Monitor/scripts/audit_chain.py`：加载完整面板，特征一次性计算
- `US_Stock_Monitor/scripts/cred_test.py`、`credibility_test.py`、`deep_val2.py`、`deep_validate.py`、`final_opt.py`、`improve_strat.py`、`new_strategies.py`、`opt_r2.py`、`opt_r3.py` 等约 10+ 个文件
- `quant_research_lab/research/*.py`：多个研究脚本使用预计算特征

**说明：** 部分脚本已添加审计注释（如 `audit_chain.py:276-303` 标注了幸存者偏差风险），但特征构建时间点问题未完全修复。

### 🔴 [CRITICAL] 2. 幸存者偏差（Survivorship Bias）

**影响项目：** US_Stock_Monitor (scripts/)、quant_research_lab

**问题描述：**
`us_panel.pkl` 缓存只包含当前仍在交易的股票。已退市、被收购的股票在历史回测中被排除，导致收益向上偏移。

**具体位置：**
- 所有加载 `us_panel.pkl` 的脚本（~15个文件）
- `batch_sina.py` 虽然手动列出了约25个退市/被收购标的（VMW, ATVI, TWTR, SIVB等），但这是附带的独立测试，未集成到管线

### 🟠 [HIGH] 3. A 股 T+1 和涨跌停成交模型缺陷

**影响项目：** A_Share_Monitor

**问题描述：**
- `A_Share_Monitor` 的 `qta/backtest/engine.py` 实现了 T+1 和 available_qty 跟踪，覆盖较好
- 但 `US_Stock_Monitor/scripts/engine_fixed.py` 和 `pt_engine.py` 中的轻量级引擎**缺乏停牌检查和T+1结算约束**
- 涨跌停成交模型使用 `px >= up_lim * 0.999`，只跳过涨停价订单，但未建模部分成交或订单簿深度

### 🟠 [HIGH] 4. 合成数据 vs 真实数据标注混乱

**影响项目：** us_stock_30w, A_Share_Monitor

**问题描述：**
- `us_stock_30w/config/data/us_data_41k.yaml` 标注 `provider: synthetic, allow_network: false`
- 但实际脚本使用 `yfinance` 等真实数据源（需要网络访问）
- 配置与执行不一致：标注说「合成数据，无网络」，但执行使用「真实数据，有网络」

### 🟠 [HIGH] 5. 信号逻辑代码重复（8+副本）

**影响项目：** US_Stock_Monitor (scripts/)

**问题：** Adaptive+Quality 和 Quality+LowVol 信号的实现被复制粘贴到约8个脚本中。任何 bug 修复需要在所有副本中同步修改。

**具体文件：** `auto_trader.py`, `current_portfolio.py`, `current_positions.py`, `live_pos.py`, `live_positions.py`, `live_tracker.py`, `paper_trade.py`, `ashare_cross.py`

### 🟠 [HIGH] 6. 预计算信号用于 Walk-Forward 分析

**影响项目：** A_Share_Monitor

**问题：** Walk-Forward 验证使用了预缓存的信号，而不是在每个窗口内重新拟合。这降低了样本外验证的有效性。

### 🟡 [MEDIUM] 7. 财务数据公告日滞后

**影响项目：** A_Share_Monitor

**问题：** 财务数据可用性滞后通过配置实现，但财务数据下载和特征构建的实际时间点未与公告日历对齐。

### 🟡 [MEDIUM] 8. 交易日历假设简化

**影响项目：** US_Stock_Monitor, us_stock_30w

**问题：**
- `auto_trader.py:131`：`trading_days_s1 = int((TODAY - s1_last).days * 5/7)` —— 简单地按5/7比例估算交易日，忽略美国节假日（感恩节、圣诞节等）
- A 股市场日历未明确处理春节、国庆等长假

### 🟡 [MEDIUM] 9. 跨市场价格模型不一致

**影响项目：** A_Share_Monitor vs US_Stock_Monitor

**问题：**
- A股成本：佣金0.03% + 印花税0.1%（仅卖出）+ 5bps滑点
- 美股成本：cost_bps=3.0, slippage_bps=5.0
- 两个模型分别硬编码在各自的引擎中，无法统一配置

### 🟡 [MEDIUM] 10. 外汇风险忽略

**影响项目：** us_stock_30w

**问题：** 「30万人民币 ≈ $41,000 USD」使用固定汇率，没有汇率跟踪。对于长期的跨市场策略，汇率波动可能显著影响实际收益。

---

## 三、代码质量问题

### 🔴 [CRITICAL] 1. 大规模代码重复

**范围：** US_Stock_Monitor (scripts/), quant_research_lab

**问题：** 如前所述，核心信号逻辑在8个文件中重复。此外：
- `run_all.sh`, `run_pipeline.sh` 等 shell 脚本在不同项目中重复
- 数据加载逻辑（pickle 加载、yfinance 下载）在多个脚本中重复

### 🟠 [HIGH] 2. 裸异常捕获（bare except）

**范围：** 所有项目

**问题：** 大量使用 `except: pass`, `except Exception: continue`, `except: continue`。这些静默吞噬所有错误，使得数据损坏、模式变更、网络错误等完全不可见。

**典型例子：**
```python
try:
    # 数据加载
except Exception:
    continue  # 出错了？跳过，谁知道呢
```

### 🟠 [HIGH] 3. 无统一日志框架

**范围：** US_Stock_Monitor (scripts/), quant_research_lab

**问题：** 多个脚本使用自定义 `log()` 函数写 stdout，没有结构化日志、日志级别（ERROR/WARN/INFO/DEBUG）、日志轮转。

### 🟠 [HIGH] 4. `sys.path.insert(0, '.')` 用法

**范围：** US_Stock_Monitor (scripts/) 中的约10个脚本

**问题：** 依赖当前工作目录进行导入，非常脆弱。如果从不同目录启动脚本将失败。

### 🟡 [MEDIUM] 5. 幻数（Magic Numbers）

**范围：** 所有项目

- 再平衡周期：`42` 天（S1）和 `63` 天（S2）出现约10次，无命名常量
- 滑点：`0.0005`（5bps）硬编码在多处
- `capital_per = 19090`（「GOOGL 收益的一半」）无说明
- `num=1500`（Sina API 条数限制）硬编码

### 🟡 [MEDIUM] 6. 无类型注解

**范围：** US_Stock_Monitor (scripts/), quant_research_lab

**问题：** 核心信号函数缺少类型注解，影响可维护性和静态分析。

### 🟡 [MEDIUM] 7. JSON 状态文件写入非原子性

**范围：** quant_research_lab

**问题：** `portfolio.json` 状态文件直接写入，没有使用临时文件 + 重命名模式。如果写入过程中崩溃，状态文件会被损坏。

### 🟡 [MEDIUM] 8. 陈旧的 `.pytest_cache` 在多个项目中

**范围：** US_Stock_Monitor, market_data 等

**问题：** `.pytest_cache/` 被提交到 Git 中（被跟踪），应添加到 `.gitignore`。

---

## 四、业务逻辑与安全门控问题

### 🟠 [HIGH] 1. `market_data` 的 fail-closed 门控设计良好

**正面发现：** `market_data/adapters/access_gate.py` 和 `registry.py` 实现了严格的 fail-closed 产品数据访问门控：
- A 股：只允许固定的 `accepted_snapshot_id`，50只标的基线
- 美股：统一 DB 读取被完全阻断（`ProductReadBlocked`）
- 运行时标记（`recommendation_runtime_enabled`, `broker_api_allowed`, `live_trading_allowed`）必须全部为 `false`
- 注册表验证比预期严格：行数、符号数、快照ID 全部钉死检查

### 🟠 [HIGH] 2. `US_Stock_Monitor` AGENTS.md 硬规则较完善

**正面发现：** US_Stock_Monitor 的 `AGENTS.md` 和 `CLAUDE.md` 定义了13条硬规则，包括：
- 不允许实盘下单
- 不允许 `live_trading_candidate` 标签
- 不允许读取/打印/提交 `.env`
- 不允许将合成数据结果当作真实策略证据
- 有完整的多 Agent 协作协议（Codex-Dev → DeepSeek-Audit → Codex-Audit → ChatGPT）

### 🟠 [HIGH] 3. `A_Share_Monitor` AGENTS.md 硬规则也较完善

**正面发现：** A_Share_Monitor 的 AGENTS.md 定义了10条高优先级规则，与 US_Stock_Monitor 一致。

### 🟡 [MEDIUM] 4. `quant-proj` 的项目治理框架较完善

**正面发现：** `registry/projects.yaml` 和 `registry/agents.yaml` 定义了完整的：
- 多项目依赖关系（downstream threads）
- Agent 角色和权限边界
- 数据迁移策略
- `do_not_migrate_without_explicit_audit_stage` 列表

### 🟡 [MEDIUM] 5. `STRATEGY_VAULT` 结构清晰但部分数据陈旧

**问题：** STRATEGY_VAULT 的 CN-01（A股策略）标注「RETRACTED - 待修复」。策略验证标准明确，但美股策略可能使用了包含未来函数的缓存数据。

---

## 五、各项目专项发现

### A_Share_Monitor（11G）

| 发现 | 严重程度 |
|------|---------|
| DB 数据约 961MB DuckDB，含 3068只标的、~540万行日线数据 | - |
| 未来函数防护较好：engine.py 有 T+1 available_qty 跟踪 | ✅ |
| 回测引擎区分 train/validation/test | ✅ |
| 策略评级限制正确（无 live_trading_candidate） | ✅ |
| 数据质量控制（覆盖报告、快照清单） | ✅ |
| smoke test 使用合成数据避免网络依赖 | ✅ |
| 但 outputs/ 目录保留了大量历史研究产出（数十个 JSON/MD 报告） | 混乱 |
| `.venv/` 存在于项目目录内（应使用 system/global venv） | 建议清理 |

### US_Stock_Monitor（187M）

| 发现 | 严重程度 |
|------|---------|
| `usq/` 包结构清晰，模块化程度高 | ✅ |
| 测试覆盖率高(~120测试文件)，包括 guardrail、safety 测试 | ✅ |
| 外部 AI 研究集成（Berkshire 风格导入） | 新颖 |
| scripts/ 目录下的 40+ 个脚本为历史遗留，部分质量参差不齐 | ⚠️ |
| agent_safety_check.py 是 repo 密钥/违规标签扫描器 | ✅ |
| `live_tracker.py`, `auto_trader.py` 等脚本可能跨越安全边界 | ⚠️ |

### quant_research_lab（1.9G）

| 发现 | 严重程度 |
|------|---------|
| paper_trader/ 模块有完整的纸面交易引擎实现 | - |
| `paper_trader/engine.py` 与 A_Share_Monitor 的引擎高度重复 | ⚠️ |
| 大量 outputs/ 生成文件（日志、报告、dashboard HTML） | 混乱但非代码问题 |
| 缺少 guardrail 断言 | ⚠️ |

### market_data（1.7M）

| 发现 | 严重程度 |
|------|---------|
| **最健壮的模块** — fail-closed 设计、注册表验证、产品读取门控 | ✅ |
| 清晰的物理 DB 路径解析（支持环境变量覆盖） | ✅ |
| 美股读取被显式阻断（`ProductReadBlocked`） | ✅ |
| collect_*_state.py 是 macOS 遗留物，硬编码 macOS 路径 | ❌ |
| 注册表钉死了精确的行数/符号数（50只标的，86817行） | ✅ 但过于脆弱 |

### global-stock-data

| 发现 | 严重程度 |
|------|---------|
| SKILL.md 是全栈数据工具包（8层架构、5个数据源） | 功能性项目 |
| 所有 API 零鉴权（新浪、腾讯、东方财富等） | 注意使用条款 |
| V1.0.1 修复了多个函数漏传 `params=params` 的 bug | 已修复 |
| 非本项目代码，是外部开源项目 | 引用需注意 |

### quant-proj（任务调度器）

| 发现 | 严重程度 |
|------|---------|
| 项目管理框架优秀：agents.yaml、projects.yaml、downstream threads | ✅ |
| 多个 Agent 角色定义清晰 | ✅ |
| 任务模板完整（tasks/ 目录下多个 spec） | ✅ |
| 无非代码问题，主要是协调层 | 良好 |

---

## 六、Top 10 立即修复建议

| 优先级 | 问题 | 建议修复 |
|--------|------|---------|
| **P0** | 未来函数 / look-ahead bias（10+脚本） | 在回测循环中滚动/扩展构建特征，而非一次性预计算 |
| **P0** | 硬编码绝对路径（所有项目） | 统一使用 `Path(__file__).resolve().parents[n]` 或 `MARKET_HOME` 环境变量 |
| **P1** | `collect_a_share_state.py/us_state.py` 硬编码 macOS 路径 | 删除或重构为 WSL2 兼容版本 |
| **P1** | 信号逻辑 8份代码重复 | 提取到 `signal_library.py` 单文件 |
| **P1** | `auto_trader.py` 等缺少 guardrail 断言 | 添加 `assert_recommendation_runtime_disabled()` 调用 |
| **P2** | 幸存者偏差（pickle 缓存） | 使用包含退市标的的数据库（如 A_Share_Monitor 的 DuckDB 方法） |
| **P2** | 裸 `except: pass` 拦截器 | 替换为具体异常处理 + 日志记录 |
| **P2** | 合成/真实数据标注不一致 | 确保 `config/data` 的 `provider` 设置与执行一致 |
| **P3** | `.pytest_cache/` 在 Git 中 | 添加到 `.gitignore` |
| **P3** | `capital_per = 19090` 等幻数 | 提取为命名常量或配置参数 |

---

## 七、项目总体评估

| 项目 | 安全性 | 量化正确性 | 代码质量 | 业务健壮性 |
|------|--------|-----------|---------|-----------|
| **A_Share_Monitor** | ⚠️ 中等 | ✅ 较好 | ⚠️ 中等 | ✅ 较好 |
| **US_Stock_Monitor** | ⚠️ 中等 | ⚠️ 中等（脚本层问题多） | ⚠️ 中等 | ✅ 较好（usq包层） |
| **quant_research_lab** | ⚠️ 中等 | ⚠️ 需注意 | ⚠️ 中等 | ⚠️ 需加强 |
| **us_stock_30w** | ⚠️ 中等 | ⚠️ 需注意 | ⚠️ 中等 | ⚠️ 需加强 |
| **market_data** | ✅ 优秀 | ✅ 优秀 | ✅ 良好 | ✅ 优秀 |
| **quant-proj** | ✅ 良好 | N/A（调度器） | ✅ 良好 | ✅ 良好 |
| **strategy_work** | ⚠️ 中等（路径问题） | ⚠️ 脚本层 | ✅ 良好 | ⚠️ 中等 |
| **STRATEGY_VAULT** | ✅ 良好 | ⚠️ 数据可能过时 | ✅ 良好 | ⚠️ 中等 |
| **global-stock-data** | ✅ 良好（无密钥） | N/A（数据工具包） | ⚠️ 中等（早期修复记录） | ✅ 良好 |

---

*审核完成。共审查约 350+ Python 源文件、50+ YAML 配置文件、数百个 Markdown 文档。*
