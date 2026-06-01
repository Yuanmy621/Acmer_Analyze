# Artifact 规则

本文用于说明 artifact 的分层、命名与落盘约束。

---

## 1. artifact 分层

推荐保持以下分层：

- `data/raw/`：原始抓取数据
- `data/normalized/`：标准化数据
- `data/intermediate/`：中间组装结果
- `data/derived/`：确定性指标结果
- `outputs/`：最终交付结果

---

## 2. 基本原则

- 原始数据不要与标准化数据混放
- 中间组装结果不要与最终报告混放
- 确定性指标与自然语言洞察应分层保存
- 可重跑阶段的 artifact 应尽量可独立检查

---

## 3. 当前建议路径

- `data/raw/contests/`
- `data/raw/standings/`
- `data/raw/problems/`
- `data/normalized/contests/`
- `data/normalized/standings/`
- `data/normalized/problems/`
- `data/intermediate/team_identity/`
- `data/intermediate/team_history/`
- `data/derived/team_metrics/`
- `outputs/insights/`
- `outputs/reports/`
- `outputs/visualizations/`
- `outputs/validation/`

---

## 4. 后续补充

后续可继续补充：

- 文件命名规范
- 按 team / source / date 的落盘规则
- 覆盖写与版本保留策略
- 哪些 artifact 应提交到仓库
