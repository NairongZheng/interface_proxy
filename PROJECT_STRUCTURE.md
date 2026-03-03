# 项目结构说明

## 目录结构

```
interface_proxy/
├── README.md                    # 项目主文档
├── PROJECT_STRUCTURE.md         # 本文件（项目结构说明）
├── requirements.txt             # Python 依赖
├── proxy_server.py              # 服务启动脚本
│
├── config/                      # 配置文件
│   └── config.yaml              # 主配置文件
│
├── proxy_app/                   # 核心应用代码
│   ├── __init__.py
│   ├── app.py                   # FastAPI 应用和路由
│   ├── config.py                # 配置加载
│   │
│   ├── adapters/                # 适配器模块
│   │   ├── __init__.py
│   │   ├── base_adapter.py      # 适配器基类
│   │   ├── openai_adapter.py    # OpenAI 格式适配器
│   │   ├── anthropic_adapter.py # Anthropic 格式适配器
│   │   └── ptu_adapter.py       # PTU 后端适配器
│   │
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   ├── common.py            # 通用模型（InternalRequest/Response）
│   │   ├── openai_models.py     # OpenAI 格式模型
│   │   └── anthropic_models.py  # Anthropic 格式模型
│   │
│   ├── monitoring/              # 监控模块
│   │   ├── __init__.py
│   │   └── simple_stats.py      # 流量统计收集器
│   │
│   └── utils/                   # 工具模块
│       ├── __init__.py
│       └── logger.py            # 日志配置
│
├── docs/                        # 文档目录
│   ├── README.md                # 文档导航
│   ├── ARCHITECTURE.md          # 架构设计
│   ├── DEVELOPMENT.md           # 开发指南
│   ├── plan.md                  # 开发计划
│   │
│   ├── features/                # 功能文档
│   │   ├── EXTRA_PARAMS_SUPPORT.md
│   │   ├── MONITORING.md
│   │   ├── PTU_INTEGRATION.md
│   │   ├── REASONING_CONTENT_SUPPORT.md
│   │   └── STRESS_TEST_GUIDE.md
│   │
│   ├── implementation-summaries/ # 实现总结
│   │   ├── DOCUMENTATION_ORGANIZATION.md
│   │   ├── EXTRA_PARAMS_COMPLETE.md
│   │   ├── PTU_IMPLEMENTATION_SUMMARY.md
│   │   ├── REFACTOR_SUMMARY.md
│   │   └── TOOL_USE_COMPLETED.md
│   │
│   └── archives/                # 归档文档
│       └── TOOL_USE_IMPLEMENTATION_PLAN.md
│
├── examples/                    # 示例代码
│   ├── README.md                # 示例导航
│   ├── openai_example.py        # OpenAI SDK 示例
│   ├── anthropic_example.py     # Anthropic SDK 示例
│   ├── ptu_example.py           # PTU 模型示例
│   ├── extra_params_example.py  # Extra Body 参数示例
│   ├── tool_use_example.py      # 工具调用示例
│   ├── verify_tool_use.py       # 工具调用验证
│   ├── models_api_example.py    # Models API 示例
│   ├── curl_examples.sh         # cURL 命令示例
│   └── test_stats.sh            # 流量统计测试
│
└── tests/                       # 测试代码
    ├── README.md                # 测试说明
    ├── test_adapters.py         # 适配器测试
    ├── test_adapter_units.py    # 适配器单元测试
    ├── test_integration.py      # 集成测试
    ├── test_ptu_adapter.py      # PTU 适配器测试
    ├── test_extra_params.py     # Extra Body 参数测试
    ├── stress_test.py           # 压力测试
    └── test_api_key.sh          # API Key 测试
```

## 核心模块说明

### proxy_app/app.py
FastAPI 应用的核心文件，包含：
- 应用创建和配置
- 路由注册
- 中间件（统计中间件）
- 请求处理逻辑
- 统计查询 API

### proxy_app/adapters/
适配器模块，实现不同格式之间的转换：
- **base_adapter.py**：定义适配器接口
- **openai_adapter.py**：OpenAI 格式适配器
- **anthropic_adapter.py**：Anthropic 格式适配器
- **ptu_adapter.py**：PTU 后端专用适配器

### proxy_app/models/
数据模型定义：
- **common.py**：内部统一格式（InternalRequest/Response）
- **openai_models.py**：OpenAI API 格式模型
- **anthropic_models.py**：Anthropic API 格式模型

### proxy_app/monitoring/
监控模块：
- **simple_stats.py**：简单的内存流量统计收集器

### proxy_app/utils/
工具模块：
- **logger.py**：日志配置和管理

