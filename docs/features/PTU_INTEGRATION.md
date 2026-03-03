# PTU 后端集成文档

## 概述

本文档介绍如何在 interface_proxy 项目中集成 PTU（第三方供应商）后端支持。用户可以通过标准 OpenAI 接口调用 PTU 模型，系统会自动识别并处理格式转换。

## 什么是 PTU 后端

PTU 后端是一个特殊的 LLM 服务后端，它返回**包装的 OpenAI 格式**：

```json
{
  "code": 10000,  // 10000=成功，10001=错误
  "msg": "成功",
  "data": {
    "task_id": 58857509,
    "response_content": {
      // 内层是标准 OpenAI 格式
      "id": "chatcmpl-123",
      "model": "Doubao-1.5-pro-32k",
      "choices": [...],
      "usage": {...}
    }
  }
}
```

**关键特性**：
- 外层：PTU 状态码和包装（code, msg, data）
- 内层：标准 OpenAI 格式响应（response_content）
- 支持多种模型：Doubao、DeepSeek、Qwen 等
- 需要额外参数：`channel_code`（doubao/ali/azure）、`transaction_id`

## 架构设计

### 设计原则

采用**方案 B：路由层智能选择适配器**，原因：
1. 符合适配器模式设计原则
2. PTU 的包装格式是它的特性，应该由适配器处理
3. 清晰的职责分离：路由选择，适配器转换
4. 良好的扩展性

### 架构流程

```
用户调用（OpenAI SDK）
   ↓
路由层（app.py）：根据模型选择适配器
   ├─ PTU 模型 → PTUAdapter
   └─ 标准模型 → OpenAIAdapter
   ↓
适配器：格式转换
   ├─ 请求：OpenAI 格式 → 内部格式
   └─ 响应：内部格式 → OpenAI 格式
   ↓
BackendProxy：根据适配器类型选择后端
   ├─ PTUAdapter → 调用 PTU 后端，解包响应
   └─ OpenAIAdapter → 调用标准后端
   ↓
后端服务（PTU 或标准）
```

### 核心组件

1. **PTUAdapter** (`proxy_app/adapters/ptu_adapter.py`)
   - 继承自 `OpenAIAdapter`
   - 提供 `unwrap_ptu_response()` 静态方法解包 PTU 响应
   - 提供 `infer_channel_code()` 静态方法推断 channel_code

2. **BackendProxy** (`proxy_app/proxy/backend_proxy.py`)
   - 根据 `adapter` 参数判断后端类型
   - PTU 后端：添加 `channel_code` 参数，解包响应
   - 标准后端：保持原有逻辑

3. **路由层** (`proxy_app/app.py`)
   - 根据 `config.is_ptu_model()` 选择适配器
   - 传递 `adapter` 给 `handle_request()`

4. **配置** (`config/config.yaml`, `proxy_app/config.py`)
   - 定义 PTU 模型列表
   - 提供 `is_ptu_model()` 判断方法
   - 支持独立的 PTU 后端 URL（可选）

## 配置指南

### 配置 PTU 模型

编辑 `config/config.yaml`，添加 PTU 配置块：

```yaml
# PTU 后端配置
ptu:
  # PTU 后端 URL（如果与标准后端不同，可配置；否则使用 backend.url）
  backend_url: null  # null 表示使用默认的 backend.url

  # PTU 模型列表（用于路由层判断模型是否属于 PTU 后端）
  models:
    - "Doubao-1.5-pro-32k"
    - "Doubao-1.5-thinking-pro"
    - "Doubao-1.5-pro-32k-character-250228"
    - "Doubao-1.5-vision-pro"
    - "DeepSeek-R1"
    - "DeepSeek-R1-distill-qwen-32b"
    - "DeepSeek-R1-distill-llama-70b"
    - "DeepSeek-V3"
    - "qwen3.5-plus"
    - "qwen3.5-flash"
    - "qwen3.5-plus-thinking"
    - "qwen3.5-flash-thinking"

# 添加 PTU 模型到可用模型列表
models:
  available_models:
    # ... 现有模型 ...

    # PTU 模型列表
    - id: "Doubao-1.5-pro-32k"
      owned_by: "bytedance"
      created: 1700000000
    - id: "DeepSeek-R1"
      owned_by: "deepseek"
      created: 1700000000
    - id: "qwen3.5-plus"
      owned_by: "alibaba"
      created: 1700000000
    # ... 更多 PTU 模型 ...
```

