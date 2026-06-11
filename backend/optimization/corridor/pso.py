"""
粒子群优化(PSO)干线绿波
用PSO搜索最优相位偏移，适应度基于延误估算
"""

import time
import random
import math
from typing import Dict, List

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


class PSOOptimizer(BaseOptimizer):
    """PSO绿波优化器"""

    def get_algorithm_name(self) -> str:
        return 'pso'

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
        n = len(nodes)

        # PSO 参数
        swarm_size = self.context.params.get('swarm_size', 50)
        iterations = self.context.params.get('iterations', 100)
        w = self.context.params.get('inertia', 0.7)
        c1 = self.context.params.get('cognitive', 1.5)
        c2 = self.context.params.get('social', 1.5)
        v_max = cycle * 0.2

        convergence = []

        # 初始化粒子
        particles = []
        velocities = []
        p_best = []
        p_best_fitness = []
        g_best = None
        g_best_fitness = float('inf')

        for _ in range(swarm_size):
            pos = [random.uniform(0, cycle) for _ in range(n)]
            vel = [random.uniform(-v_max, v_max) for _ in range(n)]
            fitness = self._evaluate_fitness(pos, travel_times, cycle, corridor_data, nodes)

            particles.append(pos)
            velocities.append(vel)
            p_best.append(pos[:])
            p_best_fitness.append(fitness)

            if fitness < g_best_fitness:
                g_best_fitness = fitness
                g_best = pos[:]

        # 迭代优化
        for it in range(iterations):
            # 线性递减惯性权重
            w_current = w - (w - 0.4) * it / iterations

            for i in range(swarm_size):
                # 更新速度
                for j in range(n):
                    r1, r2 = random.random(), random.random()
                    velocities[i][j] = (
                        w_current * velocities[i][j]
                        + c1 * r1 * (p_best[i][j] - particles[i][j])
                        + c2 * r2 * (g_best[j] - particles[i][j])
                    )
                    velocities[i][j] = max(-v_max, min(v_max, velocities[i][j]))

                # 更新位置
                for j in range(n):
                    particles[i][j] = (particles[i][j] + velocities[i][j]) % cycle

                # 评估
                fitness = self._evaluate_fitness(particles[i], travel_times, cycle, corridor_data, nodes)

                if fitness < p_best_fitness[i]:
                    p_best_fitness[i] = fitness
                    p_best[i] = particles[i][:]

                    if fitness < g_best_fitness:
                        g_best_fitness = fitness
                        g_best = particles[i][:]

            convergence.append(g_best_fitness)

        # 生成结果
        signal_timings = self._generate_signal_timings(nodes, g_best, corridor_data)
        performance = self._estimate_performance(g_best, travel_times, cycle, corridor_data, nodes)

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

    def _evaluate_fitness(self, offsets, travel_times, cycle, corridor_data, nodes):
        """适应度: 正向+反向延误加权和"""
        total_delay = 0
        n = len(offsets)

        # 正向延误
        for i in range(n - 1):
            offset_diff = offsets[i + 1] - offsets[i]
            tt = travel_times[i]
            error = (offset_diff - tt) % cycle
            if error > cycle / 2:
                error = cycle - error

            green = corridor_data.get('nodes', {}).get(nodes[i], {}).get('green_ew', 35)
            if error <= green / 2:
                delay = error * 0.5
            else:
                delay = (error - green / 2) * 2.0 + green / 4
            total_delay += delay

        # 反向延误
        for i in range(n - 1, 0, -1):
            offset_diff = offsets[i - 1] - offsets[i]
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
OptimizerFactory.register('corridor', 'pso', PSOOptimizer)
