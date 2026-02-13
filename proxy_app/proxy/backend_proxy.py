"""
后端代理模块
负责将请求转发到后端模型服务，并解析响应
"""

import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

from proxy_app.models.common import (
    InternalMessage,
    InternalRequest,
    InternalResponse,
    InternalStreamChunk,
    InternalUsage,
)
from proxy_app.utils.http_client import parse_sse_line
from proxy_app.utils.logger import logger


class BackendProxy:
    """
    后端代理类

    职责：
    1. 管理与后端服务的 HTTP 连接（httpx.AsyncClient）
    2. 将内部格式转换为后端接口格式（假设后端是 OpenAI 格式）
    3. 解析后端响应为内部格式
    4. 处理流式和非流式两种模式
    5. 错误处理和超时管理
    """

    def __init__(
        self,
        backend_url: str,
        timeout: float = 600.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
    ):
        """
        初始化后端代理

        Args:
            backend_url: 后端服务地址（例如：http://127.0.0.1:8000）
            timeout: 请求超时时间（秒）
            max_connections: 连接池最大连接数
            max_keepalive_connections: 连接池最大保活连接数
        """
        self.backend_url = backend_url.rstrip("/")  # 移除末尾的斜杠
        self.timeout = timeout

        # 初始化 httpx 异步客户端和连接池
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
        )

        logger.info(
            f"后端代理已初始化: backend_url={backend_url}, "
            f"timeout={timeout}s, max_connections={max_connections}"
        )

    async def forward(
        self, internal_request: InternalRequest
    ) -> InternalResponse | AsyncGenerator[InternalStreamChunk, None]:
        """
        转发请求到后端服务（主入口）

        根据请求的 stream 参数决定使用流式或非流式处理

        Args:
            internal_request: 内部统一格式的请求

        Returns:
            如果是非流式：返回内部格式响应字典
            如果是流式：返回内部格式流式块的异步生成器

        Raises:
            httpx.HTTPError: HTTP 请求失败
            ValueError: 后端响应格式错误
        """
        # 判断是否流式
        is_stream = internal_request.get("stream", False)

        logger.info(
            f"转发请求到后端: model={internal_request['model']}, "
            f"stream={is_stream}, messages_count={len(internal_request['messages'])}"
        )

        # 根据 stream 参数选择处理方式
        if is_stream:
            return self._forward_streaming(internal_request)
        else:
            return await self._forward_non_streaming(internal_request)

    def _convert_to_backend_format(self, internal_request: InternalRequest) -> Dict[str, Any]:
        """
        将内部格式转换为后端接口格式

        假设后端服务提供 OpenAI 格式的 /v1/chat/completions 接口，
        所以这里转换为 OpenAI 格式。

        如果您的后端使用其他格式，可以修改此方法。

        Args:
            internal_request: 内部统一格式的请求

        Returns:
            后端接口格式的请求字典（OpenAI 格式）
        """
        # 转换消息格式
        backend_messages = []
        for msg in internal_request["messages"]:
            backend_msg = {
                "role": msg["role"],
                "content": msg.get("content", ""),
            }

            # 处理工具调用
            if msg.get("tool_calls"):
                backend_msg["tool_calls"] = msg["tool_calls"]

            # 处理工具调用 ID
            if msg.get("tool_call_id"):
                backend_msg["tool_call_id"] = msg["tool_call_id"]

            # 处理消息名称
            if msg.get("name"):
                backend_msg["name"] = msg["name"]

            backend_messages.append(backend_msg)

        # 构建后端请求（OpenAI 格式）
        backend_request = {
            "model": internal_request["model"],
            "messages": backend_messages,
            "stream": internal_request.get("stream", False),
        }

        # 添加可选参数
        optional_params = [
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "presence_penalty",
            "frequency_penalty",
            "n",
            "user",
            "tools",  # 新增：转发工具定义到后端
        ]

        for param in optional_params:
            value = internal_request.get(param)
            if value is not None:
                backend_request[param] = value

        return backend_request

    async def _forward_non_streaming(
        self, internal_request: InternalRequest
    ) -> InternalResponse:
        """
        处理非流式请求

        Args:
            internal_request: 内部格式请求

        Returns:
            内部格式响应

        Raises:
            httpx.HTTPError: HTTP 请求失败
            ValueError: 响应格式错误
        """
        # 转换为后端格式
        backend_request = self._convert_to_backend_format(internal_request)

        # 构建后端 URL
        backend_endpoint = f"{self.backend_url}/v1/chat/completions"

        try:
            # 发送 POST 请求到后端
            response = await self._http_client.post(
                backend_endpoint,
                json=backend_request,
                headers={"Content-Type": "application/json"},
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析 JSON 响应
            backend_response = response.json()

            # 转换为内部格式
            internal_response = self._parse_backend_response(backend_response)

            logger.info(
                f"非流式请求完成: id={internal_response['id']}, "
                f"finish_reason={internal_response.get('finish_reason')}"
            )

            return internal_response

        except httpx.HTTPStatusError as e:
            logger.error(f"后端返回错误状态: {e.response.status_code}, {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"请求后端失败: {e}")
            raise
        except Exception as e:
            logger.error(f"处理非流式请求时发生错误: {e}")
            raise

    async def _forward_streaming(
        self, internal_request: InternalRequest
    ) -> AsyncGenerator[InternalStreamChunk, None]:
        """
        处理流式请求

        Args:
            internal_request: 内部格式请求

        Yields:
            内部格式的流式块

        Raises:
            httpx.HTTPError: HTTP 请求失败
            ValueError: 响应格式错误
        """
        # 转换为后端格式
        backend_request = self._convert_to_backend_format(internal_request)

        # 构建后端 URL
        backend_endpoint = f"{self.backend_url}/v1/chat/completions"

        try:
            # 使用 stream 上下文管理器建立流式连接
            async with self._http_client.stream(
                "POST",
                backend_endpoint,
                json=backend_request,
                headers={"Content-Type": "application/json"},
            ) as response:
                # 检查响应状态
                response.raise_for_status()

                logger.info("流式连接已建立，开始接收数据块")

                # 逐行读取 SSE 数据
                async for line in response.aiter_lines():
                    # 跳过空行
                    if not line or line.isspace():
                        continue

                    # 解析 SSE 行
                    parsed = parse_sse_line(line)
                    if not parsed or "data" not in parsed:
                        continue

                    data_str = parsed["data"]

                    # 检查是否是结束标记
                    if data_str == "[DONE]":
                        logger.info("流式响应结束")
                        break

                    # 解析 JSON 数据
                    try:
                        chunk_data = json.loads(data_str)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析 JSON 块失败: {e}, data={data_str}")
                        continue

                    # 转换为内部格式
                    internal_chunk = self._parse_backend_chunk(chunk_data)

                    # 生成内部格式块
                    yield internal_chunk

        except httpx.HTTPStatusError as e:
            logger.error(f"后端返回错误状态: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"请求后端失败: {e}")
            raise
        except Exception as e:
            logger.error(f"处理流式请求时发生错误: {e}")
            raise

    def _parse_backend_response(self, backend_response: Dict[str, Any]) -> InternalResponse:
        """
        解析后端响应（OpenAI 格式）为内部格式

        Args:
            backend_response: 后端响应字典（OpenAI ChatCompletionResponse）

        Returns:
            内部格式响应

        Raises:
            ValueError: 响应格式不正确
        """
        try:
            # 提取第一个 choice（通常只有一个）
            choice = backend_response["choices"][0]
            message = choice["message"]

            # 构建内部响应
            internal_response: InternalResponse = {
                "id": backend_response["id"],
                "created": backend_response["created"],
                "model": backend_response["model"],
                "content": message.get("content", ""),
                "role": message.get("role", "assistant"),
                "finish_reason": choice.get("finish_reason"),
            }

            # 处理工具调用
            if message.get("tool_calls"):
                internal_response["tool_calls"] = message["tool_calls"]

            # 处理推理内容
            if message.get("reasoning_content"):
                internal_response["reasoning_content"] = message["reasoning_content"]

            # 处理 usage
            if backend_response.get("usage"):
                usage = backend_response["usage"]
                internal_response["usage"] = {
                    "prompt_tokens": usage["prompt_tokens"],
                    "completion_tokens": usage["completion_tokens"],
                    "total_tokens": usage["total_tokens"],
                }

            return internal_response

        except (KeyError, IndexError) as e:
            logger.error(f"解析后端响应失败: {e}, response={backend_response}")
            raise ValueError(f"后端响应格式不正确: {e}")

    def _parse_backend_chunk(self, chunk_data: Dict[str, Any]) -> InternalStreamChunk:
        """
        解析后端流式块（OpenAI 格式）为内部格式

        Args:
            chunk_data: 后端流式块字典（OpenAI ChatCompletionChunk）

        Returns:
            内部格式流式块

        Raises:
            ValueError: 块格式不正确
        """
        try:
            # 提取第一个 choice
            choice = chunk_data["choices"][0]
            delta = choice.get("delta", {})

            # 构建内部流式块
            internal_chunk: InternalStreamChunk = {
                "id": chunk_data["id"],
                "created": chunk_data["created"],
                "model": chunk_data["model"],
            }

            # 处理增量字段
            if "role" in delta:
                internal_chunk["delta_role"] = delta["role"]

            if "content" in delta:
                internal_chunk["delta_content"] = delta["content"]

            if "tool_calls" in delta:
                internal_chunk["delta_tool_calls"] = delta["tool_calls"]

            if "reasoning_content" in delta:
                internal_chunk["delta_reasoning_content"] = delta["reasoning_content"]

            # 处理结束原因
            if choice.get("finish_reason"):
                internal_chunk["finish_reason"] = choice["finish_reason"]

            # 处理 usage（通常在最后一个块）
            if chunk_data.get("usage"):
                usage = chunk_data["usage"]
                internal_chunk["usage"] = {
                    "prompt_tokens": usage["prompt_tokens"],
                    "completion_tokens": usage["completion_tokens"],
                    "total_tokens": usage["total_tokens"],
                }

            return internal_chunk

        except (KeyError, IndexError) as e:
            logger.error(f"解析后端流式块失败: {e}, chunk={chunk_data}")
            raise ValueError(f"后端流式块格式不正确: {e}")

    async def close(self):
        """
        关闭 HTTP 客户端连接

        在应用关闭时调用，释放资源
        """
        await self._http_client.aclose()
        logger.info("后端代理连接已关闭")