### 配置说明

- **ptu.backend_url**: PTU 后端地址，可选
  - 如果为 `null`，使用 `backend.url`
  - 如果 PTU 后端地址与标准后端不同，在此指定

- **ptu.models**: PTU 模型名称列表
  - 路由层根据此列表判断是否使用 `PTUAdapter`
  - 添加新 PTU 模型时，只需添加到此列表

- **models.available_models**: 可用模型列表
  - 添加 PTU 模型到此列表，用户才能查询和调用
  - 包含 `id`、`owned_by`、`created` 字段

## 使用指南

### 标准调用方式

使用标准 OpenAI SDK 调用 PTU 模型，无需任何额外配置：

```python
import openai

# 配置代理服务地址
openai.api_base = "http://localhost:8080/v1"
openai.api_key = "dummy"  # 代理服务不需要真实 key

# 调用 PTU 模型（与标准 OpenAI 模型调用方式完全相同）
response = openai.ChatCompletion.create(
    model="Doubao-1.5-pro-32k",  # PTU 模型
    messages=[
        {"role": "user", "content": "你好"}
    ]
)

print(response.choices[0].message.content)
```

### 流式调用

```python
response = openai.ChatCompletion.create(
    model="DeepSeek-V3",  # PTU 模型
    messages=[
        {"role": "user", "content": "写一首关于春天的短诗"}
    ],
    stream=True
)

for chunk in response:
    if chunk["choices"][0].get("delta", {}).get("content"):
        print(chunk["choices"][0]["delta"]["content"], end="", flush=True)
```

### 推理内容（Thinking 模型）

```python
response = openai.ChatCompletion.create(
    model="Doubao-1.5-thinking-pro",  # PTU 推理模型
    messages=[
        {"role": "user", "content": "解释一下量子纠缠的原理"}
    ]
)

message = response.choices[0].message

# 检查是否有推理内容
if hasattr(message, "reasoning_content"):
    print(f"推理过程: {message.reasoning_content}")

print(f"回答内容: {message.content}")
```

### 多模型对比

```python
models = ["Doubao-1.5-pro-32k", "DeepSeek-V3", "qwen3.5-plus"]
question = "请用一句话解释什么是机器学习"

for model in models:
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": question}]
    )
    print(f"{model}: {response.choices[0].message.content}")
```

## PTU 模型特性

### 支持的模型列表

| 模型系列 | 模型名称 | Channel Code | 特性 |
|---------|---------|-------------|------|
| **Doubao** | Doubao-1.5-pro-32k | doubao | 工具调用、32k上下文 |
|  | Doubao-1.5-thinking-pro | doubao | 推理内容、思维链 |
|  | Doubao-1.5-pro-32k-character-250228 | doubao | 角色扮演 |
|  | Doubao-1.5-vision-pro | doubao | 视觉理解 |
| **DeepSeek** | DeepSeek-R1 | doubao | 推理内容、工具调用 |
|  | DeepSeek-V3 | doubao | 工具调用 |
|  | DeepSeek-R1-distill-qwen-32b | doubao | 蒸馏模型 |
|  | DeepSeek-R1-distill-llama-70b | doubao | 蒸馏模型 |
| **Qwen** | qwen3.5-plus | ali | 工具调用 |
|  | qwen3.5-flash | ali | 快速推理 |
|  | qwen3.5-plus-thinking | ali | 推理内容 |
|  | qwen3.5-flash-thinking | ali | 快速推理+思维 |

### Channel Code 规则

系统会根据模型名称自动推断 `channel_code`：

- **doubao**: Doubao 系列、DeepSeek 系列
- **ali**: Qwen 系列
- **azure**: GPT 系列
- **默认**: doubao

### 特殊功能支持

#### 工具调用（Function Calling）

支持模型：Doubao-1.5-pro-32k, DeepSeek 系列, Qwen 系列

```python
response = openai.ChatCompletion.create(
    model="Doubao-1.5-pro-32k",
    messages=[{"role": "user", "content": "今天北京天气怎么样？"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "城市名称"}
                }
            }
        }
    }]
)
```

#### 推理内容（Reasoning Content）

支持模型：Doubao-1.5-thinking-pro, DeepSeek-R1, Qwen thinking 系列

推理内容会自动包含在响应的 `reasoning_content` 字段中。

