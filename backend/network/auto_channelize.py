"""
自动渠化引擎
功能: 根据交叉口类型+进口道自动生成车道、转向关系、信号相位
"""
import math
from typing import Dict, List, Optional, Tuple


# 渠化规则: (road_class, lanes_count) → 车道功能分配
CHANNELIZATION_RULES = {
    # 主干道进口(3+车道): 1左转 + N-2直行 + 1右转
    'primary': {
        1: ['right_through'],
        2: ['left_through', 'right_through'],
        3: ['left_turn', 'through', 'right_turn'],
        4: ['left_turn', 'through', 'through', 'right_turn'],
    },
    'motorway': {
        4: ['left_turn', 'through', 'through', 'right_turn'],
    },
    # 次干道进口(2车道): 1左转 + 1直行+右转
    'secondary': {
        1: ['right_through'],
        2: ['left_turn', 'right_through'],
        3: ['left_turn', 'through', 'right_turn'],
    },
    'trunk': {
        2: ['left_turn', 'right_through'],
        3: ['left_turn', 'through', 'right_turn'],
    },
    # 支路: 简化渠化
    'tertiary': {
        1: ['through'],
        2: ['left_through', 'right_through'],
    },
    'residential': {
        1: ['through'],
        2: ['left_through', 'right_through'],
    },
}

# 灯型配置: 车道类型 → 默认灯型
DEFAULT_SIGNAL_DISPLAY = {
    'left_turn': 'arrow',
    'through': 'round',
    'right_turn': 'round',
    'left_through': 'mixed',
    'right_through': 'round',
    'bus': 'round',
    'emergency': 'round',
}


def get_incoming_edges(node, all_edges) -> list:
    """获取某个节点的所有进口道(to_node=该节点的边)"""
    return [e for e in all_edges if e.to_node_id == node.id]


def get_outgoing_edges(node, all_edges) -> list:
    """获取某个节点的所有出口道(from_node=该节点的边)"""
    return [e for e in all_edges if e.from_node_id == node.id]


def get_approach_direction(from_node, to_node) -> str:
    """根据节点坐标判断进口方向(N/S/E/W)"""
    dx = to_node.x - from_node.x
    dy = to_node.y - from_node.y

    if abs(dx) > abs(dy):
        return 'east' if dx > 0 else 'west'
    else:
        return 'north' if dy > 0 else 'south'


