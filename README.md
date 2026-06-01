# ACM 队伍分析 Agent

`acmer_analyze` 是一个面向 **ACM / 竞赛编程队伍分析** 的 Agent 项目。

项目围绕 **竞赛数据采集 → 队伍历史归档 → 指标计算 → 分析解读 → 报告与可视化输出** 构建，目标是把“分析一支队伍的长期表现”做成一条 **可编排、可校验、可追溯、可局部重跑** 的工程化流水线。

它不是一个把比赛结果一次性丢给模型、直接生成点评的黑盒工具，而是一个强调 **阶段拆分、结构化中间产物、确定性指标计算、最终可交付分析结果** 的分析框架。

当前仓库已经建立了：

- 项目总览文档
- 架构与协议文档
- 分类规则文档
- 面向后续实现的目录骨架

后续开发将基于这套骨架逐步补齐实际代码与运行能力。

---

## 项目定位

本项目用于分析 ACM / 竞赛编程队伍在一段时间内的历史表现，并产出结构化、可解释、可展示的分析结果。

围绕一支目标队伍，系统希望能够输出：

- 排名变化趋势
- 技能树 / 题型能力分布
- 优势与短板总结
- 阶段性表现复盘
- 可视化分析报告

当前文档中明确提到的竞赛数据源包括：

- Codeforces
- UCUP

随着后续开发推进，项目可以继续扩展到更多平台，但整体框架保持不变：

> 先采集数据，再标准化，再识别队伍，再计算指标，最后生成分析与交付结果。

---

## 当前项目状态

当前仓库已经具备以下内容：

- `README.md`、`CLAUDE.md` 两个主入口文档
- `docs/` 下的架构、协议、结构、运行流文档
- `docs/conventions/` 下的分类规则骨架
- `src/`、`scripts/`、`data/`、`outputs/`、`tests/`、`examples/`、`config/` 等目录骨架
- 各主要模块与目录的职责说明文件

当前仓库尚未具备的内容包括：

- 实际可运行的数据采集、分析、报告生成代码
- 固定的 build / lint / test / run 工作流
- 已落地的 orchestrator 入口与阶段执行命令

因此，当前项目应理解为：

> 已完成文档分层与结构骨架搭建，但尚处于实现前或实现早期阶段。

---

## 为什么采用 harness / pipeline

这个项目更适合做成多阶段流水线，而不是一次性生成，主要原因包括：

1. **外部数据源不稳定**
   - 比赛站点抓取方式可能变化
   - 字段格式可能不统一
   - 队伍名称映射可能存在歧义

2. **分析过程依赖中间结果**
   - 必须先有原始比赛与排名数据
   - 再做归一化与身份识别
   - 最后才能得到可信的趋势与能力分析

3. **AI 更适合做解释，而不是吞掉全部逻辑**
   - 排名变化、过题统计、标签聚合等应优先由程序确定性计算
   - LLM 更适合在后续负责总结、解释和报告表达

4. **最终结果需要验收**
   - 输出不只是自然语言
   - 还可能包括 JSON、图表数据、HTML 页面等交付物

5. **需要支持局部重跑**
   - 某个阶段出问题时，应只重跑相关阶段，而不是整条链全部重做

因此，本项目推荐采用：

**Orchestrator + Staged Pipeline + Validation + Artifact Store**

---

## 核心设计思想

### 1. Orchestrator 统一编排

建议由一个统一入口负责调度整个流程，保证：

- 各阶段执行顺序清晰
- 输入输出路径一致
- 支持从任意阶段开始重跑
- 方便记录一次分析任务的上下文

在这个项目里，Orchestrator 可以理解为：

> “针对某个队伍、某个时间范围的一次分析任务运行器”。

### 2. 每个阶段只做一件事

推荐把采集、清洗、建模、指标计算、AI 解读、报表生成、可视化、验收拆开，避免出现：

- 抓取逻辑和分析逻辑耦合
- 统计逻辑和自然语言生成耦合
- 报告层依赖未经验证的原始数据

### 3. 中间结果必须落盘

中间产物建议写入 `data/` 或 `outputs/`，这样可以：

- 定位问题发生在哪个阶段
- 检查原始数据是否可信
- 对分析中间结果做人工复核
- 支持局部重跑和回归验证

### 4. 校验独立于生成

生成阶段负责“产出”，校验阶段负责“验收”。

例如：

- 抓取阶段只负责拉数据
- 归一化阶段只负责统一字段
- 分析阶段只负责形成指标与结论
- 最终校验阶段负责检查报告是否完整、图表是否可渲染、关键字段是否缺失

这样可以避免“自己生成、自己证明自己没问题”的伪闭环。

---

## 整体架构

推荐把整个系统理解为一条分阶段的 harness：

```text
Contest Sources
    ↓
Stage 0  collect
    ↓
Stage 1  normalize
    ↓
Stage 2  team_identity
    ↓
Stage 3  build_history
    ↓
Stage 4  compute_metrics
    ↓
Stage 5  analyze
    ↓
Stage 6  report
    ↓
Stage 7  visualize
    ↓
Stage 8  validate_final
```

进一步看，这条链路可以抽象为三层：

### 数据准备层

- `collect`
- `normalize`
- `team_identity`
- `build_history`

职责是把外部比赛数据整理成可用于单队分析的标准化历史记录。

### 分析推理层

- `compute_metrics`
- `analyze`

职责是从队伍历史中提取趋势、能力画像、题型分布、稳定性与优劣势结论。

### 交付展示层

