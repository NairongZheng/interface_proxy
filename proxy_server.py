#!/usr/bin/env python3
"""
接口代理服务启动脚本

使用方法:
    python proxy_server.py
    python proxy_server.py --host 0.0.0.0 --port 8080
    python proxy_server.py --config custom_config.yaml
"""

import argparse
import sys

import uvicorn

from proxy_app.config import Config
from proxy_app.utils.logger import logger


def parse_args():
    """
    解析命令行参数

    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        description="接口代理服务 - 支持 OpenAI 和 Anthropic 格式互转",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="配置文件路径",
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="监听地址（覆盖配置文件中的设置）",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="监听端口（覆盖配置文件中的设置）",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别（覆盖配置文件中的设置）",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用自动重载（开发模式）",
    )

    return parser.parse_args()


def main():
    """
    主函数：启动服务
    """
    # 解析命令行参数
    args = parse_args()

    try:
        # 加载配置
        config = Config(config_path=args.config)

        # 命令行参数覆盖配置文件
        host = args.host if args.host is not None else config.server_host
        port = args.port if args.port is not None else config.server_port
        log_level = args.log_level if args.log_level is not None else config.log_level

        # 打印启动信息
        logger.info("=" * 60)
        logger.info("接口代理服务启动")
        logger.info("=" * 60)
        logger.info(f"配置文件: {args.config}")
        logger.info(f"后端服务: {config.backend_url}")
        logger.info(f"监听地址: {host}:{port}")
        logger.info(f"日志级别: {log_level}")
        logger.info(f"OpenAI 接口: {'启用' if config.openai_enabled else '禁用'}")
        logger.info(f"Anthropic 接口: {'启用' if config.anthropic_enabled else '禁用'}")
        logger.info("=" * 60)

        # 启动 uvicorn 服务器
        uvicorn.run(
            "proxy_app.app:app",  # 应用路径
            host=host,
            port=port,
            log_level=log_level.lower(),
            reload=args.reload,  # 开发模式自动重载
        )

    except FileNotFoundError as e:
        logger.error(f"配置文件不存在: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
