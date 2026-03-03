# 示例代码目录

本目录包含 Interface Proxy 的各种使用示例和测试脚本。

## 📚 目录结构

```
examples/
├── README.md                    # 本文件（示例导航）
├── openai_example.py            # OpenAI SDK 使用示例
├── anthropic_example.py         # Anthropic SDK 使用示例
├── ptu_example.py               # PTU 模型使用示例
├── extra_params_example.py      # Extra Body 参数示例
├── tool_use_example.py          # 工具调用完整示例
├── verify_tool_use.py           # 工具调用快速验证
├── models_api_example.py        # Models API 使用示例
├── curl_examples.sh             # cURL 命令示例集合
└── test_stats.sh                # 流量统计测试脚本
```

## 🚀 Python SDK 示例

### [openai_example.py](openai_example.py)
**OpenAI SDK 使用示例**

演示如何使用 OpenAI Python SDK 调用代理服务：
- 非流式请求
- 流式请求
- 错误处理

**运行方式**：
```bash
# 确保服务已启动
python proxy_server.py

# 在另一个终端运行示例
python examples/openai_example.py
```

### [anthropic_example.py](anthropic_example.py)
**Anthropic SDK 使用示例**

演示如何使用 Anthropic Python SDK 调用代理服务：
- 非流式请求
- 流式请求
- System 消息处理
- max_tokens 参数

**运行方式**：
```bash
python examples/anthropic_example.py
```

### [ptu_example.py](ptu_example.py)
**PTU 模型使用示例**

演示如何调用 PTU 后端的模型：
- Doubao 系列模型
- DeepSeek 系列模型
- Qwen 系列模型
- 自动路由到 PTU 后端

**运行方式**：
```bash
python examples/ptu_example.py
```

### [extra_params_example.py](extra_params_example.py)
**Extra Body 参数示例**

演示如何使用 OpenAI SDK 的 extra_body 参数：
- enable_thinking（DeepSeek 思考模式）
- reasoning_mode（推理模式）
- chat_template_kwargs（Qwen 模板参数）
- 自定义参数透传

**运行方式**：
```bash
python examples/extra_params_example.py
```

### [tool_use_example.py](tool_use_example.py)
**工具调用完整示例**

演示完整的工具调用流程：
- 定义工具（函数）
- 发送带工具的请求
- 处理工具调用响应
- 发送工具执行结果
- 获取最终回复

**运行方式**：
```bash
python examples/tool_use_example.py
```

### [verify_tool_use.py](verify_tool_use.py)
**工具调用快速验证**

快速验证工具调用功能是否正常：
- 简化的测试流程
- 快速检查功能状态

**运行方式**：
```bash
python examples/verify_tool_use.py
```

### [models_api_example.py](models_api_example.py)
**Models API 使用示例**

演示如何使用 Models API：
- 列出所有可用模型
- 获取特定模型信息
- 使用 OpenAI SDK 调用

**运行方式**：
```bash
python examples/models_api_example.py
```

## 🔧 Shell 脚本示例

### [curl_examples.sh](curl_examples.sh)
**cURL 命令示例集合**

包含各种 cURL 命令示例：
- OpenAI 格式请求
- Anthropic 格式请求
- 流式和非流式请求
- 工具调用请求
- Models API 查询

**运行方式**：
```bash
# 确保服务已启动
python proxy_server.py

# 在另一个终端运行
bash examples/curl_examples.sh
```

### [test_stats.sh](test_stats.sh)
**流量统计测试脚本**

测试流量监测功能：
- 查询初始统计
- 发送测试请求
- 验证统计数据
- 测试按模型过滤
- 测试不同时间范围

**运行方式**：
```bash
# 确保服务已启动
python proxy_server.py

# 在另一个终端运行
bash examples/test_stats.sh
```

## 📋 使用前准备

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置服务

编辑 `config/config.yaml`，设置后端 URL 和 API Key。

### 3. 启动服务

```bash
python proxy_server.py
```

### 4. 运行示例

在另一个终端运行任意示例脚本。

## 🎯 示例分类

### 按功能分类

- **基础功能**：openai_example.py, anthropic_example.py
- **高级功能**：tool_use_example.py, extra_params_example.py
- **后端支持**：ptu_example.py
- **API 查询**：models_api_example.py
- **监控统计**：test_stats.sh
- **快速测试**：curl_examples.sh, verify_tool_use.py

### 按语言分类

- **Python**：所有 .py 文件
- **Shell**：所有 .sh 文件

### 按难度分类

- **入门级**：openai_example.py, curl_examples.sh
- **中级**：anthropic_example.py, ptu_example.py, models_api_example.py
- **高级**：tool_use_example.py, extra_params_example.py

## 💡 使用建议

1. **新手入门**：先运行 `openai_example.py` 了解基本用法
2. **格式转换**：运行 `anthropic_example.py` 了解格式互转
3. **PTU 模型**：运行 `ptu_example.py` 了解 PTU 后端
4. **高级功能**：运行 `tool_use_example.py` 和 `extra_params_example.py`
5. **快速测试**：使用 `curl_examples.sh` 快速验证功能
6. **监控统计**：使用 `test_stats.sh` 测试流量监测

## 🐛 常见问题

### Q: 运行示例时提示连接失败？

A: 确保代理服务已启动：
```bash
python proxy_server.py
```

### Q: 提示 API Key 无效？

A: 检查 `config/config.yaml` 中的 API Key 配置是否正确。

### Q: PTU 模型调用失败？

A: 确保 `config/config.yaml` 中配置了 PTU 后端 URL 和相应的模型列表。

### Q: 工具调用示例不工作？

A: 确保后端支持工具调用功能，并检查模型是否支持 function calling。

## 📝 贡献示例

欢迎贡献新的示例！请遵循以下规范：

1. **命名规范**：使用描述性的文件名（如 `feature_example.py`）
2. **添加注释**：为关键代码添加清晰的注释
3. **错误处理**：包含适当的错误处理逻辑
4. **更新文档**：在本 README 中添加新示例的说明

---

最后更新：2024-03-03
