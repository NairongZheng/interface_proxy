"""
FastAPI 应用和路由模块
定义代理服务的 HTTP 接口
"""

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from proxy_app.adapters.base_adapter import BaseAdapter
from proxy_app.adapters.anthropic_adapter import AnthropicAdapter
from proxy_app.adapters.openai_adapter import OpenAIAdapter
from proxy_app.config import Config
from proxy_app.models.anthropic_models import AnthropicMessagesRequest
from proxy_app.models.openai_models import (
    ChatCompletionRequest,
    Model,
    ModelList,
    ModelPermission,
)
from proxy_app.proxy.backend_proxy import BackendProxy
from proxy_app.utils.logger import logger, setup_logger


# 全局变量：后端代理实例（在 startup 事件中初始化）
backend_proxy: BackendProxy = None


def create_app(config: Config = None) -> FastAPI:
    """
    创建 FastAPI 应用实例

    Args:
        config: 配置对象，如果未指定则使用默认配置

    Returns:
        FastAPI 应用实例
    """
    # 如果未提供配置，则加载默认配置
    if config is None:
        config = Config()

    # 配置日志
    setup_logger(level=config.log_level)

    # 创建 FastAPI 应用
    app = FastAPI(
        title="Interface Proxy Service",
        description="LLM 接口代理服务，支持 OpenAI 和 Anthropic 格式互转",
        version="1.0.0",
    )

    # 存储配置到 app.state
    app.state.config = config

    # 注册启动和关闭事件
    @app.on_event("startup")
    async def startup_event():
        """
        应用启动时初始化后端代理

        初始化全局的 BackendProxy 实例，用于后续请求转发
        """
        global backend_proxy

        logger.info("正在初始化后端代理...")

        backend_proxy = BackendProxy(
            backend_url=config.backend_url,
            timeout=config.backend_timeout,
            max_connections=config.backend_max_connections,
            max_keepalive_connections=config.backend_max_keepalive_connections,
        )

        logger.info("应用启动完成")

    @app.on_event("shutdown")
    async def shutdown_event():
        """
        应用关闭时清理资源

        关闭后端代理的 HTTP 连接
        """
        global backend_proxy

        logger.info("正在关闭应用...")

        if backend_proxy:
            await backend_proxy.close()

        logger.info("应用已关闭")

    # 注册路由
    register_routes(app, config)

    return app


