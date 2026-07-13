# 玻璃杯AI生成可视化设计系统

> 基于文生图模型（Pollinations.AI）+ MOPSO 多目标微粒群算法，
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
| **文生图** | 接入免费的 Pollinations.AI（免注册免 key），服务端并发抓图转 base64 data URI，避开浏览器 ORB 拦截 |
| **输入合规** | `input_guard` 模块在调文生图前预检用户 prompt，命中工业负面词直接返回 SVG 拒绝图，不污染数据 |
| **多目标优化** | MOPSO 自实现：4 目标（壁厚均匀度 / 成品废品率 / 加工能耗 / 耐热安全）、6 维工艺参数、100 代 50 粒子 |
| **可视化** | 4 个图表：方案对比 / 工艺参数表 / 收敛曲线 / 帕累托散点（ECharts 5.4.3） |
| **数据持久化** | JSON 文件数据库（`data/designs.json`），读用 `utf-8-sig` 兼容 BOM、写用 `utf-8` |

---

## 项目结构

```
玻璃杯AI生成可视化设计系统\
├── app.py                          # Flask 入口（6 个 REST API）
├── run.bat                         # Windows 一键启动
├── requirements.txt
├── README.md
├── 部署文档.md
├── frontend\templates\
│   └── index.html                  # 前端单页（HTML + CSS + 原生 JS + ECharts）
├── src\services\
│   ├── image_generator.py          # 文生图（Pollinations 接入）
│   ├── input_guard.py              # 工业负面词预检
│   ├── mopso_optimizer.py          # MOPSO 多目标优化
│   ├── objective_functions.py      # 4 项工艺目标函数
│   └── database.py                 # JSON 文件数据库
└── data\
    ├── .gitkeep
    └── designs.json                # 运行时生成（已 gitignore）
```

---

## 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 前端主页 |
| POST | `/api/generate` | prompt → 4 张设计图（含 input_guard 预检）|
| POST | `/api/optimize` | 对指定 design_id 跑 MOPSO |
| GET | `/api/designs` | 全部设计方案 |
| GET | `/api/designs/<id>` | 单个方案 |
| PUT | `/api/designs/<id>` | 更新 |
| DELETE | `/api/designs/<id>` | 删除 |

---

## 关键设计决策（why）

| 决策 | 原因 |
|------|------|
| **Pollinations 而不是本地 SD** | 课题要求「不部署/不微调生成模型」；Pollinations 免 key、响应快、零部署 |
| **4 张图串行抓取 + view 变体** | 实测同 IP 并发上限约 1，并发 4 张会被 429；串行 + 4 个 view suffix 既稳又保证 4 张视觉不同 |
| **input_guard 预检** | 工业负面词 100% 触发 Pollinations 内容过滤，混入 picsum 占位图会污染数据 |
| **SVG 拒绝图** | 内联 data URI，无新增依赖，数据库/前端/优化逻辑零修改 |
| **等权加权和选最优解** | 帕累托前沿上用加权和选一个推荐解，方便用户落地 |

---

## 已知限制

- 目标函数为经验公式仿真（**不接真实工业仿真**），符合课题「不搭建工业仿真环境」要求
- Pollinations 免费档对单 IP 4 张图理论下限 **8~45s**（上游限流客观限制）
- 帕累托图仅 2 维（X=壁厚均匀度、Y=加工能耗），4 维信息见收敛曲线 + 对比表
- 数据库为单 JSON 文件，**不支持并发写**

---

## 许可

课题演示用途，源码无开源协议。
