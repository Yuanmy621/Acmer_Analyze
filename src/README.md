# src 目录说明

本目录用于放置项目后续实现代码。

当前阶段先按系统职责拆分模块目录，后续代码建议按以下边界落地：

- `orchestrator/`：任务编排与运行控制
- `collector/`：外部数据采集
- `normalize/`：数据标准化
- `identity/`：队伍身份识别
- `models/`：领域模型
- `metrics/`：确定性指标计算
- `analyzer/`：高层分析与 AI 编排
- `report/`：报告生成
- `visualize/`：可视化输出
- `validation/`：最终验收
