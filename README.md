# Interface Proxy Service

接口代理服务，实现不同 LLM 接口格式之间的互相转换和转发。

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🌟 核心特性

### 格式转换

- ✅ **OpenAI ↔ Anthropic** 格式互转
- ✅ **OpenAI → PTU** 自动识别和处理
- ✅ **统一接口** 用标准 SDK 调用任何后端
- ✅ **流式支持** 完整支持 SSE 流式响应

### 高级功能

- ✅ **推理内容支持** OpenAI o1 和 Anthropic Extended Thinking
- ✅ **工具调用支持** 完整支持 Tool Use，兼容 Claude Code CLI
- ✅ **多模型支持** 30+ PTU 模型（Doubao, DeepSeek, Qwen）
- ✅ **自动路由** 根据模型自动选择后端

### 架构优势

- ✅ **适配器模式** 清晰的职责分离，易于扩展
- ✅ **异步架构** FastAPI + httpx，高性能
- ✅ **配置驱动** YAML 配置，灵活管理
- ✅ **对用户透明** 无需修改客户端代码

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置服务

编辑 `config/config.yaml`：

```yaml
# 后端服务配置
backend:
  url: "https://api.ppchat.vip"      # 标准 OpenAI 后端
  api_key: "your-api-key"
  timeout: 600.0

# PTU 后端配置
ptu:
  backend_url: "http://api.schedule.mtc.sensetime.com"  # PTU Gateway
  models:
    - "Doubao-1.5-pro-32k"
    - "qwen3.5-plus"
    - "DeepSeek-V3"
    # ...

# 路由配置
routes:
  openai_enabled: true
  anthropic_enabled: true
```

### 3. 启动服务

```bash
# 使用默认配置
python proxy_server.py

# 指定端口
python proxy_server.py --port 8080

# 开发模式（自动重载）
python proxy_server.py --reload
```

### 4. 测试服务

**查看服务信息**：

```bash
curl http://127.0.0.1:8080/
```

**列出可用模型**：

```bash
curl http://127.0.0.1:8080/v1/models
```

## 💡 使用示例

### Python + OpenAI SDK

```python
from openai import OpenAI

# 指向代理服务
client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="dummy",  # 代理服务不需要真实 key
)

# 调用标准模型
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)

# 调用 PTU 模型（自动识别和转换）
response = client.chat.completions.create(
    model="Doubao-1.5-pro-32k",  # PTU 模型
    messages=[{"role": "user", "content": "你好"}]
)

# 流式调用
stream = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[{"role": "user", "content": "数到10"}],
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
    api_key="dummy",
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

### curl 命令行

**OpenAI 格式 - 非流式请求**：

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 100
  }'
```

**OpenAI 格式 - PTU 模型请求**：

```bash
# 调用 Doubao 模型
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy" \
  -d '{
    "model": "Doubao-1.5-pro-32k",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "max_tokens": 100
  }'

# 调用 Qwen 模型
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-plus",
    "messages": [
      {"role": "user", "content": "介绍一下你自己"}
    ],
    "max_tokens": 200
  }'

# 调用 DeepSeek 模型
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "DeepSeek-V3",
    "messages": [
      {"role": "user", "content": "写一个冒泡排序"}
    ],
    "max_tokens": 500
  }'
```

**OpenAI 格式 - 流式请求**：

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy" \
  -d '{
    "model": "Doubao-1.5-pro-32k",
    "messages": [
      {"role": "user", "content": "数到10"}
    ],
    "stream": true,
    "max_tokens": 100
  }'
```

**Anthropic 格式 - 非流式请求**：

```bash
curl -X POST http://127.0.0.1:8080/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: dummy" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

**Anthropic 格式 - 流式请求**：

```bash
curl -X POST http://127.0.0.1:8080/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: dummy" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-opus-20240229",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Count to 10"}
    ],
    "stream": true
  }'
```

**查询可用模型列表**：

