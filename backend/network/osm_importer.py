"""
OSM路网导入器
功能: 从Overpass API下载路网 → 解析 → 检测交叉口类型 → 入库
"""
import json
import math
import random
import urllib.request
import urllib.parse
from typing import Dict, List, Tuple, Optional


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# 道路等级映射
HIGHWAY_CLASS = {
    'motorway': 'motorway', 'trunk': 'trunk', 'primary': 'primary',
    'secondary': 'secondary', 'tertiary': 'tertiary',
    'residential': 'residential', 'unclassified': 'secondary',
}

SPEED_LIMIT = {
    'motorway': 80, 'trunk': 60, 'primary': 50,
    'secondary': 40, 'tertiary': 30, 'residential': 20, 'unclassified': 40,
}

LANES_DEFAULT = {
    'motorway': 4, 'trunk': 3, 'primary': 3,
    'secondary': 2, 'tertiary': 2, 'residential': 1, 'unclassified': 2,
}


def download_osm(bbox: dict, timeout: int = 90) -> dict:
    """
    从Overpass API下载OSM路网数据
    bbox: {south, west, north, east}
    """
    s, w, n, e = bbox['south'], bbox['west'], bbox['north'], bbox['east']
    bbox_str = f"{s},{w},{n},{e}"

    query = f"""
[out:json][timeout:{timeout}];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified)$"]
    ({bbox_str});
);
out body;
>;
out skel qt;
"""

    data = urllib.parse.urlencode({'data': query}).encode('utf-8')
    req = urllib.request.Request(OVERPASS_URL, data=data)
    req.add_header('User-Agent', 'TrafficGreenSim/1.0')

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode('utf-8')
        return json.loads(raw)