## 错误处理

### PTU 错误码

- **10000**: 成功
- **10001**: 业务错误（详细信息在 `msg` 字段）

### 常见错误示例

```json
{
  "code": 10001,
  "msg": "业务错误:the requested model does not support function calling"
}
```

### 错误处理代码

```python
try:
    response = openai.ChatCompletion.create(
        model="Doubao-1.5-pro-32k-character-250228",  # 不支持工具调用
        messages=[{"role": "user", "content": "你好"}],
        tools=[...]  # 工具定义
    )
except Exception as e:
    print(f"调用失败: {e}")
    # 处理错误（如模型不支持工具调用）
```

## 扩展指南

### 添加新 PTU 模型

1. 编辑 `config/config.yaml`：

```yaml
ptu:
  models:
    - "新模型名称"  # 添加到 PTU 模型列表

models:
  available_models:
    - id: "新模型名称"
      owned_by: "供应商"
      created: 时间戳
```

2. 重启代理服务，即可使用新模型

### 添加新供应商

如果需要支持新的供应商（如供应商 X）：

1. 在 `config.yaml` 中添加供应商的模型列表
2. 如果格式不同，创建 `XAdapter` 类
3. 在 `app.py` 路由层添加判断逻辑
4. 在 `BackendProxy` 中添加相应处理

## 测试指南

### 运行单元测试

```bash
# 运行 PTU 适配器测试
pytest tests/test_ptu_adapter.py -v

# 运行所有测试
pytest tests/ -v
```

### 运行示例

```bash
# 确保代理服务已启动
python proxy_server.py

# 在另一个终端运行示例
python examples/ptu_example.py
```

### 测试覆盖

单元测试覆盖以下场景：
- ✅ PTU 响应解包（成功和错误）
- ✅ Channel code 推断（Doubao/DeepSeek/Qwen/GPT）
- ✅ 缺少必要字段的错误处理
- ✅ 适配器继承关系验证
- ✅ 请求和响应适配

## 技术细节

### PTU 请求格式

BackendProxy 会自动添加 PTU 特有参数：

```json
{
  "model": "Doubao-1.5-pro-32k",
  "messages": [...],
  "channel_code": "doubao",
  "transaction_id": "proxy-Doubao-1.5-pro-32k",
  ...  // 其他 OpenAI 参数
}
```

### PTU 响应格式

非流式响应：

```json
{
  "code": 10000,
  "msg": "成功",
  "data": {
    "task_id": 58857509,
    "response_content": {
      "id": "chatcmpl-123",
      "model": "Doubao-1.5-pro-32k",
      "choices": [...],
      "usage": {...}
    }
  }
}
```

流式响应：与标准 OpenAI SSE 格式相同，无需额外解包。

### 内部格式转换流程

```
OpenAI 请求
   ↓ PTUAdapter.adapt_request()
内部格式请求
   ↓ BackendProxy._build_ptu_request()
PTU 请求（添加 channel_code）
   ↓ HTTP POST
PTU 响应
   ↓ PTUAdapter.unwrap_ptu_response()
OpenAI 响应
   ↓ BackendProxy._parse_backend_response()
内部格式响应
   ↓ PTUAdapter.adapt_response()
OpenAI 响应（返回给用户）
```

## 常见问题

### Q: 如何判断某个模型是否是 PTU 模型？

A: 检查 `config.yaml` 中的 `ptu.models` 列表，或使用 `config.is_ptu_model(model_name)` 方法。

### Q: PTU 后端地址可以与标准后端不同吗？

A: 可以，在 `config.yaml` 中设置 `ptu.backend_url`。如果不设置，默认使用 `backend.url`。

### Q: 所有 PTU 模型都支持工具调用吗？

A: 不是，请参考"PTU 模型特性"表格。不支持的模型会返回错误。

### Q: 流式响应是否也需要解包？

A: 流式响应与标准 OpenAI SSE 格式相同，无需额外解包。

### Q: 如何添加自定义的 channel_code 规则？

A: 修改 `PTUAdapter.infer_channel_code()` 方法，添加自定义判断逻辑。

## 参考资料

- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
- [适配器模式](https://refactoring.guru/design-patterns/adapter)
- [项目 README](../README.md)

## 更新日志

- **2026-03-02**: 初始版本，支持 Doubao、DeepSeek、Qwen 系列模型
