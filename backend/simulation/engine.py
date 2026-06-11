"""
仿真引擎核心逻辑
基于UXsim的简化实现
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class VehicleState:
    """车辆状态"""
    id: str
    link_id: str
    lane_index: int
    position: float  # 在路段上的位置(米)
    speed: float  # 速度(m/s)
    target_speed: float  # 目标速度
    waiting_time: float = 0  # 等待时间
    stops: int = 0  # 停车次数


@dataclass
class SignalState:
    """信号灯状态"""
    node_id: str
    current_phase: int
    phase_elapsed: float  # 当前相位已过时间
    phases: List[Dict]  # 相位配置


@dataclass
class LinkState:
    """路段状态"""
    id: str
    vehicles: List[VehicleState] = field(default_factory=list)
    density: float = 0  # 密度(辆/km)
    flow: float = 0  # 流量(辆/h)
    avg_speed: float = 0  # 平均速度


class SimulationEngine:
    """仿真引擎"""
    
    def __init__(self, network_data, config=None):
        self.network_data = network_data
        self.config = config or {}
        
        # 仿真参数
        self.step_size = self.config.get('step_size', 1.0)
        self.duration = self.config.get('duration', 3600)
        self.current_time = 0
        
        # 状态
        self.vehicles: Dict[str, VehicleState] = {}
        self.signals: Dict[str, SignalState] = {}
        self.links: Dict[str, LinkState] = {}
        
        # 跟车模型参数 (简化Wiedemann)
        self.min_gap = 2.0  # 最小间距(米)
        self.max_acceleration = 2.0  # 最大加速度(m/s²)
        self.comfortable_deceleration = 3.0  # 舒适减速度(m/s²)
        
        # 统计
        self.total_vehicles_generated = 0
        self.total_vehicles_completed = 0
        
        # 初始化
        self._initialize_network()
    
    def _initialize_network(self):
        """初始化路网状态"""
        # 初始化路段
        for edge in self.network_data.get('edges', []):
            self.links[edge['id']] = LinkState(id=edge['id'])
        
        # 初始化信号灯
        for signal in self.network_data.get('signals', []):
            self.signals[signal['node_id']] = SignalState(
                node_id=signal['node_id'],
                current_phase=0,
                phase_elapsed=0,
                phases=signal.get('phases', [])
            )
    
    def step(self):
        """执行一个仿真步长"""
        # 1. 更新信号灯
        self._update_signals()
        
        # 2. 生成车辆
        self._generate_vehicles()
        
        # 3. 更新车辆位置
        self._update_vehicles()
        
        # 4. 处理交叉口
        self._process_intersections()
        
        # 5. 移除完成的车辆
        self._remove_completed_vehicles()
        
        # 6. 更新时间
        self.current_time += self.step_size
        
        return self._get_state()
    
    def _update_signals(self):
        """更新信号灯状态"""
        for node_id, signal in self.signals.items():
            if not signal.phases:
                continue
            
            current_phase_config = signal.phases[signal.current_phase]
            phase_duration = current_phase_config.get('green', 30) + \
                           current_phase_config.get('yellow', 3) + \
                           current_phase_config.get('all_red', 1)
            
            signal.phase_elapsed += self.step_size
            
            if signal.phase_elapsed >= phase_duration:
                # 切换到下一相位
                signal.current_phase = (signal.current_phase + 1) % len(signal.phases)
                signal.phase_elapsed = 0
    
    def _generate_vehicles(self):
        """生成车辆"""
        # 简化实现: 随机生成车辆
        for edge_id, link in self.links.items():
            # 根据流量概率生成车辆
            edge_data = self._get_edge_data(edge_id)
            if not edge_data:
                continue
            
            flow = edge_data.get('flow', 0)  # 辆/小时
            prob = (flow / 3600) * self.step_size
            
            if random.random() < prob:
                vehicle_id = f"v_{self.total_vehicles_generated}"
                vehicle = VehicleState(
                    id=vehicle_id,
                    link_id=edge_id,
                    lane_index=random.randint(0, edge_data.get('lanes', 1) - 1),
                    position=0,
                    speed=edge_data.get('speed_limit', 50) / 3.6,  # 转换为m/s
                    target_speed=edge_data.get('speed_limit', 50) / 3.6
                )
                self.vehicles[vehicle_id] = vehicle
                self.links[edge_id].vehicles.append(vehicle)
                self.total_vehicles_generated += 1
    
    def _update_vehicles(self):
        """更新车辆位置 (简化跟车模型)"""
        for edge_id, link in self.links.items():
            # 按位置排序车辆
            link.vehicles.sort(key=lambda v: v.position, reverse=True)
            
            for i, vehicle in enumerate(link.vehicles):
                # 获取前车
                leader = link.vehicles[i - 1] if i > 0 else None
                
                # 计算加速度
                acceleration = self._calculate_acceleration(vehicle, leader, edge_id)
                
                # 更新速度
                vehicle.speed = max(0, vehicle.speed + acceleration * self.step_size)
                vehicle.speed = min(vehicle.speed, vehicle.target_speed)
                
                # 更新位置
                vehicle.position += vehicle.speed * self.step_size
                
                # 记录停车
                if vehicle.speed < 0.1 and acceleration < 0:
                    vehicle.stops += 1
                    vehicle.waiting_time += self.step_size
    
    def _calculate_acceleration(self, vehicle, leader, edge_id):
        """计算加速度 (简化跟车模型)"""
        if leader is None:
            # 无前车，自由行驶
            return self.max_acceleration * (1 - vehicle.speed / vehicle.target_speed)
        
        # 计算与前车的间距
        gap = leader.position - vehicle.position - self.min_gap
        
        if gap <= 0:
            # 紧急制动
            return -self.comfortable_deceleration * 2
        
        # 简化的跟车模型
        speed_diff = vehicle.speed - leader.speed
        desired_gap = self.min_gap + vehicle.speed * 1.5  # 1.5秒车头时距
        
        if gap < desired_gap:
            # 需要减速
            deceleration = self.comfortable_deceleration * (desired_gap - gap) / desired_gap
            return -deceleration
        else:
            # 可以加速
            acceleration = self.max_acceleration * (1 - vehicle.speed / vehicle.target_speed)
            return acceleration
    
    def _process_intersections(self):
        """处理交叉口车辆放行"""
        for node_id, signal in self.signals.items():
            if not signal.phases:
                continue

            current_phase = signal.phases[signal.current_phase]
            green_links = current_phase.get('green_links', [])

            if not green_links:
                phase_idx = signal.current_phase
                edge_ids = list(self.links.keys())
                if len(edge_ids) > 1:
                    half = len(edge_ids) // 2
                    green_links = edge_ids[:half] if phase_idx == 0 else edge_ids[half:]

            for edge_id in green_links:
                link = self.links.get(edge_id)
                if not link:
                    continue

                discharge_count = min(3, len(link.vehicles))
                for vehicle in link.vehicles[:discharge_count]:
                    if vehicle.speed < 1.0:
                        vehicle.speed = vehicle.target_speed * 0.5
    
    def _remove_completed_vehicles(self):
        """移除已完成行程的车辆，支持全网多路段连续行驶"""
        completed = []

        for vehicle_id, vehicle in self.vehicles.items():
            edge_data = self._get_edge_data(vehicle.link_id)
            if not edge_data:
                continue

            edge_length = edge_data.get('length', 1000)

            if vehicle.position >= edge_length:
                to_node = edge_data.get('to', '')
                next_edges = [
                    e for e in self.network_data.get('edges', [])
                    if e.get('from', '') == to_node and e.get('id', '') != vehicle.link_id
                ]

                if next_edges:
                    next_edge = random.choice(next_edges)
                    next_edge_id = next_edge['id']
                    vehicle.link_id = next_edge_id
                    vehicle.position = 0
                    vehicle.target_speed = next_edge.get('speed_limit', 50) / 3.6

                    old_link = self.links.get(vehicle.link_id)
                    if old_link:
                        old_link.vehicles = [v for v in old_link.vehicles if v.id != vehicle_id]

                    if next_edge_id in self.links:
                        self.links[next_edge_id].vehicles.append(vehicle)
                else:
                    completed.append(vehicle_id)
                    self.total_vehicles_completed += 1

        for vehicle_id in completed:
            vehicle = self.vehicles.pop(vehicle_id)
            link = self.links.get(vehicle.link_id)
            if link:
                link.vehicles = [v for v in link.vehicles if v.id != vehicle_id]
    
    def _get_edge_data(self, edge_id):
        """获取路段数据"""
        for edge in self.network_data.get('edges', []):
            if edge['id'] == edge_id:
                return edge
        return None
    
    def _get_state(self):
        """获取当前状态"""
        return {
            'time': self.current_time,
            'vehicles': [
                {
                    'id': v.id,
                    'link_id': v.link_id,
                    'lane': v.lane_index,
                    'position': v.position,
                    'speed': v.speed * 3.6,  # 转换为km/h
                    'stops': v.stops
                }
                for v in self.vehicles.values()
            ],
            'signals': {
                node_id: {
                    'current_phase': s.current_phase,
                    'phase_elapsed': s.phase_elapsed
                }
                for node_id, s in self.signals.items()
            },
            'metrics': self._calculate_metrics()
        }
    
    def _calculate_metrics(self):
        """计算性能指标"""
        if not self.vehicles:
            return {
                'avg_delay': 0,
                'avg_queue_length': 0,
                'max_queue_length': 0,
                'throughput': self.total_vehicles_completed,
                'avg_stops': 0
            }
        
        # 计算平均延误
        total_waiting = sum(v.waiting_time for v in self.vehicles.values())
        avg_delay = total_waiting / len(self.vehicles) if self.vehicles else 0
        
        # 计算排队长度
        queue_lengths = []
        for link in self.links.values():
            queue = sum(1 for v in link.vehicles if v.speed < 1.0)
            queue_lengths.append(queue)
        
        avg_queue = sum(queue_lengths) / len(queue_lengths) if queue_lengths else 0
        max_queue = max(queue_lengths) if queue_lengths else 0
        
        # 计算平均停车次数
        total_stops = sum(v.stops for v in self.vehicles.values())
        avg_stops = total_stops / len(self.vehicles) if self.vehicles else 0
        
        return {
            'avg_delay': round(avg_delay, 2),
            'avg_queue_length': round(avg_queue, 2),
            'max_queue_length': max_queue,
            'throughput': self.total_vehicles_completed,
            'avg_stops': round(avg_stops, 2)
        }
    
    def get_results(self):
        """获取仿真结果"""
        return {
            'duration': self.current_time,
            'total_vehicles': self.total_vehicles_generated,
            'completed_vehicles': self.total_vehicles_completed,
            'metrics': self._calculate_metrics()
        }