def haversine(lon1, lat1, lon2, lat2) -> float:
    """两点间距离(米)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def parse_osm(osm_json: dict) -> Tuple[List[dict], List[dict], Dict[int, dict]]:
    """
    解析OSM JSON → (nodes, edges, osm_nodes_dict)
    nodes: [{node_id, name, node_type, lng, lat, x, y, osm_id, degree}]
    edges: [{edge_id, name, from_node, to_node, length, speed_limit, lanes_count, capacity, road_class, is_oneway}]
    """
    elements = osm_json.get('elements', [])

    osm_nodes = {}
    osm_ways = []

    for el in elements:
        if el['type'] == 'node':
            osm_nodes[el['id']] = {'lon': el['lon'], 'lat': el['lat']}
        elif el['type'] == 'way':
            tags = el.get('tags', {})
            highway = tags.get('highway', '')
            if highway in HIGHWAY_CLASS:
                osm_ways.append({
                    'id': el['id'],
                    'tags': tags,
                    'nodes': el.get('nodes', [])
                })

    # 统计每个节点被多少条way引用
    node_way_count = {}
    for way in osm_ways:
        for nid in way['nodes']:
            node_way_count[nid] = node_way_count.get(nid, 0) + 1

    # 交叉口: 被>=2条way引用 或 是way端点
    intersection_ids = set()
    for nid, cnt in node_way_count.items():
        if cnt >= 2:
            intersection_ids.add(nid)
    for way in osm_ways:
        refs = way['nodes']
        if refs:
            intersection_ids.add(refs[0])
            intersection_ids.add(refs[-1])

    # 过滤: 只保留有坐标的
    intersection_ids = {nid for nid in intersection_ids if nid in osm_nodes}

    # 如果太多, 只保留高连接度的
    if len(intersection_ids) > 80:
        high_degree = {nid for nid in intersection_ids if node_way_count.get(nid, 0) >= 3}
        if len(high_degree) >= 30:
            intersection_ids = high_degree

    # 坐标投影中心
    all_lons = [osm_nodes[nid]['lon'] for nid in intersection_ids]
    all_lats = [osm_nodes[nid]['lat'] for nid in intersection_ids]
    center_lon = sum(all_lons) / len(all_lons)
    center_lat = sum(all_lats) / len(all_lats)

    # 构建节点
    nodes_out = []
    node_id_map = {}
    for i, osm_id in enumerate(sorted(intersection_ids)):
        lon = osm_nodes[osm_id]['lon']
        lat = osm_nodes[osm_id]['lat']
        x = (lon - center_lon) * 111000 * math.cos(math.radians(center_lat))
        y = (lat - center_lat) * 111000
        node_id = f"N{i:03d}"
        node_id_map[osm_id] = node_id

        # 检测交叉口类型
        degree = node_way_count.get(osm_id, 0)
        nodes_out.append({
            'node_id': node_id,
            'name': f'路口{i+1}',
            'node_type': 'intersection',
            'lng': round(lon, 6),
            'lat': round(lat, 6),
            'x': round(x, 1),
            'y': round(y, 1),
            'osm_id': osm_id,
            'degree': degree,
        })

    # 构建路段
    edges_out = []
    seen_edges = set()

    for way in osm_ways:
        tags = way['tags']
        highway = tags.get('highway', 'residential')
        road_class = HIGHWAY_CLASS.get(highway, 'residential')
        speed = int(tags.get('maxspeed', SPEED_LIMIT.get(highway, 40)))
        lanes_val = int(tags.get('lanes', LANES_DEFAULT.get(highway, 2)))
        name = tags.get('name', '')
        oneway = tags.get('oneway', 'no') in ('yes', 'true', '1')

        refs = way['nodes']
        segment_points = [nid for nid in refs if nid in intersection_ids]

        for i in range(len(segment_points) - 1):
            from_osm = segment_points[i]
            to_osm = segment_points[i + 1]
            from_nid = node_id_map.get(from_osm)
            to_nid = node_id_map.get(to_osm)
            if not from_nid or not to_nid or from_nid == to_nid:
                continue

            lon1, lat1 = osm_nodes[from_osm]['lon'], osm_nodes[from_osm]['lat']
            lon2, lat2 = osm_nodes[to_osm]['lon'], osm_nodes[to_osm]['lat']
            length = haversine(lon1, lat1, lon2, lat2)
            if length < 10:
                continue

            capacity = lanes_val * 900

            key = (from_nid, to_nid)
            if key not in seen_edges:
                seen_edges.add(key)
                edges_out.append({
                    'edge_id': f"E_{from_nid}_{to_nid}",
                    'name': name or f'{from_nid}→{to_nid}',
                    'from_node': from_nid,
                    'to_node': to_nid,
                    'length': round(length, 1),
                    'speed_limit': speed,
                    'lanes_count': lanes_val,
                    'capacity': capacity,
                    'road_class': road_class,
                    'is_oneway': oneway,
                })

            if not oneway:
                rev_key = (to_nid, from_nid)
                if rev_key not in seen_edges:
                    seen_edges.add(rev_key)
                    edges_out.append({
                        'edge_id': f"E_{to_nid}_{from_nid}",
                        'name': name or f'{to_nid}→{from_nid}',
                        'from_node': to_nid,
                        'to_node': from_nid,
                        'length': round(length, 1),
                        'speed_limit': speed,
                        'lanes_count': lanes_val,
                        'capacity': capacity,
                        'road_class': road_class,
                        'is_oneway': oneway,
                    })

    return nodes_out, edges_out, osm_nodes


def detect_intersection_type(degree: int) -> str:
    """根据连接边数检测交叉口类型"""
    if degree <= 2:
        return 'non_intersection'  # 非交叉口(不生成信号)
    elif degree == 3:
        return 't_junction'
    elif degree == 4:
        return 'cross'
    else:
        return 'multi_leg'


def generate_signals_for_nodes(nodes: List[dict], edges: List[dict]) -> List[dict]:
    """为交叉口自动生成信号灯"""
    signals = []
    for node in nodes:
        nid = node['node_id']
        degree = node.get('degree', 0)

        # 非交叉口不生成信号
        if degree < 3:
            continue

        connected = [e for e in edges if e['from_node'] == nid or e['to_node'] == nid]
        if len(connected) < 2:
            continue

        # 根据道路等级确定周期
        class_rank = {'motorway': 6, 'trunk': 5, 'primary': 4, 'secondary': 3, 'tertiary': 2, 'residential': 1}
        max_class = max(
            (e['road_class'] for e in connected),
            key=lambda c: class_rank.get(c, 0)
        )
        cycle = {'motorway': 150, 'trunk': 130, 'primary': 120,
                 'secondary': 100, 'tertiary': 80, 'residential': 60}.get(max_class, 90)

        # 2相位
        effective = cycle - 8
        green_a = random.randint(int(effective * 0.35), int(effective * 0.65))
        green_b = effective - green_a

        signals.append({
            'node_id': nid,
            'signal_id': f'SIG_{nid}',
            'cycle_length': cycle,
            'offset': 0,
            'phases': [
                {'green': green_a, 'yellow': 3, 'all_red': 1},
                {'green': green_b, 'yellow': 3, 'all_red': 1},
            ]
        })
    return signals


def import_to_db(bbox: dict, network_name: str, description: str = '') -> Tuple['Network', dict]:
    """
    完整流程: 下载 → 解析 → 检测 → 生成信号 → 入库
    返回: (network, stats_dict)
    """
    from network.models import Network, Node, Edge, Signal, Phase, Intersection

    # 1. 下载
    osm_data = download_osm(bbox)

    # 2. 解析
    nodes, edges, osm_nodes = parse_osm(osm_data)

    # 3. 生成信号
    signals = generate_signals_for_nodes(nodes, edges)

    # 4. 入库
    network = Network.objects.create(
        name=network_name,
        description=description or f'从OSM导入, {len(nodes)}个交叉口, {len(edges)}条路段',
        srid=4326,
        bounds=bbox
    )

    node_map = {}
    for n in nodes:
        node = Node.objects.create(
            network=network, node_id=n['node_id'], name=n['name'],
            node_type=n['node_type'], lng=n['lng'], lat=n['lat'],
            x=n['x'], y=n['y']
        )
        node_map[n['node_id']] = node

        # 检测交叉口类型
        int_type = detect_intersection_type(n['degree'])
        if int_type != 'non_intersection':
            Intersection.objects.create(
                node=node,
                intersection_type=int_type,
                control_type='signal'
            )

    for e in edges:
        if e['from_node'] not in node_map or e['to_node'] not in node_map:
            continue
        Edge.objects.create(
            network=network, edge_id=e['edge_id'], name=e['name'],
            from_node=node_map[e['from_node']], to_node=node_map[e['to_node']],
            length=e['length'], speed_limit=e['speed_limit'],
            lanes_count=e['lanes_count'], capacity=e['capacity'],
            road_class=e['road_class'], is_oneway=e['is_oneway']
        )

    signal_count = 0
    for s in signals:
        if s['node_id'] not in node_map:
            continue
        signal = Signal.objects.create(
            node=node_map[s['node_id']], signal_id=s['signal_id'],
            cycle_length=s['cycle_length'], offset=s['offset'],
            control_mode='fixed'
        )
        for i, phase_data in enumerate(s['phases']):
            Phase.objects.create(
                signal=signal, phase_index=i,
                green_time=phase_data['green'],
                yellow_time=phase_data['yellow'],
                all_red_time=phase_data['all_red']
            )
        signal_count += 1

    stats = {
        'network_id': network.id,
        'nodes': len(nodes),
        'edges': len(edges),
        'signals': signal_count,
        'osm_elements': len(osm_data.get('elements', []))
    }
    return network, stats
