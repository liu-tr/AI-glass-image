from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import sys
import base64
import csv
import io
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.image_generator import GlassImageGenerator
from services.input_guard import is_input_blocked, find_blocked_term, build_rejection_image
from services.mopso_optimizer import MOPSOOptimizer
from services.objective_functions import (
    calculate_wall_uniformity,
    calculate_defect_rate,
    calculate_energy_consumption,
    calculate_heat_resistance
)
from services.database import JSONDatabase

app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
CORS(app)

# 初始化服务
db = JSONDatabase()

# 文生图 / 图生图服务：仅接入本地 SD WebUI（A1111，需启动时带 --api）
#   - txt2img: http://127.0.0.1:7860/sdapi/v1/txt2img
#   - img2img: http://127.0.0.1:7860/sdapi/v1/img2img
SD_WEBUI_TXT2IMG = "http://127.0.0.1:7860/sdapi/v1/txt2img"
generator = GlassImageGenerator(api_url=SD_WEBUI_TXT2IMG)

# 连接检查改为每次都探活（支持在 Flask 运行后启动 SD WebUI）
def is_sd_available():
    """动态检查 SD WebUI 是否在线，不再依赖启动时的一次性检测。"""
    try:
        generator.test_connection()
        return True
    except Exception:
        return False

# 启动时只打印状态，不再设置全局标志
if is_sd_available():
    print(f"[OK] 已连接 SD WebUI: {SD_WEBUI_TXT2IMG}")
else:
    print("[INFO] SD WebUI 未连接。启动后会自动检测，无需重启 Flask")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def generate_images():
    try:
        prompt = request.json.get('prompt', '')
        lora_weight = request.json.get('lora_weight', 0)
        sampler_name = request.json.get('sampler_name', 'Euler a')
        if not prompt:
            return jsonify({"error": "请输入设计需求"}), 400

        # 输入合规检查：命中工业负面词则直接返回 4 张拒绝提示图
        blocked_term = find_blocked_term(prompt)
        if blocked_term:
            reason = f"输入含工业敏感词「{blocked_term}」"
            images = [build_rejection_image(reason, blocked_term) for _ in range(4)]
        elif is_sd_available():
            images = generator.generate(prompt, num_images=4, lora_weight=lora_weight, sampler_name=sampler_name)
        else:
            return jsonify({"error": "SD WebUI 未连接，无法生成图片"}), 503

        design = db.add_design(prompt, images, mode="txt2img", lora_weight=lora_weight, sampler=sampler_name)
        return jsonify({"success": True, "design": design})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/img2img', methods=['POST'])
def img2img_images():
    """图生图：multipart/form-data 接收 prompt + 强度 + 起始图。"""
    try:
        prompt = request.form.get('prompt', '').strip()
        if not prompt:
            return jsonify({"error": "请输入设计需求"}), 400

        lora_weight = request.form.get('lora_weight', 0, type=float)
        sampler_name = request.form.get('sampler_name', 'Euler a')

        if not is_sd_available():
            return jsonify({"error": "SD WebUI 未连接，无法生成图片"}), 503

        # 输入合规检查
        blocked_term = find_blocked_term(prompt)
        if blocked_term:
            reason = f"输入含工业敏感词「{blocked_term}」"
            images = [build_rejection_image(reason, blocked_term) for _ in range(4)]
            design = db.add_design(prompt, images, mode="img2img", lora_weight=lora_weight, sampler=sampler_name)
            return jsonify({"success": True, "design": design})

        # 强度
        try:
            strength = float(request.form.get('denoising_strength', 0.55))
        except (TypeError, ValueError):
            strength = 0.55

        # 起始图
        if 'init_image' not in request.files:
            return jsonify({"error": "缺少起始图，请上传或选择一张"}), 400
        file = request.files['init_image']
        if not file or not file.filename:
            return jsonify({"error": "起始图无效"}), 400
        init_b64 = base64.b64encode(file.read()).decode('ascii')

        images = generator.generate_img2img(init_b64, prompt, denoising_strength=strength, lora_weight=lora_weight, sampler_name=sampler_name)
        design = db.add_design(prompt, images, mode="img2img", lora_weight=lora_weight, sampler=sampler_name)
        return jsonify({"success": True, "design": design})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_dynamic_bounds(complexity: float) -> dict:
    """根据轮廓复杂度 C 动态计算工艺参数搜索区间。

    原理：
      - C≈0（简约直筒杯）：工艺窗口宽，低温/短时/低压方案可选
      - C≈1（复杂异形杯）：工艺窗口窄，需更高温度/更长持压，冷却更慢

    返回 bounds dict，格式同 MOPSOOptimizer 要求。
    """
    # 简单杯型基础区间（C=0）
    simple = {
        "heating_temp": (550, 700),
        "heating_time": (30, 180),
        "blowing_pressure": (0.1, 0.5),
        "blowing_time": (5, 30),
        "cooling_rate": (10, 50),
        "wall_thickness_target": (2, 5),
    }
    # 复杂杯型收紧区间（C=1）
    complex_bounds = {
        "heating_temp": (580, 680),
        "heating_time": (60, 160),
        "blowing_pressure": (0.2, 0.45),
        "blowing_time": (10, 25),
        "cooling_rate": (5, 40),
        "wall_thickness_target": (3, 5),
    }

    alpha = max(0.0, min(1.0, complexity))  # 确保 0~1
    result = {}
    for key in simple:
        lo_s, hi_s = simple[key]
        lo_c, hi_c = complex_bounds[key]
        lo = lo_s + (lo_c - lo_s) * alpha
        hi = hi_s + (hi_c - hi_s) * alpha
        result[key] = (round(lo, 1), round(hi, 1))
    return result


