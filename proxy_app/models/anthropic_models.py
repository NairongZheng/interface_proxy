"""
Anthropic Messages API 数据模型定义
定义 Anthropic Messages API 的请求和响应格式
参考：https://docs.anthropic.com/claude/reference/messages_post
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ==================== 内容块相关模型 ====================

class TextContentBlock(BaseModel):
    """
    文本内容块

    Attributes:
        type: 内容类型（text）
        text: 文本内容
    """
    type: Literal["text"] = "text"
    text: str


class ImageSource(BaseModel):
    """
    图片来源

    Attributes:
        type: 来源类型（base64 或 url）
        media_type: 媒体类型（例如：image/jpeg）
        data: base64 编码的图片数据（type=base64 时使用）
        url: 图片 URL（type=url 时使用）
    """
    type: Literal["base64", "url"]
    media_type: str
    data: Optional[str] = None
    url: Optional[str] = None


class ImageContentBlock(BaseModel):
    """
    图片内容块

    Attributes:
        type: 内容类型（image）
        source: 图片来源
    """
    type: Literal["image"] = "image"
    source: ImageSource


class ThinkingContentBlock(BaseModel):
    """
    推理内容块（用于显示模型的推理过程）

    Claude 3.5 Sonnet 及更新版本支持 extended thinking 功能，
    可以在响应中包含模型的推理过程。

    Attributes:
        type: 内容类型（thinking）
        thinking: 推理过程内容
    """
    type: Literal["thinking"] = "thinking"
    thinking: str


# 内容块可以是文本、图片或推理
ContentBlock = Union[TextContentBlock, ImageContentBlock, ThinkingContentBlock]


# ==================== 消息相关模型 ====================

class AnthropicMessage(BaseModel):
    """
    Anthropic 消息格式

    Attributes:
        role: 消息角色（user 或 assistant）
        content: 消息内容（字符串或内容块列表）
    """
    role: Literal["user", "assistant"]
    content: Union[str, List[ContentBlock]]


# ==================== 请求模型 ====================

class AnthropicMessagesRequest(BaseModel):
    """
    Anthropic Messages API 请求模型

    Attributes:
        model: 模型名称（例如：claude-3-opus-20240229）
        messages: 消息列表
        max_tokens: 最大生成 token 数（必需）
        system: 系统提示（可选，独立于 messages）
        temperature: 温度参数（0-1），控制随机性
        top_p: nucleus sampling 参数（0-1）
        top_k: top-k sampling 参数
        stop_sequences: 停止序列列表
        stream: 是否流式输出
        metadata: 元数据（可选）
    """
    model: str
    messages: List[AnthropicMessage]
    max_tokens: int = Field(..., ge=1)  # 必需参数
    system: Optional[str] = None
    temperature: Optional[float] = Field(default=1.0, ge=0, le=1)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    top_k: Optional[int] = Field(default=None, ge=1)
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        # 允许额外字段
        extra = "allow"


# ==================== 响应模型 ====================

class AnthropicUsage(BaseModel):
    """
    Token 使用统计

    Attributes:
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
    """
    input_tokens: int
    output_tokens: int


class AnthropicMessagesResponse(BaseModel):
    """
    Anthropic Messages API 响应模型

    Attributes:
        id: 响应的唯一标识符
        type: 响应类型（message）
        role: 响应角色（assistant）
        content: 内容块列表（可包含 text, image, thinking 等类型）
        model: 使用的模型名称
        stop_reason: 停止原因（end_turn, max_tokens, stop_sequence）
        stop_sequence: 实际匹配的停止序列（可选）
        usage: token 使用统计
    """
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextContentBlock, ThinkingContentBlock]]
    model: str
    stop_reason: Optional[Literal["end_turn", "max_tokens", "stop_sequence"]] = None
    stop_sequence: Optional[str] = None
    usage: AnthropicUsage


# ==================== 流式响应事件模型 ====================

class MessageStartEvent(BaseModel):
    """
    消息开始事件

    Attributes:
        type: 事件类型（message_start）
        message: 消息对象（包含 id, model, role 等元信息）
    """
    type: Literal["message_start"] = "message_start"
    message: Dict[str, Any]  # 包含 id, type, role, content, model 等


class ContentBlockStartEvent(BaseModel):
    """
    内容块开始事件

    Attributes:
        type: 事件类型（content_block_start）
        index: 内容块索引
        content_block: 内容块对象（可以是 text 或 thinking 类型）
    """
    type: Literal["content_block_start"] = "content_block_start"
    index: int
    content_block: Union[TextContentBlock, ThinkingContentBlock]


class ContentBlockDeltaEvent(BaseModel):
    """
    内容块增量事件

    Attributes:
        type: 事件类型（content_block_delta）
        index: 内容块索引
        delta: 增量数据
    """
    type: Literal["content_block_delta"] = "content_block_delta"
    index: int
    delta: Dict[str, Any]  # 包含 type 和 text


class ContentBlockStopEvent(BaseModel):
    """
    内容块停止事件

    Attributes:
        type: 事件类型（content_block_stop）
        index: 内容块索引
    """
    type: Literal["content_block_stop"] = "content_block_stop"
    index: int


class MessageDeltaEvent(BaseModel):
    """
    消息增量事件

    Attributes:
        type: 事件类型（message_delta）
        delta: 增量数据（包含 stop_reason, stop_sequence）
        usage: 增量 token 使用统计
    """
    type: Literal["message_delta"] = "message_delta"
    delta: Dict[str, Any]  # 包含 stop_reason, stop_sequence
    usage: AnthropicUsage


class MessageStopEvent(BaseModel):
    """
    消息停止事件

    Attributes:
        type: 事件类型（message_stop）
    """
    type: Literal["message_stop"] = "message_stop"


class PingEvent(BaseModel):
    """
    Ping 事件

    Attributes:
        type: 事件类型（ping）
    """
    type: Literal["ping"] = "ping"


class ErrorEvent(BaseModel):
    """
    错误事件

    Attributes:
        type: 事件类型（error）
        error: 错误信息
    """
    type: Literal["error"] = "error"
    error: Dict[str, Any]


# 流式事件联合类型
StreamEvent = Union[
    MessageStartEvent,
    ContentBlockStartEvent,
    ContentBlockDeltaEvent,
    ContentBlockStopEvent,
    MessageDeltaEvent,
    MessageStopEvent,
    PingEvent,
    ErrorEvent,
]
