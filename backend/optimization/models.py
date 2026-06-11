"""
Optimization app models.
"""

from django.db import models


class OptimizationResult(models.Model):
    """优化结果"""
    LEVEL_CHOICES = [
        ('intersection', '单点交叉口'),
        ('corridor', '干线绿波'),
        ('network', '区域路网'),
    ]
    
    network = models.ForeignKey('network.Network', on_delete=models.CASCADE, related_name='optimization_results')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    algorithm = models.CharField(max_length=50)
    name = models.CharField(max_length=100, blank=True)
    
    # 优化结果
    signal_timings = models.JSONField()  # 信号配时方案
    performance = models.JSONField()  # 性能指标
    convergence = models.JSONField(null=True, blank=True)  # 收敛曲线
    
    # 计算信息
    computation_time = models.FloatField(default=0)  # 计算时间(秒)
    
    # 状态
    is_applied = models.BooleanField(default=False)  # 是否已应用
    applied_at = models.DateTimeField(null=True, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '优化结果'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.level} - {self.algorithm} - {self.created_at}"


class AlgorithmConfig(models.Model):
    """算法配置"""
    LEVEL_CHOICES = [
        ('intersection', '单点交叉口'),
        ('corridor', '干线绿波'),
        ('network', '区域路网'),
    ]
    
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    algorithm = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # 默认参数
    default_params = models.JSONField(default=dict)
    
    # 约束配置
    constraints = models.JSONField(default=dict)
    
    # 是否启用
    is_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('level', 'algorithm')
        verbose_name = '算法配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.level} - {self.algorithm}"