- `report`
- `visualize`
- `validate_final`

职责是把分析结果输出成可阅读、可展示、可验收的最终产物。

---

## 阶段说明

### Stage 0 — collect

负责拉取比赛、排名、题目信息，以及队伍原始参赛记录。

建议输出：

- `data/raw/contests/*.json`
- `data/raw/standings/*.json`
- `data/raw/problems/*.json`

### Stage 1 — normalize

负责统一时间格式、字段命名，并对不同平台的 standings / problem schema 做归一化。

建议输出：

- `data/normalized/contests/*.json`
- `data/normalized/standings/*.json`
- `data/normalized/problems/*.json`

### Stage 2 — team_identity

负责识别目标队伍在不同平台或不同比赛中的名称变体，建立统一身份映射。

建议输出：

- `data/intermediate/team_identity/<team>.json`

### Stage 3 — build_history

负责为目标队伍汇总历次比赛记录，形成后续分析所需的统一历史视图。

建议输出：

- `data/intermediate/team_history/<team>.json`

### Stage 4 — compute_metrics

负责计算排名趋势、题型能力分布、稳定性、波动性、成长性等指标。

这一层应尽量保持为确定性逻辑，不依赖 LLM。

建议输出：

- `data/derived/team_metrics/<team>.json`

### Stage 5 — analyze

负责基于结构化指标生成高层分析结论，如优势、短板、训练建议、阶段性判断。

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
│   ├── raw/
│   ├── normalized/
│   ├── intermediate/
│   └── derived/
├── outputs/
│   ├── insights/
│   ├── reports/
│   ├── visualizations/
│   └── validation/
├── tests/
│   ├── fixtures/
│   └── regression/
├── examples/
└── config/
```

这里最重要的不是目录名字本身，而是以下边界保持清晰：

- 原始数据和衍生数据分开
- 中间数据和最终输出分开
- 指标计算和自然语言生成分开
- 编排器和具体 stage 分开
- 项目说明、架构说明、协议说明、规则说明分开

更细的目录职责说明见：

- `docs/project_structure.md`

---

## Schema 文档

为了让 harness 真正可编排、可重跑，建议优先固定 Stage 间的数据协议。

当前推荐的 schema 设计已整理在：

- `docs/stage_schema.md`

其中最关键的约束包括：

- `canonical_id` 是 Stage 2 之后贯穿全流程的主键
- `contest_id` / `problem_id` 是跨 artifact 的核心关联键
- `team_raw_name` 必须在采集与归一化阶段保留下来，用于身份映射
- 指标计算应优先依赖结构化字段，而不是依赖 LLM 从原始数据自由解释

建议未来实现时，把 schema 视为 stage 之间的稳定协议；任何字段变更都应同步更新文档与代码模型。

当前阶段可以先把 `docs/stage_schema.md` 视为后续代码模型与 artifact 组织的主参考文档。

---

## 一个合理的端到端数据流

基于当前已建立的文档与目录骨架，后续实现时可以按以下顺序组织：

1. 拉取比赛与队伍原始数据
2. 归一化 contest / standing / problem schema
3. 识别并确认目标队伍身份
4. 汇总目标队伍的历史参赛记录
5. 计算趋势与题型能力指标
6. 将指标送入 AI 分析或模板总结
7. 生成最终可视化报告
8. 对最终产物做验收校验

这条数据流比“边爬边分析”更容易测试，也更方便复用中间结果。

更细的运行顺序、artifact 流转方式与局部重跑说明见：

- `docs/runtime_flow.md`

---

## 文档演进方式

这份 README 在项目中的定位，是一份持续演进的总览文档。

当前仓库已经形成了“总览文档 + 架构文档 + 协议文档 + 规则文档 + 目录骨架说明”的基本分层。

后续开发过程中，应不断补充和更新以下内容：

- 新增的数据源范围
- 更清晰的阶段职责边界
- 实际落地后的目录与入口命令
- 已确认的 artifact 路径规范
- 已落地的报告格式与可视化方式
- 验收策略与回归样本说明

但 README 仍应尽量保持在：

- 项目框架介绍
- 系统架构说明
- 使用方案总览
- 文档导航说明

更细粒度的信息建议拆分维护，例如：

- schema 协议放在 `docs/stage_schema.md`
- 目录结构说明放在 `docs/project_structure.md`
- 运行流说明放在 `docs/runtime_flow.md`
- 分类规则放在 `docs/conventions/`
- 具体命令与运行方式放在后续实现文档中
- 示例 artifact 放在 `docs/`、`examples/` 或测试样本目录中

这样可以避免 README 同时承担概念说明和全部实现细节，最终变得过重且难以维护。

---

## 相关文档

- `docs/architecture.md`：系统架构、分层边界与阶段职责
- `docs/project_structure.md`：仓库目录结构、模块职责与文件落点说明
- `docs/runtime_flow.md`：一次分析任务的运行流、artifact 流转与局部重跑说明
- `docs/stage_schema.md`：Stage 间输入输出协议与字段约束
- `docs/conventions/README.md`：分类规则文档导航
- `docs/conventions/naming.md`：命名规则（文档、目录、模块、字段、artifact）
- `CLAUDE.md`：协作入口、全局约束摘要与文档调用路由

如果你是第一次进入这个仓库，建议优先阅读顺序为：

1. `README.md`
2. `docs/architecture.md`
3. `docs/project_structure.md`
4. `docs/runtime_flow.md`
5. `docs/stage_schema.md`
6. `CLAUDE.md`
