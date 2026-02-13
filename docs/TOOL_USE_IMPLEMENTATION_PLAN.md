# 工具调用（Tool Use）功能实现计划

## 问题描述

当前代理服务不支持工具调用功能，导致 Claude Code CLI 无法正常使用工具（如 Task、Read、Bash 等）。

### 现象

- 用户请求："现在请你帮我做一个个人主页"
- 模型回复："我来帮你做一个个人主页！首先让我探索一下当前的开发环境和目录结构，然后我们将一起规划这个项目。[Task(subagent_type="Explore")]"
- 问题：模型只返回了文本描述的工具调用，而不是实际的结构化工具调用

### 根本原因

1. **请求处理缺失**：`AnthropicMessagesRequest` 没有 `tools` 参数
2. **内部格式缺失**：`InternalRequest` 没有 `tools` 字段
3. **适配器未实现**：`anthropic_adapter.py` 不处理工具定义和工具调用响应
4. **后端转发缺失**：`backend_proxy.py` 不转发工具定义到后端

## 实现方案

### 1. 扩展数据模型

#### 1.1 Anthropic 工具模型 (`proxy_app/models/anthropic_models.py`)

```python
class ToolInputSchema(BaseModel):
    """
    工具输入 schema (JSON Schema 格式)

    Attributes:
        type: schema 类型（通常是 "object"）
        properties: 参数属性定义
        required: 必需参数列表（可选）
    """
    type: Literal["object"] = "object"
    properties: Dict[str, Any]
    required: Optional[List[str]] = None


class Tool(BaseModel):
    """
    工具定义

    Attributes:
        name: 工具名称
        description: 工具描述（告诉模型何时使用此工具）
        input_schema: 工具输入参数的 JSON Schema
    """
    name: str
    description: str
    input_schema: ToolInputSchema


class ToolUseContentBlock(BaseModel):
    """
    工具调用内容块

    模型在需要调用工具时返回此类型的 content block

    Attributes:
        type: 内容类型（tool_use）
        id: 工具调用的唯一标识符
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

    用于在后续消息中返回工具执行结果给模型

    Attributes:
        type: 内容类型（tool_result）
        tool_use_id: 对应的工具调用 ID
        content: 工具执行结果（文本或内容块列表）
        is_error: 是否是错误结果（可选）
    """
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: Union[str, List[ContentBlock]]
    is_error: Optional[bool] = None
```

#### 1.2 更新请求模型

```python
class AnthropicMessagesRequest(BaseModel):
    """
    Anthropic Messages API 请求模型
    """
    model: str
    messages: List[AnthropicMessage]
    max_tokens: int = Field(..., ge=1)
    system: Optional[Union[str, List[SystemContentBlock]]] = None
    tools: Optional[List[Tool]] = None  # 新增：工具定义列表
    temperature: Optional[float] = Field(default=1.0, ge=0, le=1)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    top_k: Optional[int] = Field(default=None, ge=1)
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
```

#### 1.3 更新 ContentBlock 类型

```python
# 更新 ContentBlock 联合类型，包含新的工具相关类型
ContentBlock = Union[
    TextContentBlock,
    ImageContentBlock,
    ThinkingContentBlock,
    ToolUseContentBlock,      # 新增
    ToolResultContentBlock    # 新增
]
```

### 2. 扩展内部统一格式 (`proxy_app/models/common.py`)

```python
class InternalRequest(TypedDict, total=False):
    """内部统一的请求格式"""
    messages: List[InternalMessage]
    model: str
    stream: bool
    tools: Optional[List[Dict[str, Any]]]  # 新增：工具定义
    temperature: Optional[float]
    max_tokens: Optional[int]
    top_p: Optional[float]
    stop: Optional[List[str]]
    presence_penalty: Optional[float]
    frequency_penalty: Optional[float]
    n: Optional[int]
    user: Optional[str]


class InternalMessage(TypedDict, total=False):
    """内部统一的消息格式"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str | List[Dict[str, Any]]  # 更新：支持数组格式（用于工具调用）
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_call_id: Optional[str]
    name: Optional[str]
```

### 3. 更新 Anthropic 适配器 (`proxy_app/adapters/anthropic_adapter.py`)

#### 3.1 请求转换（adapt_request）

```python
def adapt_request(self, request_data: AnthropicMessagesRequest) -> InternalRequest:
    """
    将 Anthropic 请求格式转换为内部统一格式
    """
    # ... 现有代码 ...

    # 构建内部请求格式
    internal_request: InternalRequest = {
        "messages": internal_messages,
        "model": request_data.model,
        "stream": request_data.stream or False,
        "max_tokens": request_data.max_tokens,
        "temperature": request_data.temperature,
        "top_p": request_data.top_p,
    }

    # 新增：转换工具定义
    if request_data.tools:
        internal_request["tools"] = [
            {
                "type": "function",  # OpenAI 格式使用 "function" type
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema.model_dump(),
                }
            }
            for tool in request_data.tools
        ]

    # ... 其余代码 ...

    return internal_request
```