def channelize_intersection(intersection) -> Dict:
    """
    为单个交叉口自动生成渠化方案

    Returns: {
        'lanes_created': int,
        'connections_created': int,
        'phases_created': int,
        'phase_lanes_created': int,
        'intersection_type': str,
    }
    """
    from network.models import (
        Lane, LaneConnection, Signal, Phase, PhaseLane, Edge
    )

    node = intersection.node
    network = node.network
    edges = Edge.objects.filter(network=network)

    incoming = get_incoming_edges(node, edges)
    outgoing = get_outgoing_edges(node, edges)

    # 检测交叉口类型
    n_entries = len(incoming)
    if n_entries < 2:
        return {'error': '进口道不足2条, 无法渠化'}

    if n_entries == 3:
        intersection.intersection_type = 't_junction'
        n_phases = 3
    elif n_entries == 4:
        intersection.intersection_type = 'cross'
        n_phases = 4
    else:
        intersection.intersection_type = 'multi_leg'
        n_phases = min(n_entries, 6)

    intersection.save()

    # 确保有信号灯
    signal, _ = Signal.objects.get_or_create(
        node=node,
        defaults={
            'signal_id': f'SIG_{node.node_id}',
            'cycle_length': 120,
            'control_mode': 'fixed'
        }
    )

    # 清除旧数据
    Lane.objects.filter(edge__in=incoming).delete()
    Phase.objects.filter(signal=signal).delete()

    # 为每个进口道生成车道
    lanes_created = 0
    all_lanes = {}  # edge_id → [Lane]

    for edge in incoming:
        road_class = edge.road_class
        lanes_count = edge.lanes_count

        # 获取渠化规则
        rules = CHANNELIZATION_RULES.get(road_class, CHANNELIZATION_RULES.get('residential'))
        lane_types = rules.get(lanes_count, rules.get(min(rules.keys()), ['through']))

        # 如果规则中没有该车道数, 用最接近的
        if lanes_count not in rules:
            closest = min(rules.keys(), key=lambda k: abs(k - lanes_count))
            lane_types = rules[closest]
            # 扩展到实际车道数
            while len(lane_types) < lanes_count:
                lane_types.insert(1, 'through')  # 中间加直行车道

        edge_lanes = []
        for i, lane_type in enumerate(lane_types[:lanes_count]):
            lane = Lane.objects.create(
                edge=edge,
                lane_index=i,
                lane_type=lane_type,
                width=3.5 if lane_type in ('through', 'left_through', 'right_through') else 3.0,
                signal_display=DEFAULT_SIGNAL_DISPLAY.get(lane_type, 'round'),
                is_exclusive=(lane_type == 'bus')
            )
            edge_lanes.append(lane)
            lanes_created += 1

        all_lanes[edge.id] = edge_lanes

    # 生成转向关系(LaneConnection)
    connections_created = 0
    for in_edge in incoming:
        in_lanes = all_lanes.get(in_edge.id, [])
        for lane in in_lanes:
            for out_edge in outgoing:
                if out_edge.id == in_edge.id:
                    continue  # 不连接同一条边

                # 判断转向类型
                conn_type = _determine_turn_type(in_edge, out_edge, node)

                # 找到匹配的出口车道
                out_lanes = Lane.objects.filter(edge=out_edge)
                for out_lane in out_lanes:
                    if _is_compatible_turn(lane.lane_type, conn_type):
                        LaneConnection.objects.create(
                            from_lane=lane,
                            to_lane=out_lane,
                            connection_type=conn_type,
                            priority=0 if conn_type == 'straight' else 1,
                            has_yield=(conn_type == 'left')
                        )
                        connections_created += 1

    # 生成相位
    phases_created, phase_lanes_created = _generate_phases(
        signal, incoming, all_lanes, n_phases
    )

    return {
        'lanes_created': lanes_created,
        'connections_created': connections_created,
        'phases_created': phases_created,
        'phase_lanes_created': phase_lanes_created,
        'intersection_type': intersection.intersection_type,
    }


def _determine_turn_type(in_edge, out_edge, node) -> str:
    """判断从进口道到出口道的转向类型"""
    from_node_in = in_edge.from_node
    to_node_in = in_edge.to_node  # = node
    to_node_out = out_edge.to_node

    # 进口方向向量
    in_dx = to_node_in.x - from_node_in.x
    in_dy = to_node_in.y - from_node_in.y

    # 出口方向向量
    out_dx = to_node_out.x - node.x
    out_dy = to_node_out.y - node.y

    # 叉积判断转向
    cross = in_dx * out_dy - in_dy * out_dx
    dot = in_dx * out_dx + in_dy * out_dy

    if dot > 0 and abs(cross) < abs(dot) * 0.5:
        return 'straight'
    elif cross > 0:
        return 'left'
    elif cross < 0:
        return 'right'
    else:
        return 'u_turn'


def _is_compatible_turn(lane_type: str, conn_type: str) -> bool:
    """判断车道类型和转向类型是否兼容"""
    if lane_type == 'through':
        return conn_type == 'straight'
    elif lane_type == 'left_turn':
        return conn_type == 'left'
    elif lane_type == 'right_turn':
        return conn_type == 'right'
    elif lane_type == 'left_through':
        return conn_type in ('straight', 'left')
    elif lane_type == 'right_through':
        return conn_type in ('straight', 'right')
    elif lane_type == 'bus':
        return conn_type == 'straight'
    return False


