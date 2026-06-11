"""
NSGA-II 多目标区域信号优化算法
算法原理: Deb et al., 2002
同时优化多个目标: 延误、停车次数、吞吐量
输出Pareto前沿解集
"""

import time
import random
import math
from typing import Dict, List, Tuple
from dataclasses import dataclass

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


@dataclass
class Individual:
    """个体 (染色体)"""
    genes: Dict  # node_id -> {offset, green_ns, green_ew}
    objectives: List[float] = None  # 目标值列表
    rank: int = 0
    crowding_distance: float = 0


class NSGAIIOptimizer(BaseOptimizer):
    """NSGA-II 多目标优化器"""

    def get_algorithm_name(self) -> str:
        return 'nsga'

    def validate_inputs(self) -> bool:
        if not self.context.node_ids:
            return False
        if 'network_data' not in self.context.traffic_data:
            return False
        return True

    def optimize(self) -> OptimizationResult:
        start_time = time.time()

        network_data = self.context.traffic_data.get('network_data', {})
        nodes = self.context.node_ids
        cycle = self._get_common_cycle(network_data)

        # GA 参数
        pop_size = self.context.params.get('pop_size', 60)
        generations = self.context.params.get('generations', 100)
        crossover_rate = self.context.params.get('crossover_rate', 0.9)
        mutation_rate = self.context.params.get('mutation_rate', 0.2)

        convergence = []

        # 初始化种群
        population = self._initialize_population(pop_size, nodes, network_data, cycle)

        # 评估初始种群
        for ind in population:
            ind.objectives = self._evaluate_objectives(ind, network_data, nodes)

        # 非支配排序 + 拥挤度计算
        self._fast_non_dominated_sort(population)
        self._calculate_crowding_distance(population)

        best_front = None

        for gen in range(generations):
            # 生成子代
            offspring = self._generate_offspring(population, nodes, cycle, crossover_rate, mutation_rate)

            for ind in offspring:
                ind.objectives = self._evaluate_objectives(ind, network_data, nodes)

            # 合并父代和子代
            combined = population + offspring
            self._fast_non_dominated_sort(combined)
            self._calculate_crowding_distance(combined)

            # 选择下一代
            population = self._select_next_generation(combined, pop_size)

            # 记录最优前沿
            front_0 = [ind for ind in population if ind.rank == 0]
            if front_0:
                best_front = front_0
                best_cost = min(sum(o) for o in [ind.objectives for ind in front_0])
                convergence.append(best_cost)

        # 从Pareto前沿选折中解 (各目标归一化后距理想点最近)
        best_individual = self._select_compromise(best_front) if best_front else population[0]

        # 生成配时方案
        signal_timings = self._generate_signal_timings(best_individual, network_data, nodes)
        performance = self._evaluate_performance(best_individual, network_data, nodes)

        pareto_front = None
        if best_front:
            pareto_front = [
                {
                    'objectives': ind.objectives,
                    'solution': ind.genes
                }
                for ind in best_front[:20]
            ]

        computation_time = time.time() - start_time

        return OptimizationResult(
            level=OptimizationLevel.NETWORK,
            algorithm=self.get_algorithm_name(),
            signal_timings=signal_timings,
            performance=performance,
            convergence=convergence,
            pareto_front=pareto_front,
            computation_time=computation_time
        )

    def _get_common_cycle(self, network_data):
        cycles = []
        for node_data in network_data.get('nodes', {}).values():
            if 'cycle_length' in node_data:
                cycles.append(node_data['cycle_length'])
        return max(cycles) if cycles else self.constraints.max_cycle_length

    def _initialize_population(self, pop_size, nodes, network_data, cycle):
        population = []
        for _ in range(pop_size):
            genes = {}
            for node_id in nodes:
                node_data = network_data.get('nodes', {}).get(node_id, {})
                node_cycle = node_data.get('cycle_length', cycle)
                total_loss = 2 * (self.constraints.yellow_time + self.constraints.all_red_time)
                effective = node_cycle - total_loss

                green_ns = random.uniform(self.constraints.min_green_time,
                                          effective - self.constraints.min_green_time)
                genes[node_id] = {
                    'offset': random.uniform(0, node_cycle),
                    'green_ns': round(green_ns, 1),
                    'green_ew': round(effective - green_ns, 1),
                    'cycle': node_cycle
                }
            population.append(Individual(genes=genes))
        return population

    def _evaluate_objectives(self, ind, network_data, nodes):
        """
        三个目标:
        1. 平均延误 (最小化)
        2. 平均停车次数 (最小化)
        3. 负吞吐量 (最小化 => 实际最大化吞吐量)
        """
        total_delay = 0
        total_stops = 0
        total_flow = 0
        total_throughput = 0

        edges = network_data.get('edges', [])
        for edge in edges:
            from_node = edge.get('from')
            to_node = edge.get('to')
            flow = edge.get('flow', 0)

            if from_node not in ind.genes or to_node not in ind.genes:
                continue

            g = ind.genes[from_node]
            g_to = ind.genes[to_node]
            cycle = g['cycle']

            green_ew = g_to['green_ew']
            g_c = green_ew / cycle if cycle > 0 else 0.5

            # 协调效果
            offset_diff = (g_to['offset'] - g['offset']) % cycle
            travel_time = edge.get('travel_time', 30)
            arrival_error = abs(offset_diff - travel_time % cycle)
            if arrival_error > cycle / 2:
                arrival_error = cycle - arrival_error
            coordination = max(0, 1 - arrival_error / green_ew) if green_ew > 0 else 0

            # Webster 延误
            sat_flow = 1800
            x = flow / (sat_flow * g_c) if g_c > 0 else 1
            if 0 < x < 1:
                d1 = (0.5 * cycle * (1 - g_c) ** 2) / (1 - min(1, x) * g_c)
            else:
                d1 = 0.5 * cycle * (1 - g_c) if g_c < 1 else 0

            d_adjusted = d1 * (1 - coordination * 0.5)
            stops = flow * (1 - g_c) * (1 - coordination * 0.4) / cycle * 3600 if cycle > 0 else 0

            total_delay += d_adjusted * flow
            total_stops += stops
            total_flow += flow
            total_throughput += flow * g_c * 0.9

        avg_delay = total_delay / total_flow if total_flow > 0 else 0
        avg_stops = total_stops / total_flow if total_flow > 0 else 0

        return [avg_delay, avg_stops, -total_throughput]

    def _fast_non_dominated_sort(self, population):
        n = len(population)
        domination_count = [0] * n
        dominated_set = [[] for _ in range(n)]
        ranks = [0] * n

        for i in range(n):
            for j in range(i + 1, n):
                if self._dominates(population[i], population[j]):
                    dominated_set[i].append(j)
                    domination_count[j] += 1
                elif self._dominates(population[j], population[i]):
                    dominated_set[j].append(i)
                    domination_count[i] += 1

        current_front = [i for i in range(n) if domination_count[i] == 0]
        rank = 0

        while current_front:
            next_front = []
            for i in current_front:
                ranks[i] = rank
                for j in dominated_set[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            current_front = next_front
            rank += 1

        for i, ind in enumerate(population):
            ind.rank = ranks[i]

    def _dominates(self, a, b):
        """a 是否支配 b"""
        if a.objectives is None or b.objectives is None:
            return False
        better_in_any = False
        for oa, ob in zip(a.objectives, b.objectives):
            if oa > ob:
                return False
            if oa < ob:
                better_in_any = True
        return better_in_any

    def _calculate_crowding_distance(self, population):
        n = len(population)
        if n == 0:
            return

        for ind in population:
            ind.crowding_distance = 0

        num_objectives = len(population[0].objectives) if population[0].objectives else 0

        for m in range(num_objectives):
            sorted_pop = sorted(population, key=lambda x: x.objectives[m])
            sorted_pop[0].crowding_distance = float('inf')
            sorted_pop[-1].crowding_distance = float('inf')

            obj_range = sorted_pop[-1].objectives[m] - sorted_pop[0].objectives[m]
            if obj_range < 1e-10:
                continue

            for i in range(1, n - 1):
                sorted_pop[i].crowding_distance += (
                    sorted_pop[i + 1].objectives[m] - sorted_pop[i - 1].objectives[m]
                ) / obj_range

    def _select_next_generation(self, combined, pop_size):
        combined.sort(key=lambda x: (x.rank, -x.crowding_distance))
        return combined[:pop_size]

    def _generate_offspring(self, population, nodes, cycle, crossover_rate, mutation_rate):
        offspring = []
        pop_size = len(population)

        while len(offspring) < pop_size:
            p1 = self._tournament_select(population)
            p2 = self._tournament_select(population)

            if random.random() < crossover_rate:
                c1, c2 = self._crossover(p1, p2, nodes, cycle)
            else:
                c1 = Individual(genes={k: dict(v) for k, v in p1.genes.items()})
                c2 = Individual(genes={k: dict(v) for k, v in p2.genes.items()})

            self._mutate(c1, mutation_rate, cycle)
            self._mutate(c2, mutation_rate, cycle)

            offspring.append(c1)
            if len(offspring) < pop_size:
                offspring.append(c2)

        return offspring

    def _tournament_select(self, population, k=2):
        candidates = random.sample(population, min(k, len(population)))
        candidates.sort(key=lambda x: (x.rank, -x.crowding_distance))
        return candidates[0]

    def _crossover(self, p1, p2, nodes, cycle):
        child1_genes = {}
        child2_genes = {}
        for node_id in nodes:
            if random.random() < 0.5:
                child1_genes[node_id] = dict(p1.genes[node_id])
                child2_genes[node_id] = dict(p2.genes[node_id])
            else:
                child1_genes[node_id] = dict(p2.genes[node_id])
                child2_genes[node_id] = dict(p1.genes[node_id])
        return Individual(genes=child1_genes), Individual(genes=child2_genes)

    def _mutate(self, ind, mutation_rate, cycle):
        for node_id, g in ind.genes.items():
            if random.random() < mutation_rate:
                g['offset'] = (g['offset'] + random.gauss(0, cycle * 0.1)) % g['cycle']
            if random.random() < mutation_rate:
                total_loss = 2 * (self.constraints.yellow_time + self.constraints.all_red_time)
                effective = g['cycle'] - total_loss
                delta = random.gauss(0, effective * 0.1)
                new_ns = max(self.constraints.min_green_time,
                             min(effective - self.constraints.min_green_time, g['green_ns'] + delta))
                g['green_ns'] = round(new_ns, 1)
                g['green_ew'] = round(effective - new_ns, 1)

    def _select_compromise(self, front):
        if len(front) == 1:
            return front[0]

        # 归一化各目标
        num_obj = len(front[0].objectives)
        mins = [min(ind.objectives[i] for ind in front) for i in range(num_obj)]
        maxs = [max(ind.objectives[i] for ind in front) for i in range(num_obj)]

        best = None
        best_dist = float('inf')

        for ind in front:
            dist = 0
            for i in range(num_obj):
                rng = maxs[i] - mins[i]
                if rng > 0:
                    normed = (ind.objectives[i] - mins[i]) / rng
                else:
                    normed = 0
                dist += normed ** 2
            dist = math.sqrt(dist)

            if dist < best_dist:
                best_dist = dist
                best = ind

        return best

    def _generate_signal_timings(self, ind, network_data, nodes):
        signal_timings = {}
        for node_id in nodes:
            g = ind.genes[node_id]
            phases = [
                {'index': 0, 'name': 'NS_through', 'green': g['green_ns'],
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time},
                {'index': 1, 'name': 'EW_through', 'green': g['green_ew'],
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time}
            ]
            signal_timings[node_id] = SignalTiming(
                cycle_length=g['cycle'], offset=g['offset'], phases=phases
            )
        return signal_timings

    def _evaluate_performance(self, ind, network_data, nodes):
        objectives = ind.objectives
        avg_delay = objectives[0]
        avg_stops = objectives[1]
        throughput = -objectives[2]

        edges = network_data.get('edges', [])
        total_saturation = 0
        count = 0
        for edge in edges:
            from_node = edge.get('from')
            if from_node in ind.genes:
                flow = edge.get('flow', 0)
                sat = 1800
                total_saturation += flow / sat
                count += 1

        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_delay * 0.25, 2),
            max_queue_length=int(avg_delay * 0.4),
            throughput=int(throughput),
            avg_stops=round(avg_stops, 2),
            vcr=round(total_saturation / max(count, 1), 2)
        )


from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('network', 'nsga', NSGAIIOptimizer)