## 配置文件

### config/config.yaml
主配置文件，包含：
- 后端服务配置（URL、API Key、超时）
- PTU 后端配置
- PTU 模型列表
- 路由开关（OpenAI/Anthropic）
- 服务器配置（主机、端口）
- 日志级别

## 文档组织

### docs/
文档按类型分类：
- **核心文档**：架构、开发指南、计划
- **features/**：功能详细说明
- **implementation-summaries/**：实现总结
- **archives/**：归档文档

### examples/
示例代码按功能分类：
- Python SDK 示例
- Shell 脚本示例
- 功能验证脚本

### tests/
测试代码按类型分类：
- 单元测试
- 集成测试
- 压力测试

## 代码规范

### 命名规范
- **文件名**：小写下划线（snake_case）
- **类名**：大驼峰（PascalCase）
- **函数名**：小写下划线（snake_case）
- **常量**：大写下划线（UPPER_SNAKE_CASE）

### 注释规范
- 每个函数添加 docstring
- 关键逻辑添加行内注释
- 使用中文注释（项目内部）

### 模块化原则
- 单一职责：每个模块只负责一个功能
- 适度抽象：避免过度设计
- 清晰接口：模块间通过明确的接口交互

## 开发流程

### 添加新功能
1. 在 `proxy_app/` 相应模块添加代码
2. 在 `tests/` 添加测试
3. 在 `examples/` 添加示例
4. 在 `docs/features/` 添加文档
5. 更新 `docs/plan.md`
6. 更新主 `README.md`

### 修复 Bug
1. 在 `tests/` 添加复现测试
2. 修复代码
3. 验证测试通过
4. 更新相关文档（如需要）

### 重构代码
1. 确保现有测试通过
2. 进行重构
3. 验证测试仍然通过
4. 更新文档（如架构变化）
5. 在 `docs/implementation-summaries/` 添加重构总结

## 依赖管理

### 核心依赖
- **FastAPI**：Web 框架
- **uvicorn**：ASGI 服务器
- **httpx**：异步 HTTP 客户端
- **pydantic**：数据验证
- **PyYAML**：配置文件解析

### 开发依赖
- **pytest**：测试框架
- **black**：代码格式化
- **flake8**：代码检查

## 部署说明

### 开发环境
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python proxy_server.py
```

### 生产环境
```bash
# 使用 uvicorn 启动
uvicorn proxy_app.app:app --host 0.0.0.0 --port 8080

# 或使用 gunicorn + uvicorn workers
gunicorn proxy_app.app:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 性能考虑

### 内存占用
- 流量统计：< 1MB（固定）
- 基础应用：约 50-100MB
- 总计：约 100MB

### 并发能力
- 异步架构，支持高并发
- 建议使用多 worker 部署
- 单 worker 可处理数百并发请求

### 响应时间
- 格式转换：< 1ms
- 流量统计：< 0.01ms
- 总开销：< 5ms（不含后端调用）

## 监控和日志

### 日志级别
- **DEBUG**：详细调试信息
- **INFO**：一般信息（默认）
- **WARNING**：警告信息
- **ERROR**：错误信息

### 流量统计
- 端点：`/api/stats`
- 时间范围：24h/7d/30d
- 按模型统计
- 成功/失败分类

## 安全考虑

### API Key 管理
- 从配置文件读取
- 不在代码中硬编码
- 支持环境变量覆盖

### 请求验证
- 使用 Pydantic 验证请求格式
- 自动拒绝无效请求

### 错误处理
- 统一错误格式
- 不暴露内部错误细节
- 记录详细错误日志

## 扩展指南

### 添加新的适配器
1. 继承 `BaseAdapter`
2. 实现必需方法
3. 在 `app.py` 注册路由
4. 添加测试和文档

### 添加新的后端
1. 创建新的适配器（如需要）
2. 在配置文件添加后端配置
3. 更新路由逻辑
4. 添加测试和文档

### 添加新的监控指标
1. 在 `monitoring/` 添加收集器
2. 在中间件中调用
3. 添加查询 API
4. 添加文档

## 常见问题

### Q: 如何添加新的 PTU 模型？
A: 在 `config/config.yaml` 的 `ptu.models` 列表中添加模型名称。

### Q: 如何修改日志级别？
A: 在 `config/config.yaml` 中修改 `log_level` 配置。

### Q: 如何禁用某个路由？
A: 在 `config/config.yaml` 中设置 `routes.openai_enabled` 或 `routes.anthropic_enabled` 为 `false`。

### Q: 如何查看流量统计？
A: 访问 `/api/stats?time_range=24h` 端点。

---

最后更新：2024-03-03
