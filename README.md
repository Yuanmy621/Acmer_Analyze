# Acmer Analyze

`acmer_analyze` 是一个面向 **ACM / 竞赛编程队伍分析** 的分析型 Agent 项目。

项目目标不是做一个“一次性把网页或榜单丢给模型，然后直接返回结论”的黑盒工具，而是围绕 **可编排、可追溯、可局部重跑、可扩展** 的思路，构建一条完整分析流水线。

当前项目已经可以围绕一支目标队伍，基于比赛排名、题目信息与历史参赛记录，生成：

- 排名变化分析
- 技能树 / 题型能力分析
- 优势与短板总结
- 训练建议
- Markdown / HTML 报告
- 单页可视化分析结果

---

## 当前项目状态

当前仓库已经具备：

- 一套基于 **Python 标准库** 的最小可运行 pipeline
- 动态 CLI 参数模式
- `source=codeforces` 的真实抓取能力
- `source=browser_bridge` 的网页端导入能力
- browser bridge `import-and-run` 自动分析链路
- Codeforces standings 页面首版插件提取逻辑
- `.claude/settings.json` 命令型 hooks
- `.claude/hooks/` 运行期 hooks 体系
- 完整的基础测试集

当前仓库仍然在持续演进，尚未完全具备：

- UCUP 在线抓取能力
- 多站点成熟插件适配
- 复杂页面解析的长期鲁棒性保证
- 完整的 build / lint / CI 工程体系

因此，当前更准确的理解应是：

> 已经完成从“文档骨架”到“首版可运行分析链路”的跨越，当前处于持续增强真实数据、插件链路与 hooks 体系的阶段。

---

## 核心设计原则

### 1. pipeline 优先，而不是单次 prompt

主流程按阶段拆开：

1. `collect`
2. `normalize`
3. `team_identity`
4. `build_history`
5. `compute_metrics`
6. `analyze`
7. `report`
8. `visualize`
9. `validate_final`

### 2. 确定性计算与自然语言解释分层

- `compute_metrics` 负责确定性指标计算
- `analyze` 负责高层解释、总结、建议
- LLM 只增强解释层，不替代数据清洗和指标统计

### 3. artifact 可追溯

每个阶段都把结果落盘，便于：

- 检查问题
- 局部重跑
- 回溯错误
- 替换具体实现而不破坏整体结构

### 4. 浏览器网页导入是 collect 的扩展，而不是替代整个系统

插件与 bridge 的角色是：

- 从网页端提取结构化数据
- 导入 `data/raw/`
- 继续复用现有 pipeline 下游阶段

而不是绕开 pipeline 单独产出最终报告。

---

## 当前支持的数据入口

当前 `collect` 阶段支持：

- `fixture`
- `codeforces`
- `browser_bridge`

### 1. fixture
用于：

- 本地演示
- 回归测试
- 结构验证

### 2. codeforces
用于：

- 动态实时抓取 Codeforces 比赛与榜单数据
- 支持通过 `handle` 或 `contest_ids` 驱动分析

### 3. browser_bridge
用于：

- 从浏览器插件导入网页端提取的结构化数据
- 适合与 Codeforces standings 页面联动

---

## Stage 概览

### Stage 1 — collect

负责从外部来源获取原始数据。

当前支持：

- fixture
- Codeforces API
- browser bridge 导入

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

### Stage 4 — build_history

负责围绕目标队伍组装历史比赛记录。

输出：

- `data/intermediate/team_history/<team>.json`

### Stage 5 — compute_metrics

负责计算排名趋势、题型能力分布、稳定性、波动性、成长性等指标。

这一层尽量保持确定性逻辑，不依赖 LLM。

输出：

- `data/derived/team_metrics/<team>.json`

### Stage 6 — analyze

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

### Stage 7 — report

负责把结构化结果和分析结论渲染为最终报告。

输出：

- `outputs/reports/<team>.md`
- `outputs/reports/<team>.html`

### Stage 8 — visualize

