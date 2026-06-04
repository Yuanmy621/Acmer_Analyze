# Stage 输入输出 Schema

本文定义 `acmer_analyze` 各个 Stage 的核心输入输出对象、关键字段与稳定性约束。

本文的角色是 **Stage 间协议文档**。它关注的是：

- 哪些对象会在不同阶段之间流转
- 哪些字段必须稳定
- 哪些字段用于跨 artifact 关联
- 每个 Stage 应输入什么、输出什么

如果 `README.md` 负责项目总览，`docs/architecture.md` 负责系统架构，那么本文负责 **阶段协议与字段契约**。

---

## 1. 设计原则

### 1.1 先稳定主键，再扩展分析字段

最需要长期稳定的是跨 Stage 共享的主键和关联键，例如：

- `canonical_id`
- `contest_id`
- `problem_id`
- `team_raw_name`

分析字段可以逐步增强，但这些主键一旦漂移，会直接破坏整条流水线。

### 1.2 确定性计算与自然语言生成分离

推荐先产出结构化指标，再由 AI 或模板生成可读结论。

因此：

- Stage 0 ~ 4 以结构化数据为主
- Stage 5 开始进入高层语义分析
- Stage 6 ~ 7 负责交付
- Stage 8 只负责验收，不新增业务结论

### 1.3 输入输出优先面向 artifact

每个 Stage 都应优先产出可落盘、可检查的 JSON 结果，而不是只在内存中流转。

---

## 2. 核心实体

### 2.1 Contest

表示一场比赛的元信息。

```json
{
  "contest_id": "cf_1987",
  "source": "codeforces",
  "title": "Codeforces Round 1987",
  "start_time": "2026-05-01T19:35:00Z",
  "duration_seconds": 7200,
  "type": "online",
  "url": "https://codeforces.com/..."
}
```

字段说明：

- `contest_id`：全局唯一比赛 ID，必须稳定
- `source`：数据来源平台，必须稳定
- `title`：比赛标题，必须稳定
- `start_time`：ISO 8601 时间，必须稳定
- `duration_seconds`：比赛时长，建议稳定
- `type`：比赛类型，可选
- `url`：原始链接，可选

---

### 2.2 Problem

表示一场比赛中的题目信息。

```json
{
  "problem_id": "cf_1987_A",
  "contest_id": "cf_1987",
  "label": "A",
  "title": "Sample Problem",
  "tags": ["implementation", "math"],
  "difficulty": 900,
  "tutorial_content": "本题要求实现一个简单的模拟……"
}
```

字段说明：

- `problem_id`：题目唯一 ID，必须稳定
- `contest_id`：所属比赛 ID，必须稳定
- `label`：比赛内题号，如 `A/B/C`，必须稳定
- `title`：题目名，必须稳定
- `tags`：题目标签，高优先级可选字段
- `difficulty`：难度，可选
- `tutorial_content`：官方题解文本，可选。来自 Codeforces Tutorial 页面，用于在 analyze 阶段提供解题思路上下文

说明：

- `tags` 虽然技术上可选，但对题型能力分析非常关键，应尽量补齐。
- `tutorial_content` 在 collect 阶段从 Tutorial 页面抓取，通过 normalize 阶段注入到对应题目中。缺失时不影响主流程。

---

### 2.3 ProblemResult

表示某支队伍在某道题上的表现。

```json
{
  "problem_id": "cf_1987_A",
  "accepted": true,
  "attempts": 1,
  "first_ac_time": 14
}
```

字段说明：

- `problem_id`：题目 ID，必须稳定
- `accepted`：是否通过，必须稳定
- `attempts`：尝试次数，可选
- `first_ac_time`：首次通过时间，单位建议统一为分钟，可选

---

### 2.4 Standing

表示一支队伍在一场比赛中的排名记录。

```json
{
  "contest_id": "cf_1987",
  "team_raw_name": "ACMer Team",
  "rank": 32,
  "solved_count": 7,
  "penalty": 845,
  "problem_results": [
    {
      "problem_id": "cf_1987_A",
      "accepted": true,
      "attempts": 1,
      "first_ac_time": 14
    }
  ]
}
```

字段说明：

