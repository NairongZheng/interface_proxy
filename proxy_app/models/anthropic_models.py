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


class ToolUseContentBlock(BaseModel):
    """
    工具调用内容块

    模型在需要调用工具时返回此类型的 content block。
    这是模型请求执行某个工具的信号，客户端需要执行工具并返回结果。

    Attributes:
        type: 内容类型（tool_use）
        id: 工具调用的唯一标识符（用于匹配工具结果）
        name: 要调用的工具名称
        input: 工具输入参数（字典格式）
    """
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultContentBlock(BaseModel):
    """
    工具结果内容块

    用于在后续消息中返回工具执行结果给模型。
    客户端执行工具后，需要将结果包装在这个 content block 中发送回模型。

    Attributes:
        type: 内容类型（tool_result）
        tool_use_id: 对应的工具调用 ID（与 ToolUseContentBlock.id 匹配）
        content: 工具执行结果（文本或内容块列表）
        is_error: 是否是错误结果（可选，true 表示工具执行失败）
    """
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: Union[str, List["ContentBlock"]]
    is_error: Optional[bool] = None


# 内容块可以是文本、图片、推理、工具调用或工具结果
ContentBlock = Union[
    TextContentBlock,
    ImageContentBlock,
    ThinkingContentBlock,
    ToolUseContentBlock,
    ToolResultContentBlock,
]


class SystemTextBlock(BaseModel):
    """
    System 提示文本块

    用于 system 参数的数组格式，支持 prompt caching。
    Anthropic API 在支持 prompt caching 功能后，扩展了 system 参数的格式，
    允许将 system 提示分成多个文本块，每个块可以独立配置缓存控制。

    Attributes:
        type: 内容类型（text）
        text: 文本内容
        cache_control: 缓存控制（可选），例如: {"type": "ephemeral"}
    """
    type: Literal["text"] = "text"
    text: str
    cache_control: Optional[Dict[str, Any]] = None


# System 内容块类型（目前只支持 text 类型）
SystemContentBlock = SystemTextBlock


# ==================== 工具定义相关模型 ====================

class ToolInputSchema(BaseModel):
    """
    工具输入参数的 JSON Schema

    定义工具接受的参数格式，遵循 JSON Schema 规范。
    模型会根据这个 schema 生成符合格式的参数。

    Attributes:
        type: schema 类型（通常是 "object"）
        properties: 参数属性定义（字典，key 是参数名，value 是参数的 schema）
        required: 必需参数列表（可选）
    """
    type: Literal["object"] = "object"
    properties: Dict[str, Any]
    required: Optional[List[str]] = None


class Tool(BaseModel):
    """
    工具定义

    向模型声明一个可用的工具（函数/API），模型可以根据需要调用这个工具。

    Attributes:
        name: 工具名称（唯一标识符，只能包含字母、数字、下划线）
        description: 工具描述（告诉模型这个工具的功能和使用场景）
        input_schema: 工具输入参数的 JSON Schema
    """
    name: str
    description: str
    input_schema: ToolInputSchema


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
                支持两种格式：
                1. 字符串格式（旧格式）：简单的字符串
                2. 内容块数组格式（新格式）：支持 prompt caching
        tools: 工具定义列表（可选）
               向模型声明可用的工具，模型可以根据需要调用这些工具
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
    system: Optional[Union[str, List[SystemContentBlock]]] = None
    tools: Optional[List[Tool]] = None  # 新增：工具定义列表
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
        content: 内容块列表（可包含 text, image, thinking, tool_use 等类型）
        model: 使用的模型名称
        stop_reason: 停止原因（end_turn, max_tokens, stop_sequence, tool_use）
        stop_sequence: 实际匹配的停止序列（可选）
        usage: token 使用统计
    """
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextContentBlock, ThinkingContentBlock, ToolUseContentBlock]]
    model: str
    stop_reason: Optional[Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"]] = None
    stop_sequence: Optional[str] = None
    usage: Optional[AnthropicUsage] = None


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
