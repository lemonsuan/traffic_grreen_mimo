"""
仿真引擎核心逻辑
基于IDM跟车模型的微观交通仿真
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
    route: List[str] = field(default_factory=list)  # 预定路径
    route_index: int = 0  # 当前路径索引
    trip_time: float = 0  # 行程时间


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
    queue_count: int = 0  # 排队车辆数


class SimulationEngine:
    """仿真引擎 - IDM跟车模型"""
    
    # IDM参数
    IDM_V0 = 1.0  # 期望速度倍数
    IDM_T = 1.5  # 安全车头时距(秒)
    IDM_A = 1.5  # 最大加速度(m/s²)
    IDM_B = 2.5  # 舒适减速度(m/s²)
    IDM_DELTA = 4  # 加速度指数
    IDM_S0 = 2.0  # 最小净间距(米)
    IDM_LENGTH = 5.0  # 车辆平均长度(米)
    
    # 信号控制参数
    SATURATION_FLOW = 1800  # 饱和流率(辆/小时/车道)
    DISCHARGE_INTERVAL = 2.0  # 放行间隔(秒)
    
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
        
        # 路网拓扑
        self.adjacency: Dict[str, List[str]] = {}  # node -> outgoing edge ids
        self.edge_from_to: Dict[str, Tuple[str, str]] = {}  # edge_id -> (from_node, to_node)
        self.edge_data_map: Dict[str, Dict] = {}
        
        # 统计
        self.total_vehicles_generated = 0
        self.total_vehicles_completed = 0
        self.total_travel_time = 0
        self.total_delay = 0
        
        # 初始化
        self._initialize_network()
        self._build_topology()
        self._precompute_routes()
    
    def _initialize_network(self):
        """初始化路网状态"""
        for edge in self.network_data.get('edges', []):
            edge_id = edge.get('id') or edge.get('edge_id', '')
            edge['id'] = edge_id  # normalize
            edge.setdefault('from', edge.get('from_node', ''))
            edge.setdefault('to', edge.get('to_node', ''))
            edge.setdefault('lanes', edge.get('lanes_count', 1))
            edge.setdefault('road_class', edge.get('road_class', 'primary'))
            # 从capacity推算flow
            if 'flow' not in edge:
                cap = edge.get('capacity', 0)
                edge['flow'] = int(cap * 0.5) if cap > 0 else 0
            
            self.links[edge_id] = LinkState(id=edge_id)
            self.edge_data_map[edge_id] = edge
            from_node = edge['from']
            to_node = edge['to']
            self.edge_from_to[edge_id] = (from_node, to_node)
        
        for signal in self.network_data.get('signals', []):
            node_id = signal.get('node_id', '')
            phases = signal.get('phases', [])
            if phases:
                self.signals[node_id] = SignalState(
                    node_id=node_id,
                    current_phase=0,
                    phase_elapsed=0,
                    phases=phases
                )
    
    def _build_topology(self):
        """构建邻接表"""
        for edge_id, (from_node, to_node) in self.edge_from_to.items():
            if from_node not in self.adjacency:
                self.adjacency[from_node] = []
            self.adjacency[from_node].append(edge_id)
    
    def _precompute_routes(self):
        """预计算OD路径"""
        edges = list(self.edge_data_map.keys())
        if not edges:
            return
        
        # 找到起点(无入边的节点)和终点(无出边的节点)
        all_nodes = set()
        for from_n, to_n in self.edge_from_to.values():
            all_nodes.add(from_n)
            all_nodes.add(to_n)
        
        has_incoming = {to_n for _, to_n in self.edge_from_to.values()}
        has_outgoing = set(self.adjacency.keys())
        
        self.source_nodes = list(all_nodes - has_incoming) or list(has_outgoing)[:3]
        self.sink_nodes = list(all_nodes - has_outgoing) or list(all_nodes - has_outgoing)[:3]
        
        if not self.source_nodes:
            self.source_nodes = list(all_nodes)[:1]
        if not self.sink_nodes:
            self.sink_nodes = list(all_nodes)[:1]
    
    def _find_route(self, from_node: str, to_node: str, max_depth: int = 10) -> List[str]:
        """BFS找路径"""
        if from_node == to_node:
            return []
        
        visited = {from_node}
        queue = [(from_node, [])]
        
        while queue and max_depth > 0:
            max_depth -= 1
            current, path = queue.pop(0)
            
            for edge_id in self.adjacency.get(current, []):
                _, next_node = self.edge_from_to[edge_id]
                
                if next_node == to_node:
                    return path + [edge_id]
                
                if next_node not in visited:
                    visited.add(next_node)
                    queue.append((next_node, path + [edge_id]))
        
        # 找不到完整路径，返回随机下一步
        outgoing = self.adjacency.get(from_node, [])
        return [random.choice(outgoing)] if outgoing else []
    
    def step(self):
        """执行一个仿真步长"""
        self._update_signals()
        self._generate_vehicles()
        self._update_vehicles()
        self._process_intersections()
        self._remove_completed_vehicles()
        self.current_time += self.step_size
        return self._get_state()
    
    def _update_signals(self):
        """更新信号灯状态"""
        for node_id, signal in self.signals.items():
            if not signal.phases:
                continue
            
            current_phase_config = signal.phases[signal.current_phase]
            phase_duration = (
                current_phase_config.get('green', 30) +
                current_phase_config.get('yellow', 3) +
                current_phase_config.get('all_red', 1)
            )
            
            signal.phase_elapsed += self.step_size
            
            if signal.phase_elapsed >= phase_duration:
                signal.current_phase = (signal.current_phase + 1) % len(signal.phases)
                signal.phase_elapsed = 0
    
    def _generate_vehicles(self):
        """生成车辆 - 基于路段流量和时段特征"""
        for edge_id, edge_data in self.edge_data_map.items():
            from_node = edge_data.get('from', '')
            
            # 只在源节点或有入边的节点生成车辆
            is_source = from_node in self.source_nodes
            
            flow = edge_data.get('flow', 0)
            if flow <= 0:
                # 从capacity推算流量
                capacity = edge_data.get('capacity', 0)
                if capacity > 0:
                    flow = capacity * 0.5  # 假定50%利用率
                elif is_source:
                    flow = 400
                else:
                    continue
            
            # 时段修正因子
            hour = (self.current_time / 3600) % 24
            time_factor = self._get_time_factor(hour)
            
            # 生成概率
            prob = (flow * time_factor / 3600) * self.step_size
            
            # 检查路段是否过饱和 - 避免无限堆积
            link = self.links[edge_data['id']]
            max_vehicles = int(edge_data.get('capacity', 1800) * edge_data.get('lanes', 1) / 3600 * (edge_data.get('length', 500) / 8))
            if len(link.vehicles) >= max(max_vehicles, 5):
                continue
            
            if random.random() < prob:
                vehicle_id = f"v_{self.total_vehicles_generated}"
                
                # 规划路径
                target_sink = random.choice(self.sink_nodes) if self.sink_nodes else None
                route = self._find_route(from_node, target_sink) if target_sink else []
                
                speed_limit = edge_data.get('speed_limit', 50) / 3.6
                lanes = edge_data.get('lanes', 1)
                
                vehicle = VehicleState(
                    id=vehicle_id,
                    link_id=edge_id,
                    lane_index=random.randint(0, lanes - 1),
                    position=0,
                    speed=speed_limit * random.uniform(0.7, 1.0),
                    target_speed=speed_limit,
                    route=route,
                    route_index=0
                )
                self.vehicles[vehicle_id] = vehicle
                link.vehicles.append(vehicle)
                self.total_vehicles_generated += 1
    
    def _get_time_factor(self, hour: float) -> float:
        """时段流量修正因子"""
        # 早高峰 7-9, 晚高峰 17-19
        if 7 <= hour < 9:
            return 1.8
        elif 17 <= hour < 19:
            return 1.6
        elif 9 <= hour < 17:
            return 1.0
        elif 19 <= hour < 22:
            return 0.7
        else:
            return 0.3
    
    def _update_vehicles(self):
        """更新车辆位置 - IDM跟车模型"""
        for edge_id, link in self.links.items():
            if not link.vehicles:
                continue
            
            # 按位置降序排列(前车在前)
            link.vehicles.sort(key=lambda v: v.position, reverse=True)
            
            edge_data = self.edge_data_map.get(edge_id, {})
            edge_length = edge_data.get('length', 500)
            speed_limit = edge_data.get('speed_limit', 50) / 3.6
            
            # 检查信号灯状态 - 红灯作为虚拟障碍物
            to_node = edge_data.get('to', '')
            signal = self.signals.get(to_node)
            is_red = False
            if signal and signal.phases:
                current_phase = signal.phases[signal.current_phase]
                green_links = current_phase.get('green_links', [])
                if green_links and edge_id not in green_links:
                    is_red = True
            
            for i, vehicle in enumerate(link.vehicles):
                vehicle.trip_time += self.step_size
                vehicle.target_speed = speed_limit
                
                # 前车
                leader = link.vehicles[i - 1] if i > 0 else None
                
                # 红灯时在停车线前的车辆需要减速
                stop_pos = edge_length - 5  # 停车线位置
                virtual_leader_pos = None
                virtual_leader_speed = 0
                
                if is_red and vehicle.position < stop_pos and vehicle.position > stop_pos - 100:
                    virtual_leader_pos = stop_pos
                    virtual_leader_speed = 0
                
                # IDM加速度计算
                acc = self._idm_acceleration(
                    vehicle, leader, virtual_leader_pos, virtual_leader_speed
                )
                
                # 更新速度
                old_speed = vehicle.speed
                vehicle.speed = max(0, vehicle.speed + acc * self.step_size)
                vehicle.speed = min(vehicle.speed, vehicle.target_speed * 1.1)
                
                # 更新位置
                vehicle.position += vehicle.speed * self.step_size
                vehicle.position = max(0, vehicle.position)
                
                # 记录停车
                if vehicle.speed < 0.5 and old_speed >= 0.5:
                    vehicle.stops += 1
                
                if vehicle.speed < 0.5:
                    vehicle.waiting_time += self.step_size
    
    def _idm_acceleration(self, vehicle, leader, virtual_leader_pos, virtual_leader_speed):
        """IDM (Intelligent Driver Model) 加速度计算"""
        v = vehicle.speed
        v0 = vehicle.target_speed
        
        # 自由流加速度
        free_acc = self.IDM_A * (1 - (v / v0) ** self.IDM_DELTA) if v0 > 0 else 0
        
        # 确定有效前车信息
        if leader:
            leader_pos = leader.position
            leader_speed = leader.speed
        elif virtual_leader_pos is not None:
            leader_pos = virtual_leader_pos
            leader_speed = virtual_leader_speed
        else:
            return free_acc
        
        # 间距
        gap = leader_pos - vehicle.position - self.IDM_LENGTH
        gap = max(gap, 0.1)
        
        # 期望间距
        dv = v - leader_speed
        tau = self.IDM_T
        a = self.IDM_A
        b = self.IDM_B
        s0 = self.IDM_S0
        
        s_star = s0 + max(0, v * tau + v * dv / (2 * math.sqrt(a * b)))
        
        # IDM加速度
        interaction = -a * (s_star / gap) ** 2
        
        return free_acc + interaction
    
    def _process_intersections(self):
        """处理交叉口车辆放行"""
        for node_id, signal in self.signals.items():
            if not signal.phases:
                continue
            
            current_phase = signal.phases[signal.current_phase]
            green_links = current_phase.get('green_links', [])
            
            if not green_links:
                # 没有明确的绿灯路段，按相位分配
                phase_idx = signal.current_phase
                edge_ids = list(self.edge_data_map.keys())
                if len(edge_ids) > 1:
                    chunk = max(1, len(edge_ids) // len(signal.phases))
                    start = phase_idx * chunk
                    green_links = edge_ids[start:start + chunk]
            
            for edge_id in green_links:
                link = self.links.get(edge_id)
                if not link:
                    continue
                
                edge_data = self.edge_data_map.get(edge_id, {})
                lanes = edge_data.get('lanes', 1)
                
                # 饱和流率放行: 每车道每秒放行 sat_flow/3600 辆
                discharge_rate = self.SATURATION_FLOW * lanes / 3600 * self.step_size
                discharge_count = min(int(discharge_rate) + (1 if random.random() < discharge_rate % 1 else 0), len(link.vehicles))
                
                for vehicle in link.vehicles[:discharge_count]:
                    if vehicle.speed < 2.0:
                        vehicle.speed = vehicle.target_speed * 0.6
    
    def _remove_completed_vehicles(self):
        """移除已完成行程的车辆，支持全网多路段连续行驶"""
        completed = []
        
        for vehicle_id, vehicle in list(self.vehicles.items()):
            edge_data = self.edge_data_map.get(vehicle.link_id)
            if not edge_data:
                completed.append(vehicle_id)
                continue
            
            edge_length = edge_data.get('length', 500)
            
            if vehicle.position >= edge_length:
                to_node = edge_data.get('to', '')
                
                # 检查是否有预定路径
                next_edge_id = None
                if vehicle.route and vehicle.route_index < len(vehicle.route):
                    next_edge_id = vehicle.route[vehicle.route_index]
                    vehicle.route_index += 1
                
                # 没有预定路径则随机选择
                if not next_edge_id:
                    next_edges = self.adjacency.get(to_node, [])
                    next_edges = [e for e in next_edges if e != vehicle.link_id]
                    if next_edges:
                        # 加权选择 - 优先选择主干道
                        weights = []
                        for eid in next_edges:
                            ed = self.edge_data_map.get(eid, {})
                            road_class = ed.get('road_class', 'tertiary')
                            w = {'motorway': 5, 'trunk': 4, 'primary': 3, 'secondary': 2, 'tertiary': 1, 'residential': 0.5}.get(road_class, 1)
                            weights.append(w)
                        next_edge_id = random.choices(next_edges, weights=weights, k=1)[0]
                
                if next_edge_id and next_edge_id in self.links:
                    # 切换到下一路段
                    old_link = self.links.get(vehicle.link_id)
                    if old_link:
                        old_link.vehicles = [v for v in old_link.vehicles if v.id != vehicle_id]
                    
                    vehicle.link_id = next_edge_id
                    vehicle.position = 0
                    next_data = self.edge_data_map.get(next_edge_id, {})
                    vehicle.target_speed = next_data.get('speed_limit', 50) / 3.6
                    vehicle.lane_index = random.randint(0, next_data.get('lanes', 1) - 1)
                    
                    self.links[next_edge_id].vehicles.append(vehicle)
                else:
                    # 到达终点
                    old_link = self.links.get(vehicle.link_id)
                    if old_link:
                        old_link.vehicles = [v for v in old_link.vehicles if v.id != vehicle_id]
                    
                    completed.append(vehicle_id)
                    self.total_vehicles_completed += 1
                    self.total_travel_time += vehicle.trip_time
                    self.total_delay += vehicle.waiting_time
        
        for vehicle_id in completed:
            self.vehicles.pop(vehicle_id, None)
    
    def _calculate_metrics(self):
        """计算性能指标"""
        total_vehicles = len(self.vehicles)
        
        if total_vehicles == 0 and self.total_vehicles_completed == 0:
            return {
                'avg_delay': 0,
                'avg_queue_length': 0,
                'max_queue_length': 0,
                'throughput': 0,
                'avg_stops': 0,
                'vcr': 0,
                'total_generated': 0,
                'total_completed': 0
            }
        
        # 计算各路段排队
        queue_lengths = []
        for link in self.links.values():
            queue = sum(1 for v in link.vehicles if v.speed < 1.0)
            link.queue_count = queue
            queue_lengths.append(queue)
        
        avg_queue = sum(queue_lengths) / len(queue_lengths) if queue_lengths else 0
        max_queue = max(queue_lengths) if queue_lengths else 0
        
        # 在网车辆延误
        if total_vehicles > 0:
            total_waiting = sum(v.waiting_time for v in self.vehicles.values())
            avg_delay = total_waiting / total_vehicles
            total_stops = sum(v.stops for v in self.vehicles.values())
            avg_stops = total_stops / total_vehicles
        else:
            avg_delay = 0
            avg_stops = 0
        
        # 已完成车辆的平均延误
        if self.total_vehicles_completed > 0:
            completed_delay = self.total_delay / self.total_vehicles_completed
            avg_delay = (avg_delay + completed_delay) / 2
        
        # V/C比
        total_capacity = sum(
            e.get('capacity', 1800) * e.get('lanes', 1)
            for e in self.edge_data_map.values()
        )
        total_flow = sum(
            len(link.vehicles) * 3600 / max(self.current_time, 1)
            for link in self.links.values()
        )
        vcr = total_flow / total_capacity if total_capacity > 0 else 0
        
        return {
            'avg_delay': round(avg_delay, 2),
            'avg_queue_length': round(avg_queue, 2),
            'max_queue_length': max_queue,
            'throughput': self.total_vehicles_completed,
            'avg_stops': round(avg_stops, 2),
            'vcr': round(min(vcr, 1.5), 3),
            'total_generated': self.total_vehicles_generated,
            'total_completed': self.total_vehicles_completed
        }
    
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
                    'stops': v.stops,
                    'from_node': self.edge_from_to.get(v.link_id, ('', ''))[0],
                    'to_node': self.edge_from_to.get(v.link_id, ('', ''))[1],
                    'edge_length': self.edge_data_map.get(v.link_id, {}).get('length', 500),
                }
                for v in list(self.vehicles.values())[:1000]
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
    
    def get_results(self):
        """获取仿真结果"""
        metrics = self._calculate_metrics()
        return {
            'duration': self.current_time,
            'total_vehicles': self.total_vehicles_generated,
            'completed_vehicles': self.total_vehicles_completed,
            'avg_travel_time': round(self.total_travel_time / max(self.total_vehicles_completed, 1), 2),
            'metrics': metrics
        }