- `contest_id`：比赛 ID，必须稳定
- `team_raw_name`：抓取到的原始队伍名，必须稳定
- `rank`：名次，必须稳定
- `solved_count`：通过题数，必须稳定
- `penalty`：罚时，可选
- `problem_results`：题目级表现，必须稳定

说明：

- `team_raw_name` 是 Stage 2 做身份映射的核心输入，不能在前置阶段被覆盖。

---

### 2.5 TeamIdentity

表示目标队伍的统一身份映射。

```json
{
  "canonical_id": "team_zju_alpha",
  "display_name": "ZJU Alpha",
  "aliases": ["ZJU Alpha", "zju_alpha", "ZJU-Alpha"],
  "platform_ids": {
    "codeforces": "zju_alpha_cf",
    "ucup": "team_1024"
  },
  "school": "Zhejiang University",
  "region": "CN"
}
```

字段说明：

- `canonical_id`：全流程主键，必须稳定
- `display_name`：统一展示名，必须稳定
- `aliases`：识别到的别名集合，必须稳定
- `platform_ids`：平台侧 ID 映射，必须稳定
- `school`：学校信息，可选
- `region`：地区信息，可选

说明：

- `canonical_id` 是 Stage 2 之后所有 artifact 的主关联键。

---

### 2.6 ContestRecord

表示某支目标队伍在某场比赛中的标准化记录。

```json
{
  "contest_id": "cf_1987",
  "rank": 32,
  "solved_count": 7,
  "total_teams": 236,
  "percentile_rank": 0.8644,
  "problem_results": [
    {
      "problem_id": "cf_1987_A",
      "accepted": true,
      "attempts": 1,
      "first_ac_time": 14
    }
  ]
}
```

字段说明：

- `contest_id`：比赛 ID，必须稳定
- `rank`：名次，必须稳定
- `solved_count`：通过题数，必须稳定
- `total_teams`：总参赛队伍数，必须稳定
- `percentile_rank`：归一化名次，可选衍生字段
- `problem_results`：题目级表现，必须稳定

---

### 2.7 TeamHistory

表示某支目标队伍的历史参赛汇总。

```json
{
  "canonical_id": "team_zju_alpha",
  "contest_records": [
    {
      "contest_id": "cf_1987",
      "rank": 32,
      "solved_count": 7,
      "total_teams": 236,
      "percentile_rank": 0.8644,
      "problem_results": []
    }
  ]
}
```

字段说明：

- `canonical_id`：目标队伍主键，必须稳定
- `contest_records`：历史比赛记录列表，必须稳定

---

### 2.8 TeamMetrics

表示确定性指标计算结果。

```json
{
  "canonical_id": "team_zju_alpha",
  "rank_trend": [
    {
      "contest_id": "cf_1987",
      "rank": 32,
      "percentile_rank": 0.8644
    }
  ],
  "tag_distribution": {
    "graph": {
      "attempted": 12,
      "solved": 8,
      "solve_rate": 0.6667
    }
  },
  "stability_score": 0.78,
  "growth_score": 0.62,
  "solve_pace": {
    "avg_first_ac_minute": 18.4,
    "late_stage_solve_ratio": 0.31
  }
}
```

字段说明：

- `canonical_id`：主键，必须稳定
- `rank_trend`：排名时间序列，必须稳定
- `tag_distribution`：题型能力分布，必须稳定
- `stability_score`：稳定性指标，必须稳定
- `growth_score`：成长性指标，可选
- `solve_pace`：解题节奏特征，可选

---

### 2.9 TeamInsight

表示高层分析结论。

```json
{
  "canonical_id": "team_zju_alpha",
  "strengths": ["图论题稳定", "中低难度题通过率高"],
  "weaknesses": ["高难 DP 波动较大"],
  "summary": "这是一支基础扎实、稳定性较强，但高难题突破能力仍需提升的队伍。",
  "training_advice": ["增加高难 DP 训练", "加强后半程追分能力"],
  "stage_analysis": "近三个月表现整体上升。",
  "model_used": "claude-sonnet-4-6",
  "generated_at": "2026-05-29T10:00:00Z"
}
```

字段说明：

