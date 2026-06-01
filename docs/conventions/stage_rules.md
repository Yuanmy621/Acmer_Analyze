# Stage 实现规则

本文用于说明 Stage 拆分原则、职责边界与实现时的基本约束。

---

## 1. Stage 拆分原则

推荐保持以下阶段：

1. `collect`
2. `normalize`
3. `team_identity`
4. `build_history`
5. `compute_metrics`
6. `analyze`
7. `report`
8. `visualize`
9. `validate_final`

阶段划分的目标是：

- 可编排
- 可重跑
- 可检查
- 可替换局部实现

---

## 2. 职责边界

### collect

负责抓取原始数据，不负责复杂分析。

### normalize

负责统一结构，不负责高层业务结论。

### team_identity

负责统一目标队伍身份，不负责趋势统计。

### build_history

负责组装历史视图，不负责直接生成自然语言结论。

### compute_metrics

负责确定性指标计算，不负责报告表达。

### analyze

负责基于 metrics 形成高层解释，不应绕开结构化结果。

### report

负责交付型文本与结构渲染，不负责重新发明指标。

### visualize

负责图表与页面输出，不应从自然语言总结反推核心数据。

### validate_final

负责验收，不新增业务结论。

---

## 3. 避免跨阶段耦合

实现时应尽量避免：

- 在 `collect` 中混入分析逻辑
- 在 `analyze` 中回头重算 metrics
- 在 `report` 中自行修正上游结构化结果
- 在 `visualize` 中绕过 metrics 直接从文案取数

---

## 4. 后续补充

后续可继续补充：

- 每个 stage 的输入输出文件约定
- 每个 stage 的错误处理约定
- 每个 stage 的可测试边界
