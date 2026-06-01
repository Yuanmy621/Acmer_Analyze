# 系统架构说明

---

## 1. 架构目标

`acmer_analyze` 的目标不是构造一个单次 prompt 驱动的分析器，而是建立一条面向队伍分析任务的工程化流水线。

这条流水线需要满足以下要求：

- **可编排**：能够按固定阶段顺序执行
- **可追溯**：任意结论都能回查到上游数据与中间结果
- **可校验**：最终交付物能够独立验收
- **可局部重跑**：某个阶段修复后，只重跑下游相关阶段
- **可扩展**：未来可以新增平台、指标、可视化方式而不破坏主干流程

---

## 2. 总体架构视图

系统推荐采用以下总体结构：

```text
Contest Sources
    ↓
Collector Layer
    ↓
Normalization Layer
    ↓
Identity Resolution Layer
    ↓
History Assembly Layer
    ↓
Metrics Layer
    ↓
Analysis Layer
    ↓
Delivery Layer
    ↓
Validation Layer
```

如果映射到实际执行链路，则对应为：

```text
Stage 0  collect
Stage 1  normalize
Stage 2  team_identity
Stage 3  build_history
Stage 4  compute_metrics
Stage 5  analyze
Stage 6  report
Stage 7  visualize
Stage 8  validate_final
```

这两个视角分别对应：

- **分层视角**：强调职责边界
- **阶段视角**：强调执行顺序

---

## 3. 分层设计

### 3.1 数据准备层

包含：

- `collect`
- `normalize`
- `team_identity`
- `build_history`

职责：

- 从外部平台获取比赛数据
- 将不同来源统一为标准结构
- 确认目标队伍身份
- 构建后续分析所需的历史记录

这一层的核心目标不是输出结论，而是产出 **可信、稳定、可复查** 的标准化输入。

### 3.2 分析推理层

包含：

- `compute_metrics`
- `analyze`

职责：

- 基于历史记录计算确定性指标
- 基于结构化指标生成高层分析结论

这一层应严格区分：

- **程序负责算清楚**
- **模型负责说明白**

也就是说，排名趋势、标签分布、稳定性、成长性等应优先由代码计算；AI 分析建立在这些结果之上，而不是绕开它们直接从原始数据自由生成结论。

### 3.3 交付展示层

包含：

- `report`
- `visualize`
- `validate_final`

职责：

- 把结构化结果与分析结论渲染成报告
- 生成可展示的图表和页面
- 对最终产物做完整性与可用性校验

这一层的重点不是“重新分析”，而是“稳定交付”。

---

## 4. 阶段职责边界

### Stage 0 — collect

负责从外部竞赛平台获取原始数据，包括：

- contest 元数据
- standings / ranking
- problem 元数据
- 队伍原始参赛记录

特点：

- 尽量保留源站语义
- 不在本阶段做复杂映射
- 原始结果应完整落盘

### Stage 1 — normalize

负责将不同平台的数据归一化为统一结构，包括：

- 字段命名统一
- 时间格式统一
- standings / problem schema 统一
- 异常记录基础清洗

特点：

- 保留关键 join key
- 保留 `team_raw_name`
- 为下游建立稳定协议

### Stage 2 — team_identity

负责识别目标队伍在不同比赛与平台中的名称变体，输出统一身份映射。

特点：

- 形成稳定的 `canonical_id`
- 记录别名、平台 ID、展示名等信息
- 对有歧义的映射，应保留依据并支持人工确认

### Stage 3 — build_history

负责围绕 `canonical_id` 汇总目标队伍的历史比赛记录。

特点：

- 输出单队统一历史视图
- 建立比赛级与题目级分析基础
- 为指标计算准备稳定输入

### Stage 4 — compute_metrics

负责计算确定性指标，例如：

- 排名趋势
- 题型能力分布
- 稳定性 / 波动性
- 成长性
- 解题节奏

特点：

- 逻辑尽量可复现
- 同样输入应得到相同输出
- 对缺失题目标签等情况应有降级策略

### Stage 5 — analyze

负责把结构化指标转换为高层分析结论，例如：

- 优势与短板
- 阶段表现总结
- 训练建议
- 风格判断

特点：

- 必须建立在 metrics 之上
- 适合引入 LLM，但不应让 LLM 直接替代统计分析