- `canonical_id`：主键，必须稳定
- `strengths`：优势列表，必须稳定
- `weaknesses`：短板列表，必须稳定
- `summary`：总体结论，必须稳定
- `training_advice`：训练建议，可选
- `stage_analysis`：阶段性复盘，可选
- `model_used`：模型溯源，可选
- `generated_at`：生成时间，可选

---

### 2.10 ReportArtifact

表示最终报告产物。

```json
{
  "canonical_id": "team_zju_alpha",
  "generated_at": "2026-05-29T10:05:00Z",
  "format": "md",
  "path": "outputs/reports/team_zju_alpha.md",
  "sections_present": ["overview", "trend", "topics", "strengths", "weaknesses"]
}
```

字段说明：

- `canonical_id`：主键，必须稳定
- `generated_at`：生成时间，必须稳定
- `format`：`md` / `html`，必须稳定
- `path`：文件路径，必须稳定
- `sections_present`：已生成 section 列表，可选但推荐

---

### 2.11 VisualizationArtifact

表示图表与可视化产物。

```json
{
  "canonical_id": "team_zju_alpha",
  "generated_at": "2026-05-29T10:05:00Z",
  "format": "html",
  "path": "outputs/visualizations/team_zju_alpha.html",
  "chart_keys": ["rank_trend", "tag_distribution", "radar"]
}
```

字段说明：

- `canonical_id`：主键，必须稳定
- `generated_at`：生成时间，必须稳定
- `format`：`json` / `html`，必须稳定
- `path`：文件路径，必须稳定
- `chart_keys`：包含的图表标识，可选但推荐

---

## 3. 各 Stage 输入输出定义

### Stage 0 — collect

输入：

- 分析任务参数：`target_team`、`source`、`time_range`

输出：

- `Contest[]`
- `Standing[]`
- `Problem[]`
- `Tutorial[]`（可选）

建议落盘：

- `data/raw/contests/*.json`
- `data/raw/standings/*.json`
- `data/raw/problems/*.json`
- `data/raw/tutorials/*.json`（可选，抓取失败时不生成）

关键要求：

- 保留平台原始字段语义
- 保留 `team_raw_name`
- 不在本阶段做复杂映射
- Tutorial 题解抓取为可选步骤，失败时静默跳过

---

### Stage 1 — normalize

输入：

- Stage 0 的原始 `Contest[]`
- Stage 0 的原始 `Standing[]`
- Stage 0 的原始 `Problem[]`
- Stage 0 的可选 `Tutorial[]`

输出：

- 标准化 `Contest[]`
- 标准化 `Standing[]`
- 标准化 `Problem[]`（含 `tutorial_content`）

建议落盘：

- `data/normalized/contests/*.json`
- `data/normalized/standings/*.json`
- `data/normalized/problems/*.json`

关键要求：

- 统一字段命名与时间格式
- 尽量补齐 `tags`
- 不破坏 `contest_id`、`problem_id`、`team_raw_name`
- 将 tutorials 数据中的题解内容关联到对应的 problem 中

---

### Stage 2 — team_identity

输入：

- 标准化 `Standing[]`
- 用户给定的目标队伍标识
- 可选人工映射配置

输出：

- `TeamIdentity`

建议落盘：

- `data/intermediate/team_identity/<team>.json`

关键要求：

- 产出稳定的 `canonical_id`
- 明确 `aliases`
- 能解释映射依据，避免误认队伍

---

### Stage 3 — build_history

输入：

- `TeamIdentity`
- 标准化 `Contest[]`
- 标准化 `Standing[]`
- 标准化 `Problem[]`

输出：

- `TeamHistory`

建议落盘：

- `data/intermediate/team_history/<team>.json`

关键要求：

- 只汇总确认属于同一 `canonical_id` 的记录
- 补齐 `total_teams`
- 建立比赛级和题目级统一视图

---

### Stage 4 — compute_metrics

输入：

- `TeamHistory`
- 可选 `Problem[]` 题目标签补充信息

输出：

- `TeamMetrics`

建议落盘：

- `data/derived/team_metrics/<team>.json`

关键要求：

- 尽量保持确定性逻辑
- 指标计算可复现
- 对缺失标签、缺失题目元信息要有降级策略

---

### Stage 5 — analyze

输入：

- `TeamMetrics`
- 可选 `TeamHistory`
- 可选 `Tutorial[]`（官方题解）

输出：

