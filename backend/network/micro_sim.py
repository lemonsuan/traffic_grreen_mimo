"""
单交叉口微观仿真引擎
用于: 验证信号配时方案、渠化设计效果
独立于主仿真引擎, 只跑一个路口
"""
import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MicroVehicle:
    """微观仿真车辆"""
    id: str
    approach: str       # 进口方向: north/south/east/west
    lane_type: str      # 车道类型: through/left_turn/right_turn
    position: float = 0 # 距停止线距离(米, 正值=未到, 负值=已过)
    speed: float = 0    # 速度(m/s)
    target_speed: float = 12  # 目标速度(m/s)
    waiting: float = 0  # 等待时间
    stopped: bool = False


class IntersectionMicroSim:
    """单交叉口微观仿真"""

    # IDM参数
    IDM_T = 1.5
    IDM_A = 1.5
    IDM_B = 2.5
    IDM_S0 = 2.0
    IDM_DELTA = 4

    def __init__(self, intersection_data: dict, config: dict = None):
        """
        intersection_data: {
            'node_id': str,
            'intersection_type': str,
            'cycle_length': float,
            'phases': [{'index', 'green', 'yellow', 'all_red', 'green_lanes': [approach...]}],
            'approaches': {'north': {'lanes': [...], 'flow': 500}, ...}
        }
        """
        self.data = intersection_data
        self.config = config or {}
        self.step_size = self.config.get('step_size', 1.0)
        self.duration = self.config.get('duration', 300)
        self.current_time = 0

        # 信号状态
        self.phases = intersection_data.get('phases', [])
        self.current_phase = 0
        self.phase_elapsed = 0

        # 车辆
        self.vehicles: Dict[str, List[MicroVehicle]] = {}  # approach → [vehicles]
        self.total_generated = 0
        self.total_passed = 0
        self.total_delay = 0
        self.total_stops = 0

        # 初始化进口道
        for approach in ['north', 'south', 'east', 'west']:
            self.vehicles[approach] = []

    def step(self) -> dict:
        """执行一步仿真"""
        self._update_signal()
        self._generate_vehicles()
        self._update_vehicles()
        self._remove_passed_vehicles()
        self.current_time += self.step_size
        return self._get_state()

    def _update_signal(self):
        """更新信号灯"""
        if not self.phases:
            return

        current = self.phases[self.current_phase]
        phase_duration = current.get('green', 30) + current.get('yellow', 3) + current.get('all_red', 1)

        self.phase_elapsed += self.step_size
        if self.phase_elapsed >= phase_duration:
            self.current_phase = (self.current_phase + 1) % len(self.phases)
            self.phase_elapsed = 0

    def _is_green(self, approach: str, lane_type: str) -> bool:
        """判断某个进口某个方向是否绿灯"""
        if not self.phases:
            return True

        current = self.phases[self.current_phase]
        green_lanes = current.get('green_lanes', [])

        # 如果没有明确配置, 按相位索引分配
        if not green_lanes:
            phase_idx = self.current_phase
            approaches = ['north', 'south', 'east', 'west']
            if phase_idx == 0:
                return approach in ('north', 'south')
            else:
                return approach in ('east', 'west')

        return approach in green_lanes

    def _generate_vehicles(self):
        """生成车辆"""
        approaches = self.data.get('approaches', {})
        for approach, info in approaches.items():
            flow = info.get('flow', 400)
            prob = (flow / 3600) * self.step_size

            if random.random() < prob:
                lane_types = info.get('lanes', ['through'])
                lane_type = random.choices(
                    lane_types,
                    weights=[3 if t == 'through' else 1 for t in lane_types],
                    k=1
                )[0]

                vehicle = MicroVehicle(
                    id=f"mv_{self.total_generated}",
                    approach=approach,
                    lane_type=lane_type,
                    position=100 + random.uniform(0, 50),
                    speed=10 + random.uniform(-2, 2),
                    target_speed=12
                )
                self.vehicles[approach].append(vehicle)
                self.total_generated += 1

    def _update_vehicles(self):
        """更新车辆位置"""
        for approach, vehicles in self.vehicles.items():
            # 按位置排序(离停止线近的在前)
            vehicles.sort(key=lambda v: v.position, reverse=True)

            for i, v in enumerate(vehicles):
                leader = vehicles[i - 1] if i > 0 else None
                is_green = self._is_green(approach, v.lane_type)

                # 计算加速度
                acc = self._idm_acceleration(v, leader, is_green)

                old_speed = v.speed
                v.speed = max(0, v.speed + acc * self.step_size)
                v.speed = min(v.speed, v.target_speed)
                v.position -= v.speed * self.step_size

                if v.speed < 0.5:
                    v.stopped = True
                    v.waiting += self.step_size
                elif old_speed < 0.5 and v.speed >= 0.5:
                    v.stopped = False
                    self.total_stops += 1

    def _idm_acceleration(self, vehicle, leader, is_green) -> float:
        """IDM加速度计算"""
        v = vehicle.speed
        v0 = vehicle.target_speed

        # 红灯: 停止线作为虚拟障碍物
        if not is_green and vehicle.position > 0:
            gap = vehicle.position - 2
            if gap < 0:
                return -self.IDM_B * 2
            s_star = self.IDM_S0 + max(0, v * self.IDM_T)
            free_acc = self.IDM_A * (1 - (v / v0) ** self.IDM_DELTA) if v0 > 0 else 0
            return free_acc - self.IDM_A * (s_star / max(gap, 0.1)) ** 2

        # 有前车
        if leader:
            gap = leader.position - vehicle.position - 4
            if gap < 0:
                return -self.IDM_B * 2
            dv = v - leader.speed
            s_star = self.IDM_S0 + max(0, v * self.IDM_T + v * dv / (2 * math.sqrt(self.IDM_A * self.IDM_B)))
            free_acc = self.IDM_A * (1 - (v / v0) ** self.IDM_DELTA) if v0 > 0 else 0
            return free_acc - self.IDM_A * (s_star / max(gap, 0.1)) ** 2

        # 自由流
        return self.IDM_A * (1 - (v / v0) ** self.IDM_DELTA) if v0 > 0 else 0

    def _remove_passed_vehicles(self):
        """移除已通过交叉口的车辆"""
        for approach, vehicles in self.vehicles.items():
            passed = [v for v in vehicles if v.position < -50]
            self.total_passed += len(passed)
            for v in passed:
                self.total_delay += v.waiting
            self.vehicles[approach] = [v for v in vehicles if v.position >= -50]

    def _get_state(self) -> dict:
        """获取当前状态"""
        queue_counts = {}
        total_queue = 0
        for approach, vehicles in self.vehicles.items():
            queue = sum(1 for v in vehicles if v.stopped)
            queue_counts[approach] = queue
            total_queue += queue

        total_vehicles = sum(len(v) for v in self.vehicles.values())
        avg_delay = self.total_delay / max(self.total_passed, 1)

        return {
            'time': self.current_time,
            'current_phase': self.current_phase,
            'phase_elapsed': self.phase_elapsed,
            'vehicles': {
                approach: [
                    {'id': v.id, 'position': v.position, 'speed': v.speed * 3.6, 'stopped': v.stopped}
                    for v in vehicles[:50]
                ]
                for approach, vehicles in self.vehicles.items()
            },
            'queue': queue_counts,
            'total_queue': total_queue,
            'total_vehicles': total_vehicles,
            'total_passed': self.total_passed,
            'metrics': {
                'avg_delay': round(avg_delay, 2),
                'total_queue': total_queue,
                'throughput': self.total_passed,
                'total_stops': self.total_stops,
            }
        }

    def get_results(self) -> dict:
        """获取最终结果"""
        state = self._get_state()
        return {
            'duration': self.current_time,
            'total_generated': self.total_generated,
            'total_passed': self.total_passed,
            'avg_delay': state['metrics']['avg_delay'],
            'total_stops': self.total_stops,
        }