#### 3.2 响应转换（adapt_response）

```python
def adapt_response(self, internal_response: InternalResponse) -> AnthropicMessagesResponse:
    """
    将内部统一格式转换为 Anthropic 响应格式（非流式）
    """
    # 构建 content 块列表
    content_blocks = []

    # 如果有推理内容，先添加 thinking block
    if internal_response.get("reasoning_content"):
        content_blocks.append(
            ThinkingContentBlock(
                type="thinking",
                thinking=internal_response["reasoning_content"],
            )
        )

    # 新增：处理工具调用
    if internal_response.get("tool_calls"):
        for tool_call in internal_response["tool_calls"]:
            # OpenAI 格式：tool_call.function.name, tool_call.function.arguments
            # Anthropic 格式：name, input
            import json
            tool_use_block = ToolUseContentBlock(
                type="tool_use",
                id=tool_call["id"],
                name=tool_call["function"]["name"],
                input=json.loads(tool_call["function"]["arguments"]),
            )
            content_blocks.append(tool_use_block)

    # 添加文本内容 block（如果有）
    if internal_response.get("content"):
        content_blocks.append(
            TextContentBlock(
                type="text",
                text=internal_response["content"],
            )
        )

    # ... 其余代码 ...
```

#### 3.3 流式响应转换（adapt_streaming_response）

```python
async def adapt_streaming_response(
    self, internal_stream: AsyncGenerator[InternalStreamChunk, None]
) -> AsyncGenerator[str, None]:
    """
    将内部流式响应转换为 Anthropic SSE 格式
    """
    # ... 现有状态变量 ...

    # 新增：工具调用相关状态
    tool_use_blocks_started = []  # 已开始的工具调用块索引
    current_tool_call_buffer = {}  # 缓存累积的工具调用数据

    async for chunk in internal_stream:
        # ... 现有处理逻辑 ...

        # 新增：处理工具调用增量
        if chunk.get("delta_tool_calls"):
            for tool_call_delta in chunk["delta_tool_calls"]:
                tool_index = tool_call_delta.get("index", 0)

                # 初始化工具调用缓存
                if tool_index not in current_tool_call_buffer:
                    current_tool_call_buffer[tool_index] = {
                        "id": "",
                        "name": "",
                        "arguments": "",
                    }

                # 累积工具调用数据
                if "id" in tool_call_delta:
                    current_tool_call_buffer[tool_index]["id"] = tool_call_delta["id"]
                if "function" in tool_call_delta:
                    func = tool_call_delta["function"]
                    if "name" in func:
                        current_tool_call_buffer[tool_index]["name"] = func["name"]
                    if "arguments" in func:
                        current_tool_call_buffer[tool_index]["arguments"] += func["arguments"]

                # 如果工具调用开始（有 name），发送 content_block_start
                if (tool_call_delta.get("function", {}).get("name")
                    and tool_index not in tool_use_blocks_started):

                    yield self._format_sse_event(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": current_block_index,
                            "content_block": {
                                "type": "tool_use",
                                "id": current_tool_call_buffer[tool_index]["id"],
                                "name": current_tool_call_buffer[tool_index]["name"],
                                "input": {},
                            },
                        },
                    )
                    tool_use_blocks_started.append(tool_index)
                    current_block_index += 1

                # 如果累积的 arguments 是完整的 JSON，发送 content_block_delta
                # 注意：这里需要检查 JSON 是否完整，可能需要累积多个块

        # 在结束时，发送完整的工具调用
        if chunk.get("finish_reason"):
            # 为每个累积的工具调用发送完整的 input
            for tool_index in sorted(current_tool_call_buffer.keys()):
                tool_data = current_tool_call_buffer[tool_index]
                try:
                    import json
                    input_obj = json.loads(tool_data["arguments"])

                    # 发送 content_block_delta 包含完整的 input
                    yield self._format_sse_event(
                        "content_block_delta",
                        {
                            "type": "content_block_delta",
                            "index": tool_index,
                            "delta": {
                                "type": "input_json_delta",
                                "partial_json": tool_data["arguments"],
                            },
                        },
                    )

                    # 发送 content_block_stop
                    yield self._format_sse_event(
                        "content_block_stop",
                        {"type": "content_block_stop", "index": tool_index},
                    )
                except json.JSONDecodeError:
                    pass

    # ... 其余代码 ...
```

