# 项目文件结构说明

本文用于说明 `acmer_analyze` 的仓库目录结构、各目录职责与后续扩展边界。

如果 `README.md` 负责项目总览，`docs/architecture.md` 负责系统架构，那么本文负责回答：

- 当前仓库有哪些目录
- 每个目录应承担什么职责
- 后续新增文件应优先放在哪里
- 如何避免把不同类型内容混在一起

---

## 1. 设计原则

目录结构应尽量反映系统分层，而不是只按文件类型随意堆放。

当前建议遵循以下原则：

- 文档与实现分开
- 原始数据与衍生数据分开
- 中间结果与最终输出分开
- 编排逻辑与阶段实现分开
- 规则文档与项目说明文档分开

---

## 2. 当前推荐目录结构

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
│       ├── README.md
│       ├── language.md
│       ├── documentation.md
│       ├── structure.md
│       ├── stage_rules.md
│       ├── artifact_rules.md
│       ├── report_rules.md
│       └── validation_rules.md
├── scripts/
├── src/
│   ├── orchestrator/
│   ├── collector/
│   ├── normalize/
│   ├── identity/
│   ├── history/
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

---

## 3. 顶层文件说明

### `README.md`

用于：

- 项目简介
- 整体框架介绍
- 使用方案总览
- 文档导航

不用于承载全部细节规则。

### `CLAUDE.md`

用于：

- Claude Code 协作入口
- 全局约束摘要
- 文档调用路由

不用于长期承载所有细则。

---

## 4. docs 目录说明

### `docs/architecture.md`

系统架构说明文档，主要描述：

- 分层设计
- Stage 职责边界
- Orchestrator 角色
- Artifact Store 设计意图

### `docs/stage_schema.md`

Stage 协议文档，主要描述：

- 核心实体
- Stage 输入输出
- 关键字段稳定性
- artifact contract

### `docs/project_structure.md`

即本文，主要描述：

- 仓库目录结构
- 各目录职责
- 文件落点建议

### `docs/runtime_flow.md`

运行流文档，主要描述：

- 一次分析任务的执行路径
- artifact 如何流转
- 局部重跑依赖关系

### `docs/conventions/`

规则文档目录。

用于按主题拆分协作规则，避免把全部规则堆在 `CLAUDE.md` 或 `README.md` 中。

---

## 5. src 目录说明

`src/` 用于放后续实现代码。

当前推荐模块与职责如下：

### `src/orchestrator/`

负责：

- 分析任务编排
- stage 调度
- 运行上下文管理
- artifact 路径协调

### `src/collector/`

负责：

- 外部平台数据采集
- standings / contest / problem 抓取
- 原始数据写入
- 当前已落地：
  - `fixture_collector.py`：本地 fixture 采集
  - `codeforces_client.py`：Codeforces API 访问封装
  - `codeforces_collector.py`：真实 Codeforces 数据抓取
  - `bridge_collector.py`：browser bridge 导入结果校验与接入
  - `dispatcher.py`：按 source 分派 collect 实现

### `src/bridge/`

负责：

- 本地 HTTP bridge 服务
- 浏览器插件导入 payload 校验
- bridge 导入 metadata 落盘
- bridge 触发 pipeline 执行
- bridge 运行状态摘要输出
- 当前已落地：
  - `payloads.py`：bridge 协议校验
  - `handlers.py`：raw artifact、metadata 与 bridge run summary 写入
  - `server.py`：本地 HTTP 服务、导入与状态查询接口

### `src/normalize/`

负责：

- 字段统一
- 时间统一
- schema 归一化
- 异常记录基础清洗

### `src/identity/`

负责：

- 队伍身份识别
- 别名映射
- 平台 ID 归并
- 统一 `canonical_id`

### `src/models/`

负责：

- 领域模型定义
- schema 对应数据结构
- 共享类型与对象模型

### `src/metrics/`

负责：

- 排名趋势计算
- 标签/题型统计
- 稳定性、成长性、节奏等确定性指标

### `src/analyzer/`

负责：

- 基于 metrics 生成高层分析
- AI 分析编排
- 洞察结果组织
- 当前已落地 `insight_generator.py`，用于规则式洞察生成

