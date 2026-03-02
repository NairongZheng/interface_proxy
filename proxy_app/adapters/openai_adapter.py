"""
OpenAI 格式适配器
实现 OpenAI Chat Completions API 格式与内部统一格式的双向转换
"""

import json
import time
import uuid
from typing import AsyncGenerator, List

from proxy_app.adapters.base_adapter import BaseAdapter
from proxy_app.models.common import (
    InternalMessage,
    InternalRequest,
    InternalResponse,
    InternalStreamChunk,
    InternalUsage,
)
from proxy_app.models.openai_models import (
    ChatCompletionChunk,
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    DeltaMessage,
    StreamChoice,
    Usage,
)


class OpenAIAdapter(BaseAdapter):
    """
    OpenAI 格式适配器

    由于 OpenAI 格式本身就是我们设计内部格式的参考，
    所以转换相对简单，主要是字段映射和格式规范化。
    """

    def adapt_request(self, request_data: ChatCompletionRequest) -> InternalRequest:
        """
        将 OpenAI 请求格式转换为内部统一格式

        OpenAI 格式与内部格式非常接近，主要工作是规范化消息格式

        Args:
            request_data: OpenAI ChatCompletionRequest 对象

        Returns:
            内部统一格式的请求字典
        """
        # 转换消息列表
        internal_messages: List[InternalMessage] = []
        for msg in request_data.messages:
            internal_msg: InternalMessage = {
                "role": msg.role,
                "content": msg.content or "",  # 确保 content 不为 None
            }

            # 处理工具调用
            if msg.tool_calls:
                internal_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]

            # 处理工具调用 ID（tool 角色）
            if msg.tool_call_id:
                internal_msg["tool_call_id"] = msg.tool_call_id

            # 处理消息名称
            if msg.name:
                internal_msg["name"] = msg.name

            internal_messages.append(internal_msg)

        # 处理停止序列
        stop_sequences = None
        if request_data.stop:
            if isinstance(request_data.stop, str):
                stop_sequences = [request_data.stop]
            else:
                stop_sequences = request_data.stop

        # 构建内部请求格式
        internal_request: InternalRequest = {
            "messages": internal_messages,
            "model": request_data.model,
            "stream": request_data.stream or False,
            "temperature": request_data.temperature,
            "max_tokens": request_data.max_tokens,
            "top_p": request_data.top_p,
            "stop": stop_sequences,
            "presence_penalty": request_data.presence_penalty,
            "frequency_penalty": request_data.frequency_penalty,
            "n": request_data.n,
            "user": request_data.user,
        }

        return internal_request

    def adapt_response(self, internal_response: InternalResponse) -> ChatCompletionResponse:
        """
        将内部统一格式转换为 OpenAI 响应格式（非流式）

        Args:
            internal_response: 内部格式响应字典

        Returns:
            OpenAI ChatCompletionResponse 对象
        """
        # 构建消息对象
        message = ChatCompletionMessage(
            role="assistant",
            content=internal_response.get("content"),
        )

        # 处理工具调用
        if internal_response.get("tool_calls"):
            from proxy_app.models.openai_models import ToolCall, ToolCallFunction
            message.tool_calls = [
                ToolCall(
                    id=tc["id"],
                    type=tc.get("type", "function"),
                    function=ToolCallFunction(
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"],
                    ),
                )
                for tc in internal_response["tool_calls"]
            ]

        # 处理推理内容（o1 系列模型）
        if internal_response.get("reasoning_content"):
            message.reasoning_content = internal_response["reasoning_content"]

        # 构建 Choice 对象
        choice = Choice(
            index=0,
            message=message,
            finish_reason=internal_response.get("finish_reason"),
        )

        # 构建 Usage 对象
        usage = None
        if internal_response.get("usage"):
            usage_data = internal_response["usage"]
            usage = Usage(
                prompt_tokens=usage_data["prompt_tokens"],
                completion_tokens=usage_data["completion_tokens"],
                total_tokens=usage_data["total_tokens"],
            )

        # 构建响应对象
        response = ChatCompletionResponse(
            id=internal_response["id"],
            created=internal_response["created"],
            model=internal_response["model"],
            choices=[choice],
            usage=usage,
        )

        return response

    async def adapt_streaming_response(
        self, internal_stream: AsyncGenerator[InternalStreamChunk, None]
    ) -> AsyncGenerator[str, None]:
        """
        将内部流式响应转换为 OpenAI SSE 格式

        OpenAI 流式格式说明：
        1. 每个数据块格式：data: {JSON}\n\n
        2. 最后发送：data: [DONE]\n\n

        Args:
            internal_stream: 内部格式的异步生成器

        Yields:
            OpenAI 格式的 SSE 数据块字符串
        """
        # 逐个处理内部流式块
        async for chunk in internal_stream:
            # 构建增量消息
            delta = DeltaMessage()

            # 第一个块通常包含 role
            if chunk.get("delta_role"):
                delta.role = chunk["delta_role"]

            # 增量内容
            if chunk.get("delta_content"):
                delta.content = chunk["delta_content"]

            # 增量工具调用
            if chunk.get("delta_tool_calls"):
                from proxy_app.models.openai_models import ToolCall, ToolCallFunction
                delta.tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        type=tc.get("type", "function"),
                        function=ToolCallFunction(
                            name=tc["function"]["name"],
                            arguments=tc["function"]["arguments"],
                        ),
                    )
                    for tc in chunk["delta_tool_calls"]
                ]

            # 增量推理内容
            if chunk.get("delta_reasoning_content"):
                delta.reasoning_content = chunk["delta_reasoning_content"]

            # 构建流式选择
            stream_choice = StreamChoice(
                index=0,
                delta=delta,
                finish_reason=chunk.get("finish_reason"),
            )

            # 构建 Usage（通常只在最后一个块出现）
            usage = None
            if chunk.get("usage"):
                usage_data = chunk["usage"]
                usage = Usage(
                    prompt_tokens=usage_data["prompt_tokens"],
                    completion_tokens=usage_data["completion_tokens"],
                    total_tokens=usage_data["total_tokens"],
                )

            # 构建流式块对象
            chunk_obj = ChatCompletionChunk(
                id=chunk["id"],
                created=chunk["created"],
                model=chunk["model"],
                choices=[stream_choice],
                usage=usage,
            )

            # 转换为 SSE 格式：data: {JSON}\n\n
            sse_data = f"data: {chunk_obj.model_dump_json()}\n\n"
            yield sse_data

        # 发送结束标记
        yield "data: [DONE]\n\n"

    def _generate_chat_completion_id(self) -> str:
        """
        生成 OpenAI 风格的 chat completion ID

        格式：chatcmpl-{随机字符串}

        Returns:
            生成的 ID
        """
        random_suffix = uuid.uuid4().hex[:20]
        return f"chatcmpl-{random_suffix}"

    def get_format_name(self) -> str:
        """获取格式名称"""
        return "openai"

    async def forward(self, internal_request: InternalRequest) -> InternalResponse:
        """
        转发请求到标准 OpenAI 后端（非流式）

        流程：
        1. 构造 OpenAI 请求格式
        2. 调用 /v1/chat/completions API
        3. 解析响应为内部格式

        Args:
            internal_request: 内部统一格式的请求

        Returns:
            内部统一格式的响应

        Raises:
            Exception: 后端调用失败
        """
        from proxy_app.utils.logger import logger

        # 构造 OpenAI 请求
        openai_request = self._build_openai_request(internal_request)

        # 调用 OpenAI 后端
        client = await self.get_client()
        url = f"{self.backend_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}

        # 添加 API Key（如果有）
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"调用 OpenAI 后端: {url}")
        logger.debug(f"OpenAI 请求参数: model={openai_request['model']}")

        try:
            response = await client.post(url, json=openai_request, headers=headers)
            response.raise_for_status()
            openai_response = response.json()

            logger.debug(f"OpenAI 响应状态码: {response.status_code}")

            # 解析为内部格式
            return self._parse_openai_response(openai_response)

        except Exception as e:
            logger.error(f"OpenAI 后端调用失败: {e}", exc_info=True)
            raise

    async def forward_stream(
        self, internal_request: InternalRequest
    ) -> AsyncGenerator[InternalStreamChunk, None]:
        """
        转发请求到标准 OpenAI 后端（流式）

        流程：
        1. 构造 OpenAI 请求格式（stream=true）
        2. 调用 /v1/chat/completions API
        3. 逐块解析 SSE 响应
        4. 转换为内部流式格式

        Args:
            internal_request: 内部统一格式的请求

        Yields:
            内部统一格式的流式响应块

        Raises:
            Exception: 后端调用失败
        """
        from proxy_app.utils.logger import logger

        # 构造 OpenAI 请求
        openai_request = self._build_openai_request(internal_request)

        # 调用 OpenAI 后端（流式）
        client = await self.get_client()
        url = f"{self.backend_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}

        # 添加 API Key（如果有）
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"调用 OpenAI 后端（流式）: {url}")
        logger.debug(f"OpenAI 请求参数: model={openai_request['model']}, stream=true")

        try:
            async with client.stream("POST", url, json=openai_request, headers=headers) as response:
                response.raise_for_status()

                # 读取 SSE 流
                async for line in response.aiter_lines():
                    line = line.strip()

                    # 跳过空行和注释
                    if not line or line.startswith(":"):
                        continue

                    # 解析 SSE 格式：data: {...}
                    if line.startswith("data: "):
                        data_str = line[6:]  # 去掉 "data: " 前缀

                        # 检查结束标记
                        if data_str == "[DONE]":
                            logger.debug("OpenAI 流式响应结束")
                            break

                        try:
                            # 解析 JSON 数据
                            openai_chunk = json.loads(data_str)

                            # 解析为内部流式格式
                            internal_chunk = self._parse_openai_stream_chunk(openai_chunk)

                            yield internal_chunk

                        except json.JSONDecodeError as e:
                            logger.warning(f"解析 OpenAI 流式数据失败: {e}, data: {data_str}")
                            continue

        except Exception as e:
            logger.error(f"OpenAI 流式调用失败: {e}", exc_info=True)
            raise

    def _build_openai_request(self, internal_request: InternalRequest) -> dict:
        """
        构造标准 OpenAI 请求格式

        Args:
            internal_request: 内部统一格式的请求

        Returns:
            OpenAI 格式的请求字典
        """
        openai_request = {
            "model": internal_request["model"],
            "messages": internal_request["messages"],
        }

        # 可选参数
        if "stream" in internal_request:
            openai_request["stream"] = internal_request["stream"]
        if "temperature" in internal_request and internal_request["temperature"] is not None:
            openai_request["temperature"] = internal_request["temperature"]
        if "max_tokens" in internal_request and internal_request["max_tokens"] is not None:
            openai_request["max_tokens"] = internal_request["max_tokens"]
        if "top_p" in internal_request and internal_request["top_p"] is not None:
            openai_request["top_p"] = internal_request["top_p"]
        if "stop" in internal_request and internal_request["stop"]:
            openai_request["stop"] = internal_request["stop"]
        if "presence_penalty" in internal_request and internal_request["presence_penalty"] is not None:
            openai_request["presence_penalty"] = internal_request["presence_penalty"]
        if "frequency_penalty" in internal_request and internal_request["frequency_penalty"] is not None:
            openai_request["frequency_penalty"] = internal_request["frequency_penalty"]
        if "n" in internal_request and internal_request["n"]:
            openai_request["n"] = internal_request["n"]
        if "user" in internal_request and internal_request["user"]:
            openai_request["user"] = internal_request["user"]

        return openai_request

    def _parse_openai_response(self, openai_response: dict) -> InternalResponse:
        """
        解析 OpenAI 格式响应为内部格式

        Args:
            openai_response: OpenAI 格式的响应

        Returns:
            内部统一格式的响应
        """
        # 提取关键信息
        choices = openai_response.get("choices", [])
        if not choices:
            raise ValueError("OpenAI 响应缺少 choices 字段")

        first_choice = choices[0]
        message = first_choice.get("message", {})

        # 构造内部格式
        internal_response: InternalResponse = {
            "id": openai_response.get("id", "unknown"),
            "created": openai_response.get("created", int(time.time())),
            "model": openai_response.get("model", "unknown"),
            "role": message.get("role", "assistant"),
            "content": message.get("content", ""),
            "finish_reason": first_choice.get("finish_reason"),
            "usage": openai_response.get("usage", {}),
        }

        # 可选字段
        if "reasoning_content" in message:
            internal_response["reasoning_content"] = message["reasoning_content"]
        if "tool_calls" in message:
            internal_response["tool_calls"] = message["tool_calls"]

        return internal_response

    def _parse_openai_stream_chunk(self, openai_chunk: dict) -> InternalStreamChunk:
        """
        解析 OpenAI 流式响应块为内部格式

        Args:
            openai_chunk: OpenAI 格式的流式响应块

        Returns:
            内部统一格式的流式响应块
        """
        choices = openai_chunk.get("choices", [])
        if not choices:
            return {
                "id": openai_chunk.get("id", "unknown"),
                "created": openai_chunk.get("created", int(time.time())),
                "model": openai_chunk.get("model", "unknown"),
                "delta_content": None,
                "delta_role": None,
                "finish_reason": None,
            }

        first_choice = choices[0]
        delta = first_choice.get("delta", {})

        # 构造内部流式格式
        internal_chunk: InternalStreamChunk = {
            "id": openai_chunk.get("id", "unknown"),
            "created": openai_chunk.get("created", int(time.time())),
            "model": openai_chunk.get("model", "unknown"),
            "delta_content": delta.get("content"),
            "delta_role": delta.get("role"),
            "finish_reason": first_choice.get("finish_reason"),
        }

        # 可选字段
        if "reasoning_content" in delta:
            internal_chunk["delta_reasoning_content"] = delta["reasoning_content"]
        if "tool_calls" in delta:
            internal_chunk["delta_tool_calls"] = delta["tool_calls"]
        if "usage" in openai_chunk:
            internal_chunk["usage"] = openai_chunk["usage"]

        return internal_chunk