负责生成图表数据与单页可视化结果。

输出：

- `outputs/visualizations/<team>.json`
- `outputs/visualizations/<team>.html`

### Stage 9 — validate_final

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

```text
plugins/browser-extension
```

### 步骤 3：打开 Codeforces standings 页面

例如：

```text
https://codeforces.com/contest/1987/standings
```

### 步骤 4：在插件 popup 中填写

- `target_team`
- `aliases`

### 步骤 5：点击“发送并开始分析”

插件会自动：

1. 尝试从页面上下文调用 Codeforces standings API
2. 若失败则 fallback 到 DOM 提取
3. 调用本地 bridge `import-and-run`
4. bridge 自动导入 raw 数据并触发分析
5. 返回：
   - `run_id`
   - `status`
   - `report_path`
   - `validation_path`

### 详细说明

插件完整使用说明见：

- `docs/browser_bridge_usage.md`

---

## 方式三：task-file 模式

当前仍保留 `task-file` 模式，适合：

- 回归测试
- 示例复现
- 固定任务调试

例如：

```bash
python3 scripts/run_pipeline.py --task-file examples/codeforces_task.json
```

### 显式关闭 LLM

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --disable-llm-insight
```

### 指定模型或设置文件

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --llm-model gpt-5.4 \
  --llm-settings-path ~/.claude/settings.json
```

---

## 当前支持的主要参数

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

---

## 输出结果在哪里

### 中间产物

- `data/raw/`
- `data/normalized/`
- `data/intermediate/`
- `data/derived/`

### 最终结果

- `outputs/insights/`
- `outputs/reports/`
- `outputs/visualizations/`
- `outputs/validation/`
- `outputs/bridge_runs/`

### hooks 运行输出

- `.claude/hooks/outputs/run_logs/`
- `.claude/hooks/outputs/stage_logs/`
- `.claude/hooks/outputs/artifacts/`
- `.claude/hooks/outputs/bridge/`
- `.claude/hooks/outputs/validation/`

---

## `.claude` 相关能力

当前仓库的 `.claude/` 已经不仅是规划目录，而是包含了两层能力：

### 1. Claude 命令型 hooks

通过：

- `.claude/settings.json`

启用：

- `UserPromptSubmit`
- `PostToolUse`

当前会自动执行：

- `.claude/hooks/check-stage-output.py`
- `.claude/hooks/check-artifact-layout.py`
- `.claude/hooks/check-hooks-health.py`

### 2. 运行期 hooks 系统

通过：

- `.claude/hooks/hooks.json`
- `.claude/hooks/common/`
- `.claude/hooks/builtin/`

当前已覆盖：

- pipeline run 生命周期
- stage 生命周期
- artifact 写入
- bridge 导入 / 自动运行
- report / visualize / validation 最终交付

---

## 当前目录骨架

```text
acmer_analyze/
├── README.md
├── CLAUDE.md
├── docs/
│   ├── architecture.md
│   ├── project_structure.md
│   ├── runtime_flow.md
│   ├── stage_schema.md
│   ├── browser_bridge_usage.md
│   └── conventions/
├── scripts/
├── src/
├── plugins/
├── data/
├── outputs/
├── tests/
├── examples/
├── config/
└── .claude/
```

---

## 当前实现约束

当前实现依然保持“标准库优先”的最小风格：

- 主要使用 Python 标准库
- pipeline 编排尽量简单直接
- LLM 调用通过 HTTP 最小封装实现
- 默认测试不会依赖真实外网调用
- `.claude/settings.json` 已接入命令型 hooks，用于会话级状态检查与 hooks 健康检查
- `.claude/hooks/` 已接入运行期 hooks，用于审计 pipeline / artifact / bridge / 最终交付生命周期

因此，如果后续继续增强：

- 建议优先保持 artifact 协议稳定
- 再逐步增强 analyzer 的 prompt 与 provider 适配
- 再持续打磨插件真实页面提取的鲁棒性
- 避免把确定性计算逻辑重新塞回 LLM
