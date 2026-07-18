# 玻璃杯AI生成可视化设计系统

> 基于 Stable Diffusion WebUI（文生图 / 图生图）+ MOPSO 多目标微粒群算法，
> 实现「用户文本驱动玻璃杯设计 → 工艺参数智能寻优」一体化系统。
>
> 课题：**玻璃杯AI生成可视化设计系统**（第三组）

---

## 5 秒上手

```bash
# Windows：双击
run.bat

# 跨平台：命令行
pip install -r requirements.txt
python app.py
```

浏览器打开 [http://localhost:5000](http://localhost:5000) 即可使用。
完整步骤、依赖、停服、FAQ 见 [部署文档.md](部署文档.md)。

---

## 核心特性

| 模块 | 说明 |
|------|------|
| **文生图 / 图生图** | 接入本地 Stable Diffusion WebUI（A1111，需启动时带 --api），txt2img + img2img 双端点；采样器 7 种可选 |
| **动态 LoRA 切换** | 前端下拉选择模型 + 🔄 刷新按钮，新 .safetensors 放入目录后无需改代码即可使用 |
| **输入合规** | `input_guard` 模块在调文生图前预检用户 prompt，命中工业负面词直接返回 SVG 拒绝图，不污染数据 |
| **多目标优化** | MOPSO 自实现：4 目标（壁厚均匀度 / 成品废品率 / 加工能耗 / 耐热安全）、6 维工艺参数、100 代 50 粒子 |
| **可视化（优化结果）** | 4 个图表：方案对比 / 工艺参数表 / 收敛曲线 / 帕累托散点（ECharts 5.4.3）+ ◀ ▶ 导航箭头在各图片优化结果间切换 |
| **按图片索引优化** | 缩略图选中 → 精准优化指定图片；绿色✓/灰色○标识各图优化状态；记录自动标记"待优化/部分优化/已优化" |
| **数据持久化** | JSON 文件数据库（`data/designs.json`），读用 `utf-8-sig` 兼容 BOM、写用 `utf-8` |
| **历史管理** | 搜索按 prompt 筛选；点击展开内联缩略图；每图可下载；一键导出 CSV |

---

## 项目结构

```
玻璃杯AI生成可视化设计系统/
├── app.py                          # Flask 入口（11 个 REST API + SD WebUI 探测/降级 + LoRA 管理）
├── run.bat                         # Windows 一键启动（自动检测+等待 SD WebUI）
├── check_env.bat                   # 启动前环境自检（路径/端口/API 三步）
├── diag.bat                        # 运行中诊断（端口占用/进程/HTTP 健康）
├── requirements.txt
├── README.md
├── 部署文档.md                       # 完整部署+FAQ
├── .gitattributes                   # 强制 .bat 文件 CRLF
├── .gitignore
├── frontend/
│   └── templates/
│       └── index.html              # 前端单页（HTML + CSS + 原生 JS + ECharts）
├── src/
│   ├── __init__.py
│   └── services/
│       ├── __init__.py
│       ├── image_generator.py      # 文生图 / 图生图（SD WebUI 接入）
│       ├── input_guard.py          # 工业负面词预检 + SVG 拒绝图
│       ├── feature_extractor.py    # 生成图特征提取（Canny 边缘检测+轮廓复杂度）
│       ├── mopso_optimizer.py      # MOPSO 多目标优化
│       ├── objective_functions.py  # 4 项工艺目标函数
│       └── database.py             # JSON 文件数据库
├── documents/
│   ├── README.md                    # 文档目录索引
│   ├── 项目文档.md                   # 完整项目说明书
│   └── 数学模型与算法描述.md          # 全部算法公式与数据流说明
└── data/
    ├── .gitkeep
    └── designs.json                # 运行时生成（已 gitignore）
```

`.launcher/` 是秋葉 A绘世启动器便携版的解压目录（47 个 DLL/exe），**不在仓库内**，已在 .gitignore 排除。

---

## 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 前端主页 |
| POST | `/api/generate` | prompt → 4 张设计图（含 input_guard 预检 + sampler 选择 + LoRA 模型选择）|
| POST | `/api/img2img` | 图生图（multipart: prompt + 起始图 + 强度 + sampler + LoRA 模型）|
| POST | `/api/optimize` | 对指定 design_id + image_index 跑 MOPSO（按图精准优化）|
| GET | `/api/loras` | SD WebUI 当前可用 LoRA 模型列表（动态）|
| POST | `/api/loras/refresh` | 通知 SD WebUI 重新扫描 LoRA 目录 |
| GET | `/api/designs` | 全部设计方案 |
| GET | `/api/designs/<id>` | 单个方案 |
| PUT | `/api/designs/<id>` | 更新 |
| DELETE | `/api/designs/<id>` | 删除 |
| GET | `/api/designs/export/csv` | 导出全部方案为 CSV |

---

## 关键设计决策（why）

| 决策 | 原因 |
|------|------|
| **仅本地 SD WebUI，不接 Pollinations** | 本机已有 6GB+ 显存，SD WebUI 出图更稳可控；img2img 需要本地端点；不维护双 provider 减少出错面 |
| **input_guard 预检** | 工业负面词 100% 触发 SD WebUI 内容过滤，混入占位图会污染数据 |
| **SVG 拒绝图** | 内联 data URI，无新增依赖，数据库/前端/优化逻辑零修改 |
| **等权加权和选最优解** | 帕累托前沿上用加权和选一个推荐解，方便用户落地 |
| **图生图强度滑块 0.0~1.0 默认 0.55** | 0.3 保持原图轮廓，0.7 重画，0.55 平衡点；用户可控胜过硬编码 |
| **动态 LoRA 列表 + 刷新** | 模型文件可能随时增减，硬编码路径无法适应；通过 SD WebUI API 实时获取 + 手动刷新，零代码切换 |
| **按图片索引分别优化** | 同设计 4 张图对应不同杯型，应对不同工艺条件；各自存储结果，导航切换查看 |

---

## 已知限制

- 目标函数为经验公式仿真（**不接真实工业仿真**），符合课题「不搭建工业仿真环境」要求
- SD1.5 512×512 batch=4 单次推理 12~30s（GPU 决定上限，SDXL 会更慢）
- 帕累托图仅 2 维（X=壁厚均匀度、Y=加工能耗），4 维信息见收敛曲线 + 对比表
- 数据库为单 JSON 文件，**不支持并发写**

---

## 许可

课题演示用途，源码无开源协议。
