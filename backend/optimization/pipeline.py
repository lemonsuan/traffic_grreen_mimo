"""
一键优化管线
自动选择最优算法、全网批量优化、生成对比报告
支撑小型城市级路网的信号优化
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass

from .base import (
    OptimizerFactory, OptimizationContext, OptimizationResult,
    OptimizationLevel, OptimizationConstraints, PerformanceMetrics
)


@dataclass
class PipelineResult:
    """管线优化结果"""
    network_id: int
    total_intersections: int
    total_corridors: int
    algorithm_results: Dict[str, OptimizationResult]
    best_algorithm: str
    best_performance: PerformanceMetrics
    comparison_table: List[Dict]
    total_time: float


class OptimizationPipeline:
    """一键优化管线"""

    def __init__(self, network_id: int, network_data: Dict, constraints: Optional[OptimizationConstraints] = None):
        self.network_id = network_id
        self.network_data = network_data
        self.constraints = constraints or OptimizationConstraints()

    def run_intersection_optimization(
        self,
        node_ids: Optional[List[str]] = None,
        algorithms: Optional[List[str]] = None,
        traffic_data: Optional[Dict] = None
    ) -> PipelineResult:
        """
        对所有路口执行单点优化，对比各算法

        Args:
            node_ids: 要优化的节点列表 (None=全部)
            algorithms: 要对比的算法列表 (None=全部)
            traffic_data: 交通数据
        """
        if node_ids is None:
            nodes_data = self.network_data.get('nodes', {})
        if isinstance(nodes_data, list):
            node_ids = [n['node_id'] if isinstance(n, dict) else n for n in nodes_data]
        else:
            node_ids = list(nodes_data.keys())
        if algorithms is None:
            algorithms = OptimizerFactory.get_available_algorithms('intersection')
        if traffic_data is None:
            traffic_data = self._generate_default_traffic(node_ids)

        results = {}
        total_time = 0

        for algo in algorithms:
            try:
                algo_results = []
                for node_id in node_ids:
                    context = OptimizationContext(
                        level=OptimizationLevel.INTERSECTION,
                        network_id=self.network_id,
                        node_ids=[node_id],
                        traffic_data=traffic_data.get(node_id, traffic_data),
                        constraints=self.constraints
                    )
                    optimizer = OptimizerFactory.create(context, algo)
                    if optimizer.validate_inputs():
                        result = optimizer.optimize()
                        algo_results.append(result)

                if algo_results:
                    avg_perf = self._average_performance([r.performance for r in algo_results])
                    best_result = algo_results[0]
                    best_result.performance = avg_perf
                    results[algo] = best_result
                    total_time += sum(r.computation_time for r in algo_results)
            except Exception as e:
                print(f"算法 {algo} 优化失败: {e}")
                continue

        best_algo = self._select_best_algorithm(results)
        comparison = self._build_comparison_table(results)

        return PipelineResult(
            network_id=self.network_id,
            total_intersections=len(node_ids),
            total_corridors=0,
            algorithm_results=results,
            best_algorithm=best_algo,
            best_performance=results[best_algo].performance if best_algo else PerformanceMetrics(),
            comparison_table=comparison,
            total_time=total_time
        )

    def run_corridor_optimization(
        self,
        corridor_nodes: List[str],
        algorithms: Optional[List[str]] = None,
        desired_speed: float = 40
    ) -> PipelineResult:
        """
        执行干线绿波优化

        Args:
            corridor_nodes: 干线路口序列
            algorithms: 算法列表
            desired_speed: 设计速度
        """
        if algorithms is None:
            algorithms = OptimizerFactory.get_available_algorithms('corridor')

        corridor_data = self._build_corridor_data(corridor_nodes, desired_speed)
        results = {}
        total_time = 0

        for algo in algorithms:
            try:
                context = OptimizationContext(
                    level=OptimizationLevel.CORRIDOR,
                    network_id=self.network_id,
                    node_ids=corridor_nodes,
                    traffic_data={'corridor_data': corridor_data},
                    constraints=self.constraints,
                    params={'desired_speed': desired_speed}
                )
                optimizer = OptimizerFactory.create(context, algo)
                if optimizer.validate_inputs():
                    result = optimizer.optimize()
                    results[algo] = result
                    total_time += result.computation_time
            except Exception as e:
                print(f"干线算法 {algo} 优化失败: {e}")
                continue

        best_algo = self._select_best_algorithm(results)
        comparison = self._build_comparison_table(results)

        return PipelineResult(
            network_id=self.network_id,
            total_intersections=len(corridor_nodes),
            total_corridors=1,
            algorithm_results=results,
            best_algorithm=best_algo,
            best_performance=results[best_algo].performance if best_algo else PerformanceMetrics(),
            comparison_table=comparison,
            total_time=total_time
        )

    def run_network_optimization(
        self,
        algorithms: Optional[List[str]] = None
    ) -> PipelineResult:
        """
        执行全区域路网优化

        Args:
            algorithms: 算法列表
        """
        if algorithms is None:
            algorithms = OptimizerFactory.get_available_algorithms('network')

        nodes_data = self.network_data.get('nodes', {})
        if isinstance(nodes_data, list):
            node_ids = [n['node_id'] if isinstance(n, dict) else n for n in nodes_data]
            nodes_dict = {n['node_id']: n for n in nodes_data if isinstance(n, dict)}
        else:
            node_ids = list(nodes_data.keys())
            nodes_dict = nodes_data

        normalized = dict(self.network_data)
        normalized['nodes'] = nodes_dict
        network_data = {'network_data': normalized}
        results = {}
        total_time = 0

        for algo in algorithms:
            try:
                context = OptimizationContext(
                    level=OptimizationLevel.NETWORK,
                    network_id=self.network_id,
                    node_ids=node_ids,
                    traffic_data=network_data,
                    constraints=self.constraints
                )
                optimizer = OptimizerFactory.create(context, algo)
                if optimizer.validate_inputs():
                    result = optimizer.optimize()
                    results[algo] = result
                    total_time += result.computation_time
            except Exception as e:
                print(f"区域算法 {algo} 优化失败: {e}")
                continue

        best_algo = self._select_best_algorithm(results)
        comparison = self._build_comparison_table(results)

        return PipelineResult(
            network_id=self.network_id,
            total_intersections=len(node_ids),
            total_corridors=0,
            algorithm_results=results,
            best_algorithm=best_algo,
            best_performance=results[best_algo].performance if best_algo else PerformanceMetrics(),
            comparison_table=comparison,
            total_time=total_time
        )

    def auto_optimize(self) -> Dict:
        """
        自动选择最优策略:
        - ≤3个路口: 单点优化
        - 线形排列: 干线绿波
        - 其他: 区域优化

        Returns:
            完整优化报告
        """
        nodes_data = self.network_data.get('nodes', {})
        if isinstance(nodes_data, list):
            node_ids = [n['node_id'] if isinstance(n, dict) else n for n in nodes_data]
        else:
            node_ids = list(nodes_data.keys())
        edges = self.network_data.get('edges', [])
        n = len(node_ids)

        if n <= 3:
            result = self.run_intersection_optimization(node_ids)
            strategy = 'intersection'
        elif self._is_corridor(node_ids, edges):
            result = self.run_corridor_optimization(node_ids)
            strategy = 'corridor'
        else:
            result = self.run_network_optimization()
            strategy = 'network'

        return {
            'strategy': strategy,
            'node_count': n,
            'edge_count': len(edges),
            'best_algorithm': result.best_algorithm,
            'best_performance': result.best_performance.to_dict() if result.best_performance else {},
            'comparison': result.comparison_table,
            'total_time': result.total_time,
            'all_results': {
                algo: r.to_dict() for algo, r in result.algorithm_results.items()
            }
        }

    def _is_corridor(self, node_ids: List[str], edges: List[Dict]) -> bool:
        """判断是否为线形走廊"""
        if len(edges) == 0:
            return False
        adj = {nid: set() for nid in node_ids}
        for edge in edges:
            fn = edge.get('from_node', '') if isinstance(edge, dict) else ''
            tn = edge.get('to_node', '') if isinstance(edge, dict) else ''
            if fn in adj and tn in adj:
                adj[fn].add(tn)
                adj[tn].add(fn)

        endpoints = [nid for nid, neighbors in adj.items() if len(neighbors) == 1]
        middle = [nid for nid, neighbors in adj.items() if len(neighbors) == 2]
        return len(endpoints) == 2 and len(middle) == len(node_ids) - 2

    def _build_corridor_data(self, nodes: List[str], speed: float) -> Dict:
        """构建干线数据"""
        corridor_data = {'nodes': {}, 'edges': {}}
        speed_ms = speed / 3.6

        for node_id in nodes:
            node = self.network_data.get('nodes', {}).get(node_id, {})
            if isinstance(node, dict):
                corridor_data['nodes'][node_id] = node
            else:
                corridor_data['nodes'][node_id] = {'cycle_length': 120, 'green_ns': 45, 'green_ew': 35}

        edges = self.network_data.get('edges', [])
        for edge in edges:
            if isinstance(edge, dict):
                fn = edge.get('from_node', '')
                tn = edge.get('to_node', '')
                if fn in nodes and tn in nodes:
                    key = f"{fn}_{tn}"
                    corridor_data['edges'][key] = edge

        return corridor_data

    def _generate_default_traffic(self, node_ids: List[str]) -> Dict:
        """生成默认交通数据"""
        traffic = {}
        for node_id in node_ids:
            traffic[node_id] = {
                'approaches': {
                    'north_through': {'volume': 400 + hash(node_id) % 200},
                    'south_through': {'volume': 380 + hash(node_id) % 180},
                    'east_through': {'volume': 350 + hash(node_id) % 160},
                    'west_through': {'volume': 330 + hash(node_id) % 140},
                    'north_left': {'volume': 80 + hash(node_id) % 60},
                    'south_left': {'volume': 70 + hash(node_id) % 50},
                    'east_left': {'volume': 60 + hash(node_id) % 40},
                    'west_left': {'volume': 50 + hash(node_id) % 30}
                }
            }
        return traffic

    def _average_performance(self, performances: List[PerformanceMetrics]) -> PerformanceMetrics:
        """计算平均性能指标"""
        n = len(performances)
        if n == 0:
            return PerformanceMetrics()
        return PerformanceMetrics(
            avg_delay=round(sum(p.avg_delay for p in performances) / n, 2),
            avg_queue_length=round(sum(p.avg_queue_length for p in performances) / n, 2),
            max_queue_length=max(p.max_queue_length for p in performances),
            throughput=int(sum(p.throughput for p in performances) / n),
            avg_stops=round(sum(p.avg_stops for p in performances) / n, 2),
            vcr=round(sum(p.vcr for p in performances) / n, 2)
        )

    def _select_best_algorithm(self, results: Dict[str, OptimizationResult]) -> str:
        """选择最优算法 (延误最低)"""
        if not results:
            return ''
        return min(results, key=lambda a: results[a].performance.avg_delay)

    def _build_comparison_table(self, results: Dict[str, OptimizationResult]) -> List[Dict]:
        """构建对比表"""
        table = []
        for algo, result in results.items():
            p = result.performance
            table.append({
                'algorithm': algo,
                'avg_delay': p.avg_delay,
                'avg_queue_length': p.avg_queue_length,
                'throughput': p.throughput,
                'avg_stops': p.avg_stops,
                'vcr': p.vcr,
                'computation_time': result.computation_time
            })
        table.sort(key=lambda x: x['avg_delay'])
        return table
