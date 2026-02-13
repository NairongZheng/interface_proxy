"""
日志配置模块
提供统一的日志配置和日志记录器
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "interface_proxy",
    level: str = "INFO",
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        format_string: 自定义日志格式字符串，如果未指定则使用默认格式

    Returns:
        配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 如果已经有处理器，说明已经配置过，直接返回
    if logger.handlers:
        return logger

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # 设置日志格式
    if format_string is None:
        # 默认格式：时间 - 日志级别 - 模块名 - 消息
        format_string = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)

    # 添加处理器到日志记录器
    logger.addHandler(console_handler)

    return logger


# 创建默认的全局日志记录器
logger = setup_logger()
