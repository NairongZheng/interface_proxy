# Interface Proxy 开发计划

## 项目概述

Interface Proxy 是一个多协议 LLM API 代理服务，支持 OpenAI、Anthropic 等多种 API 格式，并能转发到不同的后端服务（标准 OpenAI、PTU Gateway 等）。

## 已完成功能

### 核心架构 ✅
- 基于适配器模式的多协议支持
- 内部统一格式（InternalRequest/InternalResponse）
- 可扩展的后端转发机制

### API 格式支持 ✅
- OpenAI Chat Completions API
- Anthropic Messages API
- 流式和非流式输出
- 工具调用（Tool Use/Function Calling）

### 后端支持 ✅
- 标准 OpenAI 后端
- PTU Gateway 后端
- 自动模型路由（基于配置）

### 高级功能 ✅
- **Tool Use 支持** (2024-02-29 完成)
  - OpenAI function calling 格式
  - Anthropic tool use 格式
  - 双向格式转换

- **Reasoning Content 支持** (2024-02-29 完成)
  - 支持 o1 系列模型的推理内容
  - 流式和非流式输出

- **压力测试工具** (2024-03-02 完成)
  - 并发请求测试
  - 性能指标收集
  - 详细的测试报告

- **Extra Body 参数支持** (2024-03-02 完成) ✅
  - 自动提取 OpenAI SDK 的 extra_body 参数
  - 支持现代 LLM 高级功能（思考模式、推理模式等）
  - 透明传递到 OpenAI 和 PTU 后端
  - 完整的测试覆盖和文档

- **流量监测功能** (2024-03-03 完成) ✅
  - 基于小时级别时间桶的内存统计
  - 支持 24h/7d/30d 时间范围查询
  - 按模型维度统计请求数、成功数、失败数
  - 极简实现，内存占用 < 1MB
  - 对请求性能影响可忽略（< 0.01ms）

- **Pydantic 模型额外字段访问优化** (2024-03-03 完成) ✅
  - 支持通过属性直接访问额外字段（与 OpenAI SDK 一致）
  - ChatCompletionMessage 和 DeltaMessage 添加 `__getattr__` 方法
  - 区分 message 级别和 response 级别的额外字段
  - 完整的单元测试覆盖

## 实现细节

### Extra Body 参数支持实现

#### 问题描述
OpenAI SDK 通过 `extra_body` 参数传递额外参数（如 `enable_thinking`、`reasoning_mode` 等），但之前的实现会丢失这些参数。

#### 解决方案
1. **扩展数据模型** (`proxy_app/models/common.py`)
   - 在 `InternalRequest` 中添加 `extra_params` 字段
   - 用于存储来自 `__pydantic_extra__` 的额外参数

2. **提取额外参数** (`proxy_app/adapters/openai_adapter.py`)
   - 在 `adapt_request()` 中提取 `__pydantic_extra__`
   - 将额外参数存储到 `extra_params` 字段

3. **合并到后端请求**
   - OpenAI 适配器：在 `_build_openai_request()` 中合并到顶层
   - PTU 适配器：在 `_build_ptu_request()` 中合并到顶层

#### 修改文件
- `proxy_app/models/common.py` - 添加 extra_params 字段定义
- `proxy_app/adapters/openai_adapter.py` - 提取和合并逻辑
- `proxy_app/adapters/ptu_adapter.py` - PTU 后端合并逻辑
- `tests/test_extra_params.py` - 单元测试（新建）
- `examples/extra_params_example.py` - 使用示例（新建）
- `docs/EXTRA_PARAMS_SUPPORT.md` - 详细文档（新建）

#### 支持的参数示例
- `enable_thinking`: 启用思考模式（DeepSeek）
- `thinking`: 思考配置（o1 系列）
- `reasoning_mode`: 推理模式
- `chat_template_kwargs`: 聊天模板参数（Qwen）
- 以及任意自定义参数

### 流量监测功能实现

#### 问题描述
需要简单的流量监测功能，用于统计不同模型的请求次数，支持查询 24h/7d/30d 的数据。

#### 解决方案
1. **极简统计模块** (`proxy_app/monitoring/simple_stats.py`)
   - 使用小时级别的时间桶存储聚合计数
   - 只存储计数器（count, success, error），不存储每条请求记录
   - 内存占用固定 < 1MB（720桶 × 10模型 × 3计数器）
   - 自动清理超过 30 天的旧数据

2. **统计中间件** (`proxy_app/app.py`)
   - 拦截 `/v1/chat/completions` 请求
   - 提取模型名称和响应状态
   - 只递增计数器，性能影响 < 0.01ms

3. **查询 API**
   - `GET /api/stats?time_range=24h&model=gpt-4` - 查询统计数据
   - `GET /api/stats/models` - 查询所有使用过的模型列表

#### 修改文件
- `proxy_app/monitoring/__init__.py` - 模块初始化（新建）
- `proxy_app/monitoring/simple_stats.py` - 统计收集器（新建）
- `proxy_app/app.py` - 添加中间件和查询路由

#### 性能特点
- 记录操作：O(1)，只递增计数器
- 查询操作：O(桶数 × 模型数)，毫秒级
- 内存占用：固定 < 1MB
- 对请求影响：< 0.01ms（可忽略）

#### 适用场景
- 单机部署
- 简单粗略统计
- 不需要长期历史数据
- 对数据丢失不敏感（重启后清零）

### Pydantic 模型额外字段访问优化

#### 问题描述
OpenAI SDK 可以通过 `extra_body` 传递参数，返回的额外字段可以直接通过 `response.choices[0].message.xxx` 访问。但在当前 proxy 中需要通过 `response.choices[0].message["model_extra"]["xxx"]` 才能访问。

