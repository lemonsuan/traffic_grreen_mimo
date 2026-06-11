"""
单元测试: 路网生成器、流量生成器、优化管线、报告生成器
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.test import TestCase
from network.generator import NetworkGenerator
from network.demand import DemandGenerator
from optimization.pipeline import OptimizationPipeline
from optimization.base import OptimizerFactory, PerformanceMetrics
from analysis.report_generator import ReportGenerator


class TestNetworkGenerator(TestCase):
    """路网生成器测试"""

    def test_grid_generation(self):
        """测试网格路网生成"""
        data = NetworkGenerator.generate_grid(3, 4)
        self.assertEqual(len(data['nodes']), 12)
        self.assertEqual(len(data['signals']), 12)
        self.assertGreater(len(data['edges']), 0)
        self.assertIn('network', data)

    def test_grid_custom_params(self):
        """测试自定义参数网格生成"""
        data = NetworkGenerator.generate_grid(2, 3, block_size=500, speed_limit=60)
        self.assertEqual(len(data['nodes']), 6)
        for edge in data['edges']:
            self.assertEqual(edge['length'], 500)
            self.assertEqual(edge['speed_limit'], 60)

    def test_corridor_generation(self):
        """测试干线走廊生成"""
        data = NetworkGenerator.generate_corridor(5, segment_length=400)
        self.assertEqual(len(data['nodes']), 5)
        self.assertEqual(len(data['edges']), 4)
        self.assertEqual(len(data['signals']), 5)

    def test_corridor_ns_direction(self):
        """测试南北方向干线"""
        data = NetworkGenerator.generate_corridor(4, direction='ns')
        self.assertEqual(len(data['nodes']), 4)
        first_node = data['nodes'][0]
        last_node = data['nodes'][-1]
        self.assertNotEqual(first_node['lat'], last_node['lat'])

    def test_small_city_generation(self):
        """测试小型城市路网生成"""
        data = NetworkGenerator.generate_small_city()
        self.assertGreater(len(data['nodes']), 10)
        self.assertGreater(len(data['edges']), 10)
        self.assertGreater(len(data['signals']), 10)

    def test_signal_phases(self):
        """测试信号灯相位配置"""
        data = NetworkGenerator.generate_grid(2, 2)
        for signal in data['signals']:
            self.assertIn('cycle_length', signal)
            self.assertIn('phases', signal)
            self.assertEqual(len(signal['phases']), 2)
            for phase in signal['phases']:
                self.assertIn('green', phase)
                self.assertIn('yellow', phase)
                self.assertIn('all_red', phase)


class TestDemandGenerator(TestCase):
    """流量生成器测试"""

    def setUp(self):
        self.edges = NetworkGenerator.generate_grid(3, 3)['edges']

    def test_edge_flows(self):
        """测试路段流量生成"""
        flows = DemandGenerator.generate_edge_flows(self.edges)
        self.assertEqual(len(flows), len(self.edges))
        for f in flows:
            self.assertIn('flow', f)
            self.assertGreater(f['flow'], 0)

    def test_flow_profiles(self):
        """测试不同流量模式"""
        for profile in ['weekday', 'weekend', 'peak']:
            flows = DemandGenerator.generate_edge_flows(self.edges, profile=profile)
            self.assertGreater(len(flows), 0)

    def test_od_matrix(self):
        """测试OD矩阵生成"""
        node_ids = [f'N{r}_{c}' for r in range(3) for c in range(3)]
        od = DemandGenerator.generate_od_matrix(node_ids, total_demand=5000)
        self.assertGreater(len(od), 0)
        total_flow = sum(pair['flow'] for pair in od)
        self.assertAlmostEqual(total_flow, 5000, delta=500)

    def test_detector_data(self):
        """测试检测器数据生成"""
        records = DemandGenerator.generate_detector_data(
            'E_test', duration_hours=1.0, interval_seconds=300, base_flow=800
        )
        self.assertEqual(len(records), 12)
        for r in records:
            self.assertIn('flow', r)
            self.assertIn('speed', r)
            self.assertIn('occupancy', r)

    def test_tod_signal_plan(self):
        """测试时段配时方案"""
        plans = DemandGenerator.generate_time_of_day_signal_plan()
        self.assertEqual(len(plans), 8)
        for p in plans:
            self.assertIn('start_hour', p)
            self.assertIn('end_hour', p)
            self.assertIn('cycle_length', p)


class TestOptimizationAlgorithms(TestCase):
    """优化算法测试"""

    def setUp(self):
        self.traffic_data = {
            'approaches': {
                'north_through': {'volume': 500},
                'south_through': {'volume': 450},
                'east_through': {'volume': 400},
                'west_through': {'volume': 380},
                'north_left': {'volume': 120},
                'south_left': {'volume': 100},
                'east_left': {'volume': 90},
                'west_left': {'volume': 80}
            }
        }

    def test_all_intersection_algorithms(self):
        """测试所有单点优化算法"""
        from optimization.base import OptimizationContext, OptimizationLevel
        algos = OptimizerFactory.get_available_algorithms('intersection')
        self.assertEqual(len(algos), 4)

        for algo in algos:
            ctx = OptimizationContext(
                level=OptimizationLevel.INTERSECTION,
                network_id=1,
                node_ids=['test'],
                traffic_data=self.traffic_data
            )
            optimizer = OptimizerFactory.create(ctx, algo)
            self.assertTrue(optimizer.validate_inputs(), f'{algo} validation failed')
            result = optimizer.optimize()
            self.assertGreater(result.signal_timings['intersection'].cycle_length, 0)
            self.assertGreater(result.performance.avg_delay, 0)

    def test_all_corridor_algorithms(self):
        """测试所有干线优化算法"""
        from optimization.base import OptimizationContext, OptimizationLevel
        algos = OptimizerFactory.get_available_algorithms('corridor')
        self.assertEqual(len(algos), 4)

        corridor_data = {
            'nodes': {f'C{i}': {'cycle_length': 120, 'green_ns': 45, 'green_ew': 35} for i in range(4)},
            'edges': {f'C{i}_C{i+1}': {'length': 500} for i in range(3)}
        }

        for algo in algos:
            ctx = OptimizationContext(
                level=OptimizationLevel.CORRIDOR,
                network_id=1,
                node_ids=['C0', 'C1', 'C2', 'C3'],
                traffic_data={'corridor_data': corridor_data},
                params={'desired_speed': 40}
            )
            optimizer = OptimizerFactory.create(ctx, algo)
            result = optimizer.optimize()
            self.assertGreater(len(result.signal_timings), 0)

    def test_all_network_algorithms(self):
        """测试所有区域优化算法"""
        from optimization.base import OptimizationContext, OptimizationLevel
        algos = OptimizerFactory.get_available_algorithms('network')
        self.assertEqual(len(algos), 3)

        grid = NetworkGenerator.generate_grid(3, 3)
        nodes_dict = {n['node_id']: n for n in grid['nodes']}
        network_data = {'network_data': {'nodes': nodes_dict, 'edges': grid['edges']}}

        for algo in algos:
            ctx = OptimizationContext(
                level=OptimizationLevel.NETWORK,
                network_id=1,
                node_ids=list(nodes_dict.keys()),
                traffic_data=network_data
            )
            optimizer = OptimizerFactory.create(ctx, algo)
            result = optimizer.optimize()
            self.assertGreater(len(result.signal_timings), 0)


class TestOptimizationPipeline(TestCase):
    """优化管线测试"""

    def test_auto_optimize_grid(self):
        """测试网格路网自动优化"""
        grid = NetworkGenerator.generate_grid(3, 3)
        pipeline = OptimizationPipeline(1, grid)
        result = pipeline.auto_optimize()
        self.assertIn('strategy', result)
        self.assertIn('best_algorithm', result)
        self.assertIn('comparison', result)
        self.assertGreater(result['total_time'], 0)

    def test_auto_optimize_corridor(self):
        """测试干线自动优化"""
        corridor = NetworkGenerator.generate_corridor(5)
        pipeline = OptimizationPipeline(1, corridor)
        result = pipeline.auto_optimize()
        self.assertEqual(result['strategy'], 'corridor')

    def test_intersection_optimization(self):
        """测试单点优化管线"""
        grid = NetworkGenerator.generate_grid(2, 2)
        pipeline = OptimizationPipeline(1, grid)
        result = pipeline.run_intersection_optimization()
        self.assertGreater(result.total_intersections, 0)

    def test_comparison_table(self):
        """测试对比表生成"""
        grid = NetworkGenerator.generate_grid(2, 2)
        pipeline = OptimizationPipeline(1, grid)
        result = pipeline.run_intersection_optimization()
        table = result.comparison_table
        self.assertGreater(len(table), 0)
        for entry in table:
            self.assertIn('algorithm', entry)
            self.assertIn('avg_delay', entry)


class TestReportGenerator(TestCase):
    """报告生成器测试"""

    def test_simulation_report(self):
        """测试仿真报告生成"""
        report = ReportGenerator.generate_simulation_report(
            {'duration': 3600, 'total_vehicles': 500, 'completed_vehicles': 450},
            {'avg_delay': 25.5, 'avg_queue_length': 8.2, 'throughput': 450},
            'TestNetwork'
        )
        self.assertEqual(report['report_type'], 'simulation')
        self.assertIn('level_of_service', report)
        self.assertIn('recommendations', report)

    def test_network_report(self):
        """测试路网报告生成"""
        grid = NetworkGenerator.generate_grid(3, 3)
        report = ReportGenerator.generate_network_report(grid, 'TestGrid')
        self.assertEqual(report['report_type'], 'network')
        self.assertEqual(report['summary']['total_nodes'], 9)

    def test_los_calculation(self):
        """测试服务水平计算"""
        los_a = ReportGenerator._calculate_los(5)
        self.assertEqual(los_a['level'], 'A')

        los_f = ReportGenerator._calculate_los(100)
        self.assertEqual(los_f['level'], 'F')

    def test_csv_export(self):
        """测试CSV导出"""
        data = [{'name': 'test', 'value': 42}]
        csv = ReportGenerator.export_to_csv(data)
        self.assertIn('name', csv)
        self.assertIn('test', csv)

    def test_json_export(self):
        """测试JSON导出"""
        report = {'title': 'test'}
        json_str = ReportGenerator.export_to_json(report)
        self.assertIn('test', json_str)

    def test_recommendations(self):
        """测试改善建议生成"""
        recs = ReportGenerator._generate_recommendations({'avg_delay': 80, 'vcr': 0.95, 'avg_stops': 3.0})
        self.assertGreater(len(recs), 1)