- `TeamInsight`

建议落盘：

- `outputs/insights/<team>.json`

关键要求：

- 结论必须建立在结构化指标之上
- 避免模型直接从原始排名自由生成结论
- 建议保留 `model_used` 和 `generated_at`
- 若存在 Tutorial 题解数据，应在 prompt 中提供给 LLM 以增强算法能力分析
- Tutorial 数据缺失时不影响分析流程

---

### Stage 6 — report

输入：

- `TeamMetrics`
- `TeamInsight`

输出：

- `ReportArtifact`
- 实际 Markdown / HTML 文件

建议落盘：

- `outputs/reports/<team>.md`
- `outputs/reports/<team>.html`

关键要求：

- 报告 section 结构稳定
- 能从 artifact 反查所使用的核心结论

---

### Stage 7 — visualize

输入：

- `TeamMetrics`
- `TeamInsight`

输出：

- `VisualizationArtifact`
- 实际图表 JSON / HTML 文件

建议落盘：

- `outputs/visualizations/<team>.json`
- `outputs/visualizations/<team>.html`

关键要求：

- 图表 key 命名稳定
- 图表数据直接来源于 metrics，而不是从自然语言反推

---

### Stage 8 — validate_final

输入：

- `TeamInsight`
- `ReportArtifact`
- `VisualizationArtifact`

输出：

- 验收结果对象（建议单独定义 `ValidationResult`）

建议落盘：

- `outputs/validation/<team>.json`

推荐结构：

```json
{
  "canonical_id": "team_zju_alpha",
  "passed": true,
  "errors": [],
  "warnings": ["missing radar chart"],
  "checked_at": "2026-05-29T10:06:00Z"
}
```

关键要求：

- 只做验收，不新增分析结论
- 明确区分 `error` 与 `warning`

---

## 4. 字段稳定性分级

### 4.1 必须稳定字段

这些字段应视为跨 Stage 协议的一部分：

- `canonical_id`
- `contest_id`
- `problem_id`
- `team_raw_name`
- `rank`
- `solved_count`
- `total_teams`
- `accepted`
- `strengths`
- `weaknesses`
- `summary`

### 4.2 高优先级可选字段

这些字段不是最小闭环必需，但对分析质量提升明显：

- `tags`
- `difficulty`
- `penalty`
- `attempts`
- `first_ac_time`
- `growth_score`
- `solve_pace`
- `training_advice`
- `stage_analysis`
- `tutorial_content`

### 4.3 审计与溯源字段

推荐长期保留：

- `source`
- `url`
- `generated_at`
- `model_used`
- `path`

---

## 5. 第一版最小可用 Schema 子集

如果要尽快跑通第一版闭环，至少保证以下字段齐全：

### collect / normalize

- `Contest.contest_id`
- `Contest.source`
- `Contest.title`
- `Contest.start_time`
- `Standing.contest_id`
- `Standing.team_raw_name`
- `Standing.rank`
- `Standing.solved_count`
- `Standing.problem_results[].problem_id`
- `Standing.problem_results[].accepted`
- `Problem.problem_id`
- `Problem.contest_id`
- `Problem.label`

### team_identity / build_history

- `TeamIdentity.canonical_id`
- `TeamIdentity.display_name`
- `TeamIdentity.aliases`
- `TeamHistory.canonical_id`
- `ContestRecord.contest_id`
- `ContestRecord.rank`
- `ContestRecord.solved_count`
- `ContestRecord.total_teams`

### compute_metrics / analyze

- `TeamMetrics.rank_trend`
- `TeamMetrics.tag_distribution`
- `TeamMetrics.stability_score`
- `TeamInsight.strengths`
- `TeamInsight.weaknesses`
- `TeamInsight.summary`

这套最小子集足以支持：

- 排名趋势分析
- 基础题型能力统计
- 第一版 Markdown 报告生成

---

## 6. 维护建议

1. 先把 schema 定义成文档，再落成代码模型
2. 代码模型可以使用 dataclass / pydantic / typed dict 之一
3. 任何 Stage 输出字段变更，都应同步更新本文档
4. 尽量为每个 Stage 保留示例 artifact，作为回归样本
5. `canonical_id` 的生成规则应尽早固定，避免后期大范围迁移