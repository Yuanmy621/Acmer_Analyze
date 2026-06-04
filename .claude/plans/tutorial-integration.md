# 计划：集成 Codeforces Tutorial 题解到分析流程

## 背景

当前 analyze 阶段仅基于 `TeamMetrics`、`TeamHistory`、`TeamIdentity` 三项结构化数据调用 LLM 生成洞察。这些数据反映的是队伍的**表现指标**（排名、通过率、稳定性），但缺少对**题目解法**的理解。

Codeforces 每场比赛通常有官方题解页面（Tutorial），包含每道题的解题思路与关键算法。如果在分析时能参考这些题解内容，LLM 可以更精准地判断队伍在哪些算法领域有优势或短板，而不仅仅依赖 tag 统计。

## 改动概览

在 `collect` 阶段之后、`analyze` 阶段之前，新增 `fetch_tutorials` 步骤：

1. 对每场已抓取的比赛，尝试获取其 Tutorial 页面
2. 解析 HTML，按题号提取每道题的题解文本
3. 存储到 `data/raw/tutorials/tutorials.json`
4. 在 `analyze` 阶段，将题解内容作为上下文传入 LLM prompt

## 需要修改/新增的文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/collector/tutorial_fetcher.py` | Tutorial 页面抓取与 HTML 解析逻辑 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/collector/codeforces_client.py` | 新增 `fetch_page(url)` 通用网页抓取方法 |
| `src/collector/codeforces_collector.py` | 在 `run_collect_codeforces` 末尾调用 tutorial 抓取 |
| `src/models/schemas.py` | `Problem` dataclass 新增 `tutorial_content` 可选字段 |
| `src/normalize/normalizer.py` | `_normalize_problems` 透传 `tutorial_content` 字段 |
| `src/analyzer/insight_generator.py` | `run_analyze` 读取 tutorials 数据，`_build_llm_prompt` 纳入题解上下文 |
| `docs/stage_schema.md` | 补充 `tutorial_content` 字段说明与 tutorials artifact 协议 |

## 详细设计

### 1. `src/collector/codeforces_client.py` — 新增 fetch_page

在 `CodeforcesClient` 类中新增一个通用 HTML 页面抓取方法：

```python
def fetch_page(self, url: str) -> str | None:
    """抓取指定 URL 的 HTML 内容，失败时返回 None。"""
```

- 使用 `urllib.request.urlopen`，复用已有的 SSL 配置与 retry 逻辑
- 失败时返回 `None`（不抛异常），因为 tutorial 不是核心数据
- 设置合理超时（10 秒）

### 2. `src/collector/tutorial_fetcher.py` — 新增文件

核心职责：抓取 Codeforces Tutorial 页面并解析为结构化题解。

```python
def fetch_tutorials(
    client: CodeforcesClient,
    contest_id: int,
) -> dict[str, str] | None:
    """获取指定比赛的 Tutorial 页面，返回 {题号: 题解文本} 映射。"""


def _parse_tutorial_html(html: str) -> dict[str, str]:
    """从 Tutorial HTML 中按题号提取题解内容。"""
```

**URL 构造**：`https://codeforces.com/contest/{contestId}/tutorial`

**HTML 解析策略**（不引入第三方依赖，使用正则）：

Codeforces Tutorial 页面的典型结构：

```html
<div class="ttypography">
  <div class="problem-statement">
    <div class="header">
      <div class="title">A. 题目名</div>
    </div>
    <div>题解文本...</div>
  </div>
</div>
```

解析步骤：
1. 定位 `<div class="ttypography">` 内容区域
2. 按 `<div class="title">` 或 `<h1>`/`<h2>` 等标题标签切分不同题目的区块
3. 提取每个区块的纯文本内容
4. 截取过长内容（每题最多 2000 字符），避免 prompt 爆炸

**容错**：
- 页面不存在（404）→ 返回 `None`
- HTML 结构不符合预期 → 返回 `None`
- 网络异常 → 返回 `None`
- 所有失败情况静默跳过，不影响主流程

### 3. `src/collector/codeforces_collector.py` — 调用 tutorial 抓取

在 `run_collect_codeforces` 函数中，完成 standings/problems/contests 写入后，增加：

```python
# 抓取每场比赛的 Tutorial 题解（可选，失败不影响主流程）
tutorials: list[dict] = []
for contest_id in contest_ids:
    tutorial_map = fetch_tutorials(client, contest_id)
    if tutorial_map:
        for problem_label, content in tutorial_map.items():
            tutorials.append({
                "problem_id": _build_problem_id(contest_id, problem_label),
                "contest_id": _build_contest_id(contest_id),
                "label": problem_label,
                "content": content,
            })
if tutorials:
    write_json(context.path("data/raw/tutorials/tutorials.json"), tutorials)
```

