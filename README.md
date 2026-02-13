# Interface Proxy Service

接口代理服务，实现不同 LLM 接口格式之间的互相转换和转发。

## 项目简介

这是一个 LLM 接口代理服务，采用**适配器模式**设计，可以在不同的 API 格式之间自动转换。当后端模型服务（如 `127.0.0.1:8000`）提供 OpenAI `/v1/chat/completions` 接口时，代理服务可以在不同端口（如 `127.0.0.1:8080`）提供多种格式的接口：

- **OpenAI 格式**：`/v1/chat/completions`（直接透传或增强）
- **Anthropic 格式**：`/v1/messages`（自动转换）
- **其他格式**：可扩展支持更多格式

## 核心价值

**问题**：后端模型服务通常只实现一种 API 格式（如 OpenAI），但客户端可能使用不同的 SDK（Anthropic、Google 等）。

**解决方案**：后端只需实现一种接口格式，代理服务自动提供多种格式支持，让客户端可以选择自己喜欢的 API 格式。

## 功能特性

✅ **格式转换**：OpenAI ↔ Anthropic 格式互转
✅ **接口转发**：代理后端模型服务的请求
✅ **流式支持**：支持流式和非流式两种模式
✅ **推理内容支持**：完整支持 reasoning_content（OpenAI o1）和 thinking（Anthropic）
✅ **模块化**：代码结构清晰，便于扩展新格式
✅ **可配置**：通过 YAML 配置文件管理
✅ **高性能**：基于 FastAPI + httpx 异步架构

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置服务

编辑 `config/config.yaml`：

```yaml
backend:
  url: "http://127.0.0.1:8000"  # 后端模型服务地址
  timeout: 600.0
  max_connections: 100

server:
  host: "0.0.0.0"
  port: 8080
  log_level: "INFO"

routes:
  openai_enabled: true
  anthropic_enabled: true
```

### 3. 启动服务

```bash
# 使用默认配置
python proxy_server.py

# 指定配置文件
python proxy_server.py --config custom_config.yaml

# 指定监听地址和端口
python proxy_server.py --host 0.0.0.0 --port 8080

# 开发模式（自动重载）
python proxy_server.py --reload
```

### 4. 测试接口

**健康检查**：

```bash
curl http://127.0.0.1:8080/health
```

**OpenAI 格式（非流式）**：

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

**OpenAI 格式（流式）**：

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'
```

**Anthropic 格式（非流式）**：

```bash
curl -X POST http://127.0.0.1:8080/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Anthropic 格式（流式）**：

```bash
curl -X POST http://127.0.0.1:8080/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'
```

## API 文档

### OpenAI Chat Completions API

**路径**：`POST /v1/chat/completions`

**请求格式**：

```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false
}
```

**响应格式**（非流式）：

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-3.5-turbo",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

**流式响应**：

```
data: {"id":"chatcmpl-123","choices":[{"delta":{"role":"assistant"},"index":0}]}

data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"Hello"},"index":0}]}

data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"!"},"index":0}]}

data: [DONE]
```

### Anthropic Messages API

**路径**：`POST /v1/messages`

**请求格式**：

```json
{
  "model": "claude-3-opus-20240229",
  "max_tokens": 1024,
  "system": "You are a helpful assistant.",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "stream": false
}
```

**响应格式**（非流式）：

```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "Hello! How can I help you today?"}
  ],
  "model": "claude-3-opus-20240229",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 20
  }
}
```

**流式响应**：

```
event: message_start
data: {"type":"message_start","message":{"id":"msg_123","type":"message","role":"assistant","content":[],"model":"claude-3-opus-20240229"}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"!"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":20}}

event: message_stop
data: {"type":"message_stop"}
```

### 推理内容支持（Reasoning Content）

代理服务完整支持模型的推理过程输出：

#### OpenAI o1 系列模型

