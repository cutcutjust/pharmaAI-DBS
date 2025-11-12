"""数据库统计工具模块。

提供用于统计药典条目数据量的通用函数，便于在数据生成或维护脚本中复用。
"""

from collections import defaultdict
from typing import Iterable, Mapping, Optional, Tuple, Dict

from utils.logger import get_logger

_logger = get_logger(__name__)


def _resolve_logger(logger=None):
    """获取可用的日志记录器。"""
    return logger or _logger


def summarize_volume_counts_from_records(records: Iterable[Mapping[str, object]]) -> Tuple[int, Dict[int, int]]:
    """根据记录列表统计各卷号数量。

    Args:
        records: 包含 volume 信息的记录迭代器。

    Returns:
        二元组 (total, counts)，其中 total 为总记录数，counts 为按卷号统计的字典。
    """
    counts: Dict[int, int] = defaultdict(int)
    for record in records:
        volume = record.get("volume") if isinstance(record, Mapping) else None
        if volume is None:
            continue
        try:
            volume_int = int(volume)
        except (TypeError, ValueError):
            continue
        counts[volume_int] += 1

    sorted_counts = dict(sorted(counts.items()))
    total = sum(sorted_counts.values())
    return total, sorted_counts


def log_pharmacopoeia_items_stats_from_records(
    records: Iterable[Mapping[str, object]],
    *,
    logger=None,
    header: str = "数据库中现有记录统计:"
) -> Tuple[int, Dict[int, int]]:
    """记录并返回基于现有记录的药典条目统计信息。"""
    total, counts = summarize_volume_counts_from_records(records)
    log = _resolve_logger(logger)
    log.info(header)
    log.info("  总计: %d 条", total)
    for volume, count in counts.items():
        log.info("  第%s部: %d 条", volume, count)
    return total, counts


def log_pharmacopoeia_items_stats_from_db(
    dao,
    *,
    logger=None,
    header: str = "数据库最终记录统计:"
) -> Tuple[int, Dict[int, int]]:
    """查询数据库并记录药典条目的统计信息。"""
    stats = dao.execute_query(
        """
        SELECT volume, COUNT(*) AS count
        FROM pharmacopoeia_items
        GROUP BY volume
        ORDER BY volume
        """
    )

    counts: Dict[int, int] = {}
    total = 0
    for row in stats:
        volume = row.get("volume")
        count = row.get("count", 0)
        try:
            volume_int = int(volume)
            count_int = int(count)
        except (TypeError, ValueError):
            continue
        counts[volume_int] = count_int
        total += count_int

    log = _resolve_logger(logger)
    log.info(header)
    log.info("  总计: %d 条", total)
    for volume, count in counts.items():
        log.info("  第%s部: %d 条", volume, count)

    return total, counts