def build_intersection_data_from_db(intersection) -> dict:
    """从数据库构建交叉口仿真数据"""
    from network.models import Edge, Lane, Signal, Phase

    node = intersection.node
    network = node.network

    incoming = Edge.objects.filter(to_node=node, network=network)

    approaches = {}
    for edge in incoming:
        # 判断方向
        dx = node.x - edge.from_node.x
        dy = node.y - edge.from_node.y
        if abs(dy) >= abs(dx):
            direction = 'north' if dy > 0 else 'south'
        else:
            direction = 'east' if dx > 0 else 'west'

        lanes = list(Lane.objects.filter(edge=edge).values_list('lane_type', flat=True))
        flow = edge.capacity * 0.5 if edge.capacity else 500

        approaches[direction] = {
            'lanes': lanes or ['through'],
            'flow': int(flow),
        }

    # 信号相位
    try:
        signal = Signal.objects.get(node=node)
        phases = []
        for phase in signal.phases.all().order_by('phase_index'):
            green_lanes = []
            for pl in phase.phase_lanes.select_related('lane__edge').all():
                edge = pl.lane.edge
                dx = node.x - edge.from_node.x
                dy = node.y - edge.from_node.y
                if abs(dy) >= abs(dx):
                    direction = 'north' if dy > 0 else 'south'
                else:
                    direction = 'east' if dx > 0 else 'west'
                if direction not in green_lanes:
                    green_lanes.append(direction)

            phases.append({
                'index': phase.phase_index,
                'green': phase.green_time,
                'yellow': phase.yellow_time,
                'all_red': phase.all_red_time,
                'green_lanes': green_lanes
            })
    except Signal.DoesNotExist:
        phases = [
            {'index': 0, 'green': 35, 'yellow': 3, 'all_red': 1, 'green_lanes': ['north', 'south']},
            {'index': 1, 'green': 30, 'yellow': 3, 'all_red': 1, 'green_lanes': ['east', 'west']},
        ]

    return {
        'node_id': node.node_id,
        'intersection_type': intersection.intersection_type,
        'cycle_length': getattr(signal, 'cycle_length', 80) if hasattr(node, 'signal') else 80,
        'phases': phases,
        'approaches': approaches,
    }
