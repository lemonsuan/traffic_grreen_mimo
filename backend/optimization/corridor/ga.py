"""
遗传算法(GA)干线绿波优化
用GA搜索最优相位偏移组合，适应度基于延误估算
"""

import time
import random
import math
from typing import Dict, List, Tuple

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


class GAOptimizer(BaseOptimizer):
    """遗传算法绿波优化器"""

    def get_algorithm_name(self) -> str:
        return 'ga'

    def validate_inputs(self) -> bool:
        if len(self.context.node_ids) < 2:
            return False
        if 'corridor_data' not in self.context.traffic_data:
            return False
        return True

    def optimize(self) -> OptimizationResult:
        start_time = time.time()

        corridor_data = self.context.traffic_data.get('corridor_data', {})
        nodes = self.context.node_ids
        desired_speed = self.context.params.get('desired_speed', 40)
        desired_speed_ms = desired_speed / 3.6

        travel_times = self._calculate_travel_times(nodes, corridor_data, desired_speed_ms)
        cycle = self._get_common_cycle(corridor_data)

        # GA 参数
        pop_size = self.context.params.get('pop_size', 60)
        generations = self.context.params.get('generations', 100)
        crossover_rate = self.context.params.get('crossover_rate', 0.85)
        mutation_rate = self.context.params.get('mutation_rate', 0.15)
        elite_ratio = self.context.params.get('elite_ratio', 0.1)

        n = len(nodes)
        convergence = []

        # 初始化种群: 每个个体是 n 个偏移量
        population = self._initialize_population(pop_size, n, cycle)

        best_fitness = float('inf')
        best_individual = None

        for gen in range(generations):
            # 计算适应度
            fitness_scores = []
            for ind in population:
                fitness = self._evaluate_fitness(ind, travel_times, cycle, corridor_data, nodes)
                fitness_scores.append(fitness)

            # 记录最优
            min_idx = fitness_scores.index(min(fitness_scores))
            if fitness_scores[min_idx] < best_fitness:
                best_fitness = fitness_scores[min_idx]
                best_individual = population[min_idx][:]

            convergence.append(best_fitness)

            # 选择 + 交叉 + 变异
            elite_count = max(1, int(pop_size * elite_ratio))
            sorted_indices = sorted(range(pop_size), key=lambda i: fitness_scores[i])
            new_population = [population[sorted_indices[i]][:] for i in range(elite_count)]

            while len(new_population) < pop_size:
                p1 = self._tournament_select(population, fitness_scores)
                p2 = self._tournament_select(population, fitness_scores)

                if random.random() < crossover_rate:
                    c1, c2 = self._crossover(p1, p2, cycle)
                else:
                    c1, c2 = p1[:], p2[:]

                c1 = self._mutate(c1, mutation_rate, cycle)
                c2 = self._mutate(c2, mutation_rate, cycle)

                new_population.append(c1)
                if len(new_population) < pop_size:
                    new_population.append(c2)

            population = new_population

        # 生成配时方案
        signal_timings = self._generate_signal_timings(nodes, best_individual, corridor_data)
        performance = self._estimate_performance(best_individual, travel_times, cycle, corridor_data, nodes)

        computation_time = time.time() - start_time

        return OptimizationResult(
            level=OptimizationLevel.CORRIDOR,
            algorithm=self.get_algorithm_name(),
            signal_timings=signal_timings,
            performance=performance,
            convergence=convergence,
            computation_time=computation_time
        )

    def _calculate_travel_times(self, nodes, corridor_data, speed_ms):
        travel_times = []
        for i in range(len(nodes) - 1):
            edge_key = f"{nodes[i]}_{nodes[i+1]}"
            edge_data = corridor_data.get('edges', {}).get(edge_key, {})
            length = edge_data.get('length', 500)
            travel_times.append(length / speed_ms)
        return travel_times

    def _get_common_cycle(self, corridor_data):
        cycles = []
        for node_data in corridor_data.get('nodes', {}).values():
            if 'cycle_length' in node_data:
                cycles.append(node_data['cycle_length'])
        return max(cycles) if cycles else self.constraints.max_cycle_length

    def _initialize_population(self, pop_size, n, cycle):
        population = []
        for _ in range(pop_size):
            individual = [random.uniform(0, cycle) for _ in range(n)]
            population.append(individual)
        return population

    def _evaluate_fitness(self, individual, travel_times, cycle, corridor_data, nodes):
        """适应度 = 加权延误 + 停车惩罚"""
        total_delay = 0
        n = len(individual)

        for i in range(n - 1):
            offset_diff = individual[i + 1] - individual[i]
            tt = travel_times[i]

            # 绿波误差: 偏移差与行程时间的偏差
            error = (offset_diff - tt) % cycle
            if error > cycle / 2:
                error = cycle - error

            # 误差越大，延误越高
            green = corridor_data.get('nodes', {}).get(nodes[i], {}).get('green_ew', 35)
            if error <= green / 2:
                delay = error * 0.5
            else:
                delay = (error - green / 2) * 2.0 + green / 4

            total_delay += delay

        # 反向延误
        for i in range(n - 1, 0, -1):
            offset_diff = individual[i - 1] - individual[i]
            tt = travel_times[i - 1]
            error = (offset_diff + tt) % cycle
            if error > cycle / 2:
                error = cycle - error
            green = corridor_data.get('nodes', {}).get(nodes[i], {}).get('green_ew', 35)
            if error <= green / 2:
                delay = error * 0.3
            else:
                delay = (error - green / 2) * 1.5 + green / 6
            total_delay += delay

        return total_delay

    def _tournament_select(self, population, fitness_scores, k=3):
        candidates = random.sample(range(len(population)), min(k, len(population)))
        best = min(candidates, key=lambda i: fitness_scores[i])
        return population[best][:]

    def _crossover(self, p1, p2, cycle):
        """模拟二进制交叉 (SBX)"""
        eta = 2
        c1, c2 = p1[:], p2[:]
        for i in range(len(p1)):
            if random.random() < 0.5:
                if abs(p1[i] - p2[i]) > 1e-6:
                    u = random.random()
                    if u <= 0.5:
                        beta = (2 * u) ** (1 / (eta + 1))
                    else:
                        beta = (1 / (2 * (1 - u))) ** (1 / (eta + 1))
                    c1[i] = 0.5 * ((1 + beta) * p1[i] + (1 - beta) * p2[i])
                    c2[i] = 0.5 * ((1 - beta) * p1[i] + (1 + beta) * p2[i])
                    c1[i] = c1[i] % cycle
                    c2[i] = c2[i] % cycle
        return c1, c2

    def _mutate(self, individual, mutation_rate, cycle):
        """多项式变异"""
        eta_m = 20
        for i in range(len(individual)):
            if random.random() < mutation_rate:
                delta = random.gauss(0, cycle * 0.1)
                individual[i] = (individual[i] + delta) % cycle
        return individual

    def _generate_signal_timings(self, nodes, offsets, corridor_data):
        signal_timings = {}
        for i, node_id in enumerate(nodes):
            node_data = corridor_data.get('nodes', {}).get(node_id, {})
            cycle = node_data.get('cycle_length', 120)
            green_ns = node_data.get('green_ns', 45)
            green_ew = node_data.get('green_ew', 35)
            phases = [
                {'index': 0, 'name': 'NS_through', 'green': green_ns,
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time},
                {'index': 1, 'name': 'EW_through', 'green': green_ew,
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time}
            ]
            signal_timings[node_id] = SignalTiming(
                cycle_length=cycle, offset=offsets[i], phases=phases
            )
        return signal_timings

    def _estimate_performance(self, offsets, travel_times, cycle, corridor_data, nodes):
        fitness = self._evaluate_fitness(offsets, travel_times, cycle, corridor_data, nodes)
        n = len(offsets)
        max_possible_delay = cycle * n
        efficiency = max(0, 1 - fitness / max_possible_delay) if max_possible_delay > 0 else 0

        base_delay = 45
        avg_delay = max(5, base_delay * (1 - efficiency * 0.6))
        avg_stops = max(0.2, 2.5 * (1 - efficiency * 0.5))

        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_delay * 0.3, 2),
            max_queue_length=int(avg_delay * 0.5),
            throughput=int(2000 * (1 + efficiency * 0.3)),
            avg_stops=round(avg_stops, 2),
            vcr=round(0.7 + (1 - efficiency) * 0.2, 2)
        )


from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('corridor', 'ga', GAOptimizer)
