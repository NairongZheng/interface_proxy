"""
极简的内存统计模块 - 只存聚合计数

提供基于小时级别时间桶的流量统计功能，适合单机部署的简单监控场景
内存占用极小（约 500KB - 1MB），对请求性能影响可忽略不计
"""
import time
from typing import Dict, Any, Optional
from collections import defaultdict
from threading import Lock


class SimpleStatsCollector:
    """
    极简的统计收集器 - 只存储小时级别的聚合计数

    数据结构：
        buckets = {
            hour_timestamp: {
                model_name: {
                    "count": int,     # 总请求数
                    "success": int,   # 成功数
                    "error": int      # 失败数
                }
            }
        }

    内存占用估算：
        720桶 (30天×24小时) × 10模型 × 3计数器 × 8字节 ≈ 172KB
        加上字典开销（3-5倍）≈ 500KB - 1MB

    性能特点：
        - 记录操作：O(1)，只递增计数器，< 0.01ms
        - 查询操作：O(桶数 × 模型数)，毫秒级
        - 自动清理：每 100 次记录触发一次
    """

    def __init__(self, max_days: int = 30):
        """
        初始化统计收集器

        Args:
            max_days: 保留的最大天数（默认30天）
        """
        # 存储结构：{hour_timestamp: {model: {count, success, error}}}
        # 使用 defaultdict 自动创建嵌套字典，避免手动检查键是否存在
        self.buckets: Dict[int, Dict[str, Dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"count": 0, "success": 0, "error": 0})
        )
        self.max_days = max_days
        # 线程锁，保证多线程环境下的数据一致性
        self.lock = Lock()

    def record(self, model: str, status: str):
        """
        记录一次请求（只递增计数器）

        这是性能最关键的方法，会在每个请求中调用
        设计为极速操作（< 0.01ms），不影响请求性能

        Args:
            model: 模型名称（如 gpt-4、gpt-3.5-turbo）
            status: 状态（success/error）
        """
        # 计算当前小时桶（Unix时间戳除以3600秒）
        # 例如：1709366400 表示 2024-03-02 12:00:00 这一小时
        hour_bucket = int(time.time() // 3600)

        # 使用锁保证线程安全
        with self.lock:
            # 递增总计数器
            self.buckets[hour_bucket][model]["count"] += 1

            # 根据状态递增相应的计数器
            if status == "success":
                self.buckets[hour_bucket][model]["success"] += 1
            else:
                self.buckets[hour_bucket][model]["error"] += 1

            # 定期清理过期数据（每100次记录清理一次，避免每次都清理影响性能）
            # 只在当前桶的当前模型计数为100的倍数时清理
            if self.buckets[hour_bucket][model]["count"] % 100 == 0:
                self._cleanup()

    def _cleanup(self):
        """
        清理过期的桶（内部方法，需要在锁内调用）

        删除超过 max_days 天的旧数据，避免内存无限增长
        """
        # 计算截止时间桶（当前时间 - max_days 天）
        cutoff_bucket = int(time.time() // 3600) - (self.max_days * 24)

        # 找出所有过期的桶
        expired = [bucket for bucket in self.buckets if bucket < cutoff_bucket]

        # 删除过期数据
        for bucket in expired:
            del self.buckets[bucket]

    def get_stats(self, time_range: str = "24h", model: Optional[str] = None) -> Dict[str, Any]:
        """
        获取统计数据

        聚合指定时间范围内的统计结果，支持按模型过滤

        Args:
            time_range: 时间范围（24h/7d/30d）
            model: 模型过滤（可选，为 None 时返回所有模型）

        Returns:
            统计数据字典，包含：
            - time_range: 时间范围
            - total_requests: 总请求数
            - success_count: 成功数
            - error_count: 失败数
            - by_model: 按模型分组的详细统计（按请求数降序排列）
        """
        # 解析时间范围，转换为小时数
        if time_range == "24h":
            hours = 24
        elif time_range == "7d":
            hours = 24 * 7
        elif time_range == "30d":
            hours = 24 * 30
        else:
            # 默认 24 小时
            hours = 24

        # 计算查询的时间范围（起始桶到当前桶）
        current_bucket = int(time.time() // 3600)
        start_bucket = current_bucket - hours

        # 初始化聚合结果
        total_count = 0
        total_success = 0
        total_error = 0
        by_model = defaultdict(lambda: {"count": 0, "success": 0, "error": 0})

        # 使用锁保证读取时的数据一致性
        with self.lock:
            # 遍历时间范围内的所有桶
            for bucket in range(start_bucket, current_bucket + 1):
                if bucket in self.buckets:
                    # 遍历每个桶中的所有模型
                    for m, stats in self.buckets[bucket].items():
                        # 如果指定了模型过滤，跳过不匹配的模型
                        if model and m != model:
                            continue

                        # 累加模型维度的统计
                        by_model[m]["count"] += stats["count"]
                        by_model[m]["success"] += stats["success"]
                        by_model[m]["error"] += stats["error"]

                        # 累加总体统计
                        total_count += stats["count"]
                        total_success += stats["success"]
                        total_error += stats["error"]

        # 构建返回结果
        return {
            "time_range": time_range,
            "total_requests": total_count,
            "success_count": total_success,
            "error_count": total_error,
            # 按请求数降序排列模型统计
            "by_model": [
                {"model": m, **stats}
                for m, stats in sorted(by_model.items(), key=lambda x: x[1]["count"], reverse=True)
            ]
        }


# 全局单例实例
# 使用单例模式避免重复创建收集器，保证统计数据的一致性
_collector = SimpleStatsCollector()


def get_collector() -> SimpleStatsCollector:
    """
    获取全局统计收集器

    Returns:
        全局唯一的 SimpleStatsCollector 实例
    """
    return _collector
