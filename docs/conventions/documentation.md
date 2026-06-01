# 文档维护规则

本文用于说明项目文档之间的职责边界与同步更新要求。

---

## 1. 文档职责边界

### `README.md`

负责：

- 项目总览
- 框架介绍
- 使用方案
- 文档导航

### `docs/architecture.md`

负责：

- 系统架构
- 分层说明
- Stage 职责边界

### `docs/stage_schema.md`

负责：

- Stage 输入输出协议
- 核心实体
- 字段稳定性约束

### `docs/project_structure.md`

负责：

- 仓库目录结构
- 模块职责
- 文件落点说明

### `docs/runtime_flow.md`

负责：

- 一次运行任务的流程
- artifact 流转
- 局部重跑路径

### `docs/conventions/*`

负责：

- 分类协作规则
- 具体约束说明

---

## 2. 文档同步要求

如果修改了以下内容，应检查相关文档是否需要同步：

- Stage 名称或数量
- 关键字段或协议定义
- artifact 路径
- 目录结构
- 报告结构
- 验收逻辑

---

## 3. 避免文档漂移

推荐做法：

- 项目总览只在 README 维护
- 架构边界只在 architecture 重点维护
- 字段协议只在 stage_schema 重点维护
- 规则细节只在 conventions 下维护

不要在多个文档中长期维护同一层级的完整重复内容。

---

## 4. 后续补充

后续可继续补充：

- 文档更新 checklist
- 文档命名规则
- 示例文档维护规则
