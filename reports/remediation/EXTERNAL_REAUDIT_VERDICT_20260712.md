# 外审裁定

你给出的状态隐含了一个关键前提：**内部整改关闭矩阵、shadow audit 和绿色 CI 共同成立，就足以推出外部审计通过。**

若不接受这个前提，外审问题应重新表述为：

> 被认定为“研究就绪”的实现，是否就是生产/研究运行时实际调用的实现；外部审计员能否不依赖作者的关闭声明，直接从代码、测试和不可变证据证明这一点？

按这个标准，本轮结论是：

```text
EXTERNAL_REAUDIT_VERDICT = NOT_PASSED
PR_REVIEW = CHANGES_REQUESTED
STATUS = REWORK_REQUIRED
new_critical = 0
new_high = 1
strategy_candidate_available = false
```

## 一、总体判断

项目质量相较上一轮已经有**显著、实质性提升**。PR #11 的 head 与申报 commit 一致，已经转为 Ready for review；控制器 CI 的三个独立 job 全部成功，并采用固定 Actions SHA、带哈希依赖锁和 skip-budget 检查。

七个整改仓库的固定 head 均有成功的 exact-head GitHub Actions run，不存在“只有控制器绿灯、子仓失败”的情况。

上一轮的核心问题中，以下修复经逐行复核后可以接受：

* A 股 rebuild 现在绑定实际打开的数据库文件描述符、inode 和哈希，真实执行 whole-label purge，并在验证完成后原子发布。
* A10 生产 runner 已硬关闭，emitter 不再具有真实票据账本写入参数，并在底层再次阻断。
* Quant Lab 已改为按位置绑定因子结果，并在冻结测试中重算和使用获胜因子。
* US30W 已把 strict PIT 限定为带时区、修订链、`available_at <= decision_time` 及官方日历证据的数据资格检查；失败时自动降级，且不重开旧策略。
* `market_data` 已加入 hardlink/symlink/inode/race 防护及带回滚的原子发布。
* Luna acceptance 现在要求 `EXECUTION_ATTESTED`，重新运行命令、比较输出摘要，并强制执行与接受使用不同任务身份。
* Family 66 已移除 canonical 数据字节核验旁路；PBO 不再静默丢弃余数样本。
* 22 个许可未证明的二进制/行级产物已从当前整改 refs 删除，仍保留历史哈希以等待单独治理。

这些均不是“只改文档”的修复。

---

# 二、阻断通过的新 High：CSV 资格认定与实际运行实现分裂

## RA-001 — High

`US_Stock_Monitor` 中，CSV 数据源被明确配置为：

```text
enabled: true
tier: research
```

但资格认定逻辑只检查五个 CSV 文件路径是否存在。如果存在，即返回：

```text
status = PASS
readiness_level = RESEARCH_READY
```

它不在这一层验证：

* 文件是否非空；
* CSV 是否可解析；
* 列是否完整；
* provenance sidecar 是否存在；
* 文件哈希是否与 controller pin 一致。

随后 readiness gate 会直接据此把整个数据状态设为 `research_ready=true`。

### 更严重的是：资格检查和实际 runtime 不是同一实现

资格检查依据的是已经修复的表式 `CsvImporter`：

```text
daily_ohlcv.csv
splits.csv
dividends.csv
...
```

但 provider factory 对 `"csv"` 返回的却是另一套 `CsvProvider`。

这套实际 provider 仍存在：

```python
path = self.data_dir / f"{symbol}.csv"
df = df[~df.index.duplicated(keep="last")]
self.real_data = bool(real_data)
```

也就是：

* `symbol="../outside"` 可以越出 `data_dir`；

* 同日期冲突行情会被静默保留最后一条；

* 调用者仅传 `real_data=True`，就可以使 `synthetic_data=false`，不要求修复后的哈希 provenance 合同。

研究 pipeline 确实通过这个 factory 选择数据 provider，因此它不是纯粹不可达的废弃代码。

## 动态复现

本次最小复现得到：

```text
5 个空白占位 CSV 文件
→ qualification = PASS
→ readiness_level = RESEARCH_READY
→ research_ready = true

symbol = "../outside"
→ 成功读取 data_dir 以外的 outside.csv

同一日期两条冲突行情
→ 输入 2 行
→ 静默保留 1 行
→ 保留后一条 close=99.0

real_data=True
→ synthetic_data=false
→ 无需 pinned provenance
```

这不是自动交易风险，但它直接破坏了“研究数据已经过资格认定”的可信度，属于本项目证据体系中的 High。

---

# 三、关闭矩阵本身存在不精确映射

## RA-002 — Medium

`FINDING_CLOSURE_MATRIX.json` 把 F-008 的受影响路径写为：

```text
usq/data/csv_provider.py
```

并声明已经完成 table enum、containment、duplicate conflict 和 provenance 修复。

但实际 PR 修改的是：

```text
usq/data/csv_importer.py
```

该 importer 的确已经正确实现：

* 显式表名枚举；

* `data_dir` containment；

* symlink 拒绝；

* exact provenance 文件集合；

* 冲突重复行情 fail closed。

问题在于：**关闭矩阵把对 importer 的修复归到了 provider 上，导致未修复的活动 provider 被 shadow audit 和 CI 误认为已经覆盖。**

US Monitor 的 CI 虽然确实执行了三类 job、固定依赖和 skip-budget，但其中的 “CSV boundary and provenance mutation tests” 验证的是 importer 合同，并没有发现 factory 仍连接另一实现。

