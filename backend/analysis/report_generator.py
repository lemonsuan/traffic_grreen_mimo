"""
报告自动生成器
支持: JSON/CSV格式导出、仿真报告、优化对比报告
"""

import csv
import io
import json
from datetime import datetime
from typing import Dict, List, Optional


class ReportGenerator:
    """报告生成器"""

    @staticmethod
    def generate_simulation_report(
        simulation_data: Dict,
        metrics: Dict,
        network_name: str = ''
    ) -> Dict:
        """
        生成仿真分析报告

        Args:
            simulation_data: 仿真结果数据
            metrics: 性能指标
            network_name: 路网名称

        Returns:
            结构化报告
        """
        report = {
            'report_type': 'simulation',
            'title': f'仿真分析报告 - {network_name}',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'network_name': network_name,
                'duration': simulation_data.get('duration', 0),
                'total_vehicles': simulation_data.get('total_vehicles', 0),
                'completed_vehicles': simulation_data.get('completed_vehicles', 0),
                'completion_rate': round(
                    simulation_data.get('completed_vehicles', 0) /
                    max(simulation_data.get('total_vehicles', 1), 1) * 100, 1
                )
            },
            'performance': {
                'avg_delay': metrics.get('avg_delay', 0),
                'avg_queue_length': metrics.get('avg_queue_length', 0),
                'max_queue_length': metrics.get('max_queue_length', 0),
                'throughput': metrics.get('throughput', 0),
                'avg_stops': metrics.get('avg_stops', 0)
            },
            'level_of_service': ReportGenerator._calculate_los(metrics.get('avg_delay', 0)),
            'recommendations': ReportGenerator._generate_recommendations(metrics)
        }

        return report

    @staticmethod
    def generate_optimization_report(
        pipeline_result: Dict,
        network_name: str = ''
    ) -> Dict:
        """
        生成优化对比报告

        Args:
            pipeline_result: 一键优化管线结果
            network_name: 路网名称

        Returns:
            结构化报告
        """
        best_perf = pipeline_result.get('best_performance', {})
        comparison = pipeline_result.get('comparison', [])

        improvements = []
        if len(comparison) >= 2:
            baseline = comparison[-1] if comparison else {}
            best = comparison[0] if comparison else {}
            for metric in ['avg_delay', 'avg_queue_length', 'avg_stops']:
                base_val = baseline.get(metric, 0)
                best_val = best.get(metric, 0)
                if base_val > 0:
                    improvement = round((base_val - best_val) / base_val * 100, 1)
                    improvements.append({
                        'metric': metric,
                        'baseline': base_val,
                        'optimized': best_val,
                        'improvement_pct': improvement
                    })

        report = {
            'report_type': 'optimization',
            'title': f'信号优化报告 - {network_name}',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'network_name': network_name,
                'strategy': pipeline_result.get('strategy', ''),
                'node_count': pipeline_result.get('node_count', 0),
                'edge_count': pipeline_result.get('edge_count', 0),
                'algorithms_compared': len(comparison),
                'best_algorithm': pipeline_result.get('best_algorithm', ''),
                'total_time': round(pipeline_result.get('total_time', 0), 3)
            },
            'best_performance': best_perf,
            'level_of_service': ReportGenerator._calculate_los(best_perf.get('avg_delay', 0)),
            'comparison_table': comparison,
            'improvements': improvements,
            'recommendations': ReportGenerator._generate_recommendations(best_perf)
        }

        return report

    @staticmethod
    def generate_network_report(
        network_data: Dict,
        network_name: str = ''
    ) -> Dict:
        """
        生成路网概况报告

        Args:
            network_data: 路网数据
            network_name: 路网名称

        Returns:
            结构化报告
        """
        nodes = network_data.get('nodes', {})
        edges = network_data.get('edges', [])
        signals = network_data.get('signals', [])

        if isinstance(nodes, dict):
            node_list = list(nodes.values())
        else:
            node_list = nodes

        total_length = sum(e.get('length', 0) for e in edges if isinstance(e, dict))
        avg_speed = sum(e.get('speed_limit', 50) for e in edges if isinstance(e, dict)) / max(len(edges), 1)

        road_class_dist = {}
        for e in edges:
            if isinstance(e, dict):
                cls = e.get('road_class', 'unknown')
                road_class_dist[cls] = road_class_dist.get(cls, 0) + 1

        report = {
            'report_type': 'network',
            'title': f'路网概况报告 - {network_name}',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'network_name': network_name,
                'total_nodes': len(node_list) if isinstance(node_list, list) else len(nodes),
                'total_edges': len(edges),
                'total_signals': len(signals),
                'total_length_km': round(total_length / 1000, 2),
                'avg_speed_limit': round(avg_speed, 1)
            },
            'road_class_distribution': road_class_dist,
            'signal_coverage': round(
                len(signals) / max(len(node_list) if isinstance(node_list, list) else len(nodes), 1) * 100, 1
            )
        }

        return report

    @staticmethod
    def export_to_csv(data: List[Dict], filename: str = 'report.csv') -> str:
        """
        导出为CSV格式

        Args:
            data: 数据列表
            filename: 文件名

        Returns:
            CSV内容字符串
        """
        if not data:
            return ''

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue()

    @staticmethod
    def export_to_json(report: Dict, pretty: bool = True) -> str:
        """
        导出为JSON格式

        Args:
            report: 报告数据
            pretty: 是否格式化

        Returns:
            JSON字符串
        """
        if pretty:
            return json.dumps(report, ensure_ascii=False, indent=2)
        return json.dumps(report, ensure_ascii=False)

    @staticmethod
    def _calculate_los(avg_delay: float) -> Dict:
        """
        计算服务水平 (Level of Service)
        HCM标准: A(<10s), B(<20s), C(<35s), D(<55s), E(<80s), F(>=80s)
        """
        if avg_delay < 10:
            los, grade = 'A', '优秀'
        elif avg_delay < 20:
            los, grade = 'B', '良好'
        elif avg_delay < 35:
            los, grade = 'C', '中等'
        elif avg_delay < 55:
            los, grade = 'D', '较差'
        elif avg_delay < 80:
            los, grade = 'E', '差'
        else:
            los, grade = 'F', '极差'

        return {
            'level': los,
            'grade': grade,
            'avg_delay': avg_delay,
            'description': f'服务水平 {los} ({grade})，平均延误 {avg_delay:.1f} 秒'
        }

    @staticmethod
    def _generate_recommendations(metrics: Dict) -> List[str]:
        """根据指标生成改善建议"""
        recommendations = []
        delay = metrics.get('avg_delay', 0)
        vcr = metrics.get('vcr', 0)
        stops = metrics.get('avg_stops', 0)

        if delay > 55:
            recommendations.append('平均延误过高，建议优化信号配时或增加绿灯时间')
        if vcr > 0.9:
            recommendations.append('饱和度过高，接近过饱和状态，建议考虑拓宽路口或限制转向')
        if stops > 2.5:
            recommendations.append('停车次数偏高，建议设置绿波协调控制')
        if delay > 35 and vcr < 0.7:
            recommendations.append('延误与饱和度不匹配，可能存在绿灯时间分配不合理')
        if not recommendations:
            recommendations.append('当前服务水平良好，建议定期监测')

        return recommendations
