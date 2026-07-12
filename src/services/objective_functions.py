import numpy as np


def calculate_wall_uniformity(params):
    """计算壁厚均匀度 (越小越好)
    返回值: 变异系数CV
    """
    target = params["wall_thickness_target"]

    # 模拟壁厚分布：温度越高、压力越稳定，壁厚越均匀
    temp_factor = (params["heating_temp"] - 550) / 150  # 0-1
    pressure_factor = 1 - abs(params["blowing_pressure"] - 0.3) / 0.2  # 0-1

    # 综合因素决定标准差
    std_dev = 0.15 - (temp_factor * 0.08) - (pressure_factor * 0.04)
    std_dev = max(0.02, std_dev)  # 最小标准差

    # 生成模拟壁厚数据
    rng = np.random.default_rng(42)
    wall_thickness = rng.normal(target, std_dev, 100)

    # 计算变异系数
    cv = np.std(wall_thickness) / np.mean(wall_thickness)
    return float(cv)


def calculate_defect_rate(params):
    """计算成品废品率 (越小越好)
    返回值: 废品率 (0-1)
    """
    base_rate = 0.02  # 基础废品率

    # 温度影响：偏离最佳温度(620°C)会增加废品率
    temp_deviation = abs(params["heating_temp"] - 620)
    temp_penalty = temp_deviation / 2000

    # 时间影响：加热时间过短或过长
    time_deviation = abs(params["heating_time"] - 90)
    time_penalty = time_deviation / 3000

    # 压力影响：压力不稳定
    pressure_penalty = abs(params["blowing_pressure"] - 0.3) / 5

    total_rate = base_rate + temp_penalty + time_penalty + pressure_penalty
    return float(min(total_rate, 0.3))  # 最大废品率30%


def calculate_energy_consumption(params):
    """计算加工能耗 (越小越好)
    返回值: 能耗单位
    """
    # 基础能耗 = 温度 × 时间 × 系数
    heating_energy = params["heating_temp"] * params["heating_time"] * 0.1

    # 吹制能耗
    blowing_energy = params["blowing_pressure"] * params["blowing_time"] * 100

    # 冷却能耗：冷却速率越快，后续工艺能耗越低
    cooling_energy = (60 - params["cooling_rate"]) * 10

    total_energy = heating_energy + blowing_energy + cooling_energy
    return float(total_energy)


def calculate_heat_resistance(params):
    """计算耐热安全性 (转换为越小越好)
    返回值: 1 - 耐热指数 (0-1)
    """
    # 耐热温度 = 基础温度 + 冷却速率影响 + 壁厚影响
    base_temp = 120
    cooling_effect = params["cooling_rate"] * 0.8
    thickness_effect = params["wall_thickness_target"] * 5

    heat_temp = base_temp + cooling_effect + thickness_effect

    # 转换为最小化目标：1 - (耐热温度/最大耐热温度)
    max_heat_temp = 200
    return float(1 - (heat_temp / max_heat_temp))