def _generate_phases(signal, incoming, all_lanes, n_phases) -> Tuple[int, int]:
    """
    根据进口道数生成信号相位
    返回: (phases_created, phase_lanes_created)
    """
    from network.models import Phase, PhaseLane, Lane

    cycle = signal.cycle_length
    total_loss = n_phases * 4  # 每相位4秒损失(黄+全红)
    effective = cycle - total_loss

    phases_created = 0
    phase_lanes_created = 0

    if n_phases == 2:
        # 简单2相位: NS直行+右转, EW直行+右转
        groups = _split_approaches_2_phase(incoming)
        for idx, group in enumerate(groups):
            green = int(effective * (0.5 if len(groups) == 2 else 0.45))
            phase = Phase.objects.create(
                signal=signal, phase_index=idx,
                green_time=green, yellow_time=3, all_red_time=1,
                phase_type='through',
                light_type='round',
                allowed_movements=['straight', 'right'],
                permissive_movements=['right']
            )
            phases_created += 1

            for edge in group:
                lanes = Lane.objects.filter(edge=edge)
                for lane in lanes:
                    if lane.lane_type in ('through', 'right_turn', 'right_through'):
                        PhaseLane.objects.create(phase=phase, lane=lane)
                        phase_lanes_created += 1

    elif n_phases == 3:
        # T型: 主路直行+右转 → 主路左转 → 次路全放
        groups = _split_approaches_3_phase(incoming)
        green_times = [int(effective * 0.4), int(effective * 0.25), int(effective * 0.35)]

        for idx, group in enumerate(groups):
            is_left_phase = (idx == 1)
            phase = Phase.objects.create(
                signal=signal, phase_index=idx,
                green_time=green_times[idx], yellow_time=3, all_red_time=1,
                phase_type='left_turn' if is_left_phase else 'through',
                light_type='arrow' if is_left_phase else 'round',
                allowed_movements=['left'] if is_left_phase else ['straight', 'right'],
                protected_movements=['left'] if is_left_phase else [],
                permissive_movements=[] if is_left_phase else ['right']
            )
            phases_created += 1

            for edge in group:
                lanes = Lane.objects.filter(edge=edge)
                for lane in lanes:
                    if is_left_phase:
                        if lane.lane_type in ('left_turn', 'left_through'):
                            PhaseLane.objects.create(phase=phase, lane=lane)
                            phase_lanes_created += 1
                    else:
                        if lane.lane_type in ('through', 'right_turn', 'right_through'):
                            PhaseLane.objects.create(phase=phase, lane=lane)
                            phase_lanes_created += 1

    elif n_phases == 4:
        # 十字: NS直行+右转 → NS左转 → EW直行+右转 → EW左转
        groups = _split_approaches_4_phase(incoming)
        green_times = [
            int(effective * 0.3), int(effective * 0.15),
            int(effective * 0.3), int(effective * 0.15)
        ]

        for idx, group in enumerate(groups):
            is_left_phase = (idx % 2 == 1)
            phase = Phase.objects.create(
                signal=signal, phase_index=idx,
                green_time=green_times[idx], yellow_time=3, all_red_time=1,
                phase_type='left_turn' if is_left_phase else 'through',
                light_type='arrow' if is_left_phase else 'mixed',
                allowed_movements=['left'] if is_left_phase else ['straight', 'right'],
                protected_movements=['left'] if is_left_phase else [],
                permissive_movements=[] if is_left_phase else ['right']
            )
            phases_created += 1

            for edge in group:
                lanes = Lane.objects.filter(edge=edge)
                for lane in lanes:
                    if is_left_phase:
                        if lane.lane_type in ('left_turn', 'left_through'):
                            PhaseLane.objects.create(phase=phase, lane=lane)
                            phase_lanes_created += 1
                    else:
                        if lane.lane_type in ('through', 'right_turn', 'right_through'):
                            PhaseLane.objects.create(phase=phase, lane=lane)
                            phase_lanes_created += 1
    else:
        # 多路: 每个进口一个相位
        for idx, edge in enumerate(incoming[:n_phases]):
            green = int(effective / n_phases)
            phase = Phase.objects.create(
                signal=signal, phase_index=idx,
                green_time=green, yellow_time=3, all_red_time=1,
                phase_type='through',
                light_type='mixed',
                allowed_movements=['straight', 'left', 'right']
            )
            phases_created += 1

            lanes = Lane.objects.filter(edge=edge)
            for lane in lanes:
                PhaseLane.objects.create(phase=phase, lane=lane)
                phase_lanes_created += 1

    # 更新信号灯周期
    total_green = sum(p.green_time for p in signal.phases.all())
    signal.cycle_length = total_green + phases_created * 4
    signal.save()

    return phases_created, phase_lanes_created


