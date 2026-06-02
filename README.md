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
- **分析结果清理工具**
  - 支持按队伍清理
  - 支持全量清理
  - 支持 dry-run 预览

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

输出：

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

输出：

- `outputs/insights/<team>.json`

### Stage 6 — report

负责把结构化结果和分析结论渲染为最终报告。

输出：

- `outputs/reports/<team>.md`
- `outputs/reports/<team>.html`

### Stage 7 — visualize

负责生成图表数据与单页可视化结果。

输出：

- `outputs/visualizations/<team>.json`
- `outputs/visualizations/<team>.html`

### Stage 8 — validate_final

负责对最终产物做验收，检查报告完整性、图表可用性和关键字段缺失情况。

输出：

- `outputs/validation/<team>.json`

---

## 推荐使用方式

当前推荐使用顺序是：

1. **动态 CLI + 实时抓取 Codeforces**
2. **browser bridge + 插件导入网页数据**
3. `task-file` / `examples` 用于演示、回归、测试

---

## 方式一：直接实时抓取 Codeforces（推荐主用）

这是当前**最稳定、最直接**的使用方式。

### 示例

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --max-contests 5
```

### 说明

这条命令会自动执行：

- `collect`
- `normalize`
- `team_identity`
- `build_history`
- `compute_metrics`
- `analyze`
- `report`
- `visualize`
- `validate_final`

### 如果只想先抓取并检查数据

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --max-contests 3 \
  --end-stage normalize \
  --skip-analyze \
  --skip-visualize
```

### 如果想指定具体比赛

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --contest-ids 1987 2118
```

---

## 方式二：browser bridge + 插件链路

当前插件链路已经可以试用，适合：

- 在网页端快速导入 standings 数据
- 交互式体验 browser bridge 工作流

### 步骤 1：启动本地 bridge

```bash
python3 scripts/run_bridge.py
```

默认监听：

- `http://127.0.0.1:8765`

### 步骤 2：加载浏览器插件

加载目录：

- `plugins/browser-extension/`

### 步骤 3：导入数据并执行分析

导入后，可继续执行：

```bash
python3 scripts/run_pipeline.py \
  --source browser_bridge \
  --target-team tourist \
  --bridge-import-id <import_id> \
  --start-stage normalize
```

---

## 方式三：task-file / 示例任务

### 示例

```bash
python3 scripts/run_pipeline.py --task-file examples/sample_task.json
```

当前默认就会尝试 LLM analyze。

如需显式关闭：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --disable-llm-insight
```

---

## 清理现有分析数据

当前已提供独立清理脚本：

```bash
python3 scripts/clear_artifacts.py
```

### 1. 按队伍清理

```bash
python3 scripts/clear_artifacts.py --target-team "ZJU Alpha"
```

会删除该队伍对应的：
- team_identity
- team_history
- team_metrics
- insights
- reports
- visualizations
- validation

注意：
- 按队伍模式**不会删除共享 raw / normalized 文件**，因为这些文件当前不是按队伍拆分。

### 2. 全量清理

```bash
python3 scripts/clear_artifacts.py --all
```

会清理：
- `data/raw/`
- `data/normalized/`
- `data/intermediate/`
- `data/derived/`
- `outputs/`

中的运行产物文件，但会保留目录结构本身。

### 3. dry-run 预览

```bash
python3 scripts/clear_artifacts.py --target-team "ZJU Alpha" --dry-run
python3 scripts/clear_artifacts.py --all --dry-run
```

仅输出将删除哪些文件，不实际删除。

### 4. 清理队伍相关 bridge run 摘要

```bash
python3 scripts/clear_artifacts.py \
  --target-team tourist \
  --include-bridge-runs
```

会额外删除 `outputs/bridge_runs/` 中与该队伍相关的运行摘要。

---

## 局部重跑建议

如果某个阶段发现问题，推荐只修复对应阶段并局部重跑。例如：

- 抓取字段变化，只重跑 `collect` 和后续阶段
- 队伍别名识别有误，只重跑 `team_identity` 及下游阶段
- 指标口径调整，只重跑 `compute_metrics` 及下游阶段
- analyze prompt 更新，只重跑 `analyze` / `report` / `visualize` / `validate_final`

推荐命令示例：

```bash
python3 scripts/run_pipeline.py --task-file examples/sample_task.json --start-stage analyze
python3 scripts/run_pipeline.py --task-file examples/sample_task.json --start-stage analyze --disable-llm-insight
```

---

## 设计提醒

- 尽量不要让 LLM 直接替代 `normalize` 或 `compute_metrics`
- 高层总结应可替换，但底层协议应尽量稳定
- 若后续适配多个 provider，优先扩展 analyzer 内部客户端，而不是污染其他 stage
- 共享 raw / normalized 目前是全局文件，因此“按队伍清理”只应删除按队伍命名的 artifact
