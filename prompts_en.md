# 英文 prompt 测试集

> 给 SD WebUI 真实模式用的结构化英文 prompt。CF 11 + 这些 prompt 在 SD1.5 512×512 上出图质量稳定。
>
> 实际使用：在前端中文输入框填中文 → 系统会自动拼接到 `positive_template`（`image_generator.py:25`），由 SD WebUI 处理。
> 这里列的英文 prompt 是用来"在 SD WebUI 页面里手动测"或"绕过中文→英文丢信息"场景的。

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

## Negative prompt（已硬编码到 image_generator.py:30-35，不要复制到前端）

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
