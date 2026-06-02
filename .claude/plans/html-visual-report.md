# HTML 可视化报告实现计划

## 目标
针对当前分析结果，输出一份带可视化图表与分析图文的 **HTML 报告**，使最终交付不再只有 Markdown 和 JSON，而是可直接在浏览器中阅读的图文页面。

重点是：
- 呈现排名趋势、题型能力分布、优势/短板/建议
- 保持当前 pipeline artifact 分层
- 让 `report` / `visualize` / `validate_final` 对 HTML 产物有明确支持
- 设计上避免通用模板感，做出具有辨识度的视觉表达

## 当前现状
1. `src/report/markdown_report.py` 只输出：
   - `outputs/reports/<team>.md`
   - `outputs/reports/<team>.artifact.json`
2. `src/visualize/chart_data.py` 只输出：
   - `outputs/visualizations/<team>.json`
   - `outputs/visualizations/<team>.artifact.json`
3. `docs/conventions/report_rules.md` 已明确：
   - Markdown 与 HTML 报告应尽量保持 section 结构一致
4. `docs/stage_schema.md` 已允许：
   - `ReportArtifact.format` 为 `md` / `html`
   - `VisualizationArtifact.format` 为 `json` / `html`
5. `src/validation/validator.py` 当前只检查 section 和 chart_keys，不检查 HTML 文件是否存在。

## 设计方向
我建议这次 HTML 呈现采用：

### 风格方向：暗色编辑型数据简报（editorial dashboard）
特点：
- 深色背景 + 铜金 / 冰蓝点缀
- 标题用高识别度 display serif，正文用更克制的书面字体
- 页面像“竞赛战报 + 数据特刊”而不是普通后台
- 通过大数字卡片、斜切分区、密度适中的图表与标签云增强记忆点

### 页面结构
建议单页 HTML，包含以下 section：
1. Hero / 封面区
   - 队伍名
   - summary
   - model_used / generated_at
2. 核心指标卡
   - stability_score
   - growth_score
   - avg_first_ac_minute
   - late_stage_solve_ratio
3. 排名趋势图
   - SVG / CSS 绘制折线图
4. 题型分布图
   - 标签条形图 / 胶囊图 / 比例条
5. 优势与短板双栏
6. 训练建议卡片
7. 阶段分析长文区
8. 数据来源与 artifact 说明

## 拟修改范围
### 1. 扩展 report 阶段，输出 HTML 报告
修改：
- `src/report/markdown_report.py`

建议：
- 保留现有 Markdown 输出
- 新增 HTML 渲染函数，例如：
  - `_render_html_report(...)`
- 生成：
  - `outputs/reports/<team>.html`
- `report artifact` 需要重新设计：
  - 当前只有单个 `format` / `path`
  - 可以改为保留主格式为 `html`，并增加 `alternate_paths`
  - 或直接继续让 artifact 指向 HTML，把 Markdown 视为附带产物

更稳妥的方式：
- artifact 以 HTML 为主交付
- Markdown 继续生成但不作为主 artifact path

### 2. 扩展 visualize 阶段，输出 HTML 可视化页
修改：
- `src/visualize/chart_data.py`

建议：
- 保留当前 JSON 数据输出
- 额外生成：
  - `outputs/visualizations/<team>.html`
- 由 visualize 阶段输出“纯图表导向 HTML 页面”
- 与 report 阶段的 HTML 报告区分：
  - report = 图文叙事
  - visualize = 图表面板 / 数据看板

### 3. HTML 技术实现方式
不新增前端工程和构建链，继续遵守当前仓库“标准库最小实现”风格：
- 直接由 Python 拼接 HTML 字符串
- CSS 内联到 `<style>`
- JS 内联到 `<script>`
- 图表优先用：
  - 原生 SVG
  - 少量原生 JS
  - 不引入 npm / bundler

这样可保证：
- 无需额外依赖
- 本地双击即可查看
- artifact 更自包含

### 4. 视觉实现细节
HTML 报告中建议加入：
- 背景层次：径向光晕 + 极轻噪点 + 细网格纹理
- 标题字体与正文的明显对比
- section 标题采用大写小字号的 editorial label
- 指标卡 hover 微动效
- 趋势线加载动画
- 标签条形图渐进显示
- strengths / weaknesses 用不同色系与图标语义区分

### 5. artifact 与验证逻辑同步
修改：
- `src/validation/validator.py`
- 必要时同步 `docs/stage_schema.md`

建议新增检查：
- `outputs/reports/<team>.html` 是否存在
- `outputs/visualizations/<team>.html` 是否存在
- artifact path 是否与主交付一致

### 6. 测试补充
建议新增或更新：
- `tests/test_pipeline_smoke.py`
- 新增 `tests/test_html_outputs.py`（如需要）

检查点：
1. 跑完整 pipeline 后，报告 HTML 存在
2. 可视化 HTML 存在
3. 报告 HTML 中包含核心 section 标题
4. 可视化 HTML 中包含图表 key / canonical_id
5. validation 仍然通过

## 关键实现选择
### 方案选择
我建议采用：
- **report 阶段：生成 Markdown + HTML 报告**
- **visualize 阶段：生成 JSON + HTML 数据看板**

原因：
- 与现有架构最一致
- report 与 visualize 的职责仍清晰分层
- 既有“适合阅读”的页面，也有“偏图表”的页面

### 不建议本次做的事情
- 不引入 React / Vue / Tailwind / Vite
- 不上 canvas 图表库
- 不在当前轮次做多页面应用
- 不把所有 HTML 都塞到一个 stage，避免边界模糊

## 预期交付物
本次完成后，预计新增或稳定输出：
- `outputs/reports/<team>.md`
- `outputs/reports/<team>.html`
- `outputs/reports/<team>.artifact.json`
- `outputs/visualizations/<team>.json`
- `outputs/visualizations/<team>.html`
- `outputs/visualizations/<team>.artifact.json`

## 风险与应对
1. **HTML 拼接代码变长**
   - 通过拆分小的渲染函数控制复杂度。
2. **图表表达有限**
   - 先用 SVG 折线图 + 条形标签图满足第一版交付。
3. **artifact 语义变化**
   - 文档与验证同步调整，避免漂移。
4. **视觉太普通**
   - 明确采用 editorial dark briefing 风格，不做通用后台样式。

## 实施顺序
1. 先改 `report`，生成 HTML 图文报告
2. 再改 `visualize`，生成 HTML 图表页
3. 更新 validation 检查 HTML 产物
4. 更新 README / 规则文档中 HTML 输出说明
5. 运行测试并验证生成结果
