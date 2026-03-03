# 文档目录

本目录包含 Interface Proxy 项目的详细文档。

## 📚 文档结构

```
docs/
├── README.md                    # 本文件（文档导航）
├── ARCHITECTURE.md              # 架构设计文档
├── DEVELOPMENT.md               # 开发指南
├── plan.md                      # 开发计划和思路
├── features/                    # 功能文档
│   ├── EXTRA_PARAMS_SUPPORT.md      # Extra Body 参数支持
│   ├── MONITORING.md                # 流量监测功能
│   ├── PTU_INTEGRATION.md           # PTU 后端集成
│   ├── REASONING_CONTENT_SUPPORT.md # 推理内容支持
│   └── STRESS_TEST_GUIDE.md         # 压力测试指南
├── implementation-summaries/    # 实现总结文档
│   ├── EXTRA_PARAMS_COMPLETE.md     # Extra Body 参数实现总结
│   ├── PTU_IMPLEMENTATION_SUMMARY.md # PTU 实现总结
│   ├── REFACTOR_SUMMARY.md          # 重构总结
│   ├── TOOL_USE_COMPLETED.md        # 工具调用完成总结
│   └── DOC_ORGANIZATION_SUMMARY.md  # 文档组织总结
└── archives/                    # 归档文档
    └── TOOL_USE_IMPLEMENTATION_PLAN.md # 工具调用实现计划（已完成）
```

## 🔍 核心文档

### [ARCHITECTURE.md](ARCHITECTURE.md)
**架构设计文档** - 系统架构和设计理念：
- 整体架构设计
- 适配器模式详解
- 数据流转过程
- 扩展性设计

### [DEVELOPMENT.md](DEVELOPMENT.md)
**开发指南** - 开发相关的详细信息：
- 开发环境搭建
- 代码规范
- 测试指南
- 贡献指南

### [plan.md](plan.md)
**开发计划** - 项目开发思路和计划：
- 已完成功能清单
- 实现细节记录
- 待开发功能
- 版本历史

## 🎯 功能文档

### [features/EXTRA_PARAMS_SUPPORT.md](features/EXTRA_PARAMS_SUPPORT.md)
**Extra Body 参数支持** - OpenAI SDK extra_body 参数透传：
- 功能说明
- 使用示例
- 支持的参数类型
- 实现原理

### [features/MONITORING.md](features/MONITORING.md)
**流量监测功能** - 简单的内存流量统计：
- 功能特性
- API 接口说明
- 使用示例
- 性能特点

### [features/PTU_INTEGRATION.md](features/PTU_INTEGRATION.md)
**PTU 后端集成** - PTU Gateway 后端支持：
- PTU 模型列表
- 配置方法
- 使用示例
- 注意事项

### [features/REASONING_CONTENT_SUPPORT.md](features/REASONING_CONTENT_SUPPORT.md)
**推理内容支持** - o1 系列和 Extended Thinking 支持：
- OpenAI o1 系列的 reasoning_content
- Anthropic Extended Thinking
- 格式转换
- 使用示例

### [features/STRESS_TEST_GUIDE.md](features/STRESS_TEST_GUIDE.md)
**压力测试指南** - 性能测试工具和方法：
- 测试工具使用
- 测试场景
- 性能指标
- 优化建议

## 📋 实现总结

### [implementation-summaries/EXTRA_PARAMS_COMPLETE.md](implementation-summaries/EXTRA_PARAMS_COMPLETE.md)
Extra Body 参数功能的完整实现总结

### [implementation-summaries/PTU_IMPLEMENTATION_SUMMARY.md](implementation-summaries/PTU_IMPLEMENTATION_SUMMARY.md)
PTU 后端集成的实现总结

### [implementation-summaries/REFACTOR_SUMMARY.md](implementation-summaries/REFACTOR_SUMMARY.md)
架构重构的总结文档

### [implementation-summaries/TOOL_USE_COMPLETED.md](implementation-summaries/TOOL_USE_COMPLETED.md)
工具调用功能的实现总结

### [implementation-summaries/DOC_ORGANIZATION_SUMMARY.md](implementation-summaries/DOC_ORGANIZATION_SUMMARY.md)
文档组织的总结说明

## 🚀 快速导航

### 我想快速开始使用
👉 查看 [../README.md](../README.md) - 项目主文档

### 我想了解系统架构
👉 查看 [ARCHITECTURE.md](ARCHITECTURE.md)

### 我想了解流量监测功能
👉 查看 [features/MONITORING.md](features/MONITORING.md)

### 我想了解 Extra Body 参数支持
👉 查看 [features/EXTRA_PARAMS_SUPPORT.md](features/EXTRA_PARAMS_SUPPORT.md)

### 我想了解 PTU 后端集成
👉 查看 [features/PTU_INTEGRATION.md](features/PTU_INTEGRATION.md)

### 我想了解推理内容功能
👉 查看 [features/REASONING_CONTENT_SUPPORT.md](features/REASONING_CONTENT_SUPPORT.md)

### 我想进行压力测试
👉 查看 [features/STRESS_TEST_GUIDE.md](features/STRESS_TEST_GUIDE.md)

### 我想查看代码示例
👉 查看 [../examples/](../examples/) 目录：
- `openai_example.py` - OpenAI SDK 使用示例
- `anthropic_example.py` - Anthropic SDK 使用示例
- `extra_params_example.py` - Extra Body 参数示例
- `tool_use_example.py` - 工具调用示例
- `curl_examples.sh` - cURL 命令示例
- `test_stats.sh` - 流量统计测试脚本

### 我想查看测试代码
👉 查看 [../tests/](../tests/) 目录：
- `test_adapters.py` - 适配器测试
- `test_extra_params.py` - Extra Body 参数测试
- `stress_test.py` - 压力测试脚本
- `test_api_key.sh` - API Key 测试脚本

### 我想了解开发计划
👉 查看 [plan.md](plan.md) - 开发计划和思路

## 🎯 文档维护原则

1. **分类清晰** - 按功能、实现总结、归档分类
2. **结构合理** - 使用子目录组织相关文档
3. **保持更新** - 文档随代码实现同步更新
4. **易于导航** - 提供清晰的导航和索引
5. **避免重复** - 合并重复内容，保持单一信息源

## 📝 更新记录

- **2024-03-03**: 整理文档结构，添加流量监测功能文档
- **2024-03-02**: 添加 Extra Body 参数支持文档
- **2024-03-02**: 添加压力测试指南
- **2024-02-29**: 添加工具调用和推理内容文档
- **2024-02**: 初始文档创建

---

有问题或建议？欢迎提出！
