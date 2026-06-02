# 单页分析站升级计划

## 目标
在当前已输出 HTML 图文报告与 HTML 可视化看板的基础上，继续做“组合推进”：

1. 把图文报告与可视化表达整合成一个更完整的**单页分析站**
2. 增加更丰富的数据图表
3. 强化视觉层次、滚动节奏与微交互

最终让 `outputs/reports/<team>.html` 更像一个可直接演示的正式产品页面，而不是若干卡片的简单组合。

## 当前现状
目前已经有：
- `src/report/markdown_report.py`：生成暗色图文 HTML 报告
- `src/visualize/chart_data.py`：生成浅色 HTML 看板
- `tests/test_pipeline_smoke.py`：已校验 HTML 文件生成

但当前不足在于：
- report 与 visualize 仍是两张独立页面
- 图表类型还比较基础，主要是折线与条带
- 缺少更强的“单页叙事节奏”和产品化完成度

## 设计方向
### 风格方向：竞赛战情档案馆（competitive dossier）
我建议把最终单页 HTML 做成一种：
- 暗色基底
- 编辑型长页面
- 带一点档案馆 / 战报 / 年鉴质感

关键词：
- dramatic editorial
- dossier layout
- analytical but theatrical

页面记忆点建议是：
> 顶部像一页“队伍战情封面”，中段进入数据剖面，后段给出训练矩阵与行动建议。

## 页面结构升级建议
在 `outputs/reports/<team>.html` 中整合为一个长页：

### 1. Hero 封面区
- 队伍名
- 总体 summary
- model_used / generated_at / canonical_id
- 背景装饰与入场动画

### 2. 核心指标区
- stability
- growth
- avg_first_ac
- late_stage_solve_ratio
- 加入更明显的数值层级与状态文字

### 3. 排名趋势区
- 保留折线图
- 增加比赛节点说明
- 让点位 hover / focus 显示 contest 数据

### 4. 题型能力区
- 保留标签条形图
- 补一个“标签胜率矩阵”或密度分布块

### 5. 优势 / 短板对照区
- 左右镜像式布局
- 用明显色彩系统区分 strengths / weaknesses

### 6. 新增能力雷达图（radar）
从现有 tag_distribution 推导若干维度：
- implementation
- graph
- dp / trees / bitmasks / unknown 等按存在值取前若干
- 若样本不足则自动补齐占位维度

用途：
- 让页面出现更有辨识度的“能力轮廓”图

### 7. 新增比赛时间轴 / 历程条
基于 rank_trend / history：
- 每场比赛作为时间节点
- 显示名次、percentile、解题数
- 形成一条“近期表现轨迹”

### 8. 新增训练重点矩阵
基于 metrics + insight 规则化推导 2x2 或 3 列卡片：
- 高优先级补短板
- 稳定性维护
- 冲高难专项

### 9. 结尾 CTA / delivery note
- 提醒报告基于哪些 artifact 生成
- 给出“如何继续重跑 analyze / report”的说明

## 实现范围建议
### 主要改动文件
1. `src/report/markdown_report.py`
   - 继续升级主 HTML 报告
   - 把更多图表与叙事合到 report.html

2. `src/visualize/chart_data.py`
   - 保留为轻量看板页
   - 更像“图表速览副本”
   - 或从 report 提取一部分共享渲染逻辑（若代码量过大）

3. `src/validation/validator.py`
   - 如新增必须图表 key，可同步扩展校验

4. 测试
   - `tests/test_pipeline_smoke.py`
   - 必要时新增 `tests/test_html_outputs.py`

## 图表设计建议
### 本轮优先新增
1. **Radar chart**
   - 用 SVG 画雷达图
   - 表示题型能力轮廓

2. **Timeline**
   - 用 HTML + CSS + 轻量 JS
   - 展示各 contest 的阶段轨迹

3. **Priority matrix / action board**
   - 规则化生成训练重点卡片

### 可后续再加
- 象限图
- 热力格子
- 赛程分段流图

## 交互增强建议
- section 滚动 reveal
- 指标卡 hover 微位移与 glow
- radar / bar / timeline 加载动画
- nav dots 或浮动目录（若页面较长）

## 技术策略
仍然保持当前约束：
- 不引入前端构建工具
- 不引入第三方 chart 库
- 继续用 Python 生成自包含 HTML
- CSS / JS 内联
- 图表用 SVG + 原生 JS

## 风险与控制
1. **report 文件过长**
   - 抽辅助函数：radar、timeline、matrix、sections
2. **图表逻辑与文本逻辑缠绕**
   - 图表构建函数单独拆分，尽量让 render 只做拼接
3. **样本数据不足导致图表难看**
   - 设计空态 / 占位维度与 graceful fallback
4. **测试只校验存在，不校验结构**
   - 增加对新标题和新图表标识的断言

## 实施顺序
1. 先升级 `report.html` 为单页分析站
2. 新增 radar + timeline + training matrix
3. 视需要轻调 `visualize.html` 让其成为配套速览页
4. 更新测试断言新的 section 文案
5. 跑全量测试

## 预期结果
升级后：
- `outputs/reports/<team>.html` 成为主交付单页分析站
- `outputs/visualizations/<team>.html` 成为图表速览副页
- 页面在视觉上更像正式 demo
- 用户打开 report.html 就能看到完整图文叙事 + 多图表组合页面