```bash
# 列出所有可用模型
curl http://127.0.0.1:8080/v1/models

# 获取特定模型详情
curl http://127.0.0.1:8080/v1/models/Doubao-1.5-pro-32k

# 使用 jq 格式化输出
curl -s http://127.0.0.1:8080/v1/models | jq '.data[] | {id, owned_by}'
```

## 🎯 工作原理

### 架构概览

```
用户 (OpenAI SDK)  →  /v1/chat/completions  →  OpenAIAdapter   →  标准后端
用户 (OpenAI SDK)  →  /v1/chat/completions  →  PTUAdapter      →  PTU Gateway
用户 (Anthropic SDK) → /v1/messages         →  AnthropicAdapter → 标准后端
```

### 处理流程

1. **接收请求** → FastAPI 路由识别格式
2. **选择 Adapter** → 根据模型和格式选择
3. **格式转换** → 外部格式 → 内部格式
4. **后端调用** → Adapter 调用对应后端
5. **响应转换** → 内部格式 → 外部格式
6. **返回结果** → 用户收到期望格式的响应

### 关键特性

**自动识别 PTU 模型**：

```python
# config.yaml 中配置 PTU 模型列表
ptu:
  models:
    - "Doubao-1.5-pro-32k"
    - "qwen3.5-plus"

# 代理自动识别并使用 PTUAdapter
if config.is_ptu_model(request.model):
    adapter = PTUAdapter(...)  # PTU Gateway
else:
    adapter = OpenAIAdapter(...)  # 标准后端
```

**PTU 格式处理**：

```python
# PTU 返回包装格式
{
  "code": 10000,
  "msg": "成功",
  "data": {
    "response_content": {
      # 内层是标准 OpenAI 格式
      "choices": [...],
      "usage": {...}
    }
  }
}

# PTUAdapter 自动解包并返回标准格式
```

## 📂 项目结构

```
interface_proxy/
├── proxy_server.py              # 🚀 服务启动入口
├── requirements.txt             # 📦 Python 依赖
├── config/
│   └── config.yaml              # ⚙️ 配置文件
├── proxy_app/                   # 核心代理模块
│   ├── app.py                   # FastAPI 应用和路由
│   ├── config.py                # 配置管理
│   ├── models/                  # 数据模型定义
│   │   ├── common.py            # 内部统一格式
│   │   ├── openai_models.py     # OpenAI 格式
│   │   └── anthropic_models.py  # Anthropic 格式
│   ├── adapters/                # 🔌 格式适配器
│   │   ├── base_adapter.py      # 适配器基类
│   │   ├── openai_adapter.py    # OpenAI 适配器
│   │   ├── anthropic_adapter.py # Anthropic 适配器
│   │   └── ptu_adapter.py       # PTU 适配器
│   └── utils/                   # 工具函数
│       ├── http_client.py       # HTTP 客户端
│       └── logger.py            # 日志配置
├── tests/                       # 🧪 测试
│   ├── README.md                # 测试指南
│   ├── test_integration.py      # 集成测试（推荐）
│   ├── test_adapter_units.py    # Adapter 单元测试
│   ├── test_adapters.py         # 格式转换测试
│   ├── test_ptu_adapter.py      # PTU 适配器测试
│   └── test_api_key.sh          # API Key 验证脚本
├── examples/                    # 📝 使用示例
│   ├── openai_example.py        # OpenAI SDK 示例
│   ├── anthropic_example.py     # Anthropic SDK 示例
│   ├── ptu_example.py           # PTU 模型示例
│   └── curl_examples.sh         # curl 命令行示例（推荐）
└── docs/                        # 📚 文档
    ├── ARCHITECTURE.md          # 架构文档（详细）
    ├── DEVELOPMENT.md           # 开发文档
    ├── PTU_INTEGRATION.md       # PTU 集成说明
    └── PTU_IMPLEMENTATION_SUMMARY.md  # PTU 实施总结
```

## 🧪 测试

### 快速测试

```bash
# 1. 启动服务
python proxy_server.py

# 2. 运行集成测试（推荐）
python tests/test_integration.py
```