def register_routes(app: FastAPI, config: Config):
    """
    注册路由

    根据配置启用相应的路由

    Args:
        app: FastAPI 应用实例
        config: 配置对象
    """

    # ==================== 根路由 ====================

    @app.get("/")
    async def root():
        """
        根路由 - 返回服务基本信息

        Returns:
            服务信息字典
        """
        return {
            "service": "Interface Proxy Service",
            "version": "1.0.0",
            "description": "LLM 接口代理服务，支持 OpenAI 和 Anthropic 格式互转",
            "endpoints": {
                "health": "/health",
                "openai_chat": "/v1/chat/completions" if config.openai_enabled else None,
                "anthropic_messages": "/v1/messages" if config.anthropic_enabled else None,
                "models_list": "/v1/models",
                "model_detail": "/v1/models/{model_id}",
            },
            "backend_url": config.backend_url,
        }

    # ==================== 健康检查路由 ====================

    @app.get("/health")
    async def health_check():
        """
        健康检查接口

        Returns:
            健康状态信息
        """
        return {
            "status": "ok",
            "service": "interface_proxy",
            "backend_url": config.backend_url,
        }

    # ==================== Models API 路由 ====================

    @app.get("/v1/models")
    async def list_models():
        """
        列出所有可用模型

        实现 OpenAI Models API 的 list 接口
        返回配置文件中定义的所有可用模型

        Returns:
            ModelList: 包含所有模型信息的列表

        Example:
            GET /v1/models
            Response:
            {
                "object": "list",
                "data": [
                    {
                        "id": "gpt-3.5-turbo",
                        "object": "model",
                        "created": 1677610602,
                        "owned_by": "openai"
                    },
                    ...
                ]
            }
        """
        logger.info("收到模型列表请求")

        # 从配置中获取模型列表
        available_models = config.available_models

        # 构建 Model 对象列表
        models = []
        for model_config in available_models:
            # 创建默认权限
            permission = ModelPermission(
                id=f"modelperm-{model_config['id']}",
                created=model_config.get("created", 0),
            )

            # 创建 Model 对象
            model = Model(
                id=model_config["id"],
                created=model_config.get("created", 0),
                owned_by=model_config.get("owned_by", "openai"),
                permission=[permission],
                root=model_config.get("id"),
                parent=None,
            )
            models.append(model)

        # 构建响应
        model_list = ModelList(data=models)

        logger.info(f"返回 {len(models)} 个可用模型")

        return JSONResponse(content=model_list.model_dump())

    @app.get("/v1/models/{model_id}")
    async def get_model(model_id: str):
        """
        获取特定模型的详细信息

        实现 OpenAI Models API 的 retrieve 接口
        根据模型 ID 返回该模型的详细信息

        Args:
            model_id: 模型标识符（例如：gpt-3.5-turbo）

        Returns:
            Model: 模型详细信息

        Raises:
            HTTPException: 如果模型不存在，返回 404

        Example:
            GET /v1/models/gpt-3.5-turbo
            Response:
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai"
            }
        """
        logger.info(f"收到模型详情请求: model_id={model_id}")

        # 从配置中查找模型
        available_models = config.available_models
        model_config = None

        for m in available_models:
            if m["id"] == model_id:
                model_config = m
                break

        # 如果模型不存在，返回 404
        if model_config is None:
            logger.warning(f"模型不存在: {model_id}")
            raise HTTPException(
                status_code=404,
                detail=f"模型 '{model_id}' 不存在"
            )

        # 创建默认权限
        permission = ModelPermission(
            id=f"modelperm-{model_config['id']}",
            created=model_config.get("created", 0),
        )

        # 构建 Model 对象
        model = Model(
            id=model_config["id"],
            created=model_config.get("created", 0),
            owned_by=model_config.get("owned_by", "openai"),
            permission=[permission],
            root=model_config.get("id"),
            parent=None,
        )

        logger.info(f"返回模型详情: {model_id}")

        return JSONResponse(content=model.model_dump())

    # ==================== OpenAI 格式路由 ====================

    if config.openai_enabled:
        @app.post("/v1/chat/completions")
        async def openai_chat_completions(request: ChatCompletionRequest):
            """
            OpenAI Chat Completions API 兼容接口

            接收 OpenAI 格式的请求，转发到后端服务，返回 OpenAI 格式的响应。

            支持流式和非流式两种模式。

            Args:
                request: OpenAI ChatCompletionRequest 对象

            Returns:
                非流式：JSONResponse（OpenAI ChatCompletionResponse）
                流式：StreamingResponse（SSE 流）

            Raises:
                HTTPException: 请求处理失败
            """
            logger.info(f"收到 OpenAI 格式请求: model={request.model}, stream={request.stream}")

            # 创建 OpenAI 适配器
            adapter = OpenAIAdapter()

            # 使用通用处理函数处理请求
            return await handle_request(request, adapter)

        logger.info("OpenAI 格式路由已启用: /v1/chat/completions")

    # ==================== Anthropic 格式路由 ====================

    if config.anthropic_enabled:
        @app.post("/v1/messages")
        async def anthropic_messages(request: AnthropicMessagesRequest):
            """
            Anthropic Messages API 兼容接口

            接收 Anthropic 格式的请求，转换为内部格式，
            转发到后端服务（OpenAI 格式），再转换回 Anthropic 格式返回。

            支持流式和非流式两种模式。

            Anthropic 格式的特点：
            - system 字段独立于 messages
            - max_tokens 是必需参数
            - content 是数组格式
            - 流式响应有多种事件类型

            Args:
                request: Anthropic AnthropicMessagesRequest 对象

            Returns:
                非流式：JSONResponse（Anthropic MessagesResponse）
                流式：StreamingResponse（Anthropic SSE 流）

            Raises:
                HTTPException: 请求处理失败
            """
            logger.info(
                f"收到 Anthropic 格式请求: model={request.model}, "
                f"stream={request.stream}, max_tokens={request.max_tokens}"
            )

            # 创建 Anthropic 适配器
            adapter = AnthropicAdapter()

            # 使用通用处理函数处理请求
            return await handle_request(request, adapter)

        logger.info("Anthropic 格式路由已启用: /v1/messages")

    # ==================== 通用请求处理 ====================

    async def handle_request(request: Any, adapter: BaseAdapter):
        """
        通用请求处理函数

        实现适配器模式的核心逻辑：
        1. 请求适配：外部格式 → 内部格式
        2. 后端转发：内部格式 → 后端服务
        3. 响应适配：内部格式 → 外部格式

        Args:
            request: 外部格式的请求对象（Pydantic 模型）
            adapter: 适配器实例

        Returns:
            非流式：JSONResponse
            流式：StreamingResponse（SSE 流）

        Raises:
            HTTPException: 处理失败
        """
        try:
            # 步骤 1: 请求适配（外部格式 → 内部格式）
            internal_request = adapter.adapt_request(request)

            logger.debug(f"请求已适配为内部格式: {internal_request}")

            # 步骤 2: 后端转发（内部格式 → 后端服务）
            backend_response = await backend_proxy.forward(internal_request)

            # 步骤 3: 响应适配（内部格式 → 外部格式）
            if internal_request["stream"]:
                # 流式响应：返回 StreamingResponse
                logger.info("返回流式响应")

                return StreamingResponse(
                    adapter.adapt_streaming_response(backend_response),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    },
                )
            else:
                # 非流式响应：返回 JSONResponse
                external_response = adapter.adapt_response(backend_response)

                logger.info("返回非流式响应")

                # 将 Pydantic 模型转换为字典
                response_dict = external_response.model_dump()

                return JSONResponse(content=response_dict)

        except Exception as e:
            logger.error(f"处理请求时发生错误: {e}", exc_info=True)

            # 返回 HTTP 500 错误
            raise HTTPException(
                status_code=500,
                detail=f"处理请求失败: {str(e)}",
            )


# 创建默认应用实例（用于 uvicorn 启动）
app = create_app()
