# config 目录说明

本目录用于保存后续配置文件。

未来可在此放置：

- 数据源配置
- 任务配置
- 身份映射配置
- 报告模板配置
- 运行参数配置
- LLM analyze 相关配置说明

## 当前 LLM analyze 配置约定

当前 `analyze` 阶段默认会优先接入大模型，配置优先级如下：

1. CLI 显式参数
   - `--llm-model`
   - `--llm-settings-path`
2. 进程环境变量
   - `ANTHROPIC_BASE_URL`
   - `ANTHROPIC_AUTH_TOKEN`
   - `ANTHROPIC_MODEL`
3. `~/.claude/settings.json`
   - `env.ANTHROPIC_BASE_URL`
   - `env.ANTHROPIC_AUTH_TOKEN`
   - `env.ANTHROPIC_MODEL`
   - 顶层 `model`

默认运行时会先尝试 LLM analyze：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json
```

若希望指定模型或设置文件：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --llm-model gpt-5.4 \
  --llm-settings-path ~/.claude/settings.json
```

若希望显式关闭 LLM、改走本地规则模板：

```bash
python3 scripts/run_pipeline.py \
  --task-file examples/sample_task.json \
  --disable-llm-insight
```

默认在 LLM 调用失败时会回退到 `rule-based-template`；若不希望回退，可增加：

```bash
--disable-llm-fallback
```
