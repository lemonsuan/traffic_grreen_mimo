"""
Simulation app models.
"""

from django.db import models


class Simulation(models.Model):
    """仿真任务"""
    STATUS_CHOICES = [
        ('idle', '空闲'),
        ('running', '运行中'),
        ('paused', '已暂停'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    network = models.ForeignKey('network.Network', on_delete=models.CASCADE, related_name='simulations')
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='idle')
    
    # 配置参数
    duration = models.IntegerField(default=3600)  # 仿真时长(秒)
    step_size = models.FloatField(default=1.0)  # 步长(秒)
    speed_multiplier = models.FloatField(default=1.0)  # 速度倍数
    random_seed = models.IntegerField(null=True, blank=True)  # 随机种子
    
    # 状态信息
    current_time = models.FloatField(default=0)  # 当前仿真时间
    total_vehicles = models.IntegerField(default=0)  # 总车辆数
    completed_vehicles = models.IntegerField(default=0)  # 完成车辆数
    
    # 结果数据
    results = models.JSONField(null=True, blank=True)  # 仿真结果
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = '仿真任务'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} - {self.status}"


class SimulationSnapshot(models.Model):
    """仿真快照"""
    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name='snapshots')
    time = models.FloatField()  # 仿真时间
    
    # 车辆状态
    vehicles = models.JSONField()  # 车辆位置、速度等
    
    # 信号灯状态
    signals = models.JSONField()  # 信号灯状态
    
    # 性能指标
    metrics = models.JSONField(null=True, blank=True)  # 延误、排队等
    
    class Meta:
        unique_together = ('simulation', 'time')
        verbose_name = '仿真快照'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.simulation} - t={self.time}"


class SimulationMetrics(models.Model):
    """仿真性能指标"""
    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name='metrics')
    
    # 总体指标
    avg_delay = models.FloatField(default=0)  # 平均延误(秒)
    avg_queue_length = models.FloatField(default=0)  # 平均排队长度(辆)
    max_queue_length = models.IntegerField(default=0)  # 最大排队长度
    throughput = models.IntegerField(default=0)  # 吞吐量(辆)
    avg_stops = models.FloatField(default=0)  # 平均停车次数
    
    # 路口级指标
    intersection_metrics = models.JSONField(default=dict)  # 各路口指标
    
    class Meta:
        verbose_name = '仿真指标'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Metrics for {self.simulation}"
