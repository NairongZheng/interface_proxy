"""
配置管理模块
负责加载和解析 YAML 配置文件，提供配置访问接口
"""

import os
from pathlib import Path
from typing import List, Optional

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
    def backend_type(self) -> str:
        """
        获取后端类型

        Returns:
            后端类型：'standard'（标准OpenAI）, 'ptu'（PTU Gateway）, 'both'（两者都启用）
            默认为 'both'
        """
        return self._config["backend"].get("type", "both")

    @property
    def backend_url(self) -> str:
        """获取后端服务地址（例如：http://127.0.0.1:8000）"""
        return self._config["backend"]["url"]

    @property
    def backend_api_key(self) -> Optional[str]:
        """获取后端 API Key（用于认证）"""
        return self._config["backend"].get("api_key")

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

    # ==================== 模型配置 ====================

    @property
    def available_models(self) -> list:
        """
        获取可用的模型列表

        Returns:
            模型配置列表，每个模型包含 id, owned_by, created 字段
        """
        return self._config.get("models", {}).get("available_models", [])

    # ==================== PTU 后端配置 ====================

    @property
    def ptu_models(self) -> list:
        """
        获取 PTU 模型列表

        Returns:
            PTU 模型名称列表
        """
        return self._config.get("ptu", {}).get("models", [])

    @property
    def ptu_backend_url(self) -> Optional[str]:
        """
        获取 PTU 后端 URL

        如果配置中指定了 ptu.backend_url，则使用指定值；
        否则使用默认的 backend.url

        Returns:
            PTU 后端 URL
        """
        ptu_url = self._config.get("ptu", {}).get("backend_url")
        # 如果 ptu_url 是 None，返回默认的 backend_url
        return ptu_url if ptu_url is not None else self.backend_url

    def is_ptu_model(self, model: str) -> bool:
        """
        判断模型是否应该使用 PTU 后端

        根据 backend.type 配置决定：
        - 'standard': 总是返回 False（不使用 PTU）
        - 'ptu': 总是返回 True（所有模型都使用 PTU）
        - 'both': 检查模型是否在 ptu.models 列表中

        Args:
            model: 模型名称

        Returns:
            True 表示使用 PTU 后端，False 表示使用标准后端
        """
        backend_type = self.backend_type

        if backend_type == "standard":
            # 只使用标准后端，不使用 PTU
            return False
        elif backend_type == "ptu":
            # 所有模型都使用 PTU
            return True
        else:  # backend_type == "both"
            # 根据模型列表判断
            return model in self.ptu_models

    def get_available_models_by_backend(self) -> list:
        """
        根据启用的后端类型，返回可用的模型列表

        根据 backend.type 配置过滤：
        - 'standard': 只返回非 PTU 模型
        - 'ptu': 只返回 PTU 模型
        - 'both': 返回所有配置的模型

        Returns:
            过滤后的模型配置列表
        """
        all_models = self.available_models
        backend_type = self.backend_type
        ptu_model_ids = set(self.ptu_models)

        if backend_type == "standard":
            # 只返回非 PTU 模型
            return [m for m in all_models if m["id"] not in ptu_model_ids]
        elif backend_type == "ptu":
            # 只返回 PTU 模型
            return [m for m in all_models if m["id"] in ptu_model_ids]
        else:  # backend_type == "both"
            # 返回所有模型
            return all_models

    def __repr__(self) -> str:
        """返回配置的字符串表示"""
        return (
            f"Config(backend_url={self.backend_url}, "
            f"server_host={self.server_host}, "
            f"server_port={self.server_port})"
        )
