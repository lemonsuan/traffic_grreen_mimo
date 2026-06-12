"""
路网数据模型
"""

from django.db import models


class Network(models.Model):
    """路网容器"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    srid = models.IntegerField(default=4326)  # 坐标系
    bounds = models.JSONField(null=True, blank=True)  # 边界框
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '路网'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Node(models.Model):
    """路口节点"""
    NODE_TYPE_CHOICES = [
        ('intersection', '信号灯路口'),
        ('roundabout', '环岛'),
    ]
    
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='nodes')
    node_id = models.CharField(max_length=50)  # 用户自定义ID
    name = models.CharField(max_length=100, blank=True)
    node_type = models.CharField(max_length=20, choices=NODE_TYPE_CHOICES)
    
    # 地理坐标 (经纬度)
    lng = models.FloatField()
    lat = models.FloatField()
    
    # 本地坐标 (Three.js世界坐标)
    x = models.FloatField(default=0)
    y = models.FloatField(default=0)
    z = models.FloatField(default=0)
    
    # 几何属性
    geometry = models.JSONField(null=True, blank=True)  # GeoJSON格式
    
    class Meta:
        unique_together = ('network', 'node_id')
        verbose_name = '节点'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name or self.node_id}"


class Intersection(models.Model):
    """信号灯路口扩展信息"""
    INTERSECTION_TYPE_CHOICES = [
        ('cross', '十字路口'),
        ('t_junction', 'T形路口'),
        ('y_junction', 'Y形路口'),
        ('multi_leg', '多路交叉'),
    ]
    
    node = models.OneToOneField(Node, on_delete=models.CASCADE, related_name='intersection')
    intersection_type = models.CharField(max_length=20, choices=INTERSECTION_TYPE_CHOICES, default='cross')
    channelization = models.JSONField(default=dict)  # 进口道渠化
    control_type = models.CharField(max_length=20, default='signal', choices=[
        ('signal', '信号控制'),
        ('stop', '停车控制'),
        ('yield', '让行控制'),
    ])

    class Meta:
        verbose_name = '交叉口'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Intersection: {self.node}"


class Roundabout(models.Model):
    """环岛扩展信息"""
    node = models.OneToOneField(Node, on_delete=models.CASCADE, related_name='roundabout')
    radius = models.FloatField()  # 环岛半径(米)
    lanes_count = models.IntegerField(default=1)  # 环道数
    inscribed_circle = models.FloatField(null=True, blank=True)  # 内切圆直径
    central_island = models.JSONField(default=dict)  # 中心岛信息

    class Meta:
        verbose_name = '环岛'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Roundabout: {self.node}"


class Edge(models.Model):
    """连接段 (路段)"""
    ROAD_CLASS_CHOICES = [
        ('motorway', '高速公路'),
        ('trunk', '快速路'),
        ('primary', '主干路'),
        ('secondary', '次干路'),
        ('tertiary', '支路'),
        ('residential', '居住区道路'),
    ]
    
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='edges')
    edge_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100, blank=True)
    
    # 拓扑关系
    from_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='outgoing_edges')
    to_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='incoming_edges')
    
    # 几何属性
    geometry = models.JSONField(null=True, blank=True)  # GeoJSON LineString
    length = models.FloatField()  # 长度(米)
    
    # 交通属性
    speed_limit = models.FloatField(default=50)  # 限速(km/h)
    lanes_count = models.IntegerField(default=1)  # 车道数
    capacity = models.FloatField(null=True, blank=True)  # 通行能力(pcu/h)
    
    # 道路等级
    road_class = models.CharField(max_length=20, choices=ROAD_CLASS_CHOICES, default='primary')
    
    # 方向
    is_oneway = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('network', 'edge_id')
        verbose_name = '路段'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name or self.edge_id}"


class Lane(models.Model):
    """车道"""
    LANE_TYPE_CHOICES = [
        ('through', '直行车道'),
        ('left_turn', '左转车道'),
        ('right_turn', '右转车道'),
        ('left_through', '左直合用车道'),
        ('right_through', '右直合用车道'),
        ('bus', '公交专用道'),
        ('emergency', '应急车道'),
    ]
    
    edge = models.ForeignKey(Edge, on_delete=models.CASCADE, related_name='lanes')
    lane_index = models.IntegerField()  # 车道序号 (从左到右，0开始)
    lane_type = models.CharField(max_length=20, choices=LANE_TYPE_CHOICES, default='through')
    
    # 几何属性
    width = models.FloatField(default=3.5)  # 宽度(米)
    geometry = models.JSONField(null=True, blank=True)  # 车道中心线
    
    # 交通属性
    speed_limit = models.FloatField(null=True, blank=True)  # 车道限速
    is_parking = models.BooleanField(default=False)  # 允许停车

    # 信号灯类型
    signal_display = models.CharField(max_length=10, default='round', choices=[
        ('arrow', '箭头灯'),
        ('round', '圆灯'),
    ])
    is_exclusive = models.BooleanField(default=False)  # 是否专用道(不受信号控制)
    
    class Meta:
        unique_together = ('edge', 'lane_index')
        verbose_name = '车道'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.edge} - Lane {self.lane_index}"


class LaneConnection(models.Model):
    """车道连接 (转向关系)"""
    CONNECTION_TYPE_CHOICES = [
        ('straight', '直行'),
        ('left', '左转'),
        ('right', '右转'),
        ('u_turn', '掉头'),
    ]
    
    from_lane = models.ForeignKey(Lane, on_delete=models.CASCADE, related_name='outgoing_connections')
    to_lane = models.ForeignKey(Lane, on_delete=models.CASCADE, related_name='incoming_connections')
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPE_CHOICES)
    priority = models.IntegerField(default=0)  # 优先级
    has_yield = models.BooleanField(default=False)  # 需要让行
    
    class Meta:
        unique_together = ('from_lane', 'to_lane')
        verbose_name = '车道连接'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.from_lane} -> {self.to_lane}"


class Signal(models.Model):
    """信号灯"""
    CONTROL_MODE_CHOICES = [
        ('fixed', '固定配时'),
        ('actuated', '感应控制'),
        ('adaptive', '自适应控制'),
    ]
    
    node = models.OneToOneField(Node, on_delete=models.CASCADE, related_name='signal')
    signal_id = models.CharField(max_length=50)
    cycle_length = models.FloatField()  # 周期长(秒)
    offset = models.FloatField(default=0)  # 相位差(秒)
    control_mode = models.CharField(max_length=20, choices=CONTROL_MODE_CHOICES, default='fixed')
    is_coordinated = models.BooleanField(default=False)  # 是否参与绿波协调
    coordination_group = models.CharField(max_length=50, blank=True)  # 协调组
    
    class Meta:
        verbose_name = '信号灯'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Signal: {self.node}"


class Phase(models.Model):
    """信号相位"""
    PHASE_TYPE_CHOICES = [
        ('through', '直行相位'),
        ('left_turn', '左转相位'),
        ('pedestrian', '行人相位'),
        ('right_turn', '右转相位'),
    ]
    
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE, related_name='phases')
    phase_index = models.IntegerField()  # 相位序号
    green_time = models.FloatField()  # 绿灯时间(秒)
    yellow_time = models.FloatField(default=3)  # 黄灯时间(秒)
    all_red_time = models.FloatField(default=1)  # 全红时间(秒)
    phase_type = models.CharField(max_length=20, choices=PHASE_TYPE_CHOICES, default='through')
    allowed_movements = models.JSONField(default=list)  # ['straight', 'left', 'right']

    # 灯型配置
    light_type = models.CharField(max_length=10, default='round', choices=[
        ('arrow', '箭头灯'),
        ('round', '圆灯'),
        ('mixed', '混合'),
    ])
    protected_movements = models.JSONField(default=list)   # 箭头灯保护的转向 ['left','through','right']
    permissive_movements = models.JSONField(default=list)  # 圆灯许可的转向(需让行)
    
    class Meta:
        unique_together = ('signal', 'phase_index')
        verbose_name = '相位'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.signal} - Phase {self.phase_index}"


class PhaseLane(models.Model):
    """相位-车道映射"""
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name='phase_lanes')
    lane = models.ForeignKey(Lane, on_delete=models.CASCADE, related_name='phase_lanes')
    has_right_of_way = models.BooleanField(default=True)
    min_green_time = models.FloatField(default=7)  # 最小绿灯时间
    
    class Meta:
        unique_together = ('phase', 'lane')
        verbose_name = '相位车道映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.phase} - {self.lane}"


class TrafficDemand(models.Model):
    """交通需求"""
    DEMAND_TYPE_CHOICES = [
        ('od_matrix', 'OD矩阵'),
        ('turning_count', '转向流量'),
        ('link_flow', '路段流量'),
    ]
    
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='demands')
    name = models.CharField(max_length=100)
    time_start = models.TimeField()
    time_end = models.TimeField()
    demand_type = models.CharField(max_length=20, choices=DEMAND_TYPE_CHOICES)
    
    class Meta:
        verbose_name = '交通需求'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ODMatrix(models.Model):
    """OD矩阵"""
    demand = models.ForeignKey(TrafficDemand, on_delete=models.CASCADE, related_name='od_matrices')
    from_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='od_origins')
    to_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='od_destinations')
    flow = models.FloatField()  # 流量 (pcu/h)
    vehicle_composition = models.JSONField(default=dict)  # {'car': 0.8, 'truck': 0.2}
    
    class Meta:
        unique_together = ('demand', 'from_node', 'to_node')
        verbose_name = 'OD矩阵'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.from_node} -> {self.to_node}: {self.flow}"


class HistorySnapshot(models.Model):
    """历史快照 — 存储仿真/检测器的时序数据，支持任意时刻回放"""
    SOURCE_CHOICES = [
        ('simulation', '仿真'),
        ('detector', '检测器'),
        ('import', '导入'),
    ]

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='history_snapshots')
    timestamp = models.DateTimeField(db_index=True)   # 真实时间
    sim_time = models.FloatField(default=0)            # 仿真内时间(秒)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='simulation')

    # 车辆状态 [{id, link_id, from_node, to_node, position, speed, lane}]
    vehicles = models.JSONField(default=list)
    # 信号灯状态 {node_id: {current_phase, phase_elapsed}}
    signals = models.JSONField(default=dict)
    # 聚合指标 {avg_delay, avg_queue_length, throughput, vcr, ...}
    metrics = models.JSONField(default=dict)
    # 每个交叉口的指标 {node_id: {delay, queue, vcr, stops}}
    intersection_metrics = models.JSONField(default=dict)

    class Meta:
        verbose_name = '历史快照'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['network', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.network.name} @ {self.timestamp}"
