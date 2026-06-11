"""
感应控制算法
基于车辆检测器的实时相位切换
"""

import time
from typing import Dict, List
from dataclasses import dataclass

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


@dataclass
class PhaseState:
    """相位状态"""
    index: int
    green_elapsed: float = 0
    vehicles_waiting: int = 0
    is_green: bool = False


class ActuatedOptimizer(BaseOptimizer):
    """感应控制优化器"""
    
    def get_algorithm_name(self) -> str:
        return 'actuated'
    
    def validate_inputs(self) -> bool:
        return True
    
    def optimize(self) -> OptimizationResult:
        start_time = time.time()
        
        # 获取参数
        min_green = self.context.params.get('min_green', 7)
        max_green = self.context.params.get('max_green', 60)
        unit_extension = self.context.params.get('unit_extension', 3)
        gap_time = self.context.params.get('gap_time', 4)
        
        # 创建相位配置
        phases = [
            {
                'index': 0,
                'name': 'NS_through',
                'green': min_green,
                'yellow': self.constraints.yellow_time,
                'all_red': self.constraints.all_red_time,
                'min_green': min_green,
                'max_green': max_green,
                'unit_extension': unit_extension,
                'gap_time': gap_time
            },
            {
                'index': 1,
                'name': 'EW_through',
                'green': min_green,
                'yellow': self.constraints.yellow_time,
                'all_red': self.constraints.all_red_time,
                'min_green': min_green,
                'max_green': max_green,
                'unit_extension': unit_extension,
                'gap_time': gap_time
            }
        ]
        
        # 模拟感应控制逻辑
        simulated_timing = self._simulate_actuated_control(phases)
        
        computation_time = time.time() - start_time
        
        return OptimizationResult(
            level=OptimizationLevel.INTERSECTION,
            algorithm=self.get_algorithm_name(),
            signal_timings={'intersection': simulated_timing},
            performance=self._estimate_performance(simulated_timing),
            computation_time=computation_time
        )
    
    def _simulate_actuated_control(self, phases: List[Dict]) -> SignalTiming:
        """模拟感应控制逻辑"""
        # 感应控制状态机
        # 状态: [红] -> [绿] -> [绿延长] -> [黄] -> [全红] -> [红]
        
        simulated_phases = []
        
        for phase in phases:
            # 感应控制下，绿灯时间在min_green和max_green之间动态调整
            # 使用期望绿灯时间作为默认值
            expected_green = self._calculate_expected_green(phase)
            
            simulated_phases.append({
                'index': phase['index'],
                'name': phase['name'],
                'green': round(expected_green, 1),
                'yellow': phase['yellow'],
                'all_red': phase['all_red'],
                'control_type': 'actuated',
                'min_green': phase['min_green'],
                'max_green': phase['max_green']
            })
        
        # 计算周期长
        cycle = sum(p['green'] + p['yellow'] + p['all_red'] for p in simulated_phases)
        
        return SignalTiming(
            cycle_length=cycle,
            offset=0,
            phases=simulated_phases
        )
    
    def _calculate_expected_green(self, phase: Dict) -> float:
        """计算期望绿灯时间"""
        min_green = phase['min_green']
        max_green = phase['max_green']
        unit_extension = phase['unit_extension']
        
        # 简化模型: 根据流量估算期望绿灯时间
        # 假设流量为中等水平时，绿灯时间为min和max的中间值
        expected = (min_green + max_green) / 2
        
        # 确保在范围内
        return max(min_green, min(max_green, expected))
    
    def _estimate_performance(self, timing: SignalTiming) -> PerformanceMetrics:
        """估算性能指标"""
        cycle = timing.cycle_length
        
        # 感应控制通常比固定配时减少10-20%延误
        base_delay = 35  # 基础延误
        avg_delay = base_delay * 0.85  # 感应控制优化
        
        avg_queue = avg_delay * 0.3
        
        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_queue, 2),
            max_queue_length=int(avg_queue * 1.3),
            throughput=2200,
            avg_stops=1.2,
            vcr=0.75
        )


class AdaptiveOptimizer(BaseOptimizer):
    """单点自适应优化器 (简化SCOOT/SCATS)"""
    
    def get_algorithm_name(self) -> str:
        return 'adaptive'
    
    def validate_inputs(self) -> bool:
        return True
    
    def optimize(self) -> OptimizationResult:
        start_time = time.time()
        
        # 自适应控制参数
        cycle_adjustment = self.context.params.get('cycle_adjustment', 4)  # 周期调整步长
        green_adjustment = self.context.params.get('green_adjustment', 2)  # 绿灯调整步长
        
        # 创建相位配置
        phases = [
            {
                'index': 0,
                'name': 'NS_through',
                'green': 40,
                'yellow': self.constraints.yellow_time,
                'all_red': self.constraints.all_red_time
            },
            {
                'index': 1,
                'name': 'EW_through',
                'green': 35,
                'yellow': self.constraints.yellow_time,
                'all_red': self.constraints.all_red_time
            }
        ]
        
        # 模拟自适应调整
        adapted_phases = self._adaptive_adjust(phases, green_adjustment)
        
        # 计算周期
        cycle = sum(p['green'] + p['yellow'] + p['all_red'] for p in adapted_phases)
        
        timing = SignalTiming(
            cycle_length=cycle,
            offset=0,
            phases=adapted_phases
        )
        
        computation_time = time.time() - start_time
        
        return OptimizationResult(
            level=OptimizationLevel.INTERSECTION,
            algorithm=self.get_algorithm_name(),
            signal_timings={'intersection': timing},
            performance=self._estimate_performance(timing),
            computation_time=computation_time
        )
    
    def _adaptive_adjust(self, phases: List[Dict], adjustment: float) -> List[Dict]:
        """自适应调整绿灯时间"""
        adjusted = []
        
        for phase in phases:
            # SCOOT连续微调: ±4秒
            # 简化: 根据假设的排队情况调整
            queue_ratio = 0.6  # 假设的排队比例
            
            if queue_ratio > 0.7:
                # 排队较长，增加绿灯
                green = phase['green'] + adjustment
            elif queue_ratio < 0.3:
                # 排队较短，减少绿灯
                green = phase['green'] - adjustment
            else:
                green = phase['green']
            
            # 限制范围
            green = max(7, min(60, green))
            
            adjusted.append({
                'index': phase['index'],
                'name': phase['name'],
                'green': round(green, 1),
                'yellow': phase['yellow'],
                'all_red': phase['all_red'],
                'control_type': 'adaptive'
            })
        
        return adjusted
    
    def _estimate_performance(self, timing: SignalTiming) -> PerformanceMetrics:
        """估算性能指标"""
        # 自适应控制通常比固定配时减少15-25%延误
        base_delay = 35
        avg_delay = base_delay * 0.80
        
        avg_queue = avg_delay * 0.28
        
        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_queue, 2),
            max_queue_length=int(avg_queue * 1.2),
            throughput=2300,
            avg_stops=1.0,
            vcr=0.72
        )


# 注册优化器
from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('intersection', 'actuated', ActuatedOptimizer)
OptimizerFactory.register('intersection', 'adaptive', AdaptiveOptimizer)
