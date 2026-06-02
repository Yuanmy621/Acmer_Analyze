# 浏览器插件与本地 bridge 使用说明

本文说明如何使用当前仓库中的 **browser bridge + 插件 + pipeline** 完整链路。

---

## 1. 当前能力范围

当前已经支持：

- 在浏览器插件中输入 `target_team` 与 `aliases`
- 在 Codeforces standings 页面提取结构化数据
- 优先通过 Codeforces standings API 提取数据，失败时再回退到 DOM 解析
- 发送到本地 bridge
- bridge 自动导入 raw 数据并触发分析
- 返回 `run_id`、状态、报告路径与验收结果路径

当前仍需注意：

- Codeforces standings 页提取逻辑仍在持续打磨
- 插件首版优先支持 Codeforces
- 复杂页面结构变化时可能需要继续调整 `content.js`

---

## 2. 启动本地 bridge

在仓库根目录执行：

```bash
python3 scripts/run_bridge.py
```

启动成功后会监听：

- `http://127.0.0.1:8765`

---

## 3. 加载浏览器插件

以 Chrome / Edge 为例：

1. 打开扩展管理页面
2. 开启“开发者模式”
3. 选择“加载已解压的扩展程序”
4. 选择目录：

```text
plugins/browser-extension
```

---

## 4. 在 Codeforces standings 页面使用

### 步骤 1：打开 standings 页面
例如：

```text
https://codeforces.com/contest/1987/standings
```

### 步骤 2：打开插件 popup
点击浏览器工具栏中的插件图标。

### 步骤 3：填写目标队伍信息
在 popup 中填写：

- `target_team`
- `aliases`（多个别名用逗号分隔）

例如：

- `target_team`: `tourist`
- `aliases`: `tourist`

### 步骤 4：点击“发送并开始分析”
插件会自动：

1. 判断当前是否为 Codeforces standings 页面
2. 优先调用页面上下文可访问的 Codeforces standings API
3. 若 API 提取失败，则自动回退到 DOM 解析
4. 组装 bridge payload
5. 调用本地 bridge `import-and-run`
6. bridge 导入 raw 数据
7. 自动从 `normalize` 开始执行 pipeline
8. 返回：
   - `run_id`
   - `status`
   - `report_path`
   - `validation_path`

---

## 5. 结果查看

### 插件 popup 中可看到

- 运行状态
- `run_id`
- report 路径
- validation 路径

### 仓库中的实际结果路径

- report：
  - `outputs/reports/<team>.md`
- visualization：
  - `outputs/visualizations/<team>.json`
- validation：
  - `outputs/validation/<team>.json`
- bridge run summary：
  - `outputs/bridge_runs/<run_id>.json`

---

## 6. 手动查询 bridge 运行状态

如果你需要在浏览器外部检查 bridge 运行状态，可以请求：

```text
GET /api/bridge/runs/<run_id>
```

返回中会包含：

- `status`
- `executed_stages`
- `report_path`
- `visualization_path`
- `validation_path`
- `error`
- `error_type`

---

## 7. 常见错误

### 7.1 bridge 未启动

表现：

- 插件提示发送失败
- 本地 `127.0.0.1:8765` 无响应

处理：

```bash
python3 scripts/run_bridge.py
```

### 7.2 页面提取失败

表现：

- popup 显示页面提取失败

可能原因：

- 当前页面不是可识别的 Codeforces standings 页
- 页面结构变化
- API / DOM fallback 都未成功提取

### 7.3 bridge 执行失败

表现：

- popup 显示 `bridge 执行失败`
- 返回带 `error_type`

当前常见 `error_type` 包括：

- `payload_validation_error`
- `pipeline_validation_error`
- `pipeline_runtime_error`
- `bridge_internal_error`
- `invalid_json`
- `run_not_found`

---

## 8. 推荐使用方式

当前阶段，推荐优先级如下：

1. **动态 CLI + 实时抓取 Codeforces**
2. **browser bridge + 插件导入**
3. task-file / examples 用于测试和回归

如果你要稳定分析一支队伍，主命令仍然是：

```bash
python3 scripts/run_pipeline.py \
  --source codeforces \
  --target-team tourist \
  --codeforces-handle tourist \
  --max-contests 5
```

而插件链路更适合：

- 从网页端快速导入
- 交互式试用
- 验证 browser bridge 工作流
