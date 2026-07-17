"""工艺参数多目标优化 — 4 项目标函数。

每个函数均接受 params dict，其中可包含 "complexity" 键（0~1，由
feature_extractor 提取的轮廓复杂度）。未传入时默认 C=0.5（中等复杂度）。

复杂度 C 的影响机制（需求 3.1）：
  - C 越高 → 成型越困难 → 目标函数对参数偏差越敏感
  - C 越低 → 越接近直筒杯 → 工艺窗口更宽
"""

import numpy as np


def calculate_wall_uniformity(params):
    """计算壁厚均匀度（越小越好）。
    返回值: 变异系数 CV（0~1）

    C 影响：复杂轮廓需要更高的基础标准差。
    """
    target = params["wall_thickness_target"]
    complexity = params.get("complexity", 0.5)

    # 温度因子 (0~1)：温度越高越利于均匀
    temp_factor = (params["heating_temp"] - 550) / 150  # 0~1

    # 压力因子 (0~1)：接近 0.3 MPa 最佳
    pressure_factor = 1 - abs(params["blowing_pressure"] - 0.3) / 0.2  # 0~1

    # ---- C 影响 ----
    # 基础标准差：C=0 时 0.12（简单杯型均匀度高）
    #            C=1 时 0.18（复杂杯型均匀度天然差）
    base_std = 0.12 + complexity * 0.06

    # 均匀化能力：从温度和压力中获益的程度随 C 降低
    uniformity_gain = (1 - complexity * 0.4) * (temp_factor * 0.08 + pressure_factor * 0.04)

    std_dev = max(0.02, base_std - uniformity_gain)

    # 生成模拟壁厚数据
    rng = np.random.default_rng(42)
    wall_thickness = rng.normal(target, std_dev, 100)

    cv = np.std(wall_thickness) / np.mean(wall_thickness)
    return float(cv)


def calculate_defect_rate(params):
    """计算成品废品率（越小越好）。
    返回值: 废品率 0~1

    C 影响：复杂轮廓废品基线更高，对参数偏离更敏感。
    """
    complexity = params.get("complexity", 0.5)

    # 基础废品率：C=0 时 1%，C=1 时 4%
    base_rate = 0.01 + complexity * 0.04

    # 温度偏离（最佳 620°C）
    temp_deviation = abs(params["heating_temp"] - 620)
    # C 越高，温度偏离惩罚越大
    temp_sensitivity = 1.0 + complexity * 1.5  # 1.0~2.5x
    temp_penalty = temp_deviation * temp_sensitivity / 2000

    # 时间偏离（最佳 90s）
    time_deviation = abs(params["heating_time"] - 90)
    time_sensitivity = 1.0 + complexity * 1.0  # 1.0~2.0x
    time_penalty = time_deviation * time_sensitivity / 3000

    # 压力影响
    pressure_penalty = abs(params["blowing_pressure"] - 0.3) / 5

    total_rate = base_rate + temp_penalty + time_penalty + pressure_penalty
    return float(min(total_rate, 0.4))  # 最大 40%（复杂杯型放宽上限）


def calculate_energy_consumption(params):
    """计算加工能耗（越小越好）。

    C 影响：复杂轮廓需要更多加热/保温能量。
    """
    complexity = params.get("complexity", 0.5)

    # C 放大系数：C=0 时 ×1.0，C=1 时 ×1.3
    complexity_factor = 1.0 + complexity * 0.3

    # 加热能耗 = 温度 × 时间 × 系数 × 复杂度因子
    heating_energy = params["heating_temp"] * params["heating_time"] * 0.1 * complexity_factor

    # 吹制能耗
    blowing_energy = params["blowing_pressure"] * params["blowing_time"] * 100

    # 冷却能耗：冷却速率越快，后续工艺能耗越低
    cooling_energy = (60 - params["cooling_rate"]) * 10

    total_energy = heating_energy + blowing_energy + cooling_energy
    return float(total_energy)


def calculate_heat_resistance(params):
    """计算耐热安全性（转为越小越好）。
    返回值: 1 - 耐热指数 (0~1)

    C 影响：复杂轮廓存在应力集中点，降低等效耐热温度。
    """
    complexity = params.get("complexity", 0.5)

    base_temp = 120
    cooling_effect = params["cooling_rate"] * 0.8
    thickness_effect = params["wall_thickness_target"] * 5

    # 应力集中折减：C 越高，有效耐热越低
    stress_penalty = complexity * 20  # C=1 时 -20°C
    heat_temp = (base_temp + cooling_effect + thickness_effect) - stress_penalty

    max_heat_temp = 200
    return float(max(0.0, 1 - (heat_temp / max_heat_temp)))
