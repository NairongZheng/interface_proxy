"""
FastAPI 应用和路由模块
定义代理服务的 HTTP 接口
"""

from typing import Any, Optional
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from proxy_app.adapters.base_adapter import BaseAdapter
from proxy_app.adapters.anthropic_adapter import AnthropicAdapter
from proxy_app.adapters.openai_adapter import OpenAIAdapter
from proxy_app.adapters.ptu_adapter import PTUAdapter
from proxy_app.config import Config
from proxy_app.models.anthropic_models import AnthropicMessagesRequest
from proxy_app.models.openai_models import (
    ChatCompletionRequest,
    Model,
    ModelList,
    ModelPermission,
)
from proxy_app.utils.logger import logger, setup_logger
from proxy_app.monitoring.simple_stats import get_collector


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

    # 添加统计中间件
    @app.middleware("http")
    async def stats_middleware(request: Request, call_next):
        """
        统计中间件 - 只递增计数器，极速处理

        监控 /v1/chat/completions 路径的请求，记录模型使用情况和成功/失败状态
        """
        # 只监控 /v1/chat/completions 路径
        if not request.url.path.startswith("/v1/chat/completions"):
            return await call_next(request)

        # 提取模型信息
        model = "unknown"
        if request.method == "POST":
            try:
                # 读取请求体
                body = await request.body()
                data = json.loads(body)
                model = data.get("model", "unknown")

                # 重新设置 body 供后续读取
                # 因为 request.body() 只能读取一次，需要保存以便后续处理
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except Exception as e:
                logger.warning(f"解析请求体失败: {e}")

        # 调用下游处理
        status = "error"
        try:
            response = await call_next(request)
            # 根据 HTTP 状态码判断成功或失败
            status = "success" if response.status_code < 400 else "error"
            return response
        except Exception:
            status = "error"
            raise
        finally:
            # 记录统计（只递增计数器，极快）
            collector = get_collector()
            collector.record(model, status)

    # 注册启动和关闭事件
    @app.on_event("startup")
    async def startup_event():
        """
        应用启动事件

        新架构中，Adapter 自己管理 HTTP 客户端，无需全局初始化
        """
        logger.info("应用启动完成")

    @app.on_event("shutdown")
    async def shutdown_event():
        """
        应用关闭时清理资源
        """
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
            "version": "1.1.0",
            "description": "LLM 接口代理服务，支持多格式转换和 PTU 后端",
            "features": [
                "OpenAI 格式接口 (/v1/chat/completions)",
                "Anthropic 格式接口 (/v1/messages)",
                "PTU 后端自动识别和处理",
                "多模型支持 (30+ PTU 模型)",
                "流式和非流式响应",
            ],
            "endpoints": {
                "health": "/health",
                "openai_chat": "/v1/chat/completions" if config.openai_enabled else None,
                "anthropic_messages": "/v1/messages" if config.anthropic_enabled else None,
                "models_list": "/v1/models",
                "model_names_simple": "/v1/model-names",
                "model_detail": "/v1/models/{model_id}",
            },
            "backend": {
                "url": config.backend_url,
                "ptu_enabled": len(config.ptu_models) > 0,
                "ptu_models_count": len(config.ptu_models),
            },
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
        根据配置文件返回当前后端支持的所有模型

        模型来源：
        - 从 config.yaml 的 models.available_models 读取
        - 包含标准模型和 PTU 模型
        - 可通过修改配置文件来调整暴露的模型列表

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

        # 从配置中获取模型列表（根据后端类型过滤）
        available_models = config.get_available_models_by_backend()

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

        # 统计 PTU 模型数量
        ptu_model_ids = set(config.ptu_models)
        ptu_count = sum(1 for m in available_models if m["id"] in ptu_model_ids)

        logger.info(
            f"返回 {len(models)} 个可用模型 "
            f"(后端类型: {config.backend_type}, PTU模型: {ptu_count}, 其他模型: {len(models) - ptu_count})"
        )

        return JSONResponse(content=model_list.model_dump())

    @app.get("/v1/model-names")
    async def list_model_names():
        """
        列出所有可用模型的名称（简化版）

        只返回模型 ID 列表，不包含详细信息
        适用于需要快速获取模型列表的场景

        Returns:
            dict: 包含模型名称列表的字典

        Example:
            GET /v1/model-names
            Response:
            {
                "models": ["gpt-3.5-turbo", "gpt-4", "Doubao-1.5-pro-32k", ...],
                "count": 42
            }
        """
        logger.info("收到简化模型列表请求")

        # 从配置中获取模型列表（根据后端类型过滤）
        available_models = config.get_available_models_by_backend()

        # 只提取模型 ID
        model_names = [model_config["id"] for model_config in available_models]

        logger.info(f"返回 {len(model_names)} 个模型名称")

        return JSONResponse(content={
            "models": model_names,
            "count": len(model_names)
        })

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

        # 从配置中查找模型（根据后端类型过滤）
        available_models = config.get_available_models_by_backend()
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

            自动识别模型类型并选择合适的适配器：
            - PTU 模型：使用 PTUAdapter（处理 PTU 包装格式）
            - 标准模型：使用 OpenAIAdapter（标准 OpenAI 格式）

            对用户完全透明，统一使用 OpenAI 接口调用。

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

            # 根据模型选择适配器
            if config.is_ptu_model(request.model):
                logger.info(f"模型 {request.model} 为 PTU 模型，使用 PTUAdapter")
                # PTU 使用特定的 backend_url
                backend_url = config.ptu_backend_url or config.backend_url
                adapter = PTUAdapter(
                    backend_url=backend_url,
                    api_key=config.backend_api_key,
                    timeout=config.backend_timeout,
                )
            else:
                logger.info(f"模型 {request.model} 为标准模型，使用 OpenAIAdapter")
                adapter = OpenAIAdapter(
                    backend_url=config.backend_url,
                    api_key=config.backend_api_key,
                    timeout=config.backend_timeout,
                )

            # 使用通用处理函数处理请求
            return await handle_request(request, adapter, config)

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
            # Anthropic 目前转换为 OpenAI 格式后调用后端
            adapter = AnthropicAdapter(
                backend_url=config.backend_url,
                api_key=config.backend_api_key,
                timeout=config.backend_timeout,
            )

            # 使用通用处理函数处理请求
            return await handle_request(request, adapter, config)

        logger.info("Anthropic 格式路由已启用: /v1/messages")

    # ==================== 统计路由 ====================

    @app.get("/api/stats")
    async def get_statistics(
        time_range: str = "24h",
        model: Optional[str] = None
    ):
        """
        获取流量统计

        查询指定时间范围内的请求统计数据，支持按模型过滤

        Args:
            time_range: 时间范围（24h/7d/30d），默认 24h
            model: 模型过滤（可选），为空时返回所有模型

        Returns:
            统计数据字典，包含：
            - time_range: 时间范围
            - total_requests: 总请求数
            - success_count: 成功数
            - error_count: 失败数
            - by_model: 按模型分组的详细统计

        示例：
            GET /api/stats?time_range=24h
            GET /api/stats?time_range=7d&model=gpt-4
        """
        collector = get_collector()
        return collector.get_stats(time_range=time_range, model=model)

    @app.get("/api/stats/models")
    async def get_model_list():
        """
        获取所有使用过的模型列表

        返回最近 30 天内所有被请求过的模型名称

        Returns:
            模型列表字典，包含：
            - models: 模型名称列表
            - count: 模型数量

        示例：
            GET /api/stats/models
        """
        collector = get_collector()
        stats = collector.get_stats(time_range="30d")
        models = [item["model"] for item in stats["by_model"]]
        return {"models": models, "count": len(models)}

    logger.info("统计路由已启用: /api/stats, /api/stats/models")

    # ==================== 通用请求处理 ====================

    async def handle_request(request: Any, adapter: BaseAdapter, config: Config):
        """
        通用请求处理函数

        新架构实现：
        1. 请求适配：外部格式 → 内部格式
        2. 后端调用：Adapter 直接调用后端（forward/forward_stream）
        3. 响应适配：内部格式 → 外部格式

        Args:
            request: 外部格式的请求对象（Pydantic 模型）
            adapter: 适配器实例（已初始化 backend_url 和 api_key）
            config: 配置对象

        Returns:
            非流式：JSONResponse
            流式：StreamingResponse（SSE 流）

        Raises:
            HTTPException: 处理失败
        """
        try:
            # 步骤 1: 请求适配（外部格式 → 内部格式）
            internal_request = adapter.adapt_request(request)

            logger.debug(f"请求已适配为内部格式: model={internal_request['model']}, stream={internal_request['stream']}")

            # 步骤 2: 后端调用（Adapter 自己负责调用后端）
            if internal_request["stream"]:
                # 流式响应
                internal_stream = adapter.forward_stream(internal_request)
                external_stream = adapter.adapt_streaming_response(internal_stream)

                logger.info("返回流式响应")

                return StreamingResponse(
                    external_stream,
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    },
                )
            else:
                # 非流式响应
                internal_response = await adapter.forward(internal_request)

                # 步骤 3: 响应适配（内部格式 → 外部格式）
                external_response = adapter.adapt_response(internal_response)

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
