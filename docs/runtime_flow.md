# runtime_flow

本文用于说明 `acmer_analyze` 一次分析任务从输入到输出的整体运行流程，以及中间 artifact 如何流转、如何局部重跑。

---

## 1. 总体运行顺序

一次完整任务通常按以下顺序运行：

1. `collect`
2. `normalize`
3. `team_identity`
4. `build_history`
5. `compute_metrics`
6. `analyze`
7. `report`
8. `visualize`
9. `validate_final`

其中：

- 上游阶段尽量产出稳定、结构化的 artifact
- 下游阶段优先消费 artifact，而不是共享内存对象
- `analyze` 默认优先走 LLM，失败时回退到 rule-based-template

---

## 2. 阶段运行说明

### 3.1 collect

输入：

- task 配置
- 外部数据源或本地 fixture

处理：

- 拉取原始比赛信息
- 拉取题目信息
- 拉取榜单信息
- 写入 `data/raw/`

输出：

- `data/raw/contests/contests.json`
- `data/raw/problems/problems.json`
- `data/raw/standings/standings.json`

### 3.2 normalize

输入：

- `data/raw/*`

处理：

- 对不同来源字段做统一命名
- 收敛字段类型
- 补齐后续阶段依赖的稳定字段

输出：

- `data/normalized/contests/contests.json`
- `data/normalized/problems/problems.json`
- `data/normalized/standings/standings.json`

### 3.3 team_identity

输入：

- `data/normalized/standings/standings.json`
- task 中的 `target_team` 与 `aliases`

处理：

- 匹配目标队伍在榜单中的原始名称
- 生成统一 `canonical_id`
- 记录平台 ID、学校、地区等元信息

输出：

- `data/intermediate/team_identity/<team>.json`

### 3.4 build_history

输入：

- `TeamIdentity`
- `data/normalized/standings/standings.json`

处理：

- 抽取目标队伍各场比赛记录
- 计算每场比赛的 `percentile_rank`
- 形成统一历史记录列表

输出：

- `data/intermediate/team_history/<team>.json`

### 3.5 compute_metrics

输入：

- `TeamHistory`
- 题目标签或补充元数据

处理：

- 计算排名趋势
- 计算题型/标签分布
- 计算稳定性、成长性、解题节奏等指标

输出：

- `data/derived/team_metrics/<team>.json`

### 3.6 analyze

输入：

- `TeamMetrics`
- 可选 `TeamHistory`
- 可选 `TeamIdentity`

处理：

- 组织优势、短板、阶段表现总结
- 默认调用 LLM 做解释和归纳
- 若 LLM 调用失败，默认回退到 `rule-based-template`
- 若显式关闭 LLM，则直接走本地规则模板

输出：

- `outputs/insights/<team>.json`

说明：

- `compute_metrics` 仍然保持确定性逻辑
- LLM 只负责解释层表达
- 产物中应保留 `model_used`

### 3.7 report

输入：

- `TeamMetrics`
- `TeamInsight`

处理：

- 生成 Markdown / HTML 报告
- 渲染固定 section

输出：

- `outputs/reports/<team>.md`
- `outputs/reports/<team>.html`

### 3.8 visualize

输入：

- `TeamMetrics`
- `TeamInsight`

处理：

- 生成图表数据
- 生成可视化页面

输出：

- `outputs/visualizations/<team>.json`
- `outputs/visualizations/<team>.html`

### 3.9 validate_final

输入：

- `TeamInsight`
- 报告 artifact
- 可视化 artifact

处理：

- 检查完整性
- 检查缺失字段
- 检查交付物可用性

输出：

- `outputs/validation/<team>.json`

---

## 4. artifact 流转关系

推荐把 artifact 理解为以下几层：

### 原始层

- `data/raw/`

作用：

- 保留平台抓取原貌
- 支持回溯抓取问题

### 标准化层

- `data/normalized/`

作用：

- 为下游 stage 提供统一协议输入

### 中间组装层

- `data/intermediate/`

作用：

- 表达队伍身份与历史汇总结果

### 指标层

- `data/derived/`

作用：

- 表达确定性分析结果

### 洞察与交付层

- `outputs/insights/`
- `outputs/reports/`
- `outputs/visualizations/`
- `outputs/validation/`

作用：

- 表达高层分析结论
- 承载最终报告与验收结果

---

## 5. LLM analyze 的运行说明

当前 LLM analyze 默认启用，直接运行即可：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json
```

可选参数：

- `--disable-llm-insight`
- `--llm-model`
- `--llm-settings-path`
- `--disable-llm-fallback`

配置读取优先级：

1. CLI 显式参数
2. 环境变量
3. `~/.claude/settings.json`

支持读取的关键字段：

- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`
- 顶层 `model`

如果 LLM 调用失败且允许 fallback，则仍会输出规则模板版 insight。

如果明确不想走 LLM，可显式关闭：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --disable-llm-insight
```

---

## 6. 局部重跑建议

如果某个阶段发现问题，推荐只修复对应阶段并局部重跑。例如：

- 抓取字段变化，只重跑 `collect` 和后续阶段
- 队伍别名识别有误，只重跑 `team_identity` 及下游阶段
- 指标口径调整，只重跑 `compute_metrics` 及下游阶段
- analyze prompt 更新，只重跑 `analyze` / `report` / `visualize` / `validate_final`

推荐命令示例：

```bash
python3 scripts/run_pipeline.py --task-file examples/sample_task.json --start-stage analyze
python3 scripts/run_pipeline.py --task-file examples/sample_task.json --start-stage analyze --disable-llm-insight
```

---

## 7. 设计提醒

- 尽量不要让 LLM 直接替代 `normalize` 或 `compute_metrics`
- 高层总结应可替换，但底层协议应尽量稳定
- 若后续适配多个 provider，优先扩展 analyzer 内部客户端，而不是污染其他 stage
