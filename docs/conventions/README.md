# 规则文档说明

本目录用于存放 `acmer_analyze` 的分类协作规则。

设计目标是把原本容易集中堆在 `CLAUDE.md` 中的限制、规范与约束，按职责拆分到不同文件中，在需要时按场景查阅。

---

## 当前规则文件

### `language.md`

用于说明：

- 中文优先规则
- 英文保留场景
- 表述风格建议

### `documentation.md`

用于说明：

- 文档职责边界
- 文档同步更新要求
- 如何避免 README / architecture / schema 漂移

### `structure.md`

用于说明：

- 仓库目录结构约束
- 模块职责边界
- 新增文件的放置建议

### `naming.md`

用于说明：

- 文档、目录、模块、字段与 artifact 的命名规则
- Stage 名称与模块名称的命名约定
- 稳定标识符的命名风格

### `stage_rules.md`

用于说明：

- Stage 拆分原则
- 何种逻辑应放在哪个阶段
- 如何避免跨阶段耦合

### `artifact_rules.md`

用于说明：

- artifact 命名与落盘规则
- 原始层、中间层、输出层的区分
- 重跑时的 artifact 复用边界

### `report_rules.md`

用于说明：

- 报告生成相关规则
- section 组织规则
- 报告输出格式约定

### `validation_rules.md`

用于说明：

- 测试与验收规则
- 完整性检查规则
- 回归样本与校验约定

---

## 使用建议

当任务涉及以下主题时，优先查阅对应规则：

- 语言和文风 → `language.md`
- 文档修改与同步 → `documentation.md`
- 目录结构与模块归属 → `structure.md`
- 命名规范 → `naming.md`
- stage 拆分与职责边界 → `stage_rules.md`
- artifact 组织与落盘 → `artifact_rules.md`
- 报告生成 → `report_rules.md`
- 验收与回归 → `validation_rules.md`

---

## 当前阶段说明

当前仓库仍处于文档与架构阶段，因此这些规则文件现在以：

- 规则骨架
- 最小必要约束
- 后续补充入口

为主。

后续开发过程中，可继续把更具体的规则补充到对应文件，而不是重新堆回 `CLAUDE.md`。
