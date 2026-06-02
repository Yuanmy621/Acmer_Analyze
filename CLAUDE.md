# CLAUDE.md

本文件用于说明 Claude Code 在本仓库中的协作入口、全局约束与文档调用方式。

当前原则：**主文件保持简洁，具体规则拆分到对应文档，在需要时按职责查阅。**

---

## 1. 项目定位

本仓库用于构建一个面向 **ACM / 竞赛编程队伍分析** 的 Agent。

项目整体目标是围绕一支目标队伍，基于比赛排名、题目信息与历史参赛记录，产出：

- 排名变化分析
- 技能树 / 题型能力分析
- 优势与短板总结
- 可视化分析报告

当前明确提到的数据源包括：

- `Codeforces` `https://codeforces.com/`
- `UCUP` `https://contest.ucup.ac/`

项目整体应按照 **harness / pipeline** 思路设计，而不是做成一次性 prompt 驱动的黑盒工具。

---

## 2. 当前仓库状态

当前仓库仍处于 **文档骨架与目录骨架已建立、实现代码尚未落地** 的阶段。

现阶段已经具备：

- `README.md` 项目总览
- `docs/` 下的架构、协议、结构、运行流文档
- `docs/conventions/` 下的分类规则骨架
- `src/`、`scripts/`、`data/`、`outputs/`、`tests/`、`examples/`、`config/` 等目录骨架
- 各主要模块与目录的职责说明文件
- 一套基于 **Python 标准库** 的最小可运行流水线实现
- `scripts/run_pipeline.py` 作为当前 orchestrator CLI 入口，支持 task-file 和动态参数模式
- `scripts/run_bridge.py` 作为本地 browser bridge 服务入口
- `examples/sample_task.json` 与 `examples/sample_fixture/` 作为本地 fixture 演示输入
- `examples/codeforces_task.json` 作为真实 Codeforces 抓取示例任务
- `examples/bridge_payload.json` 作为 browser bridge 导入协议示例
- `source=codeforces` 的真实 collect 能力
- `source=browser_bridge` 的 raw 导入与下游执行能力
- bridge `import-and-run` 自动触发分析能力
- `plugins/browser-extension/` 下的浏览器插件骨架与 Codeforces standings 页面首版提取逻辑
- `python3 -m unittest discover -s tests -p 'test_*.py'` 作为当前基础测试命令

现阶段尚未具备：

- UCUP 在线抓取能力
- 多站点成熟插件适配
- 完整的 Codeforces 页面提取鲁棒性验证
- LLM 驱动的分析生成能力
- 完整的 build / lint / CI 工作流
- 更完整的 artifact 版本化与生产级运行约定

因此，在建议命令、技术方案或目录结构前，应先检查仓库是否已经新增：

- `Makefile`
- `go.mod`
- `package.json`
- `pyproject.toml`
- CI 配置
- 其他任务脚本或运行入口

若仓库已有约定，优先遵循仓库自身约定。

---

## 3. 文档优先级

本仓库文档建议按以下层级理解：

1. `README.md`
   - 项目总览、整体框架、使用方案、文档导航

2. `docs/architecture.md`
   - 系统架构、分层边界、Stage 职责

3. `docs/stage_schema.md`
   - Stage 输入输出协议、关键字段与稳定性约束

4. `docs/project_structure.md`
   - 仓库目录结构、模块职责、文件分层

5. `docs/runtime_flow.md`
   - 一次分析任务的运行流、artifact 流转、局部重跑路径

6. `docs/conventions/`
   - 分类规则文档，按场景查阅；新增细则优先补到这里

如果不同文档之间出现冲突：

- 先判断哪个文档承担该信息的主职责
- 若发现文档漂移，应同步修正文档，而不是长期忽略

---

## 4. 全局架构约束

本项目推荐采用如下主干结构：

**Orchestrator + Staged Pipeline + Validation + Artifact Store**

推荐阶段包括：

1. `collect`
2. `normalize`
3. `team_identity`
4. `build_history`
5. `compute_metrics`
6. `analyze`
7. `report`
8. `visualize`
9. `validate_final`

在后续实现中，应尽量保持以下边界清晰：

- 数据采集与数据分析分开
- 确定性指标计算与自然语言生成分开
- 中间产物与最终交付物分开
- 阶段编排逻辑与具体 stage 实现分开
- 验收逻辑独立于生成逻辑

如果后续引入 LLM，应优先让 LLM 负责：

- 解释
- 总结
- 报告表达

而不是直接替代：

- 数据清洗
- 身份映射主逻辑
- 指标统计
- 结构化结果计算

---

## 5. 全局协作规则

### 5.1 尽量使用中文

说明、注释、文档、沟通内容尽量使用中文。

以下内容可保留原文：

- 代码标识符
- 字段名
- 协议名
- 第三方平台名
- 必要的英文技术术语

更具体规则见：

- `docs/conventions/language.md`

### 5.2 优先保持结构清晰

当前阶段比起“快速堆功能”，更重要的是：

- 先明确阶段边界
- 先定义输入输出协议
- 先约定 artifact 组织方式
- 先保证后续容易扩展和重构
- 先把新增约束补到对应文档，而不是重新堆回主文档

相关规则见：

- `docs/conventions/structure.md`
- `docs/conventions/stage_rules.md`
- `docs/conventions/artifact_rules.md`

### 5.3 优先文档一致性

如果修改了：

- Stage 设计
- 关键字段
- artifact 路径
- 目录职责
- 报告结构
- 验收逻辑
- 主入口文档中的导航关系

应同步检查相关文档是否需要更新，避免长期漂移。

相关规则见：

- `docs/conventions/documentation.md`

### 5.4 不要把本仓库误认为其他项目

本仓库是一个独立的小型项目。

不要在没有明确代码与文档依据时，套用外部项目的目录、命令或架构假设。

---

## 6. 按任务调用规则文档

当任务涉及以下主题时，优先查阅对应文档：

### 6.1 项目总览与定位

- `README.md`

### 6.2 系统架构与分层边界

- `docs/architecture.md`

### 6.3 Stage 输入输出与字段协议

- `docs/stage_schema.md`

### 6.4 仓库目录结构与模块职责

- `docs/project_structure.md`

### 6.5 一次任务怎么跑、怎么重跑

- `docs/runtime_flow.md`

### 6.6 语言、表述、命名与文档规范

- `docs/conventions/language.md`
- `docs/conventions/naming.md`
- `docs/conventions/documentation.md`

### 6.7 目录结构、模块拆分与 Stage 实现边界

- `docs/conventions/structure.md`
- `docs/conventions/stage_rules.md`

### 6.8 artifact 命名、落盘与流转规则

- `docs/conventions/artifact_rules.md`

### 6.9 报告、可视化、测试、验收规则

- `docs/conventions/report_rules.md`
- `docs/conventions/validation_rules.md`

---

## 7. 当前已确定的核心稳定点

在后续实现中，应重点保持以下字段稳定：

- `canonical_id`
- `contest_id`
- `problem_id`
- `team_raw_name`

这些字段是跨阶段关联的基础，不应轻易改变语义。

更细协议见：

- `docs/stage_schema.md`

---

## 8. 后续维护方式

后续如果项目进入实现阶段，应逐步把规则继续补充到对应文档中，例如：

- 真实入口命令
- 目录职责
- 模块边界
- 测试命令
- 报告生成约定
- 代码与文档修改规则

但 `CLAUDE.md` 应继续保持以下角色：

- 协作入口
- 全局约束摘要
- 文档调用路由

而不是重新变回承载全部细节的单一文档。
