# 分析数据清理功能计划

## 目标
新增一个安全、可控的“清除现有分析数据”方法，并满足用户要求：**同时支持按队伍清理与全量清理**。

## 当前现状
当前仓库已有的分析产物路径主要包括：
- `data/raw/contests/contests.json`
- `data/raw/problems/problems.json`
- `data/raw/standings/standings.json`
- `data/raw/bridge_imports/*.json`
- `data/normalized/...`
- `data/intermediate/team_identity/*.json`
- `data/intermediate/team_history/*.json`
- `data/derived/team_metrics/*.json`
- `outputs/insights/*.json`
- `outputs/reports/*`
- `outputs/visualizations/*`
- `outputs/validation/*.json`
- `outputs/bridge_runs/*.json`

当前没有专门的清理入口，只能手工删文件。

## 用户选择
用户已经明确：
- 需要 **两种都支持**
  1. 按队伍清理
  2. 全量清理

## 设计原则
1. **默认优先安全**
   - 默认推荐按队伍清理，而不是直接全量删。
2. **CLI 入口清晰**
   - 不混在主 pipeline 执行逻辑里隐式触发。
3. **删除范围可预测**
   - 返回被删除的路径列表和统计。
4. **不误删 fixture / examples / docs / src**
   - 仅限 `data/` 与 `outputs/` 中明确的运行产物。

## 实现建议
### 方案
在 `scripts/run_pipeline.py` 中增加清理模式，或者新增独立脚本。

我更建议：
- **新增独立脚本**：`scripts/clear_artifacts.py`

原因：
- 语义更清晰
- 不污染主 pipeline CLI
- 更符合“危险动作单独入口”的习惯

### 支持两种模式
#### 1. 按队伍清理
示例：
```bash
python3 scripts/clear_artifacts.py --target-team "ZJU Alpha"
```

行为：
- 通过 `canonical_id = team_zju_alpha` 定位并删除：
  - `data/intermediate/team_identity/team_zju_alpha.json`
  - `data/intermediate/team_history/team_zju_alpha.json`
  - `data/derived/team_metrics/team_zju_alpha.json`
  - `outputs/insights/team_zju_alpha.json`
  - `outputs/reports/team_zju_alpha.*`
  - `outputs/visualizations/team_zju_alpha.*`
  - `outputs/validation/team_zju_alpha.json`
- **不删除共享 raw/normalized 文件**，因为这些文件当前不是按队伍拆分，按队伍清理无法安全删。

#### 2. 全量清理
示例：
```bash
python3 scripts/clear_artifacts.py --all
```

行为：
- 清除当前仓库运行生成的分析数据：
  - `data/raw/contests/contests.json`
  - `data/raw/problems/problems.json`
  - `data/raw/standings/standings.json`
  - `data/raw/bridge_imports/*.json`
  - `data/normalized/contests/contests.json`
  - `data/normalized/problems/problems.json`
  - `data/normalized/standings/standings.json`
  - `data/intermediate/team_identity/*.json`
  - `data/intermediate/team_history/*.json`
  - `data/derived/team_metrics/*.json`
  - `outputs/insights/*`
  - `outputs/reports/*`
  - `outputs/visualizations/*`
  - `outputs/validation/*`
  - `outputs/bridge_runs/*`
- 保留目录本身，不删目录结构。
- 保留 `.gitkeep` 之类非产物文件（若存在）。

## 文件建议
### 新增
- `scripts/clear_artifacts.py`

### 可选复用
- `src/orchestrator/context.py` 的 `canonical_id` 规则

更稳妥的方式是：
- 在清理脚本里复用 `AnalysisTask + PipelineContext` 来生成 canonical_id，避免规则漂移。

## CLI 参数建议
### 必选二选一
- `--target-team <name>`
- `--all`

### 可选参数
- `--dry-run`
  - 只打印将删除哪些文件，不实际删除
- `--include-bridge-runs`
  - 针对按队伍清理时，是否同时删除 `outputs/bridge_runs/` 中与该队伍相关的 summary

## 输出建议
清理脚本执行后输出 JSON，例如：
```json
{
  "mode": "target_team",
  "target_team": "ZJU Alpha",
  "canonical_id": "team_zju_alpha",
  "deleted": [
    "data/intermediate/team_identity/team_zju_alpha.json",
    "outputs/reports/team_zju_alpha.html"
  ],
  "missing": [
    "outputs/visualizations/team_zju_alpha.html"
  ]
}
```

## 测试建议
新增：
- `tests/test_clear_artifacts.py`

覆盖：
1. `--target-team` 时仅删除该队伍对应中间与输出文件
2. `--target-team` 时不删除共享 raw/normalized 文件
3. `--all` 时删除 data/outputs 下目标产物
4. `--dry-run` 时不实际删除文件

## 风险与控制
1. **按队伍清理无法精确清除 raw/normalized**
   - 明确文档说明：按队伍模式只删按队伍命名的 artifact，不删共享文件。
2. **全量清理动作不可逆**
   - 增加 `--all` 显式参数，避免误触。
   - 可选支持 `--dry-run` 先预览。
3. **规则重复实现**
   - 尽量复用现有 `PipelineContext.canonical_id` 逻辑。

## 实施顺序
1. 新增 `scripts/clear_artifacts.py`
2. 实现按队伍 / 全量 / dry-run 三种行为
3. 增加测试
4. 更新 README 或 runtime_flow 补充清理命令说明
5. 跑测试
