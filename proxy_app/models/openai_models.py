"""
OpenAI API 数据模型定义
定义 OpenAI Chat Completions API 的请求和响应格式
参考：https://platform.openai.com/docs/api-reference/chat
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ==================== 消息相关模型 ====================

class FunctionCall(BaseModel):
    """
    函数调用（已废弃，建议使用 tool_calls）

    Attributes:
        name: 函数名称
        arguments: 函数参数（JSON 字符串）
    """
    name: str
    arguments: str


class ToolCallFunction(BaseModel):
    """
    工具调用中的函数信息

    Attributes:
        name: 函数名称
        arguments: 函数参数（JSON 字符串）
    """
    name: str
    arguments: str


class ToolCall(BaseModel):
    """
    工具调用

    Attributes:
        id: 工具调用的唯一标识符
        type: 工具类型（目前只支持 function）
        function: 函数调用信息
    """
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ChatMessage(BaseModel):
    """
    聊天消息

    Attributes:
        role: 消息角色（system, user, assistant, tool）
        content: 消息内容（可以为 None，例如包含 tool_calls 时）
        name: 消息名称（可选）
        tool_calls: 工具调用列表（仅 assistant 角色）
        tool_call_id: 工具调用 ID（仅 tool 角色）
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None


# ==================== 请求模型 ====================

class ChatCompletionRequest(BaseModel):
    """
    Chat Completions API 请求模型

    Attributes:
        model: 模型名称（例如：gpt-3.5-turbo, gpt-4）
        messages: 消息列表
        temperature: 温度参数（0-2），控制随机性
        top_p: nucleus sampling 参数（0-1）
        n: 生成的候选数量
        stream: 是否流式输出
        stop: 停止序列（字符串或字符串列表）
        max_tokens: 最大生成 token 数
        presence_penalty: 存在惩罚（-2 到 2）
        frequency_penalty: 频率惩罚（-2 到 2）
        logit_bias: logit 偏置
        user: 用户标识符
        reasoning_effort: 推理努力程度（用于 o1 系列模型）
        tools: 可用的工具列表（用于函数调用）
        tool_choice: 工具选择策略（auto, none, 或指定工具）
    """
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=1.0, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = Field(default=None, ge=1)
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = None
    # 工具调用相关参数
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None

    class Config:
        # 允许额外字段（用于扩展）
        extra = "allow"


# ==================== 响应模型 ====================

class Usage(BaseModel):
    """
    Token 使用统计

    Attributes:
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数
        total_tokens: 总 token 数
        completion_tokens_details: 输出 token 详细信息（可选）
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    completion_tokens_details: Optional[Dict[str, Any]] = None


class ChatCompletionMessage(BaseModel):
    """
    Chat Completion 响应中的消息

    Attributes:
        role: 角色（通常是 assistant）
        content: 消息内容
        tool_calls: 工具调用列表（可选）
        reasoning_content: 推理过程内容（可选，用于 o1 系列模型）
    """
    role: Literal["assistant"]
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    reasoning_content: Optional[str] = None


class Choice(BaseModel):
    """
    Chat Completion 响应中的选择

    Attributes:
        index: 选择的索引
        message: 生成的消息
        finish_reason: 结束原因（stop, length, tool_calls, content_filter）
        logprobs: 对数概率信息（可选）
    """
    index: int
    message: ChatCompletionMessage
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionResponse(BaseModel):
    """
    Chat Completions API 响应模型

    Attributes:
        id: 响应的唯一标识符
        object: 对象类型（chat.completion）
        created: 创建时间戳（Unix 时间）
        model: 使用的模型名称
        choices: 生成的选择列表
        usage: token 使用统计
        system_fingerprint: 系统指纹（可选）
    """
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None

    class Config:
        # 允许额外字段（用于传递后端返回的非标准字段）
        extra = "allow"


# ==================== 流式响应模型 ====================

class DeltaMessage(BaseModel):
    """
    流式响应中的增量消息

    Attributes:
        role: 角色（通常只在第一个块出现）
        content: 增量内容
        tool_calls: 增量工具调用（可选）
        reasoning_content: 增量推理内容（可选）
    """
    role: Optional[Literal["assistant"]] = None
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    reasoning_content: Optional[str] = None


class StreamChoice(BaseModel):
    """
    流式响应中的选择

    Attributes:
        index: 选择的索引
        delta: 增量消息
        finish_reason: 结束原因（只在最后一个块出现）
        logprobs: 对数概率信息（可选）
    """
    index: int
    delta: DeltaMessage
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionChunk(BaseModel):
    """
    Chat Completions API 流式响应块

    Attributes:
        id: 响应的唯一标识符
        object: 对象类型（chat.completion.chunk）
        created: 创建时间戳（Unix 时间）
        model: 使用的模型名称
        choices: 增量选择列表
        usage: token 使用统计（可选，通常在最后一个块出现）
        system_fingerprint: 系统指纹（可选）
    """
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[StreamChoice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None

    class Config:
        # 允许额外字段（用于传递后端返回的非标准字段）
        extra = "allow"


# ==================== Models API 相关模型 ====================

class ModelPermission(BaseModel):
    """
    模型权限信息

    Attributes:
        id: 权限标识符
        object: 对象类型（model_permission）
        created: 创建时间戳
        allow_create_engine: 是否允许创建引擎
        allow_sampling: 是否允许采样
        allow_logprobs: 是否允许返回 logprobs
        allow_search_indices: 是否允许搜索索引
        allow_view: 是否允许查看
        allow_fine_tuning: 是否允许微调
        organization: 组织标识
        group: 组标识
        is_blocking: 是否阻塞
    """
    id: str
    object: Literal["model_permission"] = "model_permission"
    created: int
    allow_create_engine: bool = False
    allow_sampling: bool = True
    allow_logprobs: bool = True
    allow_search_indices: bool = False
    allow_view: bool = True
    allow_fine_tuning: bool = False
    organization: str = "*"
    group: Optional[str] = None
    is_blocking: bool = False


class Model(BaseModel):
    """
    模型信息

    Attributes:
        id: 模型标识符（例如：gpt-3.5-turbo）
        object: 对象类型（model）
        created: 创建时间戳
        owned_by: 所有者（例如：openai, organization-owner）
        permission: 权限列表
        root: 根模型
        parent: 父模型
    """
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "openai"
    permission: Optional[List[ModelPermission]] = None
    root: Optional[str] = None
    parent: Optional[str] = None


class ModelList(BaseModel):
    """
    模型列表响应

    Attributes:
        object: 对象类型（list）
        data: 模型列表
    """
    object: Literal["list"] = "list"
    data: List[Model]
