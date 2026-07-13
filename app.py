from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import sys

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

# 使用 Pollinations.AI 文生图（免注册、免API key）。以后要换服务时改这里的初始化参数即可。
generator = GlassImageGenerator(provider="pollinations")
try:
    generator.test_connection()
    USE_REAL_API = True
    print("✓ 已连接到 Pollinations 文生图服务")
except Exception as e:
    USE_REAL_API = False
    print(f"⚠ 文生图服务不可用，使用模拟模式: {e}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def generate_images():
    try:
        prompt = request.json.get('prompt', '')
        if not prompt:
            return jsonify({"error": "请输入设计需求"}), 400

        # 输入合规检查：命中工业负面词则直接返回 4 张拒绝提示图
        blocked_term = find_blocked_term(prompt)
        if blocked_term:
            reason = f"输入含工业敏感词「{blocked_term}」"
            images = [build_rejection_image(reason, blocked_term) for _ in range(4)]
        elif USE_REAL_API:
            images = generator.generate(prompt, num_images=4)
        else:
            # 模拟生成图片（返回示例图片）
            images = generator.generate_mock(prompt, num_images=4)

        design = db.add_design(prompt, images)
        return jsonify({"success": True, "design": design})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/optimize', methods=['POST'])
def optimize_params():
    try:
        design_id = request.json.get('design_id')
        design = db.get_design(design_id)

        if not design:
            return jsonify({"error": "设计方案不存在"}), 404

        # 执行MOPSO优化
        optimizer = MOPSOOptimizer(
            objective_functions=[
                calculate_wall_uniformity,
                calculate_defect_rate,
                calculate_energy_consumption,
                calculate_heat_resistance
            ],
            bounds={
                "heating_temp": (550, 700),
                "heating_time": (30, 180),
                "blowing_pressure": (0.1, 0.5),
                "blowing_time": (5, 30),
                "cooling_rate": (10, 50),
                "wall_thickness_target": (2, 5)
            }
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
