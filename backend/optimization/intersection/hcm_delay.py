"""
HCM延误最小化算法
算法原理: HCM 6th Edition
延误 d = d₁(PF) + d₂ + d₃
"""

import time
import math
from typing import Dict, List

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


class HCMDelayOptimizer(BaseOptimizer):
    """HCM延误最小化优化器"""
    
    def get_algorithm_name(self) -> str:
        return 'hcm'
    
    def validate_inputs(self) -> bool:
        if not self.context.traffic_data:
            return False
        approaches = self.context.traffic_data.get('approaches', {})
        return len(approaches) > 0
    
    def optimize(self) -> OptimizationResult:
        start_time = time.time()
        
        approaches = self.context.traffic_data.get('approaches', {})
        
        best_timing = None
        best_delay = float('inf')
        
        # 搜索最优周期范围
        for cycle in range(60, 181, 5):
            timing = self._optimize_for_cycle(cycle, approaches)
            delay = self._calculate_total_delay(timing, approaches)
            
            if delay < best_delay:
                best_delay = delay
                best_timing = timing
        
        performance = self._calculate_performance(best_timing, approaches)
        computation_time = time.time() - start_time
        
        return OptimizationResult(
            level=OptimizationLevel.INTERSECTION,
            algorithm=self.get_algorithm_name(),
            signal_timings={'intersection': best_timing},
            performance=performance,
            computation_time=computation_time
        )
    
    def _optimize_for_cycle(self, cycle: float, approaches: Dict) -> SignalTiming:
        """为给定周期优化绿灯分配"""
        phases = self._get_phases(approaches)
        total_loss = len(phases) * (self.constraints.yellow_time + self.constraints.all_red_time + 2)
        effective_green = cycle - total_loss
        
        # 计算各相位流量比
        phase_flows = []
        for phase in phases:
            total_flow = sum(
                approaches.get(m, {}).get('volume', 0)
                for m in phase['movements']
            )
            phase_flows.append(total_flow)
        
        sum_flow = sum(phase_flows)
        
        # 按流量比分配绿灯时间
        phase_timings = []
        for i, (phase, flow) in enumerate(zip(phases, phase_flows)):
            if sum_flow > 0:
                green = (flow / sum_flow) * effective_green
            else:
                green = effective_green / len(phases)
            
            green = max(self.constraints.min_green_time, green)
            green = min(self.constraints.max_green_time, green)
            
            phase_timings.append({
                'index': i,
                'name': phase['name'],
                'green': round(green, 1),
                'yellow': self.constraints.yellow_time,
                'all_red': self.constraints.all_red_time,
                'movements': phase['movements']
            })
        
        return SignalTiming(
            cycle_length=cycle,
            offset=0,
            phases=phase_timings
        )
    
    def _get_phases(self, approaches: Dict) -> List[Dict]:
        """获取相位配置"""
        return [
            {'name': 'NS_through', 'movements': ['north_through', 'south_through']},
            {'name': 'NS_left', 'movements': ['north_left', 'south_left']},
            {'name': 'EW_through', 'movements': ['east_through', 'west_through']},
            {'name': 'EW_left', 'movements': ['east_left', 'west_left']}
        ]
    
    def _calculate_total_delay(self, timing: SignalTiming, approaches: Dict) -> float:
        """计算总延误 (HCM方法)"""
        total_delay = 0
        total_flow = 0
        
        for phase in timing.phases:
            for movement in phase.get('movements', []):
                if movement not in approaches:
                    continue
                
                flow = approaches[movement].get('volume', 0)
                if flow == 0:
                    continue
                
                # HCM延误计算
                delay = self._calculate_hcm_delay(
                    flow=flow,
                    cycle=timing.cycle_length,
                    green=phase['green'],
                    saturation_flow=1800
                )
                
                total_delay += delay * flow
                total_flow += flow
        
        return total_delay / total_flow if total_flow > 0 else 0
    
    def _calculate_hcm_delay(
        self, flow: float, cycle: float, green: float, saturation_flow: float
    ) -> float:
        """HCM延误公式"""
        g_c = green / cycle
        X = flow / (saturation_flow * g_c) if g_c > 0 else 1
        
        # d₁: 均匀延误
        if X < 1:
            d1 = (0.5 * cycle * (1 - g_c) ** 2) / (1 - min(1, X) * g_c)
        else:
            d1 = 0.5 * cycle * (1 - g_c)
        
        # d₂: 增量延误 (简化)
        T = 0.25  # 分析时段(小时)
        k = 0.5   # 增量延误校正系数
        I = 1.0   # 上游 filtering/metering 校正系数
        c = saturation_flow * g_c
        
        if X < 1:
            d2 = 900 * T * ((X - 1) + math.sqrt((X - 1) ** 2 + (8 * k * I * X) / (c * T)))
        else:
            d2 = 900 * T * ((X - 1) + math.sqrt((X - 1) ** 2 + (8 * k * I) / (c * T)))
        
        return d1 + d2
    
    def _calculate_performance(
        self, timing: SignalTiming, approaches: Dict
    ) -> PerformanceMetrics:
        """计算性能指标"""
        total_delay = 0
        total_flow = 0
        total_queue = 0
        
        for phase in timing.phases:
            for movement in phase.get('movements', []):
                if movement not in approaches:
                    continue
                
                flow = approaches[movement].get('volume', 0)
                if flow == 0:
                    continue
                
                delay = self._calculate_hcm_delay(
                    flow=flow,
                    cycle=timing.cycle_length,
                    green=phase['green'],
                    saturation_flow=1800
                )
                
                total_delay += delay * flow
                total_flow += flow
                
                # 估算排队长度
                g_c = phase['green'] / timing.cycle_length
                queue = flow * (1 - g_c) / 3600 * timing.cycle_length
                total_queue += queue
        
        avg_delay = total_delay / total_flow if total_flow > 0 else 0
        avg_queue = total_queue / len(approaches) if approaches else 0
        
        # 计算饱和度
        vcr = sum(
            a.get('volume', 0) / 1800
            for a in approaches.values()
        ) / len(approaches) if approaches else 0
        
        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_queue, 2),
            max_queue_length=int(avg_queue * 1.5),
            throughput=int(total_flow * 0.85),
            avg_stops=round(avg_delay / 20, 2),
            vcr=round(vcr, 2)
        )


# 注册优化器
from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('intersection', 'hcm', HCMDelayOptimizer)
