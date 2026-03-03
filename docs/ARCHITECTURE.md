# 架构文档

本文档详细说明 Interface Proxy Service 的架构设计。

## 📐 整体架构

### 核心设计理念

**Adapter 负责一切**：每个 Adapter 知道如何调用自己的后端服务，包括请求格式、认证方式、URL 端点等。

```
┌─────────────────────────────────────────────────────────────┐
│                     用户（各种 SDK）                          │
│   OpenAI SDK  │  Anthropic SDK  │  其他 SDK                  │
└────────┬────────────────┬─────────────────┬──────────────────┘
         │                │                 │
         │                │                 │
┌────────▼────────────────▼─────────────────▼──────────────────┐
│                  FastAPI 路由层                                │
│  - 接收请求，识别格式                                           │
│  - 根据模型选择 Adapter                                         │
│  - 传递配置（backend_url, api_key）                            │
└────────┬────────────────┬─────────────────┬──────────────────┘
         │                │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │ OpenAI  │      │Anthropic│      │   PTU   │
    │ Adapter │      │ Adapter │      │ Adapter │
    └────┬────┘      └────┬────┘      └────┬────┘
         │                │                 │
    格式转换            格式转换           格式转换
    后端调用            后端调用           后端调用
         │                │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │ OpenAI  │      │ OpenAI  │      │   PTU   │
    │  后端   │      │  后端   │      │ Gateway │
    └─────────┘      └─────────┘      └─────────┘
```

## 🔧 核心组件

### 1. Adapter（适配器）

**职责**：
- 格式转换（外部格式 ↔ 内部格式）
- 后端调用（知道如何调用自己的后端）
- HTTP 客户端管理

**基类**：`BaseAdapter`

```python
class BaseAdapter(ABC):
    def __init__(self, backend_url, api_key, timeout):
        """初始化 Adapter，包含后端配置"""

    @abstractmethod
    def adapt_request(self, external_request) -> InternalRequest:
        """外部格式 → 内部格式"""

    @abstractmethod
    def adapt_response(self, internal_response) -> ExternalResponse:
        """内部格式 → 外部格式（非流式）"""

    @abstractmethod
    async def adapt_streaming_response(self, internal_stream) -> ExternalStream:
        """内部格式 → 外部格式（流式）"""

    @abstractmethod
    async def forward(self, internal_request) -> InternalResponse:
        """调用后端（非流式）- 每个 Adapter 自己实现"""

    @abstractmethod
    async def forward_stream(self, internal_request) -> InternalStream:
        """调用后端（流式）- 每个 Adapter 自己实现"""
```

### 2. OpenAIAdapter

**特点**：
- 标准 OpenAI API 调用
- URL: `{backend_url}/v1/chat/completions`
- 认证: `Authorization: Bearer {api_key}`

**关键方法**：

```python
async def forward(self, internal_request):
    # 构造 OpenAI 请求
    openai_request = self._build_openai_request(internal_request)

    # 调用 OpenAI 后端
    url = f"{self.backend_url}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {self.api_key}"}
    response = await client.post(url, json=openai_request, headers=headers)

    # 解析响应
    return self._parse_openai_response(response.json())
```

### 3. PTUAdapter

**特点**：
- 继承自 OpenAIAdapter（复用解析逻辑）
- 特殊的 PTU Gateway API
- URL: `{backend_url}/gateway/chatTask/callResult`
- 认证: `api-key: {api_key}`
- 请求需要额外参数：`server_name`, `transaction_id`, `channel_code`
- 响应需要解包：提取 `data.response_content`

**关键方法**：