### `src/report/`

负责：

- Markdown / HTML 报告生成
- section 渲染
- 展示型文本组织
- 当前已落地 `markdown_report.py`，用于生成 Markdown 报告与 report artifact

### `src/visualize/`

负责：

- 图表数据准备
- 可视化结果渲染
- 页面化输出
- 当前已落地 `chart_data.py`，用于输出图表 JSON 与 visualization artifact

### `src/validation/`

负责：

- 最终产物验收
- 完整性检查
- 质量校验
- 当前已落地 `validator.py`，用于输出 validation 结果

### `src/history/`

负责：

- 目标队伍历史比赛记录组装
- `TeamHistory` 构建
- 当前已落地 `builder.py`，用于从 identity 与 standings 生成队伍历史

---

## 6. scripts 目录说明

`scripts/` 用于放后续运行入口和辅助脚本，例如：

- CLI 入口
- 单阶段运行脚本
- 本地调试脚本
- 数据修复脚本
- 回归检查脚本

当前已提供：

- `scripts/run_pipeline.py`：最小可运行 orchestrator CLI，支持 task-file 与动态参数模式
- `scripts/run_bridge.py`：本地 browser bridge HTTP 服务入口
- `examples/sample_task.json`：本地 fixture 示例任务
- `examples/codeforces_task.json`：真实 Codeforces 抓取示例任务
- `examples/bridge_payload.json`：browser bridge 导入协议示例

当前阶段可先保持轻量。

---

## 7. data 目录说明

`data/` 用于保存中间数据与阶段产物。

### `data/raw/`

保存原始抓取数据。

建议继续细分：

- `contests/`
- `standings/`
- `problems/`

### `data/normalized/`

保存归一化后的标准数据。

建议继续细分：

- `contests/`
- `standings/`
- `problems/`

### `data/intermediate/`

保存中间组装结果。

建议继续细分：

- `team_identity/`
- `team_history/`

### `data/derived/`

保存确定性衍生指标。

建议继续细分：

- `team_metrics/`

---

## 8. outputs 目录说明

`outputs/` 用于保存最终或面向交付的分析结果。

建议细分为：

- `insights/`
- `reports/`
- `visualizations/`
- `validation/`

这部分内容应与 `data/` 中的中间产物区分开。

---

## 9. tests 目录说明

`tests/` 用于保存测试与回归相关内容。

### `tests/fixtures/`

用于保存：

- 示例输入
- mock 数据
- 小规模样本 artifact

### `tests/regression/`

用于保存：

- 回归样本
- 历史输出基准
- 校验结果样本

---

## 10. examples 与 config 目录说明

### `examples/`

用于保存：

- 示例任务输入
- 示例报告
- 示例可视化结果
- 演示型样本

### `config/`

用于保存后续配置，例如：

- 数据源配置
- 任务配置
- 身份映射配置
- 报告模板配置

### `./.claude/`

用于保存 Claude 协作相关配置、hooks、plans 与本地检查脚本。

当前已包括：

- `settings.json`：项目级 Claude hooks 配置
- `settings.local.json`：本地权限与个性化补充
- `hooks/`：运行期 hook 系统与命令型检查脚本
- `plans/`：规划文件

---

## 11. 文件落点建议

后续新增内容时，可优先按如下方式判断放置位置：

- 项目介绍类内容 → `README.md`
- 架构说明类内容 → `docs/architecture.md`
- 结构与目录说明 → `docs/project_structure.md`
- 协议与字段定义 → `docs/stage_schema.md`
- 规则类内容 → `docs/conventions/`
- 实现代码 → `src/`
- 运行入口与脚本 → `scripts/`
- 原始/中间/衍生数据 → `data/`
- 交付物 → `outputs/`
- 测试样本与回归样本 → `tests/`
- 示例与演示内容 → `examples/`
- 配置文件 → `config/`

---

## 12. 后续演进建议

随着代码逐步落地，本文应继续补充：

- 实际入口文件位置
- 各目录真实模块边界
- 文件命名规范
- 目录下保留文件的约定
- 哪些产物应入库，哪些不应入库

但本文应继续保持“结构说明文档”的角色，而不是演变为实现细节总表。
