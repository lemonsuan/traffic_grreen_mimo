"""
MAXBAND绿波优化算法
算法原理: Gartner et al., 1991
最大化绿波带宽
"""

import time
import numpy as np
from typing import Dict, List, Tuple
from scipy.optimize import linprog

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


class MAXBANDOptimizer(BaseOptimizer):
    """MAXBAND绿波优化器"""
    
    def get_algorithm_name(self) -> str:
        return 'maxband'
    
    def validate_inputs(self) -> bool:
        """验证输入数据"""
        if len(self.context.node_ids) < 2:
            return False
        
        if 'corridor_data' not in self.context.traffic_data:
            return False
        
        return True
    
    def optimize(self) -> OptimizationResult:
        """执行MAXBAND优化"""
        start_time = time.time()
        
        # 获取干线数据
        corridor_data = self.context.traffic_data.get('corridor_data', {})
        nodes = self.context.node_ids
        
        # 提取参数
        desired_speed = self.context.params.get('desired_speed', 40)  # km/h
        desired_speed_ms = desired_speed / 3.6  # 转换为m/s
        
        # 计算路段行程时间
        travel_times = self._calculate_travel_times(nodes, corridor_data, desired_speed_ms)
        
        # 构建并求解线性规划问题
        result = self._solve_maxband(nodes, travel_times, corridor_data)
        
        if result is None:
            # 求解失败，使用默认方案
            return self._default_solution(nodes, corridor_data)
        
        offsets, bandwidth_fwd, bandwidth_bwd = result
        
        # 生成信号配时方案
        signal_timings = self._generate_signal_timings(
            nodes, offsets, corridor_data
        )
        
        # 计算性能指标
        performance = self._estimate_performance(
            signal_timings, corridor_data, bandwidth_fwd, bandwidth_bwd
        )
        
        computation_time = time.time() - start_time
        
        return OptimizationResult(
            level=OptimizationLevel.CORRIDOR,
            algorithm=self.get_algorithm_name(),
            signal_timings=signal_timings,
            performance=performance,
            computation_time=computation_time
        )
    
    def _calculate_travel_times(
        self, nodes: List[str], corridor_data: Dict, speed_ms: float
    ) -> List[float]:
        """计算路段行程时间"""
        travel_times = []
        
        for i in range(len(nodes) - 1):
            from_node = nodes[i]
            to_node = nodes[i + 1]
            
            # 获取路段长度
            edge_key = f"{from_node}_{to_node}"
            edge_data = corridor_data.get('edges', {}).get(edge_key, {})
            length = edge_data.get('length', 500)  # 默认500米
            
            travel_time = length / speed_ms
            travel_times.append(travel_time)
        
        return travel_times
    
    def _solve_maxband(
        self, nodes: List[str], travel_times: List[float], corridor_data: Dict
    ) -> Tuple[List[float], float, float]:
        """求解MAXBAND线性规划问题"""
        n = len(nodes)
        
        if n < 2:
            return None
        
        # 获取公共周期
        cycle = self._get_common_cycle(corridor_data)
        
        # 变量: [offset_0, offset_1, ..., offset_{n-1}, bandwidth_fwd, bandwidth_bwd]
        # 约束数: 2*(n-1) + 2
        num_vars = n + 2
        
        # 目标函数: 最大化 bandwidth_fwd + bandwidth_bwd
        c = [0] * n + [-1, -1]  # 最小化负的带宽 = 最大化带宽
        
        # 约束矩阵
        A_ub = []
        b_ub = []
        
        # 相位差约束: 0 <= offset_i <= cycle
        for i in range(n):
            # offset_i >= 0
            row = [0] * num_vars
            row[i] = -1
            A_ub.append(row)
            b_ub.append(0)
            
            # offset_i <= cycle
            row = [0] * num_vars
            row[i] = 1
            A_ub.append(row)
            b_ub.append(cycle)
        
        # 绿波带宽约束
        for i in range(n - 1):
            travel_time = travel_times[i]
            
            # 正向带宽约束
            # offset_{i+1} - offset_i + bandwidth_fwd <= travel_time (mod cycle)
            row = [0] * num_vars
            row[i] = -1
            row[i + 1] = 1
            row[n] = 1  # bandwidth_fwd
            A_ub.append(row)
            b_ub.append(travel_time)
            
            # 反向带宽约束
            # offset_i - offset_{i+1} + bandwidth_bwd <= -travel_time (mod cycle)
            row = [0] * num_vars
            row[i] = 1
            row[i + 1] = -1
            row[n + 1] = 1  # bandwidth_bwd
            A_ub.append(row)
            b_ub.append(-travel_time + cycle)
        
        # 带宽非负约束
        row = [0] * num_vars
        row[n] = -1
        A_ub.append(row)
        b_ub.append(0)
        
        row = [0] * num_vars
        row[n + 1] = -1
        A_ub.append(row)
        b_ub.append(0)
        
        # 带宽上限约束
        max_bandwidth = cycle * 0.4  # 最大带宽为周期的40%
        
        row = [0] * num_vars
        row[n] = 1
        A_ub.append(row)
        b_ub.append(max_bandwidth)
        
        row = [0] * num_vars
        row[n + 1] = 1
        A_ub.append(row)
        b_ub.append(max_bandwidth)
        
        # 求解线性规划
        try:
            result = linprog(
                c, A_ub=A_ub, b_ub=b_ub,
                bounds=[(0, cycle)] * n + [(0, max_bandwidth)] * 2,
                method='highs'
            )
            
            if result.success:
                offsets = result.x[:n]
                bandwidth_fwd = result.x[n]
                bandwidth_bwd = result.x[n + 1]
                return offsets.tolist(), bandwidth_fwd, bandwidth_bwd
        except Exception as e:
            print(f"MAXBAND求解失败: {e}")
        
        return None
    
    def _get_common_cycle(self, corridor_data: Dict) -> float:
        """获取公共周期"""
        # 从路口数据中获取最大周期
        cycles = []
        for node_data in corridor_data.get('nodes', {}).values():
            if 'cycle_length' in node_data:
                cycles.append(node_data['cycle_length'])
        
        if cycles:
            return max(cycles)
        
        # 默认周期
        return self.constraints.max_cycle_length
    
    def _generate_signal_timings(
        self, nodes: List[str], offsets: List[float], corridor_data: Dict
    ) -> Dict[str, SignalTiming]:
        """生成信号配时方案"""
        signal_timings = {}
        
        for i, node_id in enumerate(nodes):
            # 获取节点配置
            node_data = corridor_data.get('nodes', {}).get(node_id, {})
            cycle = node_data.get('cycle_length', 120)
            
            # 计算绿灯时间
            green_ns = node_data.get('green_ns', 45)
            green_ew = node_data.get('green_ew', 35)
            
            phases = [
                {
                    'index': 0,
                    'name': 'NS_through',
                    'green': green_ns,
                    'yellow': self.constraints.yellow_time,
                    'all_red': self.constraints.all_red_time
                },
                {
                    'index': 1,
                    'name': 'EW_through',
                    'green': green_ew,
                    'yellow': self.constraints.yellow_time,
                    'all_red': self.constraints.all_red_time
                }
            ]
            
            signal_timings[node_id] = SignalTiming(
                cycle_length=cycle,
                offset=offsets[i],
                phases=phases
            )
        
        return signal_timings
    
    def _estimate_performance(
        self, signal_timings: Dict[str, SignalTiming],
        corridor_data: Dict, bandwidth_fwd: float, bandwidth_bwd: float
    ) -> PerformanceMetrics:
        """估算性能指标"""
        # 计算带宽效率
        cycle = list(signal_timings.values())[0].cycle_length
        efficiency = (bandwidth_fwd + bandwidth_bwd) / (2 * cycle)
        
        # 估算延误 (基于带宽效率)
        base_delay = 45  # 无绿波时的基础延误
        avg_delay = base_delay * (1 - efficiency * 0.6)
        
        # 估算停车次数
        avg_stops = 2.5 * (1 - efficiency * 0.5)
        
        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_delay * 0.3, 2),
            max_queue_length=int(avg_delay * 0.5),
            throughput=int(2000 * (1 + efficiency * 0.3)),
            avg_stops=round(avg_stops, 2),
            vcr=round(0.7 + (1 - efficiency) * 0.2, 2)
        )
    
    def _default_solution(
        self, nodes: List[str], corridor_data: Dict
    ) -> OptimizationResult:
        """默认方案 (求解失败时使用)"""
        signal_timings = {}
        
        for i, node_id in enumerate(nodes):
            node_data = corridor_data.get('nodes', {}).get(node_id, {})
            cycle = node_data.get('cycle_length', 120)
            
            signal_timings[node_id] = SignalTiming(
                cycle_length=cycle,
                offset=i * 15,  # 简单的等间距偏移
                phases=[
                    {'index': 0, 'green': 45, 'yellow': 3, 'all_red': 1},
                    {'index': 1, 'green': 35, 'yellow': 3, 'all_red': 1}
                ]
            )
        
        return OptimizationResult(
            level=OptimizationLevel.CORRIDOR,
            algorithm=self.get_algorithm_name(),
            signal_timings=signal_timings,
            performance=PerformanceMetrics(avg_delay=40, avg_stops=2.0),
            computation_time=0
        )


# 注册优化器
from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('corridor', 'maxband', MAXBANDOptimizer)
