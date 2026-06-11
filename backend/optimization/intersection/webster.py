"""
Webster经典配时算法
算法原理: Webster, 1958
最优周期 C₀ = (1.5L + 5) / (1 - ΣYᵢ)
"""

import time
from typing import Dict, List

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


class WebsterOptimizer(BaseOptimizer):
    """Webster配时优化器"""
    
    def get_algorithm_name(self) -> str:
        return 'webster'
    
    def validate_inputs(self) -> bool:
        """验证输入数据"""
        if not self.context.traffic_data:
            return False
        
        # 检查是否有流量数据
        approaches = self.context.traffic_data.get('approaches', {})
        if not approaches:
            return False
        
        return True
    
    def optimize(self) -> OptimizationResult:
        """执行Webster优化"""
        start_time = time.time()
        
        # 获取流量数据
        approaches = self.context.traffic_data.get('approaches', {})
        
        # 计算各相位流量比
        phase_flow_ratios = self._calculate_phase_flow_ratios(approaches)
        
        # 计算总损失时间
        total_loss_time = self._calculate_total_loss_time()
        
        # 计算最优周期
        optimal_cycle = self._calculate_optimal_cycle(phase_flow_ratios, total_loss_time)
        
        # 计算各相位绿灯时间
        phases = self._calculate_phase_green_times(
            optimal_cycle, phase_flow_ratios, total_loss_time
        )
        
        # 创建配时方案
        signal_timing = SignalTiming(
            cycle_length=optimal_cycle,
            offset=0,
            phases=phases
        )
        
        # 计算性能指标
        performance = self._estimate_performance(signal_timing, approaches)
        
        computation_time = time.time() - start_time
        
        return OptimizationResult(
            level=OptimizationLevel.INTERSECTION,
            algorithm=self.get_algorithm_name(),
            signal_timings={'intersection': signal_timing},
            performance=performance,
            computation_time=computation_time
        )
    
    def _calculate_phase_flow_ratios(self, approaches: Dict) -> Dict[int, float]:
        """计算各相位流量比"""
        phase_ratios = {}
        
        # 假设相位0: 南北直行, 相位1: 南北左转, 相位2: 东西直行, 相位3: 东西左转
        phase_mapping = {
            0: ['north_through', 'south_through'],
            1: ['north_left', 'south_left'],
            2: ['east_through', 'west_through'],
            3: ['east_left', 'west_left']
        }
        
        for phase_idx, movements in phase_mapping.items():
            max_ratio = 0
            for movement in movements:
                if movement in approaches:
                    flow = approaches[movement].get('volume', 0)
                    saturation_flow = 1800  # 饱和流量(pcu/h)
                    ratio = flow / saturation_flow
                    max_ratio = max(max_ratio, ratio)
            
            phase_ratios[phase_idx] = max_ratio
        
        return phase_ratios
    
    def _calculate_total_loss_time(self) -> float:
        """计算总损失时间"""
        # 假设有4个相位
        num_phases = 4
        startup_loss = 2  # 启动损失时间(秒)
        yellow_time = self.constraints.yellow_time
        all_red_time = self.constraints.all_red_time
        
        total_loss = num_phases * (startup_loss + yellow_time + all_red_time)
        return total_loss
    
    def _calculate_optimal_cycle(self, phase_ratios: Dict[int, float], total_loss: float) -> float:
        """计算最优周期"""
        # C₀ = (1.5L + 5) / (1 - ΣYᵢ)
        sum_y = sum(phase_ratios.values())
        
        if sum_y >= 1:
            # 饱和度过高，使用最大周期
            return self.constraints.max_cycle_length
        
        optimal_cycle = (1.5 * total_loss + 5) / (1 - sum_y)
        
        # 限制在约束范围内
        optimal_cycle = max(self.constraints.min_cycle_length, optimal_cycle)
        optimal_cycle = min(self.constraints.max_cycle_length, optimal_cycle)
        
        return round(optimal_cycle)
    
    def _calculate_phase_green_times(
        self, cycle: float, phase_ratios: Dict[int, float], total_loss: float
    ) -> List[Dict]:
        """计算各相位绿灯时间"""
        effective_green = cycle - total_loss
        sum_y = sum(phase_ratios.values())
        
        phases = []
        for phase_idx in sorted(phase_ratios.keys()):
            ratio = phase_ratios[phase_idx]
            
            # 按流量比分配绿灯时间
            if sum_y > 0:
                green_time = (ratio / sum_y) * effective_green
            else:
                green_time = effective_green / len(phase_ratios)
            
            # 限制在约束范围内
            green_time = max(self.constraints.min_green_time, green_time)
            green_time = min(self.constraints.max_green_time, green_time)
            
            phases.append({
                'index': phase_idx,
                'green': round(green_time, 1),
                'yellow': self.constraints.yellow_time,
                'all_red': self.constraints.all_red_time
            })
        
        return phases
    
    def _estimate_performance(
        self, timing: SignalTiming, approaches: Dict
    ) -> PerformanceMetrics:
        """估算性能指标"""
        # 使用Webster延误公式估算
        cycle = timing.cycle_length
        
        total_delay = 0
        total_flow = 0
        total_queue = 0
        
        for phase in timing.phases:
            phase_idx = phase['index']
            green = phase['green']
            
            # 获取对应流向的流量
            # 简化处理: 假设每个相位有对应流向
            flow = self._get_phase_flow(phase_idx, approaches)
            
            # Webster延误公式
            # d = 0.5C(1-g/C)² / (1 - min(1,X)(g/C))
            g_c_ratio = green / cycle
            saturation_flow = 1800
            x = flow / (saturation_flow * g_c_ratio) if g_c_ratio > 0 else 1
            
            if x < 1:
                delay = 0.5 * cycle * (1 - g_c_ratio)**2 / (1 - min(1, x) * g_c_ratio)
            else:
                delay = cycle * (1 - g_c_ratio)  # 过饱和
            
            total_delay += delay * flow
            total_flow += flow
            
            # 估算排队长度
            queue = flow * (1 - g_c_ratio) / 3600 * cycle
            total_queue += queue
        
        avg_delay = total_delay / total_flow if total_flow > 0 else 0
        avg_queue = total_queue / len(timing.phases) if timing.phases else 0
        
        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_queue, 2),
            max_queue_length=int(avg_queue * 1.5),
            throughput=int(total_flow * 0.8),  # 假设80%通行能力
            avg_stops=1.5,
            vcr=round(sum(self._get_phase_flow(i, approaches) / 1800 
                         for i in range(len(timing.phases))), 2)
        )
    
    def _get_phase_flow(self, phase_idx: int, approaches: Dict) -> float:
        """获取相位对应的流量"""
        phase_mapping = {
            0: ['north_through', 'south_through'],
            1: ['north_left', 'south_left'],
            2: ['east_through', 'west_through'],
            3: ['east_left', 'west_left']
        }
        
        movements = phase_mapping.get(phase_idx, [])
        total_flow = 0
        
        for movement in movements:
            if movement in approaches:
                total_flow += approaches[movement].get('volume', 0)
        
        return total_flow


# 注册优化器
from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('intersection', 'webster', WebsterOptimizer)
