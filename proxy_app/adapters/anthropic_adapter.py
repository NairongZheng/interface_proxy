"""
Anthropic 格式适配器
实现 Anthropic Messages API 格式与内部统一格式的双向转换
"""

import json
import time
import uuid
from typing import AsyncGenerator, List

from proxy_app.adapters.base_adapter import BaseAdapter
from proxy_app.models.anthropic_models import (
    AnthropicMessage,
    AnthropicMessagesRequest,
    AnthropicMessagesResponse,
    AnthropicUsage,
    ContentBlock,
    TextContentBlock,
)
from proxy_app.models.common import (
    InternalMessage,
    InternalRequest,
    InternalResponse,
    InternalStreamChunk,
)


class AnthropicAdapter(BaseAdapter):
    """
    Anthropic 格式适配器

    Anthropic Messages API 与 OpenAI 格式的主要差异：
    1. system 字段独立于 messages
    2. max_tokens 是必需参数
    3. stop_sequences 而非 stop
    4. content 是数组格式 [{"type": "text", "text": "..."}]
    5. stop_reason 而非 finish_reason
    6. 流式响应有多种事件类型（message_start, content_block_delta 等）
    """

    def adapt_request(self, request_data: AnthropicMessagesRequest) -> InternalRequest:
        """
        将 Anthropic 请求格式转换为内部统一格式

        主要处理：
        1. 提取独立的 system 字段并合并到 messages
        2. 转换多模态 content 为纯文本
        3. 映射参数名（stop_sequences → stop）

        Args:
            request_data: Anthropic AnthropicMessagesRequest 对象

        Returns:
            内部统一格式的请求字典
        """
        internal_messages: List[InternalMessage] = []

        # 处理 system 字段
        # Anthropic 的 system 是独立字段，我们需要转为 system 角色的消息
        if request_data.system:
            system_msg: InternalMessage = {
                "role": "system",
                "content": request_data.system,
            }
            internal_messages.append(system_msg)

        # 转换消息列表
        for msg in request_data.messages:
            internal_msg: InternalMessage = {
                "role": msg.role,
                "content": self._extract_text_content(msg.content),
            }
            internal_messages.append(internal_msg)

        # 构建内部请求格式
        internal_request: InternalRequest = {
            "messages": internal_messages,
            "model": request_data.model,
            "stream": request_data.stream or False,
            "max_tokens": request_data.max_tokens,
            "temperature": request_data.temperature,
            "top_p": request_data.top_p,
        }

        # 映射 stop_sequences → stop
        if request_data.stop_sequences:
            internal_request["stop"] = request_data.stop_sequences

        return internal_request

    def _extract_text_content(self, content: str | List[ContentBlock]) -> str:
        """
        从多模态 content 中提取纯文本

        Anthropic 的 content 可以是：
        1. 字符串（纯文本）
        2. 内容块列表（包含 text 和 image 等）

        这里我们只提取文本部分，图片内容会被忽略（因为大多数后端不支持多模态）

        Args:
            content: Anthropic 的 content 字段

        Returns:
            提取的纯文本
        """
        # 如果是字符串，直接返回
        if isinstance(content, str):
            return content

        # 如果是列表，提取所有 text 类型的块
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                # 字典格式
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            elif hasattr(block, "type") and block.type == "text":
                # Pydantic 模型格式
                text_parts.append(block.text)

        return "\n".join(text_parts)

    def adapt_response(self, internal_response: InternalResponse) -> AnthropicMessagesResponse:
        """
        将内部统一格式转换为 Anthropic 响应格式（非流式）

        主要处理：
        1. content 包装为数组格式（可包含 text 和 thinking 类型）
        2. reasoning_content → thinking content block 转换
        3. finish_reason → stop_reason 映射
        4. usage 字段格式转换

        Args:
            internal_response: 内部格式响应字典

        Returns:
            Anthropic AnthropicMessagesResponse 对象
        """
        # 构建 content 块列表
        content_blocks = []

        # 如果有推理内容，先添加 thinking block
        if internal_response.get("reasoning_content"):
            from proxy_app.models.anthropic_models import ThinkingContentBlock
            content_blocks.append(
                ThinkingContentBlock(
                    type="thinking",
                    thinking=internal_response["reasoning_content"],
                )
            )

        # 添加文本内容 block
        content_blocks.append(
            TextContentBlock(
                type="text",
                text=internal_response.get("content", ""),
            )
        )

        # 映射 finish_reason → stop_reason
        stop_reason = self._map_finish_reason(internal_response.get("finish_reason"))

        # 构建 usage
        usage = None
        if internal_response.get("usage"):
            usage_data = internal_response["usage"]
            usage = AnthropicUsage(
                input_tokens=usage_data["prompt_tokens"],
                output_tokens=usage_data["completion_tokens"],
            )

        # 构建响应对象
        response = AnthropicMessagesResponse(
            id=internal_response["id"],
            role="assistant",
            content=content_blocks,
            model=internal_response["model"],
            stop_reason=stop_reason,
            usage=usage,
        )

        return response

    async def adapt_streaming_response(
        self, internal_stream: AsyncGenerator[InternalStreamChunk, None]
    ) -> AsyncGenerator[str, None]:
        """
        将内部流式响应转换为 Anthropic SSE 格式

        Anthropic 流式格式说明：
        1. 发送多种事件类型：message_start, content_block_start, content_block_delta,
           content_block_stop, message_delta, message_stop
        2. 每个事件格式：event: {type}\ndata: {JSON}\n\n

        事件序列（有推理内容时）：
        1. message_start - 消息开始
        2. content_block_start - thinking block 开始（索引 0）
        3. content_block_delta - 多个 thinking 增量
        4. content_block_stop - thinking block 结束
        5. content_block_start - text block 开始（索引 1）
        6. content_block_delta - 多个 text 增量
        7. content_block_stop - text block 结束
        8. message_delta - 消息增量（stop_reason 和 usage）
        9. message_stop - 消息结束

        Args:
            internal_stream: 内部格式的异步生成器

        Yields:
            Anthropic 格式的 SSE 事件字符串
        """
        # 标记状态
        message_started = False
        thinking_block_started = False
        thinking_block_stopped = False
        text_block_started = False

        # 存储消息信息
        message_id = None
        message_model = None
        message_created = None

        # 当前 content block 索引
        current_block_index = 0

        # 逐个处理内部流式块
        async for chunk in internal_stream:
            # 获取消息 ID（从第一个块）
            if message_id is None:
                message_id = chunk["id"]
                message_model = chunk["model"]
                message_created = chunk["created"]

                # 发送 message_start 事件
                yield self._format_sse_event(
                    "message_start",
                    {
                        "type": "message_start",
                        "message": {
                            "id": message_id,
                            "type": "message",
                            "role": "assistant",
                            "content": [],
                            "model": message_model,
                            "stop_reason": None,
                            "stop_sequence": None,
                            "usage": {"input_tokens": 0, "output_tokens": 0},
                        },
                    },
                )
                message_started = True

            # 处理推理内容（thinking block）
            if chunk.get("delta_reasoning_content"):
                # 发送 thinking block start（只发送一次）
                if not thinking_block_started:
                    yield self._format_sse_event(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": current_block_index,
                            "content_block": {"type": "thinking", "thinking": ""},
                        },
                    )
                    thinking_block_started = True

                # 发送 thinking block delta
                yield self._format_sse_event(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": current_block_index,
                        "delta": {
                            "type": "thinking_delta",
                            "thinking": chunk["delta_reasoning_content"],
                        },
                    },
                )

            # 处理文本内容（text block）
            if chunk.get("delta_content"):
                # 如果 thinking block 已开始但未结束，先结束它
                if thinking_block_started and not thinking_block_stopped:
                    yield self._format_sse_event(
                        "content_block_stop",
                        {"type": "content_block_stop", "index": current_block_index},
                    )
                    thinking_block_stopped = True
                    current_block_index += 1

                # 发送 text block start（只发送一次）
                if not text_block_started:
                    yield self._format_sse_event(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": current_block_index,
                            "content_block": {"type": "text", "text": ""},
                        },
                    )
                    text_block_started = True

                # 发送 text block delta
                yield self._format_sse_event(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": current_block_index,
                        "delta": {"type": "text_delta", "text": chunk["delta_content"]},
                    },
                )

            # 如果是最后一个块（有 finish_reason）
            if chunk.get("finish_reason"):
                # 结束当前的 content block
                if thinking_block_started and not thinking_block_stopped:
                    # 只有 thinking block，没有 text block
                    yield self._format_sse_event(
                        "content_block_stop",
                        {"type": "content_block_stop", "index": current_block_index},
                    )
                elif text_block_started:
                    # 结束 text block
                    yield self._format_sse_event(
                        "content_block_stop",
                        {"type": "content_block_stop", "index": current_block_index},
                    )

                # 映射 finish_reason → stop_reason
                stop_reason = self._map_finish_reason(chunk["finish_reason"])

                # 构建 usage
                usage_data = {"input_tokens": 0, "output_tokens": 0}
                if chunk.get("usage"):
                    usage_data = {
                        "input_tokens": chunk["usage"]["prompt_tokens"],
                        "output_tokens": chunk["usage"]["completion_tokens"],
                    }

                # 发送 message_delta
                yield self._format_sse_event(
                    "message_delta",
                    {
                        "type": "message_delta",
                        "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                        "usage": {"output_tokens": usage_data["output_tokens"]},
                    },
                )

        # 发送 message_stop 事件
        yield self._format_sse_event("message_stop", {"type": "message_stop"})

    def _format_sse_event(self, event_type: str, data: dict) -> str:
        """
        格式化 SSE 事件

        Anthropic SSE 格式：
        event: {type}
        data: {JSON}

        (空行)

        Args:
            event_type: 事件类型
            data: 事件数据（字典）

        Returns:
            格式化的 SSE 事件字符串
        """
        data_json = json.dumps(data, ensure_ascii=False)
        return f"event: {event_type}\ndata: {data_json}\n\n"

    def _map_finish_reason(self, finish_reason: str | None) -> str | None:
        """
        映射 finish_reason 到 Anthropic 的 stop_reason

        映射关系：
        - stop → end_turn
        - length → max_tokens
        - tool_calls → end_turn
        - content_filter → end_turn
        - None → None

        Args:
            finish_reason: OpenAI 的 finish_reason

        Returns:
            Anthropic 的 stop_reason
        """
        if finish_reason is None:
            return None

        mapping = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "end_turn",
            "content_filter": "end_turn",
        }

        return mapping.get(finish_reason, "end_turn")

    def get_format_name(self) -> str:
        """获取格式名称"""
        return "anthropic"
