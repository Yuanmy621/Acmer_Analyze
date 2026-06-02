# acmer_analyze

`acmer_analyze` 是一个面向 **ACM / 竞赛编程队伍分析** 的 Agent 项目。

项目希望围绕某支目标队伍，基于比赛排名、题目信息与历史参赛记录，生成：

- 排名变化分析
- 技能树 / 题型能力分析
- 优势与短板总结
- 可视化分析报告

---

## 当前状态

当前仓库已经具备：

- 文档骨架与目录骨架
- 基于 Python 标准库的最小可运行 pipeline
- `source=fixture` 的本地联调能力
- `source=codeforces` 的真实抓取能力
- `source=browser_bridge` 的导入与下游执行能力
- report / visualize / validate 的最小实现
- **analyze 阶段的双模式能力**
  - 默认优先走 LLM analyze
  - LLM 失败时回退 `rule-based-template`

当前仓库仍然不具备或不完整的能力包括：

- UCUP 在线抓取能力
- 更复杂的网页解析与多站点插件适配
- 生产级 CI / lint / deploy 约定
- 更成熟的 HTML 可视化交付

---

## 核心设计原则

### 1. pipeline 优先，而不是单次 prompt

项目不是希望做成“一次性把原始网页喂给模型然后直接出结论”的黑盒，而是希望按阶段拆开：

1. collect
2. normalize
3. team_identity
4. build_history
5. compute_metrics
6. analyze
7. report
8. visualize
9. validate_final

### 2. 确定性计算与自然语言解释分层

- `compute_metrics` 负责确定性指标计算
- `analyze` 负责高层解释、总结、建议
- LLM 只应该增强解释层，不应替代底层数据清洗和指标统计

### 3. artifact 可追溯

每个阶段都应把中间结果落盘，便于：

- 检查问题
- 局部重跑
- 回溯错误
- 替换具体实现而不破坏整体结构

---

## Stage 概览

### Stage 1 — collect

负责从外部来源获取原始数据，当前支持：

- fixture
- Codeforces
- browser bridge

输出：

- `data/raw/contests/contests.json`
- `data/raw/problems/problems.json`
- `data/raw/standings/standings.json`

### Stage 2 — normalize

负责把不同 source 的原始结构转换为统一协议。

输出：

- `data/normalized/contests/contests.json`
- `data/normalized/problems/problems.json`
- `data/normalized/standings/standings.json`

### Stage 3 — team_identity

负责在标准化 standings 中识别目标队伍，并构造统一身份。

输出：

- `data/intermediate/team_identity/<team>.json`

### Stage 4 — compute_metrics

负责计算排名趋势、题型能力分布、稳定性、波动性、成长性等指标。

这一层应尽量保持为确定性逻辑，不依赖 LLM。

建议输出：

- `data/derived/team_metrics/<team>.json`

### Stage 5 — analyze

负责基于结构化指标生成高层分析结论，如优势、短板、训练建议、阶段性判断。

当前支持两种模式：

1. **LLM analyze**
   - 默认模式
   - 从环境变量或 `~/.claude/settings.json` 读取配置
   - 调用失败时默认回退到 `rule-based-template`
2. **rule-based-template**
   - 可通过显式关闭 LLM 使用
   - 不依赖外部模型

建议输出：

- `outputs/insights/<team>.json`

### Stage 6 — report

负责把结构化结果和分析结论渲染为最终报告。

建议输出：

- `outputs/reports/<team>.md`
- `outputs/reports/<team>.html`

### Stage 7 — visualize

负责生成图表数据与单页可视化结果。

建议输出：

- `outputs/visualizations/<team>.json`
- `outputs/visualizations/<team>.html`

### Stage 8 — validate_final

负责对最终产物做验收，检查报告完整性、图表可用性和关键字段缺失情况。

---

## 使用方案

本项目的推荐使用方式，不是把它当作单一函数式工具，而是把它当作一条可执行的分析任务链。

一个典型的使用过程可以理解为：

### 1. 指定分析任务

输入至少包括：

- 目标队伍标识（队名、别名或平台 ID）
- 比赛范围（平台、时间区间、赛事集合）
- 可选分析参数（例如是否生成可视化、是否启用 AI 总结）

### 2. 触发流水线运行

由 Orchestrator 依次调度：