### Stage 6 — report

负责渲染最终报告，建议支持：

- Markdown
- HTML

特点：

- 结构稳定
- 可阅读
- 可以从报告反查对应结构化结论

### Stage 7 — visualize

负责生成图表数据和可视化页面，典型内容包括：

- 排名趋势图
- 题型分布图
- 时间轴
- 雷达图

特点：

- 图表数据应直接来源于 metrics
- 不应从自然语言总结反推图表

### Stage 8 — validate_final

负责对最终交付物做验收，包括：

- 报告 section 完整性
- 图表数据完整性
- 关键字段缺失检查
- 最终页面可展示性检查

特点：

- 只做验收
- 不新增业务结论

---

## 5. Orchestrator 的角色

Orchestrator 是整条流水线的统一执行入口。

它应至少承担以下职责：

- 接收分析任务参数
- 决定从哪个阶段开始运行
- 调度各个 stage 的执行顺序
- 管理 artifact 路径与任务上下文
- 记录每次运行的输入、输出与状态
- 在失败时支持中断定位与下游重跑

从系统设计角度看，Orchestrator 不应该承载具体业务分析逻辑；它更像是：

> 任务运行控制器 + artifact 路径协调器 + stage 生命周期管理器。

---

## 6. Artifact Store 的必要性

本项目推荐所有关键阶段都把中间结果落盘，而不是只在内存中传递。

这样做有几个直接好处：

1. **方便调试**
   - 可以快速定位错误发生在哪一层

2. **方便人工复核**
   - 可以直接检查原始 standings、身份映射、metrics 结果是否合理

3. **方便局部重跑**
   - 上游结果不变时，下游可以直接复用已有 artifact

4. **方便回归验证**
   - 后续修改算法时，可以拿历史 artifact 做比对

推荐的 artifact 分层：

- `data/raw/`：原始抓取数据
- `data/normalized/`：标准化数据
- `data/intermediate/`：身份映射与历史组装结果
- `data/derived/`：确定性指标结果
- `outputs/`：最终洞察、报告、可视化、验收结果

---

## 7. 推荐目录结构

当前仓库尚未实现代码，但建议后续围绕以下结构组织：

```text
acmer_analyze/
├── README.md
├── CLAUDE.md
├── scripts/
├── src/
│   ├── collector/
│   ├── normalize/
│   ├── identity/
│   ├── models/
│   ├── metrics/
│   ├── analyzer/
│   ├── report/
│   └── visualize/
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
└── docs/
```

这里更重要的是职责边界，而不是目录名称本身。

---

## 8. 推荐运行方式

一个典型分析任务的执行过程建议如下：

1. 指定目标队伍与分析范围
2. 运行 `collect`
3. 运行 `normalize`
4. 运行 `team_identity`
5. 运行 `build_history`
6. 运行 `compute_metrics`
7. 运行 `analyze`
8. 运行 `report`
9. 运行 `visualize`
10. 运行 `validate_final`

如果其中某个阶段发现问题，则应允许只从该阶段重新开始，而不是整条链全部重跑。

这也是本项目区别于一次性 prompt 应用的关键：

> 它是一个可执行、可检查、可重跑的分析系统，而不是一个只返回文本的聊天式工具。

---

## 9. 与 Schema 文档的关系

本文用于说明整体架构和阶段职责。

更细的 Stage 输入输出协议、关键字段、主键约束与 artifact contract，统一维护在：

- `docs/stage_schema.md`

建议文档分工保持如下：

- `README.md`：项目总览、整体定位、使用方式
- `docs/architecture.md`：系统架构、分层设计、阶段边界
- `docs/stage_schema.md`：Stage 间协议与字段约束

这样可以避免不同文档承载重复信息，降低后续维护时的漂移风险。

---

## 10. 后续演进方向

随着项目实现推进，本文可以持续补充：

- 实际采用的运行入口
- stage 模块的真实落地路径
- artifact 命名规范
- 支持的数据源清单
- 报告渲染方式
- 可视化技术方案
- 验收与回归策略

但建议继续保持本文的角色不变：

- 说明整体系统如何组织
- 说明模块之间如何协作
- 说明为什么要这样分层与拆阶段

而不是把它演变成逐行实现说明或命令大全。