# Plan: 添加 img2img（文生图 / 图生图 Tab）+ 删除 Pollinations 兑底

## Context

项目目前是"文生图"单功能，调用 SD WebUI（首选）或 Pollinations（兑底）。用户要求：

1. **加图生图（img2img）功能**——上传本地图 / 复用上次生成图，两种起始图都支持
2. **加"重绘强度"滑块**（0.0~1.0，默认 0.55）
3. **前端顶部 Tab 切换**（文生图 / 图生图）
4. **删除 Pollinations 兑底**——只保留 SD WebUI（本机已在用，删了行为不变）

## 要修改的文件（5 个）

| 文件 | 改动 | 行数估计 |
|------|------|----------|
| [src/services/image_generator.py](file:///d:/trae/玻璃杯AI生成可视化设计系统/src/services/image_generator.py) | 加 `_generate_img2img()`，删 Pollinations（_generate_pollinations / _fetch_as_data_uri） | 净 +30 行 |
| [app.py](file:///d:/trae/玻璃杯AI生成可视化设计系统/app.py) | 加 `POST /api/img2img` 路由 | +40 行 |
| [frontend/templates/index.html](file:///d:/trae/玻璃杯AI生成可视化设计系统/frontend/templates/index.html) | 加 Tab UI + 起始图选择器 + 强度滑块 + JS 逻辑 | +80 行 |
| [README.md](file:///d:/trae/玻璃杯AI生成可视化设计系统/README.md) | 更新"项目结构"和"核心特性"描述，删 Pollinations 相关说明 | ~20 行改 |
| [prompts_en.md](file:///d:/trae/玻璃杯AI生成可视化设计系统/prompts_en.md) | 删 Pollinations 相关测试说明，保留 SD WebUI 路径 | ~10 行改 |

## 实现细节

### 1. image_generator.py

**新增 `_generate_img2img()`**：

```python
def _generate_img2img(self, init_image_b64, prompt, denoising_strength=0.55, num_images=4):
    """Stable Diffusion WebUI img2img。
    
    init_image_b64: base64 编码的起始图（不带 data:image/png;base64, 前缀）
    denoising_strength: 0.0~1.0，越高越偏离原图
    """
    full_prompt = self.positive_template.format(prompt=prompt)
    payload = {
        "init_images": [init_image_b64],
        "prompt": full_prompt,
        "negative_prompt": self.negative_prompt,
        "denoising_strength": denoising_strength,
        "batch_size": num_images,
        "width": 512, "height": 512,
        "seed": -1, "steps": 25, "cfg_scale": 11,
        "sampler_name": "Euler a",
        "restore_faces": False,
    }
    img2img_url = self.api_url.replace("/txt2img", "/img2img")
    response = requests.post(img2img_url, json=payload, timeout=180)
    response.raise_for_status()
    result = response.json()
    if "images" in result and result["images"]:
        return [f"data:image/png;base64,{img}" for img in result["images"]]
    raise Exception("SD WebUI img2img 返回为空")
```

**删除**：
- `test_connection()` 里 pollinations 分支（L39-43）
- `_generate_pollinations()`（L66-92）
- `_fetch_as_data_uri()`（L94-108）
- `generate_mock()`（L156-160）— 也用不到了
- `POLLINATIONS_BASE` 类常量
- `positive_template` 里加一行 `+ ", " + str(num_images) + " variations"` 类多变体措辞——**不加**，原来已经有 prompt 模板了，不要瞎改

### 2. app.py

**加新路由**（紧跟 `/api/generate` 之后）：

```python
@app.route("/api/img2img", methods=["POST"])
def api_img2img():
    """图生图：multipart/form-data 接收 prompt + 强度 + 起始图。"""
    prompt = request.form.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "设计需求不能为空"}), 400
    if input_guard.is_input_blocked(prompt):
        return jsonify(input_guard.build_blocked_response(prompt))
    strength = float(request.form.get("denoising_strength", 0.55))
    if "init_image" not in request.files:
        return jsonify({"error": "缺少起始图"}), 400
    file = request.files["init_image"]
    init_b64 = base64.b64encode(file.read()).decode("ascii")
    try:
        images = image_gen._generate_img2img(init_b64, prompt, strength)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"images": images, "prompt": prompt, "mode": "img2img"})
```

**删除**：
- `input_guard.build_blocked_response` 调用（如果还有）；保留 input_guard 本身（img2img 也要用）

### 3. frontend/templates/index.html

**HTML 改动**（在 `<h2>个性化设计生成</h2>` 上方加 Tab + 起始图 UI）：

```html
<div class="mode-tabs">
  <button class="tab active" data-mode="txt2img">文生图</button>
  <button class="tab" data-mode="img2img">图生图</button>
</div>

<div id="img2img-options" style="display:none">
  <div class="init-image-source">
    <label><input type="radio" name="init_source" value="upload" checked> 上传本地图</label>
    <label><input type="radio" name="init_source" value="last"> 复用上次生成图</label>
  </div>
  <input type="file" id="init-image-upload" accept="image/*">
  <div id="last-image-preview" style="display:none"></div>
  <div class="slider-row">
    <label>重绘强度：<span id="strength-value">0.55</span></label>
    <input type="range" id="denoising-strength" min="0.0" max="1.0" step="0.05" value="0.55">
  </div>
</div>
```

**JS 改动**：
- `displayImages()` 函数保存 4 张图到 `window.lastGeneratedImages`（base64）
- `generateBtn` click handler 根据当前 Tab 决定调 `/api/generate` 还是 `/api/img2img`
- Tab 切换时显示/隐藏 `#img2img-options`
- 滑块 input 事件更新 `#strength-value` 文字

**CSS 改动**（加 ~30 行）：
- `.mode-tabs` 容器 + `.tab` 按钮 active/inactive 状态
- `.slider-row` 滑块样式
- `.init-image-source` radio 组样式

### 4. README.md

- "核心特性" 表里"文生图"行改"文生图 + 图生图"
- "关键设计决策" 表删 Pollinations 相关 3 行
- "已知限制" 表删 Pollinations 限流那行
- "项目结构" 树里 `image_generator.py` 注释从"文生图（SD WebUI / Pollinations 接入）"改"文生图 / 图生图（SD WebUI 接入）"

### 5. prompts_en.md

- 删 "Pollinations 路径" 相关段落
- 加 "img2img 模式用同样 prompt，附加 `denoising_strength: 0.55`" 提示

## 验证步骤

1. **代码检查**：
   - 跑 `python -c "from src.services.image_generator import ImageGenerator"` 确认导入无误
   - 跑 `python -c "from app import app"` 确认 Flask app 注册无误
2. **端到端测试**（在浏览器，http://127.0.0.1:5000）：
   - [ ] 顶部 Tab 切换可见，"文生图" 默认 active
   - [ ] 点"图生图" Tab：起始图选择器 + 滑块显示
   - [ ] 选上传本地图 → 选一张 PNG → 拖动滑块 → 点"生成设计方案"
   - [ ] 4 张图出来（基于上传图的重绘变体）
   - [ ] 切回"文生图" → 输入 prompt → 4 张新图（和之前一样）
   - [ ] 选"复用上次生成图" → 再生成 → 用的是上一轮的结果图
3. **回归测试**（确保 Pollinations 删干净）：
   - [ ] 全文 `grep -ri pollinations` 应**零结果**（除历史 commit）
   - [ ] 启动 Flask 不应有任何 "Pollinations" 日志
4. **性能测试**：
   - [ ] txt2img 仍 12~15s
   - [ ] img2img 第一次会慢一点（GPU 冷启动），后续 15~20s

## 风险与回退

| 风险 | 缓解 |
|------|------|
| **大改动回归风险** | 一个 commit + 强测试；出问题时 `git revert` 即可 |
| **img2img 端点不存在** | SD WebUI 启用 `--api` 后 img2img 必在；如 404 走同一降级到 500 |
| **起始图太大** | 前端限制 2MB；后端不强校验（SD WebUI 会自己限） |
| **上次生成图失效** | 页面刷新会清空；用 radio 显式提示 |

## 不做的事

- ❌ 不加 Pollinations 兑底（要删干净）
- ❌ 不改 input_guard（img2img 复用同一规则即可）
- ❌ 不改 MOPSO（这是图生图，跟优化算法无关）
- ❌ 不改历史设计记录存储格式（仍是同一份 designs.json）
