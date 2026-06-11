"""
Analysis app views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Max, Min, Count

from .models import AnalysisReport, PerformanceMetric
from .serializers import (
    AnalysisReportSerializer, PerformanceMetricSerializer,
    MetricsQuerySerializer, ComparisonRequestSerializer
)


class AnalysisReportViewSet(viewsets.ModelViewSet):
    queryset = AnalysisReport.objects.all()
    serializer_class = AnalysisReportSerializer
    filterset_fields = ['network', 'report_type']


class PerformanceMetricViewSet(viewsets.ModelViewSet):
    queryset = PerformanceMetric.objects.all()
    serializer_class = PerformanceMetricSerializer
    filterset_fields = ['network', 'node_id', 'metric_type']


class AnalysisViewSet(viewsets.ViewSet):
    """分析接口"""
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """获取性能指标"""
        serializer = MetricsQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        queryset = PerformanceMetric.objects.filter(network_id=data['network_id'])
        
        if data.get('node_id'):
            queryset = queryset.filter(node_id=data['node_id'])
        
        if data.get('metric_type'):
            queryset = queryset.filter(metric_type=data['metric_type'])
        
        if data.get('start_time'):
            queryset = queryset.filter(timestamp__gte=data['start_time'])
        
        if data.get('end_time'):
            queryset = queryset.filter(timestamp__lte=data['end_time'])
        
        # 计算统计信息
        stats = queryset.values('metric_type').annotate(
            avg_value=Avg('value'),
            max_value=Max('value'),
            min_value=Min('value'),
            count=Count('id')
        )
        
        return Response({
            'metrics': PerformanceMetricSerializer(queryset[:100], many=True).data,
            'statistics': list(stats)
        })
    
    @action(detail=False, methods=['post'])
    def compare(self, request):
        """对比优化结果"""
        serializer = ComparisonRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        result_ids = data['result_ids']
        metrics = data['metrics']
        
        from optimization.models import OptimizationResult
        
        results = OptimizationResult.objects.filter(id__in=result_ids)
        
        comparison = []
        for result in results:
            perf = result.performance or {}
            comparison.append({
                'result_id': result.id,
                'algorithm': result.algorithm,
                'level': result.level,
                'metrics': {
                    metric: perf.get(metric, 0)
                    for metric in metrics
                }
            })
        
        return Response({'comparison': comparison})
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """导出报告"""
        import csv
        import io
        from django.http import HttpResponse

        network_id = request.query_params.get('network_id')
        report_type = request.query_params.get('type', 'simulation')
        export_format = request.query_params.get('format', 'json')

        if not network_id:
            return Response(
                {'error': '请提供 network_id 参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        metrics = PerformanceMetric.objects.filter(network_id=network_id)
        reports = AnalysisReport.objects.filter(network_id=network_id)

        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="report_{network_id}.csv"'
            response.write('\ufeff')

            writer = csv.writer(response)
            writer.writerow(['类型', '节点ID', '指标类型', '值', '时间'])
            for m in metrics:
                writer.writerow(['metric', m.node_id, m.metric_type, m.value, m.timestamp])

            writer.writerow([])
            writer.writerow(['报告ID', '名称', '类型', '摘要', '创建时间'])
            for r in reports:
                writer.writerow([r.id, r.name, r.report_type, r.summary, r.created_at])

            return response

        return Response({
            'network_id': network_id,
            'type': report_type,
            'metrics': list(metrics.values('node_id', 'metric_type', 'value', 'timestamp')[:500]),
            'reports': list(reports.values('id', 'name', 'report_type', 'summary', 'created_at')[:50]),
            'total_metrics': metrics.count(),
            'total_reports': reports.count()
        })

    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        """自动生成分析报告"""
        from .report_generator import ReportGenerator

        report_type = request.data.get('type', 'network')
        network_id = request.data.get('network_id')

        if not network_id:
            return Response(
                {'error': '请提供 network_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from network.models import Network
        try:
            network = Network.objects.get(id=network_id)
        except Network.DoesNotExist:
            return Response(
                {'error': f'路网 {network_id} 不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        if report_type == 'network':
            network_data = {
                'nodes': {n.node_id: {'name': n.name} for n in network.nodes.all()},
                'edges': list(network.edges.values('length', 'speed_limit', 'road_class')),
                'signals': list(network.nodes.filter(signal__isnull=False).values())
            }
            report = ReportGenerator.generate_network_report(network_data, network.name)
        else:
            report = ReportGenerator.generate_network_report({}, network.name)

        report_obj = AnalysisReport.objects.create(
            network=network,
            name=report['title'],
            report_type=report_type,
            summary=str(report.get('summary', {})),
            data=report
        )

        return Response({
            'report_id': report_obj.id,
            'report': report
        })