关闭矩阵以后应绑定：

```text
audited_path
audited_blob_sha
fixed_path
fixed_blob_sha
test_node_ids
runtime_factory_binding
```

而不是只写仓库级 commit 和自然语言结论。

---

# 四、受控 data-room 证据尚未由本外审会话独立验真

## EA-001 — 外部证据阻塞

GitHub 索引记录了 A 股 canonical engineering bundle 的：

* 授权记录；
* manifest；
* Markdown 报告；
* Parquet；
* 数据库与 universe 哈希；
* 136,767 行、77 个证券；
* 2,779 条跨边界标签全部被 purge；
* publisher commit/tree。

GitHub brief 也明确说明，行级数据仍在受控 data room 中，不进入公共 Git。

但本次外审会话没有得到 data-room bundle 本身，因此无法独立重算其哈希、读取 manifest 或检查 Parquet 内容。

此外，索引记录的 publisher commit：

```text
3903977d2480a5ad9be67c4c267cd2a5c5a4bdb8
```

无法通过当前连接的 GitHub 仓库解析。它可能是有意保留在 data room 中的本地发布 commit，但在提供 commit object、Git bundle 或哈希绑定 source archive 前，我只能接受修复代码和 GitHub 索引，不能接受 canonical bundle 的外部验真结论。

这不是证明 bundle 错误，而是：

```text
EVIDENCE_PRESENT_BY_INDEX
INDEPENDENT_BYTE_VERIFICATION_NOT_COMPLETED
```

---

# 五、历史凭据结论只能作为管理层声明接受

凭据 attestation 明确记录：

* 账户所有者通过官方控制台删除；
* provider receipt 不可用；
* 旧字节仍留在 Git 历史；
* 不允许继续使用。

因此本外审接受：

```text
OWNER_REPORTED_REVOKED
OPERATIONAL_USE_FORBIDDEN
```

但不能升级为：

```text
PROVIDER_INDEPENDENTLY_CONFIRMED_REVOKED
```

历史 secret scan 本身已覆盖全部配置 refs 和完整历史，并披露 QRL 中一个唯一候选。

这一项不是新的 High；历史重写仍可保持为单独治理决策。较理想的补强是在私有 data room 放置脱敏控制台截图、provider event export 或第二审查者签字，而不是重新访问或测试旧 secret。

---

# 六、最终裁定

## 已通过的部分

```text
CORE_REMEDIATION_CODE = SUBSTANTIALLY_ACCEPTED
EXACT_HEAD_CI = ACCEPTED
ORIGINAL_STRATEGY_CONCLUSIONS = ACCEPTED
AUTOMATED_BROKER_ORDER_PAPER_LIVE_PATH = NOT_FOUND
strategy_candidate_available = false
```

最终 controller root 本身也正确禁止整改方自行签发外部通过结论，只允许保持 `NOT_YET_PASSED`。

## 未通过的原因

```text
NEW_HIGH_RA_001 = OPEN
F008_CLOSURE_MAPPING = INACCURATE
A_SHARE_DATA_ROOM_BYTES = NOT_INDEPENDENTLY_VERIFIED
```

所以 PR #11 当前外审意见应为：

```text
CHANGES_REQUESTED
```

而不是 Approve。

---

# 七、最窄整改清单

完成以下内容后，无需再做一次完整 repository-wide 外审，只需要定向复审：

1. **统一 CSV 实现。** 推荐从 factory 移除 `CsvProvider`，让 `"csv"` 返回基于修复后 `CsvImporter` 的 DataProvider adapter。
2. **删除调用者控制的 `real_data` 真实性声明。** `synthetic_data=false` 只能来自 controller-pinned provenance 验证。
3. **重写 readiness gate。** 必须实例化并验证实际 runtime provider；空文件、不可解析文件或缺失 provenance 不能得到 `RESEARCH_READY`。
4. **加入合同测试。**

   * 五个空文件不得 research-ready；
   * qualification implementation 与 factory implementation 必须相同；
   * `../`、绝对路径、symlink escape 均失败；
   * 冲突重复行情失败；
   * 无 pinned provenance 不得生成 real-data manifest。
5. **修正 F-008/F-009 closure path 和 blob 绑定。**
6. **重新运行 US Monitor 与 controller exact-head CI，并更新最终 controller root。**
7. **向外审方提供只读 data-room bundle及 publisher source object/source archive。**
8. **保持 `strategy_candidate_available=false`，不得借此整改重跑旧策略。**

---

# 外审交付件

* [完整外审裁定报告](sandbox:/mnt/data/repository_reaudit_external_verdict_20260712.md)
* [机器可读 findings 与裁定](sandbox:/mnt/data/repository_reaudit_findings_20260712.json)
* [CSV split-brain 动态复现脚本](sandbox:/mnt/data/reproduce_us_csv_provider_split_brain_20260712.py)
* [动态复现输出](sandbox:/mnt/data/reproduce_us_csv_provider_split_brain_20260712.txt)
* [完整外审证据包](sandbox:/mnt/data/repository_reaudit_evidence_20260712.zip)
* [证据包 SHA-256](sandbox:/mnt/data/repository_reaudit_evidence_20260712.zip.sha256)

证据包 SHA-256：

```text
fafa5c566d2d45fe7eee1c39e05ae3e5dd1e851473c2e3ec10cb86e79952ac78
```
