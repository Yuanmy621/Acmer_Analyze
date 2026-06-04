# Acmer Analyze

> 面向 ACM / 竞赛编程队伍的工程化分析流水线

`acmer_analyze` 不是一次性 prompt 驱动的黑盒工具，而是一条 **可编排、可追溯、可局部重跑** 的分析流水线。它围绕目标队伍，基于比赛排名、题目信息与历史参赛记录，自动生成结构化分析报告。

***

## 目录

- [核心能力](#核心能力)
- [快速开始](#快速开始)
- [安装指南](#安装指南)
- [使用方式](#使用方式)
- [项目结构](#项目结构)
- [Stage 概览](#stage-概览)
- [示例与代码片段](#示例与代码片段)
- [清理与局部重跑](#清理与局部重跑)
- [设计原则](#设计原则)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [联系信息与致谢](#联系信息与致谢)

***

## 核心能力

| 能力       | 说明                                    |
| -------- | ------------------------------------- |
| 排名变化分析   | 追踪队伍在多场比赛中的排名趋势                       |
| 题型能力分析   | 基于题目标签统计解题分布与通过率                      |
| 优势与短板总结  | 基于结构化指标生成高层洞察                         |
| 可视化报告    | 输出 Markdown / HTML 报告与图表页面            |
| 多数据源支持   | 支持 Codeforces 实时抓取、浏览器插件导入、本地 fixture |
| LLM 增强分析 | 可选接入 LLM 生成高层解释与训练建议                  |

***

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/acmer_analyze.git
cd acmer_analyze

# 2. 安装依赖（当前基于 Python 标准库，无额外依赖）
python3 --version  # 确认 Python 3.8+

# 3. 运行一次完整分析（以 Codeforces 用户 tourist 为例）
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --max-contests 5
```

运行完成后，产出文件位于：

- `outputs/reports/` — Markdown / HTML 报告
- `outputs/visualizations/` — 可视化图表
- `outputs/insights/` — 结构化洞察
- `outputs/validation/` — 验收结果

***

## 安装指南

### 环境要求

| 依赖       | 版本要求    | 说明                    |
| -------- | ------- | --------------------- |
| Python   | >= 3.8  | 运行时环境                 |
| requests | >= 2.28 | Codeforces API 抓取（可选） |

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/yourusername/acmer_analyze.git
cd acmer_analyze

# 安装依赖（如有 requirements.txt）
pip install -r requirements.txt
```

### LLM 配置（可选）

如需使用 LLM 增强分析能力，需配置以下环境变量：

```bash
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
export ANTHROPIC_AUTH_TOKEN="your-token-here"
export ANTHROPIC_MODEL="model-name"
```

也可将配置写入 `~/.claude/settings.json`，系统会自动读取。

> **说明**：LLM 配置缺失或调用失败时，analyze 阶段会直接报错，不会回退到本地规则模板。

***

## 使用方式

当前推荐使用优先级：

1. **动态 CLI + 实时抓取 Codeforces**（推荐主用）
2. **browser bridge + 插件导入网页数据**
3. **task-file / examples**（用于演示、回归、测试）

### 方式一：直接实时抓取 Codeforces

这是当前**最稳定、最直接**的使用方式。

#### 完整分析

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --max-contests 5
```

这条命令会自动执行完整的 9 阶段流水线：`collect` → `normalize` → `team_identity` → `build_history` → `compute_metrics` → `analyze` → `report` → `visualize` → `validate_final`。

#### 仅抓取并检查数据

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

#### 指定具体比赛

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --contest-ids 1987 2118
```

### 方式二：browser bridge + 插件链路

适合在网页端快速导入 standings 数据，交互式体验 browser bridge 工作流。

```bash
# 步骤 1：启动本地 bridge 服务
python3 scripts/run_bridge.py
# 默认监听 http://127.0.0.1:8765

# 步骤 2：在浏览器中加载插件
# 插件目录：plugins/browser-extension/

# 步骤 3：导入数据后执行分析
python3 scripts/run_pipeline.py \
  --source browser_bridge \
  --target-team tourist \
  --bridge-import-id <import_id> \
  --start-stage normalize
```

### 方式三：task-file / 示例任务

```bash
# 使用本地 fixture 示例
python3 scripts/run_pipeline.py --task-file examples/sample_task.json

# 使用真实 Codeforces 示例
python3 scripts/run_pipeline.py --task-file examples/codeforces_task.json
```

***

## 项目结构

```text
acmer_analyze/
├── README.md                  # 项目总览与使用指南
├── CLAUDE.md                  # Claude Code 协作入口与全局约束
├── docs/                      # 项目文档
│   ├── architecture.md        # 系统架构、分层设计、阶段边界
│   ├── stage_schema.md        # Stage 输入输出协议与字段约束
│   ├── project_structure.md   # 仓库目录结构与模块职责
│   ├── runtime_flow.md        # 一次任务的运行流与 artifact 流转
│   └── conventions/           # 协作规则文档
├── scripts/                   # 运行入口与辅助脚本
│   ├── run_pipeline.py        # 主 pipeline CLI 入口
│   ├── run_bridge.py          # 本地 browser bridge 服务入口
│   └── clear_artifacts.py     # 分析产物清理脚本
├── src/                       # 源代码
│   ├── orchestrator/          # 任务编排与 stage 调度
│   ├── collector/             # 外部平台数据采集
│   ├── bridge/                # 本地 HTTP bridge 服务
│   ├── normalize/             # 字段统一与 schema 归一化
│   ├── identity/              # 队伍身份识别与别名映射
│   ├── history/               # 历史比赛记录组装
│   ├── models/                # 领域模型与数据结构
│   ├── metrics/               # 确定性指标计算
│   ├── analyzer/              # 高层分析与 LLM 编排
│   ├── report/                # Markdown / HTML 报告生成
│   ├── visualize/             # 图表数据与可视化页面
│   └── validation/            # 最终产物验收
├── data/                      # 中间数据与阶段产物
│   ├── raw/                   # 原始抓取数据
│   ├── normalized/            # 标准化数据
│   ├── intermediate/          # 身份映射与历史组装
│   └── derived/               # 确定性指标结果
├── outputs/                   # 最终交付物
│   ├── insights/              # 结构化洞察
│   ├── reports/               # Markdown / HTML 报告
│   ├── visualizations/        # 图表与可视化页面
│   └── validation/            # 验收结果
├── tests/                     # 测试与回归
├── examples/                  # 示例任务与演示数据
├── plugins/                   # 浏览器插件
│   └── browser-extension/     # Codeforces standings 提取插件
└── config/                    # 配置文件
```

### 目录职责速查

| 目录          | 职责           |
| ----------- | ------------ |
| `src/`      | 所有实现代码，按模块拆分 |
| `scripts/`  | CLI 入口与辅助脚本  |
| `data/`     | 中间产物，按阶段分层   |
| `outputs/`  | 最终交付物，面向用户   |
| `docs/`     | 架构、协议、规则文档   |
| `tests/`    | 测试脚本与回归样本    |
| `examples/` | 示例任务与演示数据    |
| `plugins/`  | 浏览器插件等外部工具   |

***

## Stage 概览

流水线按以下 9 个阶段顺序执行：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   collect    │ ──→ │  normalize  │ ──→ │  team_identity   │
│  数据采集     │     │  字段归一化   │     │  队伍身份识别     │
└─────────────┘     └─────────────┘     └─────────────────┘
                                                │
                                                ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   analyze    │ ←── │  compute_   │ ←── │  build_history   │
│  高层分析     │     │  metrics    │     │  历史记录组装     │
└─────────────┘     │  指标计算     │     └─────────────────┘
       │            └─────────────┘
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   report     │ ──→ │  visualize  │ ──→ │  validate_final  │
│  报告生成     │     │  可视化      │     │  最终验收        │
└─────────────┘     └─────────────┘     └─────────────────┘
```

| 阶段                | 职责                         | 输出                                 |
| ----------------- | -------------------------- | ---------------------------------- |
| `collect`         | 从外部平台获取原始数据                | `data/raw/`                        |
| `normalize`       | 统一字段命名、时间格式、schema         | `data/normalized/`                 |
| `team_identity`   | 识别目标队伍，生成统一 `canonical_id` | `data/intermediate/team_identity/` |
| `build_history`   | 汇总目标队伍历史比赛记录               | `data/intermediate/team_history/`  |
| `compute_metrics` | 计算排名趋势、题型分布、稳定性等确定性指标      | `data/derived/team_metrics/`       |
| `analyze`         | 基于指标生成优势、短板、训练建议等高层洞察      | `outputs/insights/`                |
| `report`          | 渲染 Markdown / HTML 报告      | `outputs/reports/`                 |
| `visualize`       | 生成图表数据与可视化页面               | `outputs/visualizations/`          |
| `validate_final`  | 验收报告完整性与图表可用性              | `outputs/validation/`              |

***

## 示例与代码片段

### 示例 1：分析某支队伍的 Codeforces 表现

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team "ZJU Alpha" \
  --codeforces-handle zju_alpha \
  --max-contests 10
```

此命令会：

1. 从 Codeforces 抓取该用户最近 10 场比赛数据
2. 归一化字段并识别队伍身份
3. 构建历史记录并计算确定性指标
4. 调用 LLM 生成高层分析洞察
5. 输出 Markdown / HTML 报告与可视化图表

### 示例 2：仅运行数据采集与标准化

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --max-contests 5 \
  --end-stage normalize
```

适合先检查抓取数据质量，再决定是否继续下游分析。

### 示例 3：从 analyze 阶段重跑

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --start-stage analyze
```

当修改了 analyze prompt 或 LLM 配置后，无需重跑数据采集，直接从分析阶段开始。

### 输出示例

运行完成后，`outputs/reports/` 下会生成类似以下结构的报告：

```markdown
# ZJU Alpha 队伍分析报告

## 概览
- 分析比赛数：10
- 平均排名百分位：13.6%

## 排名趋势
近 10 场比赛排名整体呈上升趋势...

## 题型能力分布
- 图论：通过率 66.7%
- 动态规划：通过率 50.0%
...

## 优势与短板
**优势**：图论题稳定，中低难度题通过率高
**短板**：高难 DP 波动较大

## 训练建议
1. 增加高难 DP 训练
2. 加强后半程追分能力
```

***

## 清理与局部重跑

### 清理分析产物

```bash
# 按队伍清理（保留共享的 raw / normalized 文件）
python3 scripts/clear_artifacts.py --target-team "ZJU Alpha"

# 全量清理（保留目录结构）
python3 scripts/clear_artifacts.py --all

# 预览将删除的文件（不实际删除）
python3 scripts/clear_artifacts.py --target-team "ZJU Alpha" --dry-run

# 额外清理 bridge run 摘要
python3 scripts/clear_artifacts.py --target-team tourist --include-bridge-runs
```

### 局部重跑建议

| 场景                | 重跑范围                                                  |
| ----------------- | ----------------------------------------------------- |
| 抓取字段变化            | `collect` 及后续阶段                                       |
| 队伍别名识别有误          | `team_identity` 及下游阶段                                 |
| 指标口径调整            | `compute_metrics` 及下游阶段                               |
| analyze prompt 更新 | `analyze` / `report` / `visualize` / `validate_final` |

***

## 设计原则

### 1. pipeline 优先，而不是单次 prompt

项目不是"一次性把原始网页喂给模型然后直接出结论"的黑盒，而是按阶段拆开，每个阶段有明确的输入输出协议。

### 2. 确定性计算与自然语言解释分层

- `compute_metrics` 负责确定性指标计算（程序算清楚）
- `analyze` 负责高层解释与总结（模型说明白）
- LLM 只应增强解释层，不应替代底层数据清洗和指标统计

### 3. artifact 可追溯

每个阶段都把中间结果落盘，便于：

- 检查问题定位
- 局部重跑
- 回溯错误
- 替换具体实现而不破坏整体结构

### 4. 字段稳定性优先

以下字段是跨阶段关联的基础，不应轻易改变语义：

- `canonical_id` — 全流程主键
- `contest_id` — 比赛唯一标识
- `problem_id` — 题目唯一标识
- `team_raw_name` — 原始队伍名

***

## 贡献指南

我们欢迎各种形式的贡献，包括但不限于代码、文档、问题报告和功能建议。

### 如何贡献

1. **了解项目** — 阅读 `README.md` 和 `docs/` 下的文档，了解项目架构和设计原则
2. **找到机会** — 查看 [Issues](https://github.com/yourusername/acmer_analyze/issues) 找到可以解决的问题
3. **提交代码**
   - Fork 项目到你的 GitHub 账户
   - 创建特性分支：`git checkout -b feature/your-feature`
   - 在本地开发和测试
   - 提交 Pull Request

### 代码规范

- 代码与注释使用中文（代码标识符、字段名、协议名保留英文）
- 遵循项目既有的目录结构与模块边界
- 新增 Stage 实现时，先定义输入输出协议，再编写实现代码
- 变更关键字段时，同步更新 `docs/stage_schema.md`

### 提交 Issue

- 使用明确、具体的标题描述问题
- 提供重现步骤、预期行为和实际行为
- 如可能，附加相关日志或截图

### 提交 Pull Request

- 清晰描述更改的目的和必要性
- 确保通过现有测试：`python3 -m unittest discover -s tests -p 'test_*.py'`
- 如涉及协议变更，同步更新相关文档

***

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

你可以自由地使用、修改和分发本项目的代码，但需保留原始许可证和版权声明。详见 [LICENSE](LICENSE) 文件。

***

## 联系信息与致谢

### 联系方式

如有问题或建议，欢迎通过以下方式联系：

- **QQ-email**：[2481069080@qq.com](https://github.com/yourusername/acmer_analyze/issues)

### 致谢

感谢所有为本项目做出贡献的开发者和社区成员。

本项目的分析能力受益于以下数据源：

- [Codeforces](https://codeforces.com/) — 竞赛编程平台

### 社区

我们欢迎每一个人的参与和贡献，无论你的技能水平如何，都有Acmer的一席之地。

***

## 相关文档

| 文档                                   | 说明                    |
| ------------------------------------ | --------------------- |
| [架构说明](docs/architecture.md)         | 系统架构、分层设计、阶段边界        |
| [Stage Schema](docs/stage_schema.md) | Stage 输入输出协议与字段约束     |
| [项目结构](docs/project_structure.md)    | 仓库目录结构与模块职责           |
| [运行流](docs/runtime_flow.md)          | 一次任务的运行流与 artifact 流转 |
| [协作规则](docs/conventions/)            | 语言、命名、文档等协作规范         |

