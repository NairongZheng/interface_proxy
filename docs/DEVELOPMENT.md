# Interface Proxy 开发文档

本文档记录 interface_proxy 项目的开发细节、实现思路和使用指南。

## 目录
- [实现总结](#实现总结)
- [Models API 使用指南](#models-api-使用指南)
- [开发日志](#开发日志)
  - [2026-02-13: 实现工具调用（Tool Use）功能](#2026-02-13-实现工具调用tool-use功能)
  - [2026-02-13: 实现 Models API 和根路由](#2026-02-13-实现-models-api-和根路由)
- [技术细节](#技术细节)

---

## 实现总结

### ✅ 已完成的功能

#### 1. 根路由 (GET /)
返回服务基本信息和所有可用端点列表。

#### 2. Models API
- **GET /v1/models** - 列出所有可用模型
- **GET /v1/models/{model_id}** - 获取特定模型详情
- 完全兼容 OpenAI API 规范
- 支持 OpenAI SDK 直接调用

#### 3. 配置管理
在 `config/config.yaml` 中添加了 8 个预配置模型：
- **OpenAI**: gpt-4, gpt-4-turbo, gpt-3.5-turbo, o1-preview, o1-mini
- **Anthropic**: claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-5-sonnet-20241022

### 📁 修改的文件

1. **proxy_app/models/openai_models.py** (+88 行)
   - 新增 `ModelPermission`, `Model`, `ModelList` 数据模型
   - 添加详细的中文注释

2. **config/config.yaml** (+28 行)
   - 新增 `models` 配置段
   - 定义 8 个可用模型

3. **proxy_app/config.py** (+10 行)
   - 新增 `available_models` 属性

4. **proxy_app/app.py** (+142 行)
   - 新增根路由 `/`
   - 新增 `/v1/models` 和 `/v1/models/{model_id}` 路由
   - 所有函数都有详细注释

5. **README.md**
   - 更新文档，添加 Models API 说明
   - 添加使用示例

### 🎯 设计特点

1. **完全兼容 OpenAI API** - 可与 OpenAI SDK 无缝集成
2. **配置驱动** - 通过 YAML 文件灵活管理模型列表
3. **模块化设计** - 代码结构清晰，易于维护
4. **详细注释** - 所有函数和关键逻辑都有中文注释
5. **错误处理** - 提供清晰的错误信息（如模型不存在时返回 404）

---

## Models API 使用指南

### 快速测试

#### 启动服务
```bash
python proxy_server.py
```

#### 测试接口
```bash
# 服务信息
curl http://127.0.0.1:8080/

# 列出所有模型
curl http://127.0.0.1:8080/v1/models

# 获取特定模型
curl http://127.0.0.1:8080/v1/models/gpt-3.5-turbo

# 运行完整测试
python examples/models_api_example.py
```

### API 端点详解

#### 1. 根路由 (GET /)

**请求示例**:
```bash
curl http://127.0.0.1:8080/
```

**响应示例**:
```json
{
  "service": "Interface Proxy Service",
  "version": "1.0.0",
  "description": "LLM 接口代理服务，支持 OpenAI 和 Anthropic 格式互转",
  "endpoints": {
    "health": "/health",
    "openai_chat": "/v1/chat/completions",
    "anthropic_messages": "/v1/messages",
    "models_list": "/v1/models",
    "model_detail": "/v1/models/{model_id}"
  },
  "backend_url": "http://127.0.0.1:8000"
}
```

#### 2. 列出所有模型 (GET /v1/models)

**请求示例**:
```bash
curl http://127.0.0.1:8080/v1/models
```

**响应示例**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1687882411,
      "owned_by": "openai",
      "permission": [
        {
          "id": "modelperm-gpt-4",
          "object": "model_permission",
          "created": 1687882411,
          "allow_create_engine": false,
          "allow_sampling": true,
          "allow_logprobs": true,
          "allow_search_indices": false,
          "allow_view": true,
          "allow_fine_tuning": false,
          "organization": "*",
          "group": null,
          "is_blocking": false
        }
      ],
      "root": "gpt-4",
      "parent": null
    }
  ]
}
```

#### 3. 获取特定模型详情 (GET /v1/models/{model_id})

**请求示例**:
```bash
curl http://127.0.0.1:8080/v1/models/gpt-3.5-turbo
```

**响应示例**:
```json
{
  "id": "gpt-3.5-turbo",
  "object": "model",
  "created": 1677610602,
  "owned_by": "openai",
  "permission": [...],
  "root": "gpt-3.5-turbo",
  "parent": null
}
```

**错误响应** (模型不存在):
```bash
curl http://127.0.0.1:8080/v1/models/non-existent-model
```
```json
{
  "detail": "模型 'non-existent-model' 不存在"
}
```
HTTP 状态码: 404

### 使用 OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="dummy"
)

# 列出所有模型
models = client.models.list()
for model in models.data:
    print(f"{model.id} - {model.owned_by}")

# 获取特定模型信息
model = client.models.retrieve("gpt-3.5-turbo")
print(f"Model: {model.id}, Owner: {model.owned_by}")
```

### 如何添加新模型

编辑 `config/config.yaml`：

```yaml
models:
  available_models:
    - id: "your-new-model"
      owned_by: "your-organization"
      created: 1234567890  # Unix 时间戳
```

重启服务即可生效，无需修改代码！

### 支持的模型列表

当前配置支持以下模型：

#### OpenAI 模型
- `gpt-4`
- `gpt-4-turbo`
- `gpt-3.5-turbo`
- `o1-preview`
- `o1-mini`

#### Anthropic 模型
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-5-sonnet-20241022`

---

## 开发日志

### 2026-02-13: 实现工具调用（Tool Use）功能

#### 问题背景

之前的代理服务不支持工具调用功能，导致 Claude Code CLI 无法正常工作：
- 模型想调用工具（如 Task、Read、Bash 等）时，只能返回文本描述 `[Task(subagent_type="Explore")]`
- 原因：请求中的 `tools` 参数未转发，响应中的 `tool_use` content block 无法处理

#### 实现内容

**Phase 1: 基础工具调用支持（必需功能）**

1. **扩展 Anthropic 数据模型** (`proxy_app/models/anthropic_models.py`)
   - 新增 `ToolInputSchema`：工具输入参数的 JSON Schema 定义
   - 新增 `Tool`：工具定义模型（name, description, input_schema）
   - 新增 `ToolUseContentBlock`：工具调用内容块（模型请求调用工具）
   - 新增 `ToolResultContentBlock`：工具结果内容块（返回工具执行结果）
   - 更新 `ContentBlock` 联合类型：包含 tool_use 和 tool_result
   - 更新 `AnthropicMessagesRequest`：添加 `tools` 参数
   - 更新 `AnthropicMessagesResponse`：content 支持 `ToolUseContentBlock`，stop_reason 支持 `tool_use`

2. **扩展内部统一格式** (`proxy_app/models/common.py`)
   - 更新 `InternalMessage.content`：支持 `str | List[Dict[str, Any]]`（用于 tool_result）
   - 更新 `InternalRequest`：添加 `tools` 字段

3. **更新 Anthropic 适配器** (`proxy_app/adapters/anthropic_adapter.py`)

   **请求转换** (`adapt_request`):
   - 将 Anthropic 格式的 tools 转换为 OpenAI 格式
   - Anthropic 格式：`Tool(name, description, input_schema)`
   - OpenAI 格式：`{"type": "function", "function": {...}}`
   - 更新 `_extract_text_content`：支持 tool_result（返回结构化内容）

   **非流式响应转换** (`adapt_response`):
   - 将 OpenAI 格式的 tool_calls 转换为 Anthropic 格式的 tool_use
   - OpenAI：`{"id": "...", "function": {"name": "...", "arguments": "..."}}`
   - Anthropic：`{"type": "tool_use", "id": "...", "name": "...", "input": {...}}`
   - 解析 JSON 格式的 arguments 字符串
   - 更新 `_map_finish_reason`：`tool_calls` → `tool_use`

   **流式响应转换** (`adapt_streaming_response`):
   - 处理增量工具调用数据（delta_tool_calls）
   - 缓存和累积工具调用数据（id, name, arguments）
   - 发送 Anthropic SSE 事件序列：
     - `content_block_start`：tool_use block 开始
     - `content_block_delta`：增量 JSON 参数（input_json_delta）
     - `content_block_stop`：tool_use block 结束
   - 正确处理多个工具调用的索引管理

4. **更新后端代理** (`proxy_app/proxy/backend_proxy.py`)
   - 在 `_convert_to_backend_format` 中添加 `tools` 到可选参数列表
   - 将工具定义转发给后端模型服务

#### 技术亮点

1. **格式转换**：
   - Anthropic 使用 `input_schema`，OpenAI 使用 `parameters`
   - Anthropic 使用 `tool_use`，OpenAI 使用 `tool_calls`
   - 正确映射 `stop_reason: tool_use` ↔ `finish_reason: tool_calls`

2. **流式处理复杂性**：
   - 工具调用的 arguments 可能跨多个流式块
   - 需要缓存和累积完整的 JSON 数据
   - 正确管理多个 content block 的索引（thinking → tool_use → text）

3. **多轮工具调用支持**：
   - `tool_result` 消息以结构化内容传递
   - 保留完整的 content block 列表，而不只是提取文本

#### 代码变更统计

- `proxy_app/models/anthropic_models.py`: +100 行（工具模型定义）
- `proxy_app/models/common.py`: +10 行（内部格式更新）
- `proxy_app/adapters/anthropic_adapter.py`: +150 行（工具转换逻辑）
- `proxy_app/proxy/backend_proxy.py`: +1 行（转发 tools 参数）
- `docs/TOOL_USE_IMPLEMENTATION_PLAN.md`: 新文件（实现计划文档）

#### 测试验证

**基础功能**：
- ✅ 接受带 tools 参数的请求
- ✅ 转发工具定义到后端
- ✅ 解析非流式工具调用响应
- ✅ 转换为 Anthropic 格式

**流式功能**：
- ✅ 处理增量工具调用
- ✅ 正确发送 SSE 事件序列
- ✅ 支持多个工具调用

**Claude Code CLI 兼容**：
- ✅ 模型可以正确调用工具（Task, Read, Bash 等）
- ✅ 工具结果可以正确返回给模型
- ✅ 支持多轮工具调用循环

#### 下一步优化

1. ⏱ 添加单元测试覆盖工具调用场景
2. ⏱ 添加工具调用示例到 examples/
3. ⏱ 优化流式响应的 JSON 解析（检测完整 JSON）
4. ⏱ 添加工具调用监控和日志

#### 参考文档

- [Anthropic Tool Use API 文档](https://docs.anthropic.com/claude/docs/tool-use)
- [OpenAI Function Calling 文档](https://platform.openai.com/docs/guides/function-calling)
- [实现计划文档](./TOOL_USE_IMPLEMENTATION_PLAN.md)

---

### 2026-02-13: 实现 Models API 和根路由

#### 开发目标
实现 OpenAI Models API 兼容的端点，让客户端可以查询代理服务支持的模型列表。

#### 实现的功能

**1. 根路由 (GET /)**
- **目的**: 提供服务的基本信息和可用端点列表
- **实现位置**: `proxy_app/app.py:113-133`
- **核心逻辑**:
  - 返回服务名称、版本、描述
  - 列出所有可用的端点路径
  - 根据配置动态显示启用/禁用的端点

**2. Models API (GET /v1/models)**
- **目的**: 列出所有配置的可用模型
- **实现位置**: `proxy_app/app.py:153-210`
- **核心逻辑**:
  - 从配置文件读取 `models.available_models` 列表
  - 为每个模型创建 `Model` 和 `ModelPermission` 对象
  - 返回符合 OpenAI API 规范的 `ModelList` 响应

**关键实现细节**:
- 模型权限使用默认配置（allow_sampling=true, allow_view=true）
- 支持 OpenAI 和 Anthropic 两种提供商的模型
- 完全兼容 OpenAI SDK 的 `client.models.list()` 调用

**3. Model Detail API (GET /v1/models/{model_id})**
- **目的**: 获取特定模型的详细信息
- **实现位置**: `proxy_app/app.py:212-276`
- **核心逻辑**:
  - 根据 `model_id` 在配置中查找对应模型
  - 如果模型不存在，返回 404 错误
  - 返回符合 OpenAI API 规范的 `Model` 响应

**关键实现细节**:
- 使用线性搜索在配置列表中查找模型
- 提供清晰的错误信息（"模型 'xxx' 不存在"）
- 完全兼容 OpenAI SDK 的 `client.models.retrieve()` 调用

#### 设计思路

**为什么需要 Models API？**
1. **兼容性**: OpenAI SDK 客户端通常会先调用 `list()` 检查可用模型
2. **透明性**: 让用户清楚代理服务支持哪些模型
3. **动态配置**: 通过配置文件灵活管理模型列表，无需修改代码

**数据流**:
```
客户端请求
  ↓
GET /v1/models
  ↓
从 config.yaml 读取 models.available_models
  ↓
构建 Model 和 ModelPermission 对象
  ↓
返回 ModelList JSON 响应
```

**配置驱动设计**:
- 模型列表完全由配置文件管理
- 添加新模型只需编辑 `config.yaml`
- 支持任意 LLM 提供商（OpenAI、Anthropic、Google 等）

#### 模块化设计

遵循项目的模块化原则：
- **数据模型** (`models/openai_models.py`): 定义 API 数据结构
- **配置管理** (`config.py`): 统一管理配置读取
- **路由层** (`app.py`): 处理 HTTP 请求和响应
- **文档** (`docs/DEVELOPMENT.md`): 开发文档
- **示例** (`examples/models_api_example.py`): 可执行的测试代码

每个模块职责清晰，便于维护和扩展。

---

## 技术细节

### 实现细节

#### 数据模型
在 `proxy_app/models/openai_models.py` 中新增了以下数据模型：
- `ModelPermission`: 模型权限信息
- `Model`: 单个模型的详细信息
- `ModelList`: 模型列表响应

#### 配置文件
在 `config/config.yaml` 中新增了 `models` 配置段，包含可用模型列表：
```yaml
models:
  available_models:
    - id: "gpt-4"
      owned_by: "openai"
      created: 1687882411
```

#### 配置管理
在 `proxy_app/config.py` 中新增了 `available_models` 属性，用于读取配置文件中的模型列表。

#### 路由实现
在 `proxy_app/app.py` 的 `register_routes()` 函数中新增了三个路由：
1. `GET /` - 根路由
2. `GET /v1/models` - 列出所有模型
3. `GET /v1/models/{model_id}` - 获取特定模型详情

### 注释风格

按照要求添加了详细的中文注释：
- **类注释**: 说明类的用途和属性
- **函数注释**: 说明功能、参数、返回值、异常
- **关键逻辑注释**: 在代码中标注重要步骤
- **示例**: 在函数注释中提供 API 使用示例

### Pydantic 模型验证
- 所有数据模型使用 Pydantic 进行自动验证
- `model_dump()` 方法自动将对象转换为字典
- 类型安全，减少运行时错误

### FastAPI 路径参数
- `{model_id}` 自动解析为函数参数
- FastAPI 自动处理 URL 编码和解码

### 错误处理
- 使用 `HTTPException` 返回标准 HTTP 错误
- 提供清晰的中文错误信息

### 代码质量

- ✅ 通过 Python 语法检查
- ✅ 遵循项目现有的代码风格
- ✅ 添加了完整的类型注解
- ✅ 所有函数都有详细的文档字符串
- ✅ 关键逻辑都有注释说明

### 兼容性

- ✅ 完全兼容 OpenAI Models API 规范
- ✅ 可直接与 OpenAI SDK 配合使用
- ✅ 向后兼容，不影响现有功能
- ✅ 配置文件向后兼容（使用 `get()` 提供默认值）

### 测试建议

运行测试示例：
```bash
# 启动代理服务
python proxy_server.py

# 在另一个终端运行测试
python examples/models_api_example.py
```

测试覆盖：
1. 根路由 - 获取服务信息
2. 列出所有模型（原始 HTTP + OpenAI SDK）
3. 获取特定模型详情（存在 + 不存在）
4. 健康检查

### 未来扩展建议

1. **动态模型发现**:
   - 可以添加功能，从后端服务动态获取可用模型列表
   - 目前是静态配置，未来可以考虑实现自动发现

2. **模型能力标注**:
   - 在配置中添加每个模型的能力标注（如：支持函数调用、最大上下文长度等）
   - 客户端可以根据能力选择合适的模型

3. **模型别名**:
   - 支持为模型配置别名（如：`gpt-4-latest` 指向 `gpt-4-turbo`）
   - 便于版本管理和向后兼容

4. **缓存优化**:
   - 模型列表可以缓存，避免每次请求都重新构建
   - 配置文件变更时自动刷新缓存

---

## 注意事项

1. **模型列表仅用于信息展示**：这些模型配置只是告诉客户端代理服务"认识"哪些模型，实际的模型推理能力取决于后端服务。
2. **模型 ID 的作用**：客户端在调用 `/v1/chat/completions` 或 `/v1/messages` 时可以指定这些模型 ID，代理服务会将请求转发到后端。
3. **扩展性**：如果需要添加新的 LLM 提供商（如 Google、Cohere 等），只需在配置文件中添加相应的模型即可。
