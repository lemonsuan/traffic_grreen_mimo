"""
历史数据管理
功能: 快照存储、按时间查询、数据压缩、过期清理
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from django.utils import timezone
from django.db.models import QuerySet


def save_snapshot(network, sim_time: float, source: str,
                  vehicles: list, signals: dict, metrics: dict,
                  intersection_metrics: dict = None,
                  timestamp: datetime = None) -> 'HistorySnapshot':
    """存储单条历史快照"""
    from network.models import HistorySnapshot

    if timestamp is None:
        timestamp = timezone.now()

    return HistorySnapshot.objects.create(
        network=network,
        timestamp=timestamp,
        sim_time=sim_time,
        source=source,
        vehicles=vehicles,
        signals=signals,
        metrics=metrics,
        intersection_metrics=intersection_metrics or {}
    )


def batch_save_snapshots(network, snapshots: List[Dict],
                         source: str = 'simulation',
                         base_timestamp: datetime = None) -> int:
    """批量存储快照(仿真完成后调用)"""
    from network.models import HistorySnapshot

    if base_timestamp is None:
        base_timestamp = timezone.now()

    objects = []
    for i, snap in enumerate(snapshots):
        objects.append(HistorySnapshot(
            network=network,
            timestamp=base_timestamp + timedelta(seconds=snap.get('time', i)),
            sim_time=snap.get('time', i),
            source=source,
            vehicles=snap.get('vehicles', []),
            signals=snap.get('signals', {}),
            metrics=snap.get('metrics', {}),
            intersection_metrics=snap.get('intersection_metrics', {})
        ))

    HistorySnapshot.objects.bulk_create(objects, batch_size=200)
    return len(objects)


def get_snapshots(network, date: str = None,
                  from_time: str = None, to_time: str = None,
                  source: str = None,
                  limit: int = 3600) -> QuerySet:
    """
    按时间范围查询快照
    date: '2024-03-15'
    from_time: '08:00' (可选)
    to_time: '09:00' (可选)
    """
    from network.models import HistorySnapshot

    qs = HistorySnapshot.objects.filter(network=network)

    if date:
        day = datetime.strptime(date, '%Y-%m-%d').date()
        qs = qs.filter(timestamp__date=day)

        if from_time:
            h, m = map(int, from_time.split(':'))
            start = timezone.make_aware(datetime.combine(day, datetime.min.time().replace(hour=h, minute=m)))
            qs = qs.filter(timestamp__gte=start)

        if to_time:
            h, m = map(int, to_time.split(':'))
            end = timezone.make_aware(datetime.combine(day, datetime.min.time().replace(hour=h, minute=m)))
            qs = qs.filter(timestamp__lte=end)

    if source:
        qs = qs.filter(source=source)

    return qs.order_by('timestamp')[:limit]


def get_snapshot_at(network, timestamp_str: str) -> Optional['HistorySnapshot']:
    """查询指定时刻的快照(最近的一条)"""
    from network.models import HistorySnapshot

    ts = datetime.fromisoformat(timestamp_str)
    if timezone.is_naive(ts):
        ts = timezone.make_aware(ts)

    return HistorySnapshot.objects.filter(
        network=network,
        timestamp__lte=ts
    ).order_by('-timestamp').first()


def get_intersection_history(network, node_id: str, date: str) -> List[Dict]:
    """
    获取某个交叉口当天的指标序列(用于趋势图)
    返回: [{time, delay, queue, vcr, stops}, ...]
    """
    from network.models import HistorySnapshot

    day = datetime.strptime(date, '%Y-%m-%d').date()
    qs = HistorySnapshot.objects.filter(
        network=network,
        timestamp__date=day
    ).order_by('timestamp').only('sim_time', 'timestamp', 'intersection_metrics')

    result = []
    for snap in qs:
        node_metrics = snap.intersection_metrics.get(node_id, {})
        if node_metrics:
            result.append({
                'time': snap.timestamp.strftime('%H:%M:%S'),
                'sim_time': snap.sim_time,
                'delay': node_metrics.get('delay', 0),
                'queue': node_metrics.get('queue', 0),
                'vcr': node_metrics.get('vcr', 0),
                'stops': node_metrics.get('stops', 0),
            })

    return result


def get_available_dates(network) -> List[str]:
    """获取有数据的日期列表"""
    from network.models import HistorySnapshot
    from django.db.models import TruncDate

    dates = HistorySnapshot.objects.filter(network=network).annotate(
        date=TruncDate('timestamp')
    ).values_list('date', flat=True).distinct().order_by('date')

    return [d.strftime('%Y-%m-%d') for d in dates]


def compress_old_data(network, days: int = 30):
    """压缩旧数据: 每5分钟保留一条"""
    from network.models import HistorySnapshot

    cutoff = timezone.now() - timedelta(days=days)
    old_snaps = HistorySnapshot.objects.filter(
        network=network,
        timestamp__lt=cutoff
    ).order_by('timestamp')

    keep_ids = []
    last_kept = None
    for snap in old_snaps:
        if last_kept is None or (snap.timestamp - last_kept).total_seconds() >= 300:
            keep_ids.append(snap.id)
            last_kept = snap.timestamp

    deleted_count = old_snaps.exclude(id__in=keep_ids).delete()[0]
    return deleted_count


def cleanup_expired(network, days: int = 365):
    """清理过期数据"""
    from network.models import HistorySnapshot

    cutoff = timezone.now() - timedelta(days=days)
    deleted_count = HistorySnapshot.objects.filter(
        network=network,
        timestamp__lt=cutoff
    ).delete()[0]
    return deleted_count
