"""
UXsim集成模块
基于UXsim的交通仿真引擎封装
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class UXsimNode:
    """UXsim节点"""
    name: str
    x: float
    y: float


@dataclass
class UXsimLink:
    """UXsim路段"""
    name: str
    start_node: str
    end_node: str
    length: float
    lanes: int = 1
    free_flow_speed: float = 50
    capacity: float = 2000


@dataclass
class UXsimSignal:
    """UXsim信号灯"""
    node_name: str
    phases: List[Dict]
    cycle: float
    offset: float = 0


@dataclass
class UXsimDemand:
    """UXsim交通需求"""
    start_node: str
    end_node: str
    start_time: float
    end_time: float
    volume: float


class UXsimAdapter:
    """UXsim适配器"""
    
    def __init__(self):
        self.nodes: Dict[str, UXsimNode] = {}
        self.links: Dict[str, UXsimLink] = {}
        self.signals: Dict[str, UXsimSignal] = {}
        self.demands: List[UXsimDemand] = []
    
    def add_node(self, name: str, x: float, y: float):
        """添加节点"""
        self.nodes[name] = UXsimNode(name=name, x=x, y=y)
    
    def add_link(
        self, name: str, start: str, end: str, length: float,
        lanes: int = 1, speed: float = 50, capacity: float = 2000
    ):
        """添加路段"""
        self.links[name] = UXsimLink(
            name=name,
            start_node=start,
            end_node=end,
            length=length,
            lanes=lanes,
            free_flow_speed=speed,
            capacity=capacity
        )
    
    def add_signal(
        self, node_name: str, phases: List[Dict], cycle: float, offset: float = 0
    ):
        """添加信号灯"""
        self.signals[node_name] = UXsimSignal(
            node_name=node_name,
            phases=phases,
            cycle=cycle,
            offset=offset
        )
    
    def add_demand(
        self, start: str, end: str, start_time: float, end_time: float, volume: float
    ):
        """添加交通需求"""
        self.demands.append(UXsimDemand(
            start_node=start,
            end_node=end,
            start_time=start_time,
            end_time=end_time,
            volume=volume
        ))
    
    def to_uxsim_config(self) -> Dict:
        """转换为UXsim配置"""
        return {
            'nodes': [
                {'name': n.name, 'x': n.x, 'y': n.y}
                for n in self.nodes.values()
            ],
            'links': [
                {
                    'name': l.name,
                    'start': l.start_node,
                    'end': l.end_node,
                    'length': l.length,
                    'lanes': l.lanes,
                    'free_flow_speed': l.free_flow_speed,
                    'capacity': l.capacity
                }
                for l in self.links.values()
            ],
            'signals': [
                {
                    'node': s.node_name,
                    'phases': s.phases,
                    'cycle': s.cycle,
                    'offset': s.offset
                }
                for s in self.signals.values()
            ],
            'demands': [
                {
                    'start': d.start_node,
                    'end': d.end_node,
                    'start_time': d.start_time,
                    'end_time': d.end_time,
                    'volume': d.volume
                }
                for d in self.demands
            ]
        }
    
    def run_simulation(self, duration: float = 3600, step_size: float = 1.0) -> Dict:
        """运行仿真"""
        try:
            from uxsim import World
            
            # 创建UXsim世界
            W = World(
                name="traffic_simulation",
                deltan=5,
                tmax=int(duration),
                print_mode=0,
                save_mode=0,
                show_mode=0
            )
            
            # 添加节点
            for node in self.nodes.values():
                W.addNode(node.name, node.x, node.y)
            
            # 添加路段
            for link in self.links.values():
                W.addLink(
                    link.name,
                    link.start_node,
                    link.end_node,
                    length=link.length,
                    lanes=link.lanes,
                    free_flow_speed=link.free_flow_speed,
                    capacity=link.capacity
                )
            
            # 添加信号灯
            for signal in self.signals.values():
                phase_list = [
                    [p.get('green_links', [])]
                    for p in signal.phases
                ]
                W.addSignal(
                    signal.node_name,
                    phase_list,
                    cycle=signal.cycle,
                    offset=signal.offset
                )
            
            # 添加交通需求
            for demand in self.demands:
                W.adddemand(
                    demand.start_node,
                    demand.end_node,
                    demand.start_time,
                    demand.end_time,
                    volume=demand.volume
                )
            
            # 运行仿真
            W.exec_simulation()
            
            # 收集结果
            return {
                'success': True,
                'metrics': {
                    'avg_delay': getattr(W.analyzer, 'average_delay', 0),
                    'total_flow': getattr(W.analyzer, 'total_flow', 0),
                    'avg_speed': getattr(W.analyzer, 'average_speed', 0)
                },
                'duration': duration
            }
            
        except ImportError:
            return {
                'success': False,
                'error': 'UXsim未安装，请运行: pip install uxsim',
                'metrics': self._estimate_metrics(duration)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'metrics': self._estimate_metrics(duration)
            }
    
    def _estimate_metrics(self, duration: float) -> Dict:
        """估算指标 (UXsim不可用时)"""
        total_volume = sum(d.volume for d in self.demands)
        avg_delay = 30 + (total_volume / 5000) * 20
        
        return {
            'avg_delay': round(avg_delay, 2),
            'total_flow': int(total_volume * 0.8),
            'avg_speed': 35
        }


class NetworkToUXsimConverter:
    """路网数据转UXsim格式"""
    
    @staticmethod
    def convert(network_data: Dict) -> UXsimAdapter:
        """转换路网数据为UXsim格式"""
        adapter = UXsimAdapter()
        
        # 转换节点
        for node in network_data.get('nodes', []):
            adapter.add_node(
                name=node['id'],
                x=node.get('x', 0),
                y=node.get('y', 0)
            )
        
        # 转换路段
        for edge in network_data.get('edges', []):
            adapter.add_link(
                name=edge['id'],
                start=edge['from'],
                end=edge['to'],
                length=edge.get('length', 500),
                lanes=edge.get('lanes', 1),
                speed=edge.get('speed_limit', 50),
                capacity=edge.get('capacity', 2000)
            )
        
        # 转换信号灯
        for signal in network_data.get('signals', []):
            adapter.add_signal(
                node_name=signal['node_id'],
                phases=signal.get('phases', []),
                cycle=signal.get('cycle_length', 120),
                offset=signal.get('offset', 0)
            )
        
        # 转换交通需求
        for demand in network_data.get('demands', []):
            adapter.add_demand(
                start=demand['from'],
                end=demand['to'],
                start_time=demand.get('start_time', 0),
                end_time=demand.get('end_time', 3600),
                volume=demand.get('volume', 500)
            )
        
        return adapter


class SimulationValidator:
    """仿真结果验证器"""
    
    @staticmethod
    def validate(
        our_results: Dict,
        reference_results: Dict,
        thresholds: Optional[Dict] = None
    ) -> Dict:
        """验证仿真结果"""
        if thresholds is None:
            thresholds = {
                'avg_delay': 0.15,
                'total_flow': 0.10,
                'avg_speed': 0.20
            }
        
        comparison = {}
        
        for metric, threshold in thresholds.items():
            our_value = our_results.get(metric, 0)
            ref_value = reference_results.get(metric, 0)
            
            if ref_value == 0:
                relative_error = float('inf')
            else:
                relative_error = abs(our_value - ref_value) / ref_value
            
            comparison[metric] = {
                'ours': our_value,
                'reference': ref_value,
                'relative_error': round(relative_error, 4),
                'acceptable': relative_error <= threshold
            }
        
        all_acceptable = all(c['acceptable'] for c in comparison.values())
        
        return {
            'valid': all_acceptable,
            'comparison': comparison,
            'summary': '验证通过' if all_acceptable else '验证失败'
        }
