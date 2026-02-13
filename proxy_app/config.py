"""
配置管理模块
负责加载和解析 YAML 配置文件，提供配置访问接口
"""

import os
from pathlib import Path
from typing import Optional

import yaml


class Config:
    """
    配置管理类
    从 config.yaml 加载配置，提供配置项的访问接口
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，如果未指定则使用默认路径 config/config.yaml
        """
        if config_path is None:
            # 默认配置文件路径：项目根目录下的 config/config.yaml
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "config.yaml"

        self._config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """
        加载 YAML 配置文件

        Returns:
            配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: 配置文件格式错误
        """
        if not os.path.exists(self._config_path):
            raise FileNotFoundError(f"配置文件不存在: {self._config_path}")

        with open(self._config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    # ==================== 后端服务配置 ====================

    @property
    def backend_url(self) -> str:
        """获取后端服务地址（例如：http://127.0.0.1:8000）"""
        return self._config["backend"]["url"]

    @property
    def backend_timeout(self) -> float:
        """获取后端请求超时时间（秒）"""
        return self._config["backend"]["timeout"]

    @property
    def backend_max_connections(self) -> int:
        """获取后端连接池最大连接数"""
        return self._config["backend"]["max_connections"]

    @property
    def backend_max_keepalive_connections(self) -> int:
        """获取后端连接池最大保活连接数"""
        return self._config["backend"]["max_keepalive_connections"]

    # ==================== 代理服务配置 ====================

    @property
    def server_host(self) -> str:
        """获取代理服务监听地址"""
        return self._config["server"]["host"]

    @property
    def server_port(self) -> int:
        """获取代理服务监听端口"""
        return self._config["server"]["port"]

    @property
    def log_level(self) -> str:
        """获取日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）"""
        return self._config["server"]["log_level"]

    # ==================== 路由配置 ====================

    @property
    def openai_enabled(self) -> bool:
        """是否启用 OpenAI 格式接口"""
        return self._config["routes"]["openai_enabled"]

    @property
    def anthropic_enabled(self) -> bool:
        """是否启用 Anthropic 格式接口"""
        return self._config["routes"]["anthropic_enabled"]

    def __repr__(self) -> str:
        """返回配置的字符串表示"""
        return (
            f"Config(backend_url={self.backend_url}, "
            f"server_host={self.server_host}, "
            f"server_port={self.server_port})"
        )
