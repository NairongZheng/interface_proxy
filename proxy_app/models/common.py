"""
内部统一格式定义
定义适配器之间转换使用的中间格式，避免 N×N 转换
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict


class InternalMessage(TypedDict, total=False):
    """
    内部统一的消息格式

    Attributes:
        role: 消息角色（system, user, assistant, tool）
        content: 消息内容（文本字符串或内容块列表）
                 - 字符串：纯文本消息
                 - 列表：包含多种类型的内容块（如 tool_result）
        tool_calls: 工具调用列表（可选，assistant 角色使用）
        tool_call_id: 工具调用 ID（可选，tool 角色使用）
        name: 消息名称（可选）
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: str | List[Dict[str, Any]]  # 更新：支持数组格式（用于工具结果）
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_call_id: Optional[str]
    name: Optional[str]


class InternalRequest(TypedDict, total=False):
    """
    内部统一的请求格式

    所有外部请求格式（OpenAI、Anthropic 等）都会转换为这个内部格式

    Attributes:
        messages: 消息列表
        model: 模型名称
        stream: 是否流式输出
        tools: 工具定义列表（可选）
        temperature: 温度参数（0-2），控制随机性
        max_tokens: 最大生成 token 数
        top_p: nucleus sampling 参数（0-1）
        stop: 停止序列列表
        presence_penalty: 存在惩罚（-2 到 2）
        frequency_penalty: 频率惩罚（-2 到 2）
        n: 生成的候选数量
        user: 用户标识符（可选）
    """
    messages: List[InternalMessage]
    model: str
    stream: bool
    tools: Optional[List[Dict[str, Any]]]  # 新增：工具定义列表
    temperature: Optional[float]
    max_tokens: Optional[int]
    top_p: Optional[float]
    stop: Optional[List[str]]
    presence_penalty: Optional[float]
    frequency_penalty: Optional[float]
    n: Optional[int]
    user: Optional[str]


class InternalUsage(TypedDict):
    """
    内部统一的 token 使用统计格式

    Attributes:
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数
        total_tokens: 总 token 数
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class InternalResponse(TypedDict, total=False):
    """
    内部统一的响应格式（非流式）

    所有后端响应都会转换为这个内部格式，然后再转为外部格式

    Attributes:
        id: 响应唯一标识符
        created: 创建时间戳（Unix 时间）
        model: 使用的模型名称
        content: 生成的文本内容
        role: 响应的角色（通常是 assistant）
        tool_calls: 工具调用列表（可选）
        reasoning_content: 推理过程内容（可选，用于支持 o1 等模型）
        finish_reason: 结束原因（stop, length, tool_calls, content_filter 等）
        usage: token 使用统计
    """
    id: str
    created: int
    model: str
    content: str
    role: str
    tool_calls: Optional[List[Dict[str, Any]]]
    reasoning_content: Optional[str]
    finish_reason: Optional[str]
    usage: Optional[InternalUsage]


class InternalStreamChunk(TypedDict, total=False):
    """
    内部统一的流式数据块格式

    流式响应的每个数据块都使用这个格式

    Attributes:
        id: 响应唯一标识符
        created: 创建时间戳（Unix 时间）
        model: 使用的模型名称
        delta_content: 增量文本内容
        delta_role: 增量角色（通常只在第一个块出现）
        delta_tool_calls: 增量工具调用（可选）
        delta_reasoning_content: 增量推理内容（可选）
        finish_reason: 结束原因（只在最后一个块出现）
        usage: token 使用统计（可选，只在最后一个块出现）
    """
    id: str
    created: int
    model: str
    delta_content: Optional[str]
    delta_role: Optional[str]
    delta_tool_calls: Optional[List[Dict[str, Any]]]
    delta_reasoning_content: Optional[str]
    finish_reason: Optional[str]
    usage: Optional[InternalUsage]


# 类型别名，方便使用
InternalFormat = InternalRequest | InternalResponse | InternalStreamChunk