### 4. `src/models/schemas.py` — Problem 扩展

```python
@dataclass(slots=True)
class Problem:
    problem_id: str
    contest_id: str
    label: str
    title: str
    tags: list[str] = field(default_factory=list)
    difficulty: int | None = None
    tutorial_content: str | None = None  # 新增：题解文本
```

### 5. `src/normalize/normalizer.py` — 透传 tutorial_content

`_normalize_problems` 函数中，为每个 normalized item 增加：

```python
"tutorial_content": item.get("tutorial_content"),
```

同时在 `run_normalize` 中，如果存在 `data/raw/tutorials/tutorials.json`，则读取并将题解内容关联到对应的 normalized problem：

```python
# 将 tutorial 内容注入到对应的 problem 中
tutorials_path = context.path("data/raw/tutorials/tutorials.json")
if os.path.exists(tutorials_path):
    tutorials = read_json(tutorials_path)
    tutorial_map = {t["problem_id"]: t["content"] for t in tutorials}
    for problem in normalized_problems:
        pid = problem["problem_id"]
        if pid in tutorial_map:
            problem["tutorial_content"] = tutorial_map[pid]
```

### 6. `src/analyzer/insight_generator.py` — 纳入题解上下文

**`run_analyze` 修改**：额外读取 tutorials 数据

```python
def run_analyze(context: PipelineContext) -> None:
    metrics = read_json(...)
    identity = read_json(...)
    history = read_json(...)

    # 读取 tutorials（可选）
    tutorials_path = context.path("data/raw/tutorials/tutorials.json")
    tutorials = read_json(tutorials_path) if os.path.exists(tutorials_path) else []

    payload = _build_llm_insight(context, identity, history, metrics, tutorials)
    write_json(...)
```

**`_build_llm_prompt` 修改**：在 prompt payload 中增加 `tutorials` 字段

```python
def _build_llm_prompt(context, identity, history, metrics, tutorials=None):
    prompt_payload = {
        "task": {...},
        "identity": identity,
        "history": history,
        "metrics": metrics,
        "tutorials": tutorials or [],  # 新增
        "output_schema": {...},
    }
    # prompt 指令中增加：
    # "5. 输入中的 tutorials 包含各题的官方题解，请结合题解内容分析队伍的算法能力特点。
    #    例如：队伍在某类算法上通过率高但题解显示该类题目难度较低，说明基础扎实但进阶不足。
    #    如果 tutorials 为空，则仅基于 tags 和 metrics 进行分析。"
```

### 7. `docs/stage_schema.md` — 文档更新

- Problem 实体增加 `tutorial_content` 字段说明
- 新增 tutorials artifact 协议说明
- 更新 collect 阶段输出描述

## 产出 artifact 路径

```
data/raw/tutorials/tutorials.json
```

结构：

```json
[
  {
    "problem_id": "cf_1987_A",
    "contest_id": "cf_1987",
    "label": "A",
    "content": "本题要求实现一个简单的模拟……关键思路是……"
  }
]
```

## 容错与降级策略

| 场景 | 行为 |
|------|------|
| Tutorial 页面不存在（比赛无官方题解） | 跳过该比赛，不报错 |
| 网络抓取失败 | 跳过，不报错，不影响主流程 |
| HTML 解析失败（页面结构变化） | 跳过，不报错 |
| tutorials.json 不存在 | analyze 阶段正常运行，prompt 中 tutorials 为空列表 |
| 单题题解过长 | 截取前 2000 字符 |

## 实现顺序

1. `codeforces_client.py` — 新增 `fetch_page`
2. `tutorial_fetcher.py` — 新建，实现抓取与解析
3. `codeforces_collector.py` — 调用 tutorial 抓取，写入 raw artifact
4. `schemas.py` — Problem 增加 `tutorial_content`
5. `normalizer.py` — 透传 `tutorial_content`，关联 tutorials
6. `insight_generator.py` — 读取 tutorials，扩展 prompt
7. `docs/stage_schema.md` — 文档同步更新

## 测试

- `tutorial_fetcher.py` 的 HTML 解析函数应有单元测试（构造 mock HTML）
- 验证 tutorials.json 缺失时 analyze 阶段不报错
- 验证 tutorials 内容正确出现在 LLM prompt 中