OpenAI 的 o1 系列模型（如 o1-preview, o1-mini）会在 `reasoning_content` 字段返回推理过程：

**响应示例**：

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "model": "o1-preview",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "最终答案是 42。",
      "reasoning_content": "首先我需要分析这个问题...\n然后考虑各种可能性...\n最终得出结论..."
    },
    "finish_reason": "stop"
  }]
}
```

**流式响应**：

```
data: {"choices":[{"delta":{"reasoning_content":"首先我需要"}}]}
data: {"choices":[{"delta":{"reasoning_content":"分析..."}}]}
data: {"choices":[{"delta":{"content":"最终答案"}}]}
```

#### Anthropic 的 Extended Thinking

Anthropic 的 Claude 3.5 Sonnet 及更新模型支持 extended thinking 功能，使用 `thinking` content block：

**响应示例**：

```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "thinking",
      "thinking": "让我思考一下这个问题...\n首先需要考虑...\n然后分析..."
    },
    {
      "type": "text",
      "text": "最终答案是 42。"
    }
  ],
  "model": "claude-3-5-sonnet-20241022"
}
```

**流式响应**：

```
event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"thinking","thinking":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"thinking_delta","thinking":"让我思考..."}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"text_delta","text":"最终答案"}}
```

#### 格式转换

代理服务会自动在两种格式之间转换推理内容：

- **OpenAI → Anthropic**：`reasoning_content` 字段转换为 `thinking` content block（索引 0）
- **Anthropic → OpenAI**：`thinking` content block 转换为 `reasoning_content` 字段

这样无论后端使用哪种格式，客户端都能收到正确格式的推理内容！

### 健康检查

**路径**：`GET /health`

**响应**：

```json
{
  "status": "ok",
  "service": "interface_proxy",
  "backend_url": "http://127.0.0.1:8000"
}
```

## 使用示例

### Python + OpenAI SDK

```python
from openai import OpenAI

# 指向代理服务
client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="dummy"  # 代理服务不需要 API key
)

# 非流式
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)

# 流式
stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Count to 10"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Python + Anthropic SDK

```python
from anthropic import Anthropic

# 指向代理服务
client = Anthropic(
    base_url="http://127.0.0.1:8080",
    api_key="dummy"  # 代理服务不需要 API key
)

# 非流式
response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.content[0].text)

# 流式
with client.messages.stream(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Count to 10"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="")
```

## 架构说明

### 适配器模式

本项目采用**适配器模式**（Adapter Pattern）实现格式转换：

```
客户端请求 → 路由层 → 适配器（外部→内部） → 后端代理 → 模型服务
                                                          ↓
客户端响应 ← 适配器（内部→外部） ← 后端代理 ← 模型服务响应
```

**核心思想**：
1. **统一内部格式**：定义统一的内部数据格式，避免 N×N 格式转换
2. **适配器解耦**：每个格式适配器独立，互不影响
3. **双向转换**：每个适配器实现请求和响应的双向转换

### 项目结构

```
interface_proxy/
├── proxy_server.py              # 服务启动入口
├── requirements.txt             # Python 依赖
├── config/
│   └── config.yaml              # 配置文件
├── proxy_app/                   # 核心代理模块
│   ├── app.py                   # FastAPI 应用和路由
│   ├── config.py                # 配置管理
│   ├── models/                  # 数据模型定义
│   │   ├── common.py            # 内部统一格式
│   │   ├── openai_models.py     # OpenAI 格式模型
│   │   └── anthropic_models.py  # Anthropic 格式模型
│   ├── adapters/                # 格式适配器
│   │   ├── base_adapter.py      # 适配器基类
│   │   ├── openai_adapter.py    # OpenAI 格式适配
│   │   └── anthropic_adapter.py # Anthropic 格式适配
│   ├── proxy/                   # 代理核心逻辑
│   │   └── backend_proxy.py     # 后端转发逻辑
│   └── utils/                   # 工具函数
│       ├── http_client.py       # HTTP 客户端封装
│       └── logger.py            # 日志配置
├── tests/                       # 测试
└── examples/                    # 使用示例
```

