# Extra Body 参数支持文档

## 概述

Interface Proxy 现已支持 OpenAI SDK 的 `extra_body` 参数，允许用户传递任意额外参数到后端服务。同时，后端返回的额外字段也会被保留并传递回客户端。这使得 proxy 能够支持现代 LLM 的高级功能，如思考模式、推理模式、自定义模板参数等。

## 功能特性

### 请求参数支持 ✅
- ✅ 自动提取 `extra_body` 参数
- ✅ 透明传递到后端（OpenAI、PTU）
- ✅ 支持所有数据类型（布尔、数字、字符串、列表、字典）

### 响应字段支持 ✅ **新增**
- ✅ 自动提取后端返回的额外字段
- ✅ 透明传递到客户端
- ✅ 支持流式和非流式输出
- ✅ 保留字段完整性（无数据丢失）

### 通用特性
- ✅ 向后兼容，不影响现有功能
- ✅ 完整的日志记录和调试支持

## 使用方法

### 基础用法

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="your-api-key"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Hello"}],
    extra_body={
        "enable_thinking": True
    }
)
```

### 常见参数

#### 1. 思考模式 (enable_thinking)

适用于 DeepSeek 等支持思考的模型：

```python
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[...],
    extra_body={
        "enable_thinking": True
    }
)
```

#### 2. 思考配置 (thinking)

适用于 o1 系列模型：

```python
response = client.chat.completions.create(
    model="o1-preview",
    messages=[...],
    extra_body={
        "thinking": {
            "type": "enable",
            "budget": "high"
        }
    }
)
```

#### 3. 推理模式 (reasoning_mode)

控制推理质量：

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    extra_body={
        "reasoning_mode": "high"
    }
)
```

#### 4. 聊天模板参数 (chat_template_kwargs)

适用于 Qwen 等模型：

```python
response = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[...],
    extra_body={
        "chat_template_kwargs": {
            "add_generation_prompt": True,
            "temperature": 0.9
        }
    }
)
```

## 工作原理

### 请求参数流 (客户端 → 后端)

```
客户端请求 (extra_body)
    ↓
ChatCompletionRequest (__pydantic_extra__)
    ↓
adapt_request() 提取额外参数
    ↓
InternalRequest (extra_params 字段)
    ↓
_build_*_request() 合并到顶层
    ↓
后端请求 (包含所有参数)
```

### 响应字段流 (后端 → 客户端) ✨**新增**

```
后端响应 (包含额外字段)
    ↓
_parse_openai_response() 提取额外字段
    ↓
InternalResponse (extra_fields 字段)
    ↓
adapt_response() 合并到响应对象
    ↓
ChatCompletionResponse (extra="allow")
    ↓
客户端接收 (包含所有额外字段)
```

### 核心实现

#### 1. 数据模型 (common.py)

```python
class InternalRequest(TypedDict, total=False):
    # ... 标准字段 ...
    extra_params: Optional[Dict[str, Any]]  # 新增
```

#### 2. 参数提取 (openai_adapter.py)

```python
def adapt_request(self, request_data: ChatCompletionRequest) -> InternalRequest:
    # 提取 Pydantic 的额外字段
    if hasattr(request_data, "__pydantic_extra__") and request_data.__pydantic_extra__:
        extra_params = dict(request_data.__pydantic_extra__)
        internal_request["extra_params"] = extra_params
```

#### 3. 参数合并 (openai_adapter.py / ptu_adapter.py)

```python
def _build_openai_request(self, internal_request: InternalRequest) -> dict:
    # 合并额外参数到顶层
    if "extra_params" in internal_request:
        openai_request.update(internal_request["extra_params"])
```

## 测试验证

### 运行单元测试

```bash
# 使用 pytest
pytest tests/test_extra_params.py -v

# 或直接运行
python tests/test_extra_params.py
```

### 运行示例

```bash
# 启动 proxy 服务
python proxy_app/main.py

# 运行示例
python examples/extra_params_example.py
```

## 支持的后端

| 后端类型 | 是否支持 | 说明 |
|---------|---------|------|
| OpenAI | ✅ | 直接传递所有额外参数 |
| PTU | ✅ | 通过 Gateway 传递到下游服务 |
| Anthropic | ✅ | 继承 OpenAI 适配器的实现 |

## 注意事项

1. **参数验证**：proxy 不会验证额外参数，由后端负责
2. **参数冲突**：如果 `extra_body` 与标准参数重名，会覆盖标准参数
3. **后端兼容性**：后端必须支持相应参数，否则可能被忽略或报错
4. **日志记录**：所有额外参数都会记录到 DEBUG 日志中

## 故障排查

### 参数未生效

1. 检查日志中是否有"提取到 N 个额外参数"
2. 检查日志中是否有"合并 N 个额外参数到后端请求"
3. 确认后端支持该参数

### 后端报错

1. 查看后端错误信息
2. 确认参数名称和格式正确
3. 尝试去掉额外参数，测试标准功能

## 示例场景

### 场景 1: 启用 DeepSeek 思考模式

```python
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "为什么天空是蓝色的？"}],
    extra_body={"enable_thinking": True}
)

# 可能包含 reasoning_content
if hasattr(response.choices[0].message, 'reasoning_content'):
    print(response.choices[0].message.reasoning_content)
```

### 场景 2: 配置 o1 推理预算

```python
response = client.chat.completions.create(
    model="o1-preview",
    messages=[{"role": "user", "content": "设计一个缓存系统"}],
    extra_body={
        "thinking": {"type": "enable", "budget": "high"}
    }
)
```

### 场景 3: 组合多个参数

```python
response = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[...],
    temperature=0.7,
    max_tokens=500,
    extra_body={
        "enable_thinking": True,
        "reasoning_mode": "high",
        "chat_template_kwargs": {"add_generation_prompt": True}
    }
)
```

## 技术细节

### Pydantic Extra Fields

OpenAI SDK 使用 Pydantic v2，通过 `Config.extra = "allow"` 允许额外字段。这些字段存储在 `__pydantic_extra__` 属性中。

### TypedDict 可选字段

使用 `total=False` 使得 `extra_params` 成为可选字段：

```python
class InternalRequest(TypedDict, total=False):
    extra_params: Optional[Dict[str, Any]]
```

### 参数合并策略

使用 `dict.update()` 合并参数，后者覆盖前者：

```python
openai_request.update(extra_params)
```

## 版本历史

- **v1.0** (2024-03-02): 初始实现
  - 支持 OpenAI 和 PTU 后端
  - 完整的测试覆盖
  - 文档和示例

## 相关文档

- [架构文档](ARCHITECTURE.md)
- [开发指南](DEVELOPMENT.md)
- [PTU 集成](PTU_INTEGRATION.md)
