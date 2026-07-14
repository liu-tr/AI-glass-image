# 英文 prompt 测试集

> 给 SD WebUI 用的结构化英文 prompt。CFG 11 + 这些 prompt 在 SD1.5 512×512 上出图质量稳定。
>
> 实际使用：在前端中文输入框填中文 → 系统会自动拼接到 `positive_template`（`image_generator.py:18-22`），由 SD WebUI 处理。
> 这里列的英文 prompt 是用来"在 SD WebUI 页面里手动测"或"绕过中文→英文丢信息"场景的。
>
> **支持文生图 (txt2img) 和图生图 (img2img) 两种模式**。图生图 mode 下，相同的 prompt 配合不同的 `denoising_strength` 滑块值（0.0~1.0）会得到不同强度的变体。

## 直接复制即用

### 1. 简约透明玻璃杯
```
a minimalist transparent glass cup, cylindrical shape, simple and elegant design,
smooth surface, no decoration, crystal clear glass, professional product photography,
studio lighting, white background, soft shadows, high quality, 8k, photorealistic
```

### 2. 圆柱磨砂玻璃杯
```
a cylindrical frosted glass cup, matte surface texture, soft translucent appearance,
modern minimalist design, even wall thickness, professional product photography,
studio lighting, white background, high quality, 8k, photorealistic, detailed texture
```

### 3. 锥形红酒杯
```
an elegant conical wine glass, long thin stem, transparent crystal glass, classic stemware,
refined silhouette, professional product photography, studio lighting, white background,
soft shadows, high quality, 8k, photorealistic
```

### 4. 方形琥珀色威士忌杯
```
a square amber whiskey tumbler, thick glass walls, warm golden brown color, solid heavy base,
masculine design, professional product photography, studio lighting, dark wood background,
soft shadows, high quality, 8k, photorealistic
```

### 5. 球形鸡尾酒杯
```
a spherical round cocktail glass, long elegant stem, martini-style coupe,
delicate thin glass, luxurious design, professional product photography,
studio lighting, white background, high quality, 8k, photorealistic
```

### 6. 蓝色海洋风高脚杯
```
a tall blue ocean-themed stemmed glass, gradient blue color from deep navy at base
to sky blue at rim, transparent glass, decorative seashell base, artistic design,
professional product photography, studio lighting, white background, high quality,
8k, photorealistic
```

## Negative prompt（已硬编码到 image_generator.py:23-28，不要复制到前端）

```
deformed, broken, cracked, uneven thickness, distorted, blurry, watermark,
text, logo, ugly, unrealistic, cartoon style, anime, drawing, sketch,
indoor, room, scene, person, character, 2d, illustration, painting,
low quality, bad lighting
```

## 在 SD WebUI 页面直接测

1. 浏览器打开 http://127.0.0.1:7860
2. 切到 txt2img
3. 粘贴上面任一 prompt
4. 粘贴上面 negative prompt
5. Steps=25 / CFG=11 / Sampler=Euler a / Size=512×512
6. 点击 Generate

## 在本系统前端测

中文输入框填：
- `简约风格，圆柱形，透明玻璃杯` → 接近 prompt 1
- `圆柱磨砂玻璃，哑光质感` → 接近 prompt 2
- `高脚红酒杯，优雅造型` → 接近 prompt 3
- `方形琥珀色威士忌杯，厚重底座` → 接近 prompt 4
- `球形鸡尾酒杯` → 接近 prompt 5
- `蓝色海洋风高脚杯` → 接近 prompt 6

中文 prompt 会被系统自动加上"glass cup, transparent glass, ..."的工业后缀，比手动 SD 多了**正面模板加成**。

## 图生图 (img2img) 模式

文生图生成的 4 张图，**任选一张**作为起点，进入"图生图"模式后：
- 同样的 prompt 写"我希望改成 XXX" / "改成红色" / "加个手柄"等修饰
- 拖动**重绘强度**滑块：
  - `0.0 ~ 0.3` → 几乎保留原图，只微调颜色/光线
  - `0.4 ~ 0.6` → 保留轮廓，重画细节（**推荐 0.55**）
  - `0.7 ~ 0.9` → 大幅重画，可能失去原图特征
  - `1.0` → 几乎完全重画（接近 txt2img）

**技巧**：先用 txt2img 找一张满意轮廓 → 切 img2img → 把 prompt 改成"same cup, ..." 加变体描述 → 滑块 0.4~0.5 → 4 张变体出来。
