# System 参数格式修复实现报告

## 修复时间
2026-02-13

## 问题描述

**错误信息**：
```
API Error: 422 {
  "detail": [{
    "type": "string_type",
    "loc": ["body", "system"],
    "msg": "Input should be a valid string",
    "input": [
      {"type":"text","text":"x-anthropic-billing-header: cc_version=2.1.17.7fe; cc_entrypoint=cli"},
      {"type":"text","text":"You are Claude Code..."},
      ...
    ]
  }]
}
```

**根本原因**：
- 客户端（Claude Code CLI）发送的是新版 Anthropic API 格式，其中 `system` 参数支持数组格式（用于 prompt caching）
- 代理服务器的模型定义只支持字符串格式的 `system` 参数
- Pydantic 验证时发现类型不匹配，抛出 422 错误

## 解决方案

### 1. 修改的文件

#### proxy_app/models/anthropic_models.py (第 73-92 行)
**添加 SystemTextBlock 模型**，支持 prompt caching 的新格式：

```python
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
```

#### proxy_app/models/anthropic_models.py (第 133 行)
**修改 system 字段类型**，支持两种格式：

```python
system: Optional[Union[str, List[SystemContentBlock]]] = None
```

#### proxy_app/adapters/anthropic_adapter.py (第 18 行)
**导入新模型**：

```python
from proxy_app.models.anthropic_models import (
    # ...
    SystemContentBlock,  # 新增
    # ...
)
```

#### proxy_app/adapters/anthropic_adapter.py (第 59-71 行)
**修改 system 处理逻辑**，调用新的提取方法：

```python
# 处理 system 字段
# Anthropic 的 system 可以是：
# 1. 字符串（旧格式）
# 2. 内容块数组（新格式，支持 prompt caching）
if request_data.system:
    # 提取文本内容
    system_text = self._extract_system_content(request_data.system)

    system_msg: InternalMessage = {
        "role": "system",
        "content": system_text,
    }
    internal_messages.append(system_msg)
```

#### proxy_app/adapters/anthropic_adapter.py (第 130-163 行)
**添加 _extract_system_content 方法**，处理两种格式的 system 参数：

```python
def _extract_system_content(self, system: str | List[SystemContentBlock]) -> str:
    """
    从 system 参数中提取文本内容

    system 可以是两种格式：
    1. 字符串（旧格式）- 直接返回
    2. 内容块数组（新格式，支持 prompt caching）- 提取所有 text 块

    注意：
    - cache_control 信息会被忽略（因为大多数后端不支持 prompt caching）
    - 如果需要支持 cache_control，需要在后端代理中实现相关逻辑

    Args:
        system: system 参数（字符串或内容块数组）

    Returns:
        提取的纯文本
    """
    # 如果是字符串，直接返回
    if isinstance(system, str):
        return system

    # 如果是列表，提取所有 text 块
    text_parts = []
    for block in system:
        if isinstance(block, dict):
            # 字典格式
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        elif hasattr(block, "type") and block.type == "text":
            # Pydantic 模型格式
            text_parts.append(block.text)

    return "\n".join(text_parts)
```

### 2. 处理流程

修改后的处理流程：

```
客户端请求（新格式）
  ↓
POST /v1/messages
  {
    "model": "claude-sonnet-4-5-20250929",
    "system": [
      {"type": "text", "text": "x-anthropic-billing-header: ..."},
      {"type": "text", "text": "You are Claude Code...", "cache_control": {"type": "ephemeral"}}
    ],
    "messages": [...],
    "max_tokens": 1024
  }
  ↓
[Pydantic 验证]
  ✓ system 字段验证通过（Union[str, List[SystemContentBlock]]）
  ↓
[AnthropicAdapter.adapt_request()]
  ↓
[_extract_system_content()]
  - 遍历 system 数组
  - 提取所有 text 块的 text 字段
  - 忽略 cache_control（后端不支持）
  - 用换行符拼接多个文本块
  ↓
内部格式请求
  {
    "messages": [
      {
        "role": "system",
        "content": "x-anthropic-billing-header: ...\nYou are Claude Code..."
      },
      ...
    ],
    ...
  }
  ↓
[继续原有流程...]
```

### 3. 兼容性保证

1. **向后兼容**：旧的字符串格式仍然支持
2. **新格式支持**：支持内容块数组格式
3. **Cache control**：会被解析但不会转发到后端（因为大多数后端不支持 prompt caching）

## 测试验证

创建了测试脚本 `test_system_fix.py`，验证三种场景：

### 测试 1: System 字符串格式（旧格式）
```python
request = AnthropicMessagesRequest(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    system="You are a helpful assistant",  # 字符串格式
    messages=[{"role": "user", "content": "Hello"}]
)
```
✓ 测试通过

### 测试 2: System 数组格式（新格式）
```python
request = AnthropicMessagesRequest(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    system=[  # 数组格式
        {"type": "text", "text": "Header info"},
        {"type": "text", "text": "You are Claude Code", "cache_control": {"type": "ephemeral"}}
    ],
    messages=[{"role": "user", "content": "Hello"}]
)
```
✓ 测试通过

### 测试 3: 无 System 参数
```python
request = AnthropicMessagesRequest(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```
✓ 测试通过

## 关键特性

1. **最小化修改**：只修改必要的模型定义和适配器逻辑
2. **向后兼容**：不影响现有的字符串格式 system 参数
3. **功能完整**：支持新版 API 的数组格式 system 参数
4. **易于测试**：清晰的测试用例和验证方案
5. **可扩展**：为未来支持 prompt caching 预留空间
6. **良好注释**：每个函数都有详细的注释说明

## 注意事项

### 1. Prompt Caching 支持

当前方案会**忽略** `cache_control` 字段，因为：
- 大多数后端服务不支持 Anthropic 的 prompt caching
- 要完整支持需要在后端代理中实现缓存逻辑

如果未来需要支持 prompt caching：
- 需要在内部格式中添加 `cache_control` 字段
- 需要后端服务支持类似的缓存机制
- 需要在 `backend_proxy.py` 中转换和转发缓存控制信息

### 2. 文本拼接策略

当 system 是数组时，使用 `\n` 拼接多个文本块。这是一个合理的默认策略，能够：
- 保持不同文本块的边界清晰
- 避免文本块之间内容混淆
- 兼容大多数后端的处理方式

## 相关文档

- [Anthropic Messages API 文档](https://docs.anthropic.com/claude/reference/messages_post)
- [Anthropic Prompt Caching 文档](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- 项目 README: `/Users/zhengnairong/code/vibe_coding/interface_proxy/README.md`

## 实现总结

这个修复方案成功解决了 422 错误问题，使代理服务器能够：
1. 正确解析 Claude Code CLI 发送的新格式 system 参数
2. 保持对旧格式的向后兼容
3. 为未来支持 prompt caching 功能预留扩展空间

修改遵循了代码规范，添加了详细注释，并通过了完整的测试验证。
