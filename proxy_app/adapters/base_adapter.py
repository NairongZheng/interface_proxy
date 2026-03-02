"""
适配器基类模块
定义所有格式适配器的统一接口
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional
import httpx

from proxy_app.models.common import InternalRequest, InternalResponse, InternalStreamChunk


class BaseAdapter(ABC):
    """
    适配器抽象基类

    所有格式适配器都需要继承此类并实现核心方法：
    1. adapt_request: 外部格式 → 内部格式
    2. adapt_response: 内部格式 → 外部格式（非流式）
    3. adapt_streaming_response: 内部格式 → 外部格式（流式）
    4. forward: 调用后端服务（每个后端的调用方式可能不同）

    适配器模式的核心思想：
    - 定义统一的内部格式，避免 N×N 格式转换
    - 每个适配器知道如何调用自己的后端服务
    - 适配器之间完全解耦，互不影响
    """

    def __init__(self, backend_url: str = None, api_key: str = None, timeout: float = 600.0):
        """
        初始化适配器

        Args:
            backend_url: 后端服务 URL
            api_key: API Key（如果需要）
            timeout: 请求超时时间（秒）
        """
        self.backend_url = backend_url
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    def adapt_request(self, request_data: Any) -> InternalRequest:
        """
        将外部请求格式转换为内部统一格式

        这是适配器的核心方法之一，负责将各种外部 API 格式（OpenAI、Anthropic 等）
        转换为统一的内部格式，以便后续处理。

        Args:
            request_data: 外部格式的请求数据
                - 可以是 Pydantic 模型实例（推荐）
                - 也可以是字典

        Returns:
            内部统一格式的请求字典，包含以下标准字段：
                - messages: List[InternalMessage] 消息列表
                - model: str 模型名称
                - stream: bool 是否流式输出
                - temperature: Optional[float] 温度参数
                - max_tokens: Optional[int] 最大 token 数
                - top_p: Optional[float] top_p 参数
                - stop: Optional[List[str]] 停止序列
                - 其他可选参数

        Examples:
            >>> adapter = OpenAIAdapter()
            >>> request = ChatCompletionRequest(...)
            >>> internal = adapter.adapt_request(request)
            >>> print(internal["messages"])
            [{"role": "user", "content": "Hello"}]
        """
        pass

    @abstractmethod
    def adapt_response(
        self,
        internal_response: InternalResponse
    ) -> Any:
        """
        将内部统一格式转换为外部响应格式（非流式）

        这是适配器的第二个核心方法，负责将内部统一格式的响应
        转换为特定外部 API 的格式。

        Args:
            internal_response: 内部格式响应字典，包含：
                - id: str 响应 ID
                - created: int 创建时间戳
                - model: str 模型名称
                - content: str 生成的内容
                - role: str 角色
                - finish_reason: str 结束原因
                - usage: dict token 使用统计
                - 其他可选字段

        Returns:
            外部格式的响应对象（通常是 Pydantic 模型实例）

        Examples:
            >>> adapter = OpenAIAdapter()
            >>> internal = {"id": "chatcmpl-123", "content": "Hello!", ...}
            >>> response = adapter.adapt_response(internal)
            >>> print(type(response))
            <class 'ChatCompletionResponse'>
        """
        pass

    @abstractmethod
    async def adapt_streaming_response(
        self,
        internal_stream: AsyncGenerator[InternalStreamChunk, None]
    ) -> AsyncGenerator[str, None]:
        """
        将内部流式响应转换为外部流式格式

        这是适配器的第三个核心方法，负责将内部统一格式的流式响应
        转换为特定外部 API 的 SSE（Server-Sent Events）格式。

        不同的 API 有不同的 SSE 格式：
        - OpenAI: 简单的 "data: {...}\n\n" 格式，最后发送 "data: [DONE]\n\n"
        - Anthropic: 复杂的事件流，包含 message_start, content_block_delta 等多种事件

        Args:
            internal_stream: 内部统一格式的异步生成器
                每个 yield 的数据块包含：
                - id: str 响应 ID
                - delta_content: Optional[str] 增量内容
                - delta_role: Optional[str] 增量角色
                - finish_reason: Optional[str] 结束原因
                - 其他可选字段

        Yields:
            外部格式的 SSE 数据块（字符串），包含换行符
            例如：
            - OpenAI: "data: {...}\n\n"
            - Anthropic: "event: content_block_delta\ndata: {...}\n\n"

        Examples:
            >>> adapter = OpenAIAdapter()
            >>> async for chunk in adapter.adapt_streaming_response(internal_stream):
            ...     print(chunk)
            data: {"id": "chatcmpl-123", "choices": [...]}

            data: [DONE]
        """
        pass

    def validate_request(self, request_data: Any) -> bool:
        """
        验证请求数据的有效性（可选实现）

        子类可以重写此方法以添加额外的请求验证逻辑

        Args:
            request_data: 外部格式的请求数据

        Returns:
            验证是否通过

        Raises:
            ValueError: 验证失败时抛出异常
        """
        return True

    def get_format_name(self) -> str:
        """
        获取适配器支持的格式名称

        Returns:
            格式名称（例如：'openai', 'anthropic'）
        """
        return self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    async def forward(self, internal_request: InternalRequest) -> InternalResponse:
        """
        转发请求到后端服务（非流式）

        每个适配器知道如何调用自己的后端：
        - OpenAIAdapter: 调用标准 OpenAI API
        - PTUAdapter: 调用 PTU Gateway API
        - AnthropicAdapter: 可以转换后调用 OpenAI 后端，或直接调用 Anthropic 后端

        Args:
            internal_request: 内部统一格式的请求

        Returns:
            内部统一格式的响应

        Raises:
            Exception: 后端调用失败
        """
        pass

    @abstractmethod
    async def forward_stream(
        self, internal_request: InternalRequest
    ) -> AsyncGenerator[InternalStreamChunk, None]:
        """
        转发请求到后端服务（流式）

        Args:
            internal_request: 内部统一格式的请求

        Yields:
            内部统一格式的流式响应块

        Raises:
            Exception: 后端调用失败
        """
        pass