def _split_approaches_2_phase(incoming) -> List[list]:
    """2相位分组: NS vs EW"""
    ns, ew = [], []
    for edge in incoming:
        dx = edge.to_node.x - edge.from_node.x
        dy = edge.to_node.y - edge.from_node.y
        if abs(dy) >= abs(dx):
            ns.append(edge)
        else:
            ew.append(edge)
    return [g for g in [ns, ew] if g]


def _split_approaches_3_phase(incoming) -> List[list]:
    """3相位分组: 主路直行 → 主路左转 → 次路"""
    if len(incoming) < 3:
        return [incoming]

    # 找主路(最长的两条对向边)
    lengths = [(e.length, e) for e in incoming]
    lengths.sort(reverse=True)
    main_pair = [lengths[0][1], lengths[1][1]] if len(lengths) >= 2 else [lengths[0][1]]
    secondary = [lengths[2][1]] if len(lengths) >= 3 else []

    return [main_pair, main_pair, secondary] if secondary else [main_pair, main_pair[:1], main_pair[1:]]


def _split_approaches_4_phase(incoming) -> List[list]:
    """4相位分组: NS直行 → NS左转 → EW直行 → EW左转"""
    ns, ew = [], []
    for edge in incoming:
        dx = edge.to_node.x - edge.from_node.x
        dy = edge.to_node.y - edge.from_node.y
        if abs(dy) >= abs(dx):
            ns.append(edge)
        else:
            ew.append(edge)
    return [ns, ns, ew, ew]


def channelize_network(network) -> Dict:
    """批量渠化路网中所有有信号灯的交叉口"""
    from network.models import Intersection

    intersections = Intersection.objects.filter(node__network=network)
    results = {}
    total_lanes = 0
    total_connections = 0
    total_phases = 0

    for intersection in intersections:
        result = channelize_intersection(intersection)
        results[intersection.node.node_id] = result
        total_lanes += result.get('lanes_created', 0)
        total_connections += result.get('connections_created', 0)
        total_phases += result.get('phases_created', 0)

    return {
        'intersections_processed': len(intersections),
        'total_lanes': total_lanes,
        'total_connections': total_connections,
        'total_phases': total_phases,
        'details': results
    }


def rebuild_phases_on_lane_change(intersection) -> Dict:
    """车道变更后自动重建相位"""
    from network.models import Phase, PhaseLane

    # 清除旧相位
    signal = intersection.node.signal
    Phase.objects.filter(signal=signal).delete()

    # 重新生成
    from network.models import Edge
    edges = Edge.objects.filter(network=intersection.node.network)
    incoming = get_incoming_edges(intersection.node, edges)

    from network.models import Lane
    all_lanes = {}
    for edge in incoming:
        all_lanes[edge.id] = list(Lane.objects.filter(edge=edge))

    n_phases = len(incoming) if len(incoming) >= 3 else 2
    phases_created, phase_lanes_created = _generate_phases(
        signal, incoming, all_lanes, n_phases
    )

    return {
        'phases_created': phases_created,
        'phase_lanes_created': phase_lanes_created
    }
