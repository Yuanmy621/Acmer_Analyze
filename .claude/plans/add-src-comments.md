# 为 src 代码补充注释计划

## 目标
在 `src/` 目录的 Python 源码中补充中文注释，帮助后续维护者快速理解各模块职责、关键辅助函数的用途，以及各 stage 的输入输出关系；同时避免把实现细节逐行翻译成噪声注释。

## 现状判断
- 当前 `src/` 目录约 1300 余行 Python 代码，覆盖 orchestrator、collector、normalize、identity、history、metrics、analyzer、report、visualize、validation、bridge、models 等模块。
- 大多数文件几乎没有注释，仅少数异常类存在 docstring。
- 代码整体比较简洁，函数粒度小、命名清晰，因此更适合补充“模块级 / 函数级 / 关键分支级”注释，而不是逐行注释。

## 注释策略
1. **模块入口与阶段函数优先**
   - 为各 stage 文件中的 `run_*` 函数补充 docstring 或块注释。
   - 说明该阶段读取哪些 artifact、产出哪些 artifact、承担什么职责。

2. **关键辅助函数补充意图说明**
   - 为存在业务含义的辅助函数添加简短注释，例如：
     - `collector/codeforces_collector.py` 中的 ID 构造、standing 转换、contest 选择逻辑。
     - `normalize/normalizer.py` 中的时间与原始字段标准化。
     - `metrics/builder.py` 中的稳定性、成长性、解题节奏等指标计算。
     - `analyzer/insight_generator.py` 中的优势/短板挑选逻辑。
     - `bridge/handlers.py` 中 bridge 导入与一键执行流程。

3. **数据模型以结构说明为主**
   - 在 `models/schemas.py` 中为数据类分组添加注释，说明其对应 pipeline 中的哪类 artifact。
   - 不给每个字段重复写显而易见的注释，避免冗长。

4. **保持风格一致**
   - 注释统一使用中文。
   - 以 docstring 和少量行上方注释为主。
   - 不改动函数行为、字段命名和数据结构；只做注释层面的可读性增强。

## 预计修改范围
优先覆盖以下有实际逻辑的文件：
- `src/orchestrator/context.py`
- `src/orchestrator/task.py`
- `src/orchestrator/pipeline.py`
- `src/collector/*.py`
- `src/normalize/normalizer.py`
- `src/identity/resolver.py`
- `src/history/builder.py`
- `src/metrics/builder.py`
- `src/analyzer/insight_generator.py`
- `src/report/markdown_report.py`
- `src/visualize/chart_data.py`
- `src/validation/validator.py`
- `src/bridge/*.py`
- `src/models/schemas.py`
- `src/models/serde.py`

`__init__.py` 暂不补充无意义注释；若文件仅 1 行且无逻辑，则保持不动。

## 执行步骤
1. 先在核心 orchestrator / model / serde 文件中补充总体说明，建立阅读入口。
2. 再按 pipeline 顺序为各 stage 文件补充职责与关键转换说明。
3. 最后补充 bridge 相关注释，说明 browser bridge 的导入与执行路径。
4. 运行基础测试：`python3 -m unittest discover -s tests -p 'test_*.py'`，确认仅添加注释未破坏行为。

## 风险与控制
- **风险**：注释过密，反而降低可读性。
  - **控制**：只在跨阶段语义、非直观转换、异常分支处添加注释。
- **风险**：注释与实现不一致。
  - **控制**：只描述当前实际行为，不提前写未来设计。

## 交付结果
- `src/` 下主要 Python 实现文件获得统一、适度的中文注释。
- 代码行为不变。
- 测试通过后向用户汇报修改范围与验证结果。