@app.route('/api/optimize', methods=['POST'])
def optimize_params():
    try:
        design_id = request.json.get('design_id')
        design = db.get_design(design_id)

        if not design:
            return jsonify({"error": "设计方案不存在"}), 404

        # 读取该设计的轮廓复杂度（由 feature_extractor 在生成时提取）
        design_complexity = design.get("complexity") or 0.5

        # 执行MOPSO优化（传入复杂度，动态调整搜索区间 + 目标函数）
        bounds = get_dynamic_bounds(design_complexity)
        optimizer = MOPSOOptimizer(
            objective_functions=[
                calculate_wall_uniformity,
                calculate_defect_rate,
                calculate_energy_consumption,
                calculate_heat_resistance
            ],
            bounds=bounds,
            complexity=design_complexity
        )

        pareto_front, logbook = optimizer.optimize()

        # 选择最优解（综合权重）
        best_solution = optimizer.select_best_solution(pareto_front)

        # 获取迭代历史用于可视化
        iteration_history = optimizer.get_iteration_history(logbook)

        # 更新数据库
        db.update_design(design_id, {
            "optimization_result": {
                "params": {k: round(float(v), 2)
                           for k, v in zip(list(optimizer.bounds.keys()), best_solution)},
                "objectives": {
                    "wall_uniformity": round(best_solution.fitness.values[0] * 100, 2),
                    "defect_rate": round(best_solution.fitness.values[1] * 100, 2),
                    "energy_consumption": round(best_solution.fitness.values[2], 2),
                    "heat_resistance": round((1 - best_solution.fitness.values[3]) * 100, 2)
                },
                "pareto_front": optimizer.pareto_to_dict(pareto_front),
                "iteration_history": iteration_history
            }
        })

        return jsonify({"success": True, "design": db.get_design(design_id)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/designs', methods=['GET'])
def get_all_designs():
    try:
        designs = db.get_all_designs()
        return jsonify({"success": True, "designs": designs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/designs/<design_id>', methods=['GET'])
def get_design(design_id):
    try:
        design = db.get_design(design_id)
        if not design:
            return jsonify({"error": "设计方案不存在"}), 404
        return jsonify({"success": True, "design": design})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/designs/<design_id>', methods=['PUT'])
def update_design(design_id):
    try:
        updates = request.json
        db.update_design(design_id, updates)
        return jsonify({"success": True, "design": db.get_design(design_id)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/designs/<design_id>', methods=['DELETE'])
def delete_design(design_id):
    try:
        db.delete_design(design_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/designs/export/csv', methods=['GET'])
def export_designs_csv():
    """导出全部设计方案为 CSV 文件。"""
    try:
        designs = db.get_all_designs()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "模式", "Prompt", "LoRA权重", "采样器",
                          "轮廓复杂度", "选中图", "创建时间", "已优化", "壁厚均匀度",
                          "废品率", "能耗", "耐热性"])
        for d in designs:
            opt = d.get("optimization_result") or {}
            objs = opt.get("objectives", {}) if opt else {}
            writer.writerow([
                d.get("id", ""),
                d.get("mode", "txt2img"),
                d.get("prompt", ""),
                d.get("lora_weight", 0),
                d.get("sampler", "Euler a"),
                d.get("complexity", ""),
                "是" if d.get("selected_image") else "否",
                d.get("created_at", ""),
                "是" if opt else "否",
                objs.get("wall_uniformity", ""),
                objs.get("defect_rate", ""),
                objs.get("energy_consumption", ""),
                objs.get("heat_resistance", ""),
            ])
        csv_bytes = output.getvalue().encode('utf-8-sig')
        return (
            csv_bytes,
            200,
            {
                "Content-Type": "text/csv; charset=utf-8-sig",
                "Content-Disposition": f"attachment; filename=designs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            },
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # debug=False 避免 stat 文件变化触发 reload worker 多开，占满 5000 端口
    app.run(debug=False, host='0.0.0.0', port=5000)