1. 数据采集
2. 数据归一化
3. 队伍身份识别
4. 历史记录构建
5. 指标计算
6. 分析生成
7. 报告与可视化生成
8. 最终验收

当前最小运行命令为：

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --max-contests 3
```

当前也支持：

- task-file 模式
- browser bridge 导入模式
- browser bridge 导入并自动开始分析

例如：

```bash
python3 scripts/run_pipeline.py --task-file examples/codeforces_task.json
python3 scripts/run_pipeline.py --source browser_bridge --target-team tourist --bridge-import-id <import_id> --start-stage normalize
python3 scripts/run_bridge.py
```

当前默认就会尝试 LLM analyze，因此直接运行即可：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json
```

若希望指定模型或设置文件：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --llm-model gpt-5.4 \
  --llm-settings-path ~/.claude/settings.json
```

若希望显式关闭 LLM、改走本地规则模板：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --disable-llm-insight
```

如果你要使用浏览器插件完整链路，建议同时阅读：

- `docs/browser_bridge_usage.md`

当前支持的主要参数包括：

- `--task-file`
- `--source`
- `--target-team`
- `--aliases`
- `--codeforces-handle`
- `--contest-ids`
- `--max-contests`
- `--bridge-import-id`
- `--bridge-metadata-path`
- `--disable-llm-insight`
- `--llm-model`
- `--llm-settings-path`
- `--disable-llm-fallback`
- `--start-stage`
- `--end-stage`
- `--skip-analyze`
- `--skip-visualize`

这意味着当前已经可以：

- 基于动态参数实时抓取 Codeforces 数据
- 基于本地 fixture 跑完整链路
- 基于 browser bridge 导入网页端提取数据
- 通过 browser bridge 自动导入并启动分析
- 默认优先使用 LLM analyze
- 从某个阶段继续往后执行
- 通过 artifact 检查各阶段中间结果

### 3. 检查中间产物

在任意阶段，使用者或开发者都可以查看落盘 artifact，例如：

- 原始 standings 是否正确
- 队伍身份映射是否可信
- 指标结果是否符合预期
- 报告内容是否与 metrics 一致

### 4. 局部修复与重跑

如果某个阶段发现问题，推荐只修复对应阶段并局部重跑。例如：

- 抓取字段变化，只重跑 `collect` 和后续阶段
- 队伍别名识别有误，只重跑 `team_identity` 及下游阶段
- 报告模板更新，只重跑 `report` / `visualize` / `validate_final`

因此，本项目的使用方案本质上也是开发方案的一部分：

> 一切阶段都应设计成可单独验证、可局部重跑、可通过 artifact 追溯。

---

## 建议输入与输出

### 输入

一个最小可用分析任务至少需要：

- 目标队伍标识（队名、别名或平台 ID）
- 比赛范围（平台、时间区间、赛事集合）
- 对应比赛的排名数据
- 对应比赛的题目信息

### 输出

建议输出拆为两类：

- **结构化结果**：适合程序消费，例如 JSON / 中间分析结果
- **展示型结果**：适合用户阅读，例如 Markdown / HTML / 图表报告

一份完整分析结果可以包含：

- 队伍概览
- 排名趋势图
- 题型能力分布图
- 强弱项总结
- AI 结论与建议

---

## 当前目录骨架与 Artifact Store

当前仓库已经按 artifact store 与分层实现思路补齐了基础骨架，当前目录包括：

```text
acmer_analyze/
├── README.md
├── CLAUDE.md
├── docs/
│   ├── architecture.md
│   ├── project_structure.md
│   ├── runtime_flow.md
│   ├── stage_schema.md
│   └── conventions/
├── scripts/
├── src/
│   ├── orchestrator/
│   ├── collector/
│   ├── normalize/
│   ├── identity/
│   ├── models/
│   ├── metrics/
│   ├── analyzer/
│   ├── report/
│   ├── visualize/
│   └── validation/
├── data/
├── outputs/
├── tests/
├── examples/
└── config/
```

---

## 当前实现约束

当前实现依然保持“标准库优先”的最小风格：

- 主要使用 Python 标准库
- pipeline 编排尽量简单直接
- LLM 调用通过 HTTP 最小封装实现
- 默认测试不会依赖真实外网调用

因此，如果后续继续增强：

- 建议优先保持 artifact 协议稳定
- 再逐步增强 analyzer 的 prompt 与 provider 适配
- 避免把确定性计算逻辑重新塞回 LLM
