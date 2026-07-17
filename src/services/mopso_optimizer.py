import random
import numpy as np


class Fitness:
    """轻量级多目标适应度（最小化：weights全为负）"""
    def __init__(self, weights):
        self.weights = weights
        self.values = ()

    @property
    def valid(self):
        return len(self.values) != 0

    @property
    def wvalues(self):
        return tuple(w * v for w, v in zip(self.weights, self.values))

    def dominates(self, other):
        """基于加权值判断是否支配 other（最大化 wvalues）"""
        not_worse = all(a >= b for a, b in zip(self.wvalues, other.wvalues))
        strictly_better = any(a > b for a, b in zip(self.wvalues, other.wvalues))
        return not_worse and strictly_better

    def __gt__(self, other):
        return self.wvalues > other.wvalues


class Particle(list):
    """粒子：位置向量（list）+ 速度 + 适应度 + 个体历史最优"""
    def __init__(self, values, weights):
        super().__init__(values)
        self.fitness = Fitness(weights)
        self.speed = []
        self.best = None


class ParetoArchive:
    """帕累托非支配解归档（替代 deap.tools.ParetoFront）"""
    def __init__(self, max_size=100):
        self.items = []
        self.max_size = max_size

    def update(self, population):
        for ind in population:
            if not ind.fitness.valid:
                continue
            dominated_by_archive = False
            to_remove = []
            for i, member in enumerate(self.items):
                if member.fitness.dominates(ind.fitness):
                    dominated_by_archive = True
                    break
                if ind.fitness.dominates(member.fitness):
                    to_remove.append(i)
            if dominated_by_archive:
                continue
            for i in reversed(to_remove):
                self.items.pop(i)
            # 避免重复解
            if not any(list(m) == list(ind) for m in self.items):
                clone = Particle(list(ind), ind.fitness.weights)
                clone.fitness.values = ind.fitness.values
                self.items.append(clone)
        self._truncate()

    def _truncate(self):
        """归档超限时，按首目标排序均匀抽稀，保持解集分布"""
        if len(self.items) <= self.max_size:
            return
        self.items.sort(key=lambda p: p.fitness.values[0])
        step = len(self.items) / self.max_size
        self.items = [self.items[int(i * step)] for i in range(self.max_size)]

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)


class MOPSOOptimizer:
    def __init__(self, objective_functions, bounds, num_particles=50, max_gen=100, complexity=0.5):
        self.objectives = objective_functions
        self.bounds = bounds
        self.num_particles = num_particles
        self.max_gen = max_gen
        self.complexity = complexity  # 轮廓复杂度 C（0~1），影响目标函数的行为
        self.param_names = list(bounds.keys())
        self.weights = (-1.0,) * len(objective_functions)  # 全部最小化
        self.iteration_history = []

    def _generate_particle(self):
        values = [random.uniform(self.bounds[name][0], self.bounds[name][1])
                  for name in self.param_names]
        particle = Particle(values, self.weights)
        particle.speed = [random.uniform(-1, 1) for _ in self.param_names]
        particle.best = None
        return particle

    def _evaluate(self, particle):
        params = dict(zip(self.param_names, particle))
        params["complexity"] = self.complexity
        return tuple(func(params) for func in self.objectives)

    def _update_particle(self, particle, global_best, w=0.5, c1=1.5, c2=1.5):
        """更新粒子位置和速度"""
        # 更新个体历史最优
        if particle.best is None or particle.fitness > particle.best.fitness:
            particle.best = Particle(list(particle), self.weights)
            particle.best.fitness.values = particle.fitness.values

        for i in range(len(particle)):
            r1 = random.random()
            r2 = random.random()

            cognitive = c1 * r1 * (particle.best[i] - particle[i])
            social = c2 * r2 * (global_best[i] - particle[i])

            particle.speed[i] = w * particle.speed[i] + cognitive + social

            # 速度限制
            max_speed = (self.bounds[self.param_names[i]][1] -
                         self.bounds[self.param_names[i]][0]) * 0.1
            particle.speed[i] = max(-max_speed, min(max_speed, particle.speed[i]))

            # 更新位置
            particle[i] += particle.speed[i]

            # 边界约束
            lower, upper = self.bounds[self.param_names[i]]
            particle[i] = max(lower, min(upper, particle[i]))

    def optimize(self):
        """执行MOPSO优化，返回(帕累托前沿, None)"""
        pop = [self._generate_particle() for _ in range(self.num_particles)]
        pareto_front = ParetoArchive()

        global_best = None

        for gen in range(self.max_gen):
            # 评价所有粒子
            for particle in pop:
                particle.fitness.values = self._evaluate(particle)

            # 更新帕累托前沿
            pareto_front.update(pop)

            # 从帕累托前沿中随机选择全局引导解
            if len(pareto_front) > 0:
                global_best = random.choice(list(pareto_front))

            # 更新粒子
            for particle in pop:
                if global_best is not None:
                    self._update_particle(particle, global_best)

            # 记录迭代历史
            self._record_history(pop, gen)

            if (gen + 1) % 10 == 0:
                print(f"第{gen+1}代: 帕累托解数量={len(pareto_front)}")

        return pareto_front, None

    def _record_history(self, pop, generation):
        """记录每代的目标函数值统计"""
        fitness_values = [ind.fitness.values for ind in pop if ind.fitness.valid]

        if fitness_values:
            avg_fitness = np.mean(fitness_values, axis=0)
            min_fitness = np.min(fitness_values, axis=0)

            self.iteration_history.append({
                "generation": generation,
                "avg_wall_uniformity": round(float(avg_fitness[0]) * 100, 4),
                "avg_defect_rate": round(float(avg_fitness[1]) * 100, 4),
                "avg_energy": round(float(avg_fitness[2]), 2),
                "avg_heat_resistance": round((1 - float(avg_fitness[3])) * 100, 4),
                "min_wall_uniformity": round(float(min_fitness[0]) * 100, 4),
                "min_defect_rate": round(float(min_fitness[1]) * 100, 4),
                "min_energy": round(float(min_fitness[2]), 2),
                "min_heat_resistance": round((1 - float(min_fitness[3])) * 100, 4)
            })

    def select_best_solution(self, pareto_front):
        """从帕累托前沿中选择综合最优解（加权评分最小）"""
        if not len(pareto_front):
            return None

        best_solution = None
        best_score = float('inf')
        weights = [0.25, 0.25, 0.25, 0.25]  # 四个目标权重相等

        for solution in pareto_front:
            score = sum(w * v for w, v in zip(weights, solution.fitness.values))
            if score < best_score:
                best_score = score
                best_solution = solution

        return best_solution

    def pareto_to_dict(self, pareto_front):
        """将帕累托前沿转换为可JSON序列化的字典列表"""
        result = []
        for solution in pareto_front:
            result.append({
                "params": {k: round(float(v), 2)
                           for k, v in zip(self.param_names, solution)},
                "objectives": {
                    "wall_uniformity": round(solution.fitness.values[0] * 100, 4),
                    "defect_rate": round(solution.fitness.values[1] * 100, 4),
                    "energy_consumption": round(solution.fitness.values[2], 2),
                    "heat_resistance": round((1 - solution.fitness.values[3]) * 100, 4)
                }
            })
        return result

    def get_iteration_history(self, logbook=None):
        """获取迭代历史"""
        return self.iteration_history
