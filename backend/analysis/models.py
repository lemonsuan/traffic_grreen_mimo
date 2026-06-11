"""
Analysis app models.
"""

from django.db import models


class AnalysisReport(models.Model):
    """分析报告"""
    REPORT_TYPE_CHOICES = [
        ('simulation', '仿真报告'),
        ('optimization', '优化报告'),
        ('comparison', '对比报告'),
    ]
    
    network = models.ForeignKey('network.Network', on_delete=models.CASCADE, related_name='analysis_reports')
    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    
    # 报告内容
    summary = models.TextField(blank=True)
    data = models.JSONField()  # 报告数据
    
    # 关联对象
    simulation = models.ForeignKey(
        'simulation.Simulation',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='analysis_reports'
    )
    optimization_result = models.ForeignKey(
        'optimization.OptimizationResult',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='analysis_reports'
    )
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '分析报告'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.report_type}"


class PerformanceMetric(models.Model):
    """性能指标记录"""
    METRIC_TYPE_CHOICES = [
        ('delay', '延误'),
        ('queue', '排队长度'),
        ('throughput', '吞吐量'),
        ('stops', '停车次数'),
        ('vcr', '饱和度'),
    ]
    
    network = models.ForeignKey('network.Network', on_delete=models.CASCADE, related_name='metrics')
    node_id = models.CharField(max_length=50, blank=True)  # 路口ID
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPE_CHOICES)
    value = models.FloatField()
    
    # 时间信息
    timestamp = models.DateTimeField(auto_now_add=True)
    simulation_time = models.FloatField(null=True, blank=True)  # 仿真时间
    
    class Meta:
        verbose_name = '性能指标'
        verbose_name_plural = verbose_name
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.metric_type}: {self.value}"