## 扩展指南

### 如何添加新的格式适配器

1. **定义数据模型**（`proxy_app/models/your_format_models.py`）：
   ```python
   from pydantic import BaseModel

   class YourFormatRequest(BaseModel):
       # 定义请求字段
       pass

   class YourFormatResponse(BaseModel):
       # 定义响应字段
       pass
   ```

2. **实现适配器**（`proxy_app/adapters/your_format_adapter.py`）：
   ```python
   from proxy_app.adapters.base_adapter import BaseAdapter

   class YourFormatAdapter(BaseAdapter):
       def adapt_request(self, request_data):
           # 外部格式 → 内部格式
           pass

       def adapt_response(self, internal_response):
           # 内部格式 → 外部格式
           pass

       async def adapt_streaming_response(self, internal_stream):
           # 流式响应转换
           pass
   ```

3. **添加路由**（在 `proxy_app/app.py` 的 `register_routes()` 中）：
   ```python
   @app.post("/your/path")
   async def your_format_endpoint(request: YourFormatRequest):
       adapter = YourFormatAdapter()
       return await handle_request(request, adapter)
   ```

4. **更新配置**（`config/config.yaml`）：
   ```yaml
   routes:
     your_format_enabled: true
   ```

## 配置说明

### config.yaml 参数详解

```yaml
backend:
  url: "http://127.0.0.1:8000"
    # 后端模型服务地址
    # 示例：http://127.0.0.1:8000, http://your-server:8000

  timeout: 600.0
    # 请求超时时间（秒）
    # 推荐：流式请求设置较大值（600-1200秒）

  max_connections: 100
    # HTTP 连接池最大连接数
    # 根据并发量调整，一般 50-200

  max_keepalive_connections: 20
    # HTTP 连接池最大保活连接数
    # 一般设置为 max_connections 的 10-20%

server:
  host: "0.0.0.0"
    # 监听地址
    # "0.0.0.0" - 监听所有网卡
    # "127.0.0.1" - 只监听本地

  port: 8080
    # 监听端口

  log_level: "INFO"
    # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL

routes:
  openai_enabled: true
    # 是否启用 OpenAI 格式接口 /v1/chat/completions

  anthropic_enabled: true
    # 是否启用 Anthropic 格式接口 /v1/messages
```

## 性能优化

- **异步架构**：基于 FastAPI + httpx 的异步 I/O
- **连接池**：复用 HTTP 连接，减少建立连接开销
- **流式传输**：支持流式响应，降低首字节延迟
- **内存优化**：流式传输避免大量数据在内存中累积

## 常见问题

### Q: 后端服务不是 OpenAI 格式怎么办？

A: 修改 `proxy_app/proxy/backend_proxy.py` 中的 `_convert_to_backend_format()` 和 `_parse_backend_response()` 方法，适配您的后端格式。

### Q: 如何支持多模态（图片）？

A: Anthropic 适配器已支持多模态 content 格式解析，但需要确保后端服务支持图片输入。

### Q: 性能瓶颈在哪里？

A: 代理层本身开销很小（<5ms），主要延迟来自后端模型推理。可以通过增加 `max_connections` 提高并发能力。

### Q: 如何添加认证？

A: 在 `proxy_app/app.py` 中添加 FastAPI 的 `Depends` 中间件实现 API Key 验证。

## 开发计划

- [ ] 添加单元测试和集成测试
- [ ] 支持更多格式（Google PaLM, Hugging Face TGI 等）
- [ ] 添加多后端负载均衡
- [ ] 添加缓存层（Redis）
- [ ] 添加监控和指标（Prometheus）
- [ ] WebUI 管理界面

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 作者

Interface Proxy Service