#### 解决方案
1. **添加 Pydantic Config** (`proxy_app/models/openai_models.py`)
   - 为 `ChatCompletionMessage` 添加 `extra = "allow"` 配置
   - 为 `DeltaMessage` 添加 `extra = "allow"` 配置
   - 允许模型接受额外字段

2. **实现 `__getattr__` 方法**
   - 在 `ChatCompletionMessage` 中添加自定义 `__getattr__`
   - 在 `DeltaMessage` 中添加自定义 `__getattr__`
   - 支持通过属性访问 `__pydantic_extra__` 中的字段

3. **Adapter 额外字段处理** (`proxy_app/adapters/openai_adapter.py`)
   - 在 `adapt_response()` 中区分 message 和 response 级别的额外字段
   - 在 `adapt_streaming_response()` 中区分 delta 和 chunk 级别的额外字段
   - 使用 `message_` 前缀标识 message 级别的字段

#### 修改文件
- `proxy_app/models/openai_models.py` - 添加 Config 和 `__getattr__` 方法
- `proxy_app/adapters/openai_adapter.py` - 额外字段分类处理逻辑
- `tests/test_extra_fields_access.py` - 单元测试（新建）

#### 主要改进
- ✅ 可以像 OpenAI SDK 一样通过 `message.custom_field` 访问额外字段
- ✅ 流式响应也支持通过 `delta.custom_field` 访问
- ✅ 保持与 OpenAI SDK 一致的 API 体验
- ✅ 向后兼容，不影响现有功能

## 待开发功能

### 短期计划

#### 1. 配置管理优化
- [ ] YAML 配置文件支持
- [ ] 热重载配置
- [ ] 环境变量覆盖

#### 2. 监控和日志
- [x] 简单流量统计（已完成 2024-03-03）
- [ ] 结构化日志输出
- [ ] Prometheus metrics
- [ ] 请求追踪（Trace ID）

#### 3. 错误处理增强
- [ ] 统一错误格式
- [ ] 重试机制
- [ ] 降级策略

### 中期计划

#### 4. 性能优化
- [ ] 连接池管理
- [ ] 请求缓存
- [ ] 响应压缩

#### 5. 安全增强
- [ ] API Key 管理
- [ ] 请求限流
- [ ] 访问控制列表

#### 6. 更多后端支持
- [ ] Azure OpenAI
- [ ] AWS Bedrock
- [ ] Google Vertex AI

### 长期计划

#### 7. 高级功能
- [ ] 请求队列管理
- [ ] 负载均衡
- [ ] 故障转移

#### 8. 开发工具
- [ ] 交互式 API 调试工具
- [ ] 性能分析面板
- [ ] 文档生成器

## 文档组织

项目文档已按功能模块组织：

### 核心文档
- `README.md` - 项目概览和快速开始
- `ARCHITECTURE.md` - 架构设计
- `DEVELOPMENT.md` - 开发指南
- `plan.md` - 开发计划（本文档）

### 功能文档
- `PTU_INTEGRATION.md` - PTU 后端集成
- `TOOL_USE_IMPLEMENTATION_PLAN.md` - 工具调用实现计划
- `TOOL_USE_COMPLETED.md` - 工具调用完成总结
- `REASONING_CONTENT_SUPPORT.md` - 推理内容支持
- `STRESS_TEST_GUIDE.md` - 压力测试指南
- `EXTRA_PARAMS_SUPPORT.md` - Extra Body 参数支持 ✨新增

### 总结文档
- `REFACTOR_SUMMARY.md` - 重构总结
- `PTU_IMPLEMENTATION_SUMMARY.md` - PTU 实现总结
- `DOC_ORGANIZATION_SUMMARY.md` - 文档组织总结

## 测试策略

### 单元测试
- 适配器转换逻辑
- 后端调用模拟
- Extra Body 参数提取和合并 ✨新增

### 集成测试
- 端到端 API 调用
- 多后端切换
- 工具调用流程
- Extra Body 参数传递 ✨新增

### 压力测试
- 并发请求处理
- 流式输出性能
- 资源使用监控

## 贡献指南

### 开发流程
1. 从 `main` 分支创建功能分支
2. 实现功能并添加测试
3. 更新相关文档
4. 提交 Pull Request

### 代码规范
- 遵循 PEP 8
- 使用类型注解
- 添加函数和关键逻辑注释
- 保持模块化设计

### 提交规范
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 其他修改

## 版本历史

- **v0.4.1** (2024-03-03) - Pydantic 模型额外字段访问优化
  - 支持通过属性直接访问额外字段
  - 与 OpenAI SDK 保持一致的 API 体验
  - 完整的单元测试覆盖

- **v0.4.0** (2024-03-03) - 流量监测功能
  - 基于小时级别时间桶的内存统计
  - 支持 24h/7d/30d 时间范围查询
  - 按模型维度统计
  - 极简实现，性能影响可忽略

- **v0.3.0** (2024-03-02) - Extra Body 参数支持
  - 支持 OpenAI SDK extra_body 参数
  - 透明传递到后端
  - 完整测试和文档

- **v0.2.1** (2024-03-02) - 压力测试工具
  - 添加并发测试脚本
  - 性能指标收集

- **v0.2.0** (2024-02-29) - Tool Use 和 Reasoning Content
  - 完整的工具调用支持
  - o1 系列模型推理内容支持

- **v0.1.0** (2024-02) - 初始版本
  - 基础架构
  - OpenAI 和 Anthropic 格式支持
  - PTU 后端集成

## 联系方式

- 项目地址：[待添加]
- 问题反馈：[待添加]
- 文档地址：`docs/` 目录

---

最后更新：2024-03-03 (v0.4.1)