### 4. 更新后端代理 (`proxy_app/proxy/backend_proxy.py`)

```python
def _convert_to_backend_format(self, internal_request: InternalRequest) -> Dict[str, Any]:
    """
    将内部格式转换为后端接口格式
    """
    # ... 现有代码 ...

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
        "tools",  # 新增：转发工具定义
    ]

    for param in optional_params:
        value = internal_request.get(param)
        if value is not None:
            backend_request[param] = value

    return backend_request
```

### 5. 更新消息处理

#### 5.1 处理 tool_result 消息

在 `_extract_text_content` 中添加对 `tool_result` 的处理：

```python
def _extract_text_content(self, content: str | List[ContentBlock]) -> str | List[Dict[str, Any]]:
    """
    从多模态 content 中提取内容

    对于包含 tool_result 的消息，需要保留完整的结构
    """
    # 如果是字符串，直接返回
    if isinstance(content, str):
        return content

    # 检查是否包含 tool_result
    has_tool_result = any(
        (isinstance(block, dict) and block.get("type") == "tool_result")
        or (hasattr(block, "type") and block.type == "tool_result")
        for block in content
    )

    # 如果包含 tool_result，返回完整的结构化内容
    if has_tool_result:
        return [
            block.model_dump() if hasattr(block, "model_dump") else block
            for block in content
        ]

    # 否则提取纯文本（现有逻辑）
    text_parts = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        elif hasattr(block, "type") and block.type == "text":
            text_parts.append(block.text)

    return "\n".join(text_parts)
```

## 实现优先级

### Phase 1: 基础工具调用支持（必需）
1. ✅ 定义工具相关数据模型
2. ✅ 更新请求/响应适配器
3. ✅ 后端转发工具定义
4. ✅ 处理非流式工具调用响应

### Phase 2: 流式工具调用支持（推荐）
1. ⬜ 实现流式工具调用响应
2. ⬜ 处理增量 tool_calls

### Phase 3: 完整工具循环（可选）
1. ⬜ 处理 tool_result 消息
2. ⬜ 支持多轮工具调用

## 测试计划

### 单元测试
```python
# tests/test_tool_use.py

def test_anthropic_request_with_tools():
    """测试带工具定义的请求转换"""
    request = AnthropicMessagesRequest(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": "What's the weather?"}],
        tools=[
            Tool(
                name="get_weather",
                description="Get weather info",
                input_schema=ToolInputSchema(
                    type="object",
                    properties={"location": {"type": "string"}},
                    required=["location"]
                )
            )
        ]
    )

    adapter = AnthropicAdapter()
    internal_req = adapter.adapt_request(request)

    assert "tools" in internal_req
    assert internal_req["tools"][0]["function"]["name"] == "get_weather"


def test_anthropic_response_with_tool_call():
    """测试工具调用响应转换"""
    internal_response = {
        "id": "msg_123",
        "created": 1234567890,
        "model": "claude-3-opus-20240229",
        "content": "",
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Paris"}'
                }
            }
        ],
        "finish_reason": "tool_calls",
    }

    adapter = AnthropicAdapter()
    anthropic_resp = adapter.adapt_response(internal_response)

    assert len(anthropic_resp.content) == 1
    assert anthropic_resp.content[0].type == "tool_use"
    assert anthropic_resp.content[0].name == "get_weather"
    assert anthropic_resp.content[0].input == {"location": "Paris"}
```

### 集成测试
```bash
# 启动代理服务
python proxy_server.py

# 测试工具调用
curl -X POST http://127.0.0.1:8080/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "max_tokens": 1024,
    "tools": [
      {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g. San Francisco, CA"
            }
          },
          "required": ["location"]
        }
      }
    ],
    "messages": [
      {"role": "user", "content": "What is the weather like in Paris?"}
    ]
  }'
```

## 参考资料

- [Anthropic Tool Use API 文档](https://docs.anthropic.com/claude/docs/tool-use)
- [OpenAI Function Calling 文档](https://platform.openai.com/docs/guides/function-calling)

## 注意事项

1. **格式差异**：
   - Anthropic 使用 `tools` 和 `tool_use`
   - OpenAI 使用 `functions` 或 `tools` 和 `function_call`
   - 需要在适配器中正确转换

2. **工具结果处理**：
   - Anthropic 使用 `tool_result` content block
   - OpenAI 使用 `tool` role 消息
   - 需要双向转换

3. **流式响应复杂性**：
   - 工具调用的 arguments 可能跨多个块
   - 需要缓存和累积完整的 JSON
   - 只有在 JSON 完整时才能解析

4. **错误处理**：
   - 工具调用失败时需要正确传递错误信息
   - 使用 `is_error: true` 标记错误结果
