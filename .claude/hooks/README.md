# Claude Hooks

本目录用于承载当前仓库的运行时 hooks 扩展脚本。

当前 hooks 主要用于：

- pipeline 生命周期记录
- stage 耗时统计
- artifact 写入审计
- bridge 导入与自动分析审计
- validation 摘要记录

目录约定：

- `common/`：hook 上下文、事件常量、调度器与通用工具
- `builtin/`：仓库内建 hooks 实现
- `outputs/`：hook 运行输出
- `hooks.json`：启用项与事件绑定配置
