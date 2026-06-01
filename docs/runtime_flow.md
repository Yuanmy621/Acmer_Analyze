# 运行流程说明

本文用于说明 `acmer_analyze` 一次分析任务从输入到输出的整体运行流程，以及中间 artifact 如何流转、如何局部重跑。

如果 `docs/architecture.md` 回答的是“系统如何分层”，那么本文回答的是：

- 一次分析任务会经过哪些步骤
- 每一步产出什么结果
- 上下游之间如何衔接
- 当某个阶段出问题时，应该如何重跑

---

## 1. 一次分析任务的基本输入

一个分析任务通常至少包含以下信息：

- 目标队伍标识
  - 队名
  - 别名
  - 平台 ID
- 数据源范围
  - Codeforces
  - UCUP
  - 后续更多平台
- 时间范围或比赛集合
- 可选运行参数
  - 是否生成可视化
  - 是否生成 AI 总结
  - 是否跳过某些阶段

这些输入由 Orchestrator 接收，并转化为一次可执行的分析任务。

---

## 2. 标准执行路径

推荐的一次完整执行路径如下：

```text
输入任务参数
  ↓
collect
  ↓
normalize
  ↓
team_identity
  ↓
build_history
  ↓
compute_metrics
  ↓
analyze
  ↓
report
  ↓
visualize
  ↓
validate_final
  ↓
最终交付结果
```

这条路径既是运行顺序，也是 artifact 逐步收敛的过程。

---

## 3. 各阶段运行流

### 3.1 collect

输入：

- 目标队伍标识
- 数据源
- 时间范围

处理：

- 获取比赛元数据
- 获取 standings / ranking
- 获取题目信息
- 保留原始来源语义

输出：

- `data/raw/contests/*.json`
- `data/raw/standings/*.json`
- `data/raw/problems/*.json`

### 3.2 normalize

输入：

- 原始 contest / standing / problem 数据

处理：

- 统一字段命名
- 统一时间格式
- 统一 schema
- 做基础清洗

输出：

- `data/normalized/contests/*.json`
- `data/normalized/standings/*.json`
- `data/normalized/problems/*.json`

### 3.3 team_identity

输入：

- 标准化 standings
- 用户给定目标队伍标识

处理：

- 识别队伍别名
- 建立平台 ID 映射
- 确定统一 `canonical_id`

输出：

- `data/intermediate/team_identity/<team>.json`

### 3.4 build_history

输入：

- `TeamIdentity`
- 标准化 contest / standing / problem 数据

处理：

- 汇总目标队伍历次比赛记录
- 建立比赛级和题目级统一视图

输出：

- `data/intermediate/team_history/<team>.json`

### 3.5 compute_metrics

输入：

- `TeamHistory`
- 题目标签或补充元数据

处理：

- 计算排名趋势
- 计算题型/标签分布
- 计算稳定性、成长性、解题节奏等指标

输出：

- `data/derived/team_metrics/<team>.json`

### 3.6 analyze

输入：

- `TeamMetrics`
- 可选 `TeamHistory`

处理：

- 组织优势、短板、阶段表现总结
- 根据需要调用 LLM 做解释和归纳

输出：

- `outputs/insights/<team>.json`

### 3.7 report

输入：

- `TeamMetrics`
- `TeamInsight`

处理：

- 生成 Markdown / HTML 报告
- 渲染固定 section

输出：

- `outputs/reports/<team>.md`
- `outputs/reports/<team>.html`

### 3.8 visualize

输入：

- `TeamMetrics`
- `TeamInsight`

处理：

- 生成图表数据
- 生成可视化页面

输出：

- `outputs/visualizations/<team>.json`
- `outputs/visualizations/<team>.html`

### 3.9 validate_final

输入：

- `TeamInsight`
- 报告 artifact
- 可视化 artifact

处理：

- 检查完整性
- 检查缺失字段
- 检查交付物可用性

输出：

- `outputs/validation/<team>.json`

---

## 4. artifact 流转关系

推荐把 artifact 理解为以下几层：

### 原始层

- `data/raw/`

作用：

- 保留平台抓取原貌
- 支持回溯抓取问题

### 标准化层

- `data/normalized/`

作用：

- 为下游 stage 提供统一协议输入

### 中间组装层

- `data/intermediate/`

作用：

- 表达队伍身份与历史汇总结果

### 指标层

- `data/derived/`

作用：

- 表达确定性分析结果

### 交付层

- `outputs/`

作用：

- 表达洞察、报告、图表、验收结果

---

## 5. 局部重跑原则

本项目不推荐每次都从头执行整条链路。

当某个阶段出问题时，应优先判断能否从该阶段重跑。

### 场景 1：抓取字段变化

影响：

- `collect`
- 下游所有阶段

处理建议：

- 从 `collect` 重新开始

### 场景 2：归一化规则调整

影响：

- `normalize`
- 下游所有阶段

处理建议：

- 保留原始数据
- 从 `normalize` 重新开始

### 场景 3：身份映射修正

影响：

- `team_identity`
- `build_history`
- 下游分析与交付

处理建议：

- 从 `team_identity` 重新开始

### 场景 4：指标计算逻辑调整

影响：

- `compute_metrics`
- `analyze`
- `report`
- `visualize`
- `validate_final`

处理建议：

- 从 `compute_metrics` 重新开始

### 场景 5：报告模板调整

影响：

- `report`
- 可能影响 `validate_final`

处理建议：

- 从 `report` 重新开始

### 场景 6：可视化样式或图表规则调整

影响：

- `visualize`
- `validate_final`

处理建议：

- 从 `visualize` 重新开始

### 场景 7：验收规则调整

影响：

- `validate_final`

处理建议：

- 只重跑 `validate_final`

---

## 6. Orchestrator 在运行流中的角色

Orchestrator 应至少负责：

- 接收任务参数
- 确定运行起点
- 组织阶段执行顺序
- 读取与写入 artifact 路径
- 记录每次运行状态
- 处理失败后的重跑入口

它本身更偏向“运行控制器”，而不是承载具体业务逻辑。

---

## 7. 后续实现建议

当后续开始写代码时，建议优先实现以下能力：

1. 可指定目标队伍与时间范围
2. 可单独运行 `collect`
3. 可单独运行 `normalize`
4. 可从某个阶段继续往后执行
5. 可把中间结果稳定落盘
6. 可基于 artifact 进行简单回归检查

这样更符合本项目“可编排、可重跑、可追溯”的定位。

---

## 8. 与其他文档的关系

- `README.md`：说明项目是什么、怎么理解整体方案
- `docs/architecture.md`：说明系统怎么分层
- `docs/stage_schema.md`：说明每个阶段的数据协议
- `docs/project_structure.md`：说明文件和目录如何组织

本文则专门说明：

> 一次分析任务实际上是如何流动起来的。