```python
async def forward(self, internal_request):
    # 构造 PTU 请求（添加特殊参数）
    ptu_request = self._build_ptu_request(internal_request)

    # 调用 PTU Gateway
    url = f"{self.backend_url}/gateway/chatTask/callResult"
    headers = {"api-key": self.api_key}
    response = await client.post(url, json=ptu_request, headers=headers)

    # 解包 PTU 响应
    openai_response = self.unwrap_ptu_response(response.json())

    # 解析为内部格式（复用父类逻辑）
    return self._parse_openai_response(openai_response)

def _build_ptu_request(self, internal_request):
    return {
        "server_name": "test",
        "model": internal_request["model"],
        "messages": internal_request["messages"],
        "transaction_id": f"{user}-{model}",
        "channel_code": self.infer_channel_code(model),
        # ... 其他参数
    }

@staticmethod
def unwrap_ptu_response(ptu_response):
    """解包 PTU 包装格式"""
    if ptu_response["code"] != 10000:
        raise ValueError(f"PTU 错误: {ptu_response['msg']}")
    return ptu_response["data"]["response_content"]
```

### 4. AnthropicAdapter

**特点**：
- 继承自 OpenAIAdapter
- 处理 Anthropic 特殊格式（system 字段、content 数组）
- 转换为 OpenAI 格式后调用标准后端
- 响应转回 Anthropic 格式

**格式转换**：

```python
def adapt_request(self, anthropic_request):
    # 处理 system 字段（Anthropic 独立，OpenAI 在 messages 中）
    messages = []
    if anthropic_request.system:
        messages.append({"role": "system", "content": anthropic_request.system})

    # 处理 content 数组（Anthropic 支持多模态）
    for msg in anthropic_request.messages:
        if isinstance(msg.content, list):
            # 提取文本内容
            text = "".join([c.text for c in msg.content if c.type == "text"])
            messages.append({"role": msg.role, "content": text})
        else:
            messages.append({"role": msg.role, "content": msg.content})

    return {"messages": messages, ...}

def adapt_response(self, internal_response):
    # OpenAI 响应 → Anthropic 响应
    return AnthropicMessagesResponse(
        id=f"msg_{uuid}",
        content=[{"type": "text", "text": internal_response["content"]}],
        model=internal_response["model"],
        stop_reason=self._map_finish_reason(internal_response["finish_reason"]),
        usage=...
    )
```

### 5. 路由层（FastAPI）

**职责**：
- 接收 HTTP 请求
- 识别请求格式（OpenAI `/v1/chat/completions` vs Anthropic `/v1/messages`）
- 根据模型选择 Adapter
- 初始化 Adapter（传递 backend_url, api_key）
- 调用 Adapter 处理请求

**路由逻辑**：

```python
@app.post("/v1/chat/completions")
async def openai_chat_completions(request: ChatCompletionRequest):
    # 根据模型选择 Adapter
    if config.is_ptu_model(request.model):
        # PTU 模型：使用 PTU Gateway
        adapter = PTUAdapter(
            backend_url=config.ptu_backend_url,
            api_key=config.backend_api_key,
            timeout=config.backend_timeout,
        )
    else:
        # 标准模型：使用标准 OpenAI 后端
        adapter = OpenAIAdapter(
            backend_url=config.backend_url,
            api_key=config.backend_api_key,
            timeout=config.backend_timeout,
        )

    # 处理请求
    return await handle_request(request, adapter)

async def handle_request(request, adapter):
    # 1. 格式转换
    internal_request = adapter.adapt_request(request)

    # 2. 后端调用（Adapter 自己负责）
    if internal_request["stream"]:
        internal_stream = adapter.forward_stream(internal_request)
        external_stream = adapter.adapt_streaming_response(internal_stream)
        return StreamingResponse(external_stream)
    else:
        internal_response = await adapter.forward(internal_request)
        external_response = adapter.adapt_response(internal_response)
        return JSONResponse(external_response.model_dump())
```

## 🔄 请求处理流程

### 非流式请求

```
1. 用户请求 → FastAPI 路由
         ↓
2. 识别格式和模型 → 选择 Adapter
         ↓
3. Adapter.adapt_request() → 转为内部格式
         ↓
4. Adapter.forward() → 调用后端
         ↓
5. 后端响应 → Adapter 解析为内部格式
         ↓
6. Adapter.adapt_response() → 转为外部格式
         ↓
7. 返回给用户
```