测试涵盖：
- ✅ OpenAI 格式 → 标准后端
- ✅ OpenAI 格式 → PTU 后端
- ✅ Anthropic 格式 → OpenAI 后端
- ✅ 流式和非流式响应
- ✅ Models API

详见 [测试指南](tests/README.md)。

## 🔧 配置说明

### Backend 配置

```yaml
backend:
  url: "https://api.ppchat.vip"  # 后端 URL
  api_key: "your-key"            # API Key
  timeout: 600.0                 # 超时（秒）
  max_connections: 100           # 最大连接数
```

### PTU 配置

```yaml
ptu:
  backend_url: "http://api.schedule.mtc.sensetime.com"  # PTU Gateway
  models:                        # PTU 模型列表
    - "Doubao-1.5-pro-32k"
    - "Doubao-1.5-thinking-pro"
    - "DeepSeek-R1"
    - "DeepSeek-V3"
    - "qwen3.5-plus"
    - "qwen3.5-flash"
    # ... 更多模型
```

### Routes 配置

```yaml
routes:
  openai_enabled: true           # 启用 OpenAI 接口
  anthropic_enabled: true        # 启用 Anthropic 接口
```

## 🔌 API 端点

| 端点 | 格式 | 说明 |
|------|------|------|
| `GET /` | - | 服务信息 |
| `GET /health` | - | 健康检查 |
| `GET /v1/models` | OpenAI | 列出所有模型 |
| `GET /v1/models/{id}` | OpenAI | 获取模型详情 |
| `POST /v1/chat/completions` | OpenAI | Chat Completions |
| `POST /v1/messages` | Anthropic | Messages API |

## 📖 文档

- **[架构文档](docs/ARCHITECTURE.md)** - 详细架构设计和工作原理
- **[开发文档](docs/DEVELOPMENT.md)** - 实现细节和开发指南
- **[PTU 集成](docs/PTU_INTEGRATION.md)** - PTU 后端集成说明
- **[测试指南](tests/README.md)** - 完整的测试文档

## 🛠️ 扩展指南

### 添加新格式适配器

1. **定义数据模型**（`proxy_app/models/your_format_models.py`）

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

       async def forward(self, internal_request):
           # 调用后端服务
           pass
   ```

3. **添加路由**（在 `proxy_app/app.py` 中）：
   ```python
   @app.post("/your/path")
   async def your_endpoint(request: YourFormatRequest):
       adapter = YourFormatAdapter(...)
       return await handle_request(request, adapter)
   ```

4. **更新配置**（`config/config.yaml`）

## 🎨 设计模式

本项目采用 **适配器模式**（Adapter Pattern）：

**核心思想**：
- 定义统一的内部格式
- 每个适配器负责格式转换和后端调用
- 适配器之间完全解耦

**优势**：
- 📦 模块化：每个格式适配器独立
- 🔧 可扩展：添加新格式只需新增适配器
- 🧹 清晰：职责分离，易于维护
- 🚀 高效：异步架构，高性能

详见 [架构文档](docs/ARCHITECTURE.md)。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

添加新功能时，请：
1. 编写相应的测试
2. 更新相关文档
3. 遵循现有代码风格

## 📝 开发计划

- [x] ~~OpenAI 和 Anthropic 格式互转~~ ✅
- [x] ~~PTU 后端支持（30+ 模型）~~ ✅
- [x] ~~工具调用支持~~ ✅
- [x] ~~推理内容支持~~ ✅
- [x] ~~新架构：Adapter 负责后端调用~~ ✅
- [ ] 支持更多格式（Google PaLM, Hugging Face TGI 等）
- [ ] 多后端负载均衡
- [ ] 缓存层（Redis）
- [ ] 监控和指标（Prometheus）
- [ ] WebUI 管理界面

## 📄 许可证

MIT License

## 👨‍💻 作者

Interface Proxy Service

---

**相关链接**：
- 📖 [架构文档](docs/ARCHITECTURE.md)
- 🧪 [测试指南](tests/README.md)
- 💡 [使用示例](examples/)

最后更新：2026-03-02
