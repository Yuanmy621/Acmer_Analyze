# 命名规则

本文用于说明本项目当前建议采用的命名规则。

当前目标不是一次性把所有命名细节完全定死，而是先建立一组 **可持续扩展、便于协作、与现有文档一致** 的基础约束。

---

## 1. 总体原则

命名应优先满足以下要求：

- 清晰可读
- 语义稳定
- 尽量与职责一致
- 尽量与现有文档和 schema 保持一致
- 优先机器可处理，不依赖自然语言猜测

避免：

- 模糊缩写
- 同一概念多种写法长期并存
- 中文、英文、拼音混杂命名
- 只对当前个人临时习惯友好的命名

---

## 2. 文档文件命名

除约定俗成的顶层文件外，文档文件名建议使用：

- 小写英文
- 下划线分隔
- 与职责直接对应

当前已采用的形式包括：

- `project_structure.md`
- `runtime_flow.md`
- `stage_schema.md`
- `artifact_rules.md`
- `validation_rules.md`

### 保留约定名的文件

以下文件保留其通用约定写法：

- `README.md`
- `CLAUDE.md`

---

## 3. 目录命名

目录名建议使用：

- 小写英文
- 尽量单义
- 与模块职责直接对应

例如：

- `collector`
- `normalize`
- `identity`
- `metrics`
- `visualize`
- `validation`

对于聚合性目录，可使用清晰复数或类别名，例如：

- `docs`
- `scripts`
- `examples`
- `outputs`

---

## 4. Stage 命名

Stage 名称应优先保持与架构文档一致，不随实现层局部习惯频繁变化。

当前约定的 stage 名称为：

1. `collect`
2. `normalize`
3. `team_identity`
4. `build_history`
5. `compute_metrics`
6. `analyze`
7. `report`
8. `visualize`
9. `validate_final`

规则：

- Stage 名称用于表达流水线步骤
- 不要随意改成临时缩写
- 若实现模块名与 stage 名不同，应在文档中明确映射关系

例如：

- stage：`collect`
- module：`src/collector/`

这种差异是允许的，但应保持稳定并可解释。

---

## 5. 模块命名

实现模块名建议与职责保持直接对应。

推荐模式：

- 编排层：`orchestrator`
- 数据采集：`collector`
- 数据标准化：`normalize`
- 身份映射：`identity`
- 领域模型：`models`
- 指标计算：`metrics`
- 分析编排：`analyzer`
- 报告生成：`report`
- 可视化：`visualize`
- 验收：`validation`

避免：

- 同义模块重复并存
- 某个模块名过大，职责覆盖多个 stage
- 文件夹名与实际职责长期不符

---

## 6. 字段命名

结构化字段名建议使用：

- 小写英文
- 下划线分隔
- 含义稳定

例如：

- `canonical_id`
- `contest_id`
- `problem_id`
- `team_raw_name`
- `solved_count`
- `generated_at`

规则：

- 同一概念只保留一种主写法
- 避免同时出现缩写版与全写版长期共存
- 新增字段时优先参考 `docs/stage_schema.md` 既有风格

---

## 7. 标识符命名

### 7.1 `canonical_id`

建议：

- 保持稳定
- 小写英文
- 使用下划线分隔
- 不依赖展示名大小写
- 不混入临时分析参数

当前示例风格：

- `team_zju_alpha`

### 7.2 `contest_id`

建议：

- 带来源前缀
- 可与平台原始 ID 稳定映射
- 避免后续重算后变义

当前示例风格：

- `cf_1987`

### 7.3 `problem_id`

建议：

- 能稳定关联到 `contest_id`
- 在 contest 维度下保持唯一

当前示例风格：

- `cf_1987_A`

---

## 8. artifact 文件命名

当前阶段建议：

- 结构化单队结果优先使用稳定标识命名
- 优先与 `canonical_id` 对齐
- 报告与可视化文件优先按输出格式区分扩展名

当前示例风格：

- `outputs/insights/<team>.json`
- `outputs/reports/<team>.md`
- `outputs/reports/<team>.html`
- `outputs/visualizations/<team>.json`
- `outputs/visualizations/<team>.html`

后续如果增加更复杂的命名策略，可继续补充：

- 是否带 source
- 是否带日期
- 是否带版本号
- 是否区分覆盖写与历史保留

---

## 9. 后续补充

后续可继续补充更细规则，例如：

- Python / Go / TypeScript 代码文件命名规范
- 测试文件命名规范
- 配置文件命名规范
- 示例文件命名规范
- artifact 版本命名规范
