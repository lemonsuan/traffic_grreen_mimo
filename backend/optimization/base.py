"""
优化器基类和数据结构定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class OptimizationLevel(Enum):
    """优化层级"""
    INTERSECTION = 'intersection'  # 单点交叉口
    CORRIDOR = 'corridor'  # 干线绿波
    NETWORK = 'network'  # 区域路网


@dataclass
class SignalTiming:
    """信号配时方案"""
    cycle_length: float  # 周期长(秒)
    offset: float = 0  # 相位差(秒)
    phases: List[Dict] = field(default_factory=list)  # 相位配置
    
    def to_dict(self):
        return {
            'cycle_length': self.cycle_length,
            'offset': self.offset,
            'phases': self.phases
        }


@dataclass
class PerformanceMetrics:
    """性能指标"""
    avg_delay: float = 0  # 平均延误(秒)
    avg_queue_length: float = 0  # 平均排队长度(辆)
    max_queue_length: int = 0  # 最大排队长度
    throughput: int = 0  # 吞吐量(辆)
    avg_stops: float = 0  # 平均停车次数
    vcr: float = 0  # 饱和度(v/c ratio)
    
    def to_dict(self):
        return {
            'avg_delay': self.avg_delay,
            'avg_queue_length': self.avg_queue_length,
            'max_queue_length': self.max_queue_length,
            'throughput': self.throughput,
            'avg_stops': self.avg_stops,
            'vcr': self.vcr
        }


@dataclass
class OptimizationConstraints:
    """优化约束"""
    min_green_time: float = 7  # 最小绿灯时间(秒)
    max_green_time: float = 60  # 最大绿灯时间(秒)
    min_cycle_length: float = 60  # 最小周期(秒)
    max_cycle_length: float = 180  # 最大周期(秒)
    yellow_time: float = 3  # 黄灯时间(秒)
    all_red_time: float = 1  # 全红时间(秒)
    pedestrian_phase_required: bool = False  # 是否需要行人相位


@dataclass
class OptimizationContext:
    """优化上下文"""
    level: OptimizationLevel  # 优化层级
    network_id: int  # 路网ID
    node_ids: List[str] = field(default_factory=list)  # 节点ID列表
    traffic_data: Dict = field(default_factory=dict)  # 交通数据
    constraints: OptimizationConstraints = field(default_factory=OptimizationConstraints)
    params: Dict = field(default_factory=dict)  # 算法特定参数


@dataclass
class OptimizationResult:
    """优化结果"""
    level: OptimizationLevel
    algorithm: str
    signal_timings: Dict[str, SignalTiming] = field(default_factory=dict)  # 路口ID -> 配时方案
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    convergence: List[float] = field(default_factory=list)  # 收敛曲线
    pareto_front: Optional[List[Dict]] = None  # 多目标Pareto前沿
    computation_time: float = 0  # 计算时间(秒)
    
    def to_dict(self):
        return {
            'level': self.level.value,
            'algorithm': self.algorithm,
            'signal_timings': {
                k: v.to_dict() for k, v in self.signal_timings.items()
            },
            'performance': self.performance.to_dict(),
            'convergence': self.convergence,
            'pareto_front': self.pareto_front,
            'computation_time': self.computation_time
        }


class BaseOptimizer(ABC):
    """优化器基类"""
    
    def __init__(self, context: OptimizationContext):
        self.context = context
        self.constraints = context.constraints
    
    @abstractmethod
    def optimize(self) -> OptimizationResult:
        """执行优化"""
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """获取算法名称"""
        pass
    
    def validate_inputs(self) -> bool:
        """验证输入数据"""
        return True
    
    def calculate_performance(self, signal_timings: Dict[str, SignalTiming]) -> PerformanceMetrics:
        """计算性能指标 (需要子类实现或使用仿真器)"""
        return PerformanceMetrics()


class OptimizerFactory:
    """优化器工厂"""
    
    _optimizers = {}
    
    @classmethod
    def register(cls, level: str, algorithm: str, optimizer_class):
        """注册优化器"""
        key = (level, algorithm)
        cls._optimizers[key] = optimizer_class
    
    @classmethod
    def create(cls, context: OptimizationContext, algorithm: str) -> BaseOptimizer:
        """创建优化器"""
        key = (context.level.value, algorithm)
        optimizer_class = cls._optimizers.get(key)
        
        if not optimizer_class:
            raise ValueError(f"Unknown optimizer: {key}")
        
        return optimizer_class(context)
    
    @classmethod
    def get_available_algorithms(cls, level: str) -> List[str]:
        """获取可用算法列表"""
        return [
            algorithm for (l, algorithm) in cls._optimizers.keys()
            if l == level
        ]