### 流式请求

```
1. 用户请求 → FastAPI 路由
         ↓
2. 识别格式和模型 → 选择 Adapter
         ↓
3. Adapter.adapt_request() → 转为内部格式
         ↓
4. Adapter.forward_stream() → 调用后端（返回生成器）
         ↓
5. 逐块接收后端 SSE → 解析为内部流式格式
         ↓
6. Adapter.adapt_streaming_response() → 转为外部 SSE 格式
         ↓
7. 流式返回给用户
```

## 📦 内部格式定义

### InternalRequest

统一的请求格式，兼容所有外部格式：

```python
{
    "model": str,
    "messages": [
        {"role": "user|assistant|system", "content": str},
        ...
    ],
    "stream": bool,
    "temperature": float,
    "max_tokens": int,
    "top_p": float,
    "stop": List[str],
    "tools": List[dict],  # 可选
    "tool_choice": str,   # 可选
    ...
}
```

### InternalResponse

统一的响应格式：

```python
{
    "id": str,
    "created": int,
    "model": str,
    "role": str,
    "content": str,
    "finish_reason": str,
    "usage": {
        "prompt_tokens": int,
        "completion_tokens": int,
        "total_tokens": int,
    },
    "tool_calls": List[dict],        # 可选
    "reasoning_content": str,        # 可选（o1 系列）
}
```

### InternalStreamChunk

统一的流式响应块：

```python
{
    "id": str,
    "created": int,
    "model": str,
    "delta_role": str,              # 可选
    "delta_content": str,           # 可选
    "finish_reason": str,           # 可选
    "delta_tool_calls": List[dict], # 可选
    "usage": dict,                  # 可选（最后一块）
}
```

## 🎯 设计优势

### 1. 职责清晰

- **路由层**：负责识别和选择
- **Adapter**：负责转换和调用
- 每个 Adapter 是独立的，互不影响

### 2. 易于扩展

添加新格式只需：
1. 创建新 Adapter 类（继承 BaseAdapter）
2. 实现格式转换和后端调用方法
3. 在路由层添加判断逻辑

### 3. 后端定制化

每个 Adapter 知道如何调用自己的后端：
- **OpenAIAdapter**: 标准 REST API
- **PTUAdapter**: 特殊 Gateway API + 包装格式
- **未来**: 可以添加 gRPC、WebSocket 等不同协议

### 4. 对用户透明

用户只需：
- 使用标准 SDK（OpenAI / Anthropic）
- 配置代理服务地址
- 系统自动处理所有转换

## 📈 性能考虑

### 1. HTTP 客户端池

每个 Adapter 管理自己的 HTTP 客户端：

```python
async def get_client(self):
    if self._client is None:
        self._client = httpx.AsyncClient(timeout=self.timeout)
    return self._client
```

### 2. 流式传输

使用异步生成器，逐块传输：

```python
async def forward_stream(self, request):
    async with client.stream("POST", url, json=request) as response:
        async for line in response.aiter_lines():
            # 逐行解析和转换
            yield parsed_chunk
```

### 3. 无状态设计

每个请求创建新的 Adapter 实例，无全局状态，天然支持并发。

## 🔒 安全考虑

### 1. API Key 管理

- API Key 存储在配置文件中
- 通过 Adapter 初始化传递
- 不在日志中输出完整 Key

### 2. 错误处理

- 捕获所有异常，返回友好错误信息
- 不暴露内部实现细节
- 记录详细日志用于调试

### 3. 输入验证

- 使用 Pydantic 模型验证请求
- 检查必需字段
- 限制请求大小

## 🔗 相关文档

- [开发文档](DEVELOPMENT.md) - 实现细节
- [PTU 集成文档](PTU_INTEGRATION.md) - PTU 特殊处理
- [测试指南](../tests/README.md) - 测试方法

---

最后更新：2026-03-02
