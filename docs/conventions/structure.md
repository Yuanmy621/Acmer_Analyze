# 目录结构规则

本文用于说明项目目录结构的基本约束与新增文件的放置原则。

---

## 1. 基本原则

目录结构应尽量反映系统职责边界，而不是随意按个人习惯堆放。

优先遵循：

- 文档与实现分开
- 数据与交付物分开
- 中间结果与最终结果分开
- 编排层与功能层分开

---

## 2. 新增文件放置原则

- 项目介绍 → `README.md`
- 架构说明 → `docs/architecture.md`
- 协议定义 → `docs/stage_schema.md`
- 结构说明 → `docs/project_structure.md`
- 运行说明 → `docs/runtime_flow.md`
- 分类规则 → `docs/conventions/`
- 代码实现 → `src/`
- 运行脚本 → `scripts/`
- 中间数据 → `data/`
- 最终输出 → `outputs/`
- 测试样本 → `tests/`
- 示例内容 → `examples/`
- 配置内容 → `config/`

---

## 3. 模块边界

推荐保持以下目录职责稳定：

- `src/orchestrator/`：任务编排
- `src/collector/`：数据采集
- `src/normalize/`：数据标准化
- `src/identity/`：身份映射
- `src/models/`：领域模型
- `src/metrics/`：确定性指标计算
- `src/analyzer/`：高层分析与 AI 编排
- `src/report/`：报告生成
- `src/visualize/`：可视化输出
- `src/validation/`：最终验收

---

## 4. 后续补充

后续可继续补充：

- 文件命名规范
- 目录保留文件规范
- 哪些目录内容应入库
- 哪些目录内容应忽略
