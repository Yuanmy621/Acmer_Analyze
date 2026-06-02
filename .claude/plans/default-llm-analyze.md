# 默认启用 LLM analyze 调整计划

## 目标
把当前“显式传 `--enable-llm-insight` 才走 LLM”的行为，调整为“默认所有 analyze 都优先走 LLM，而不是本地规则模板”。

同时保留规则模板作为失败回退路径，避免因为配置缺失或网关异常导致整个 pipeline 大面积不可用。

## 当前现状
目前默认值仍是本地规则模式：
- `src/models/schemas.py` 中 `enable_llm_insight = False`
- `src/orchestrator/task.py` 中 payload 默认读取为 `False`
- `scripts/run_pipeline.py` 里 `--enable-llm-insight` 是显式开关
- `examples/sample_task.json` 里也写的是 `false`

因此当前只有显式开启时才会调用 LLM。

## 拟调整点
### 1. 默认任务配置切到 LLM
修改：
- `src/models/schemas.py`
- `src/orchestrator/task.py`
- `scripts/run_pipeline.py`
- `examples/sample_task.json`

建议改法：
- `AnalysisTask.enable_llm_insight` 默认值从 `False` 改为 `True`
- `build_task_from_payload()` 的默认读取改为 `True`
- CLI 不再把 `--enable-llm-insight` 作为“开启开关”，而是补一个显式关闭开关：
  - `--disable-llm-insight`
- 动态参数模式下，未显式关闭时默认启用 LLM

### 2. 保留 fallback
不改：
- `llm_fallback_to_rule` 仍默认 `True`

原因：
- 默认所有分析都走 LLM 后，如果完全不保留 fallback，当前网关一旦不可用，默认 smoke test 和用户日常运行都会更脆弱。
- 保留 fallback 可以实现“优先 LLM，失败退规则模板”。

### 3. 文档同步
更新：
- `README.md`
- `config/README.md`
- `docs/runtime_flow.md`

说明从：
- “默认 rule-based，显式启用 LLM”

改为：
- “默认优先 LLM，显式关闭时才走本地规则”
- 并说明 fallback 行为

### 4. 测试调整
更新：
- `tests/test_analyze_llm.py`
- 视需要更新 `tests/test_pipeline_smoke.py`

调整点：
- 断言默认配置为启用 LLM
- 但现有 smoke test 不应依赖真实联网，所以仍建议让测试数据中通过 task-file 显式设置：
  - `enable_llm_insight: false`
  或通过 mock 保持稳定

更稳妥的方式是：
- 保持 `examples/sample_task.json` 也切为 `true`
- 然后在 smoke test 里改用测试专用 task 或通过 mock 控制 analyze

为了避免牵动过大，本次更建议：
- 先把默认逻辑改为 LLM
- 再把测试里需要稳定离线的路径显式设置为 `enable_llm_insight=false`

## 预期行为
调整后：
- 用户直接运行 `python3 scripts/run_pipeline.py --task-file ...` 时，默认先走 LLM analyze
- 若 LLM 成功，`outputs/insights/*.json` 中 `model_used` 为真实模型名
- 若 LLM 失败，默认回退到 `rule-based-template`
- 若用户明确不想走 LLM，可传：
  - `--disable-llm-insight`
  或在 task-file 里写：
  - `"enable_llm_insight": false`

## 风险
1. 默认联网行为变强
   - 需要在文档中明确说明 analyze 默认会访问外部模型服务。

2. 测试可能被默认配置影响
   - 需要把离线 smoke test 固定为显式关闭 LLM，确保 CI / 本地测试稳定。

3. 用户网关不兼容当前接口
   - 仍可能 fallback 到本地模板，但至少默认行为已符合“优先走 LLM”的要求。

## 实施顺序
1. 调整 schema / task / CLI 的默认值与开关命名
2. 更新 sample task 和文档
3. 修正测试以保证离线稳定
4. 跑全量测试
