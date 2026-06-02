# 接入 LLM analyze 计划

## 目标
把当前 `analyze` 阶段从纯规则模板升级为“可真正调用大模型生成分析结论”的实现，同时保留 deterministic metrics 作为输入基础，并提供 rule-based fallback，保证在未配置或调用失败时流水线仍可运行。

参考配置来源：`/Users/mac148/.claude/settings.json`
- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`
- 顶层 `model`

## 当前现状
1. 当前 analyze 入口是 `src/analyzer/insight_generator.py`。
2. 当前输出明确写死：`model_used = "rule-based-template"`。
3. `scripts/run_pipeline.py` 只有 `--skip-analyze`，没有 LLM 配置开关。
4. 仓库当前没有专门的配置文件实现，`config/README.md` 仅保留占位说明。
5. 测试以 `tests/test_pipeline_smoke.py` 和 bridge 用例为主，默认会跑完整 pipeline。

## 设计原则
1. **LLM 只负责解释层**
   - `compute_metrics` 仍保持确定性计算。
   - `analyze` 基于 metrics + history + identity 生成高层结论。

2. **优先复用用户现有 Claude 风格配置**
   - 从环境变量读取：`ANTHROPIC_BASE_URL`、`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_MODEL`。
   - 若环境变量缺失，再尝试读取 `~/.claude/settings.json` 中的 `env` 字段与顶层 `model`。

3. **不新增第三方依赖**
   - 继续使用 Python 标准库 `urllib.request` 发送 HTTP 请求。
   - 避免引入 `anthropic` SDK，保持仓库当前“标准库最小实现”风格。

4. **失败可退化**
   - 配置缺失、网络失败、响应解析失败时，默认退回 rule-based analyze。
   - 产物中保留 `model_used` 与额外 metadata，便于溯源。

5. **显式开关**
   - 支持用户显式启用/关闭 LLM analyze，避免默认隐式联网让行为不透明。

## 拟修改范围
### 1. 新增 LLM 配置与客户端模块
建议新增：
- `src/analyzer/llm_client.py`
- `src/analyzer/prompt_builder.py`（可选，若不拆则并入 `insight_generator.py`）

职责：
- 解析环境变量 / `~/.claude/settings.json`
- 组装请求头与请求体
- 调用兼容 Chat Completions 风格接口
- 提取模型返回文本

### 2. 扩展任务配置结构
修改：
- `src/models/schemas.py`
- `src/orchestrator/task.py`
- `scripts/run_pipeline.py`

新增字段建议：
- `enable_llm_insight: bool = False`
- `llm_provider: str | None = None`（先可默认 anthropic-compatible）
- `llm_model: str | None = None`
- `llm_settings_path: str | None = None`
- `llm_fallback_to_rule: bool = True`

CLI 增加参数建议：
- `--enable-llm-insight`
- `--disable-llm-fallback`
- `--llm-model`
- `--llm-settings-path`

默认行为：
- 不加 `--enable-llm-insight` 时，继续使用现有 rule-based analyze。
- 加了后优先走 LLM，失败时默认 fallback。

### 3. 重构 analyze 阶段
修改：
- `src/analyzer/insight_generator.py`

实现结构建议：
- 保留现有 rule-based 逻辑，抽成 `_build_rule_based_insight(...)`
- 新增 `_build_llm_prompt(...)`
- 新增 `_run_llm_analyze(...)`
- `run_analyze(...)` 中按任务开关选择：
  1. 若未启用 LLM → 走 rule-based
  2. 若启用 LLM → 调用 LLM
  3. 若失败且允许 fallback → 回退 rule-based，并记录 fallback 原因
  4. 若失败且不允许 fallback → 抛错中断

建议 LLM 输出格式：
- 要求模型只返回 JSON
- 字段：`strengths`、`weaknesses`、`summary`、`training_advice`、`stage_analysis`
- 解析失败则视为 LLM 调用失败

### 4. 更新 bridge 自动运行路径
`bridge/handlers.py` 当前 import-and-run 默认写死：
- `generate_visualize=True`
- `generate_insight=True`

若要让 bridge 也可触发 LLM analyze，可考虑：
- 先不动 bridge 请求协议，保持默认 `enable_llm_insight=False`
- 或在 bridge payload 的 `metadata` 中预留字段，后续再扩展

为了控制范围，本次建议**先不让 bridge 默认启用 LLM**，避免浏览器侧请求直接触发外部 API。

### 5. 更新文档
建议同步更新：
- `README.md`
- `docs/runtime_flow.md`
- `docs/architecture.md`
- `config/README.md`

至少说明：
- analyze 现支持 rule-based / LLM 两种模式
- LLM 配置读取优先级
- CLI 启用方式
- fallback 行为

### 6. 测试补充
建议新增测试：
- `tests/test_analyze_llm.py`

覆盖：
1. 未启用 LLM 时，仍输出 rule-based 结果
2. 启用 LLM 且 mock 成功响应时，输出 LLM 结果
3. 启用 LLM 且 mock 失败时，默认 fallback 成 rule-based
4. 禁用 fallback 时，LLM 失败会中断 pipeline

同时更新现有 smoke test：
- 保持默认不启用 LLM，因此现有测试应继续稳定通过

## 关键实现细节
### 配置读取优先级
1. CLI 显式传入 `--llm-model` / `--llm-settings-path`
2. 进程环境变量
3. `~/.claude/settings.json` 的 `env` 和顶层 `model`
4. 默认值（如无 model 则使用 `gpt-5.4` 仅作兜底）

### 兼容接口形状
由于 `ANTHROPIC_BASE_URL` 当前看起来是网关地址而非官方固定端点，建议客户端做“Anthropic-compatible messages API”优先设计，但留出端点可配置，例如：
- 默认请求：`{base_url}/v1/messages`
- 若后续网关实际是 OpenAI chat completions 风格，再根据返回错误调整

为降低首次改动风险，本次实现建议：
- 在客户端内集中处理 endpoint 拼接
- 若收到明显的 404 / unsupported 结构，再给出清晰异常

如果用户的网关实际是 OpenAI 兼容而不是 Anthropic 兼容，则第二轮可再适配。

## 风险与应对
1. **网关协议不确定**
   - 先封装独立客户端模块，减少后续调整影响面。
   - 首版可以优先按最可能的兼容格式实现，并通过 mock 测试保证本地稳定。

2. **测试环境不能真实联网**
   - 测试全部 mock HTTP 层，不依赖外网。

3. **输出不稳定**
   - 使用 JSON-only prompt，并保留 fallback。

4. **敏感配置泄露**
   - 不把 `settings.json` 内容写入仓库。
   - 日志与 artifact 中不记录 token，只记录 `model_used`、provider、fallback 状态。

## 实施顺序
1. 新增 LLM 配置读取与 HTTP 客户端
2. 扩展 `AnalysisTask` 和 CLI 参数
3. 重构 `run_analyze` 为 LLM + fallback 双路径
4. 补充/更新测试
5. 更新 README / runtime_flow / config 说明
6. 跑完整测试

## 预期结果
- 用户可通过 CLI 显式启用 LLM analyze。
- analyze 阶段可实际读取 `~/.claude/settings.json` 参考配置并调用外部模型接口。
- 未启用或调用失败时仍可安全回退到当前规则模板。
- 默认测试与本地最小流水线保持稳定。
