# 文档目录

本目录包含 Interface Proxy 项目的详细文档。

## 📚 文档列表

### [DEVELOPMENT.md](DEVELOPMENT.md)
**开发文档** - 完整的开发历史和实现细节：
- **实现总结** - 已实现的功能概览
- **Models API 使用指南** - 模型列表 API 的使用方法
- **开发日志** - 按时间记录的开发过程
  - 2026-02-13: 工具调用（Tool Use）功能实现
  - 2026-02-13: Models API 和根路由实现
- **技术细节** - 数据模型、配置、实现细节等

### [REASONING_CONTENT_SUPPORT.md](REASONING_CONTENT_SUPPORT.md)
**推理内容支持说明** - 详细介绍：
- OpenAI o1 系列模型的 `reasoning_content` 支持
- Anthropic Extended Thinking 的 `thinking` content block 支持
- 两种格式之间的自动转换
- 使用示例和最佳实践

### [TOOL_USE_IMPLEMENTATION_PLAN.md](TOOL_USE_IMPLEMENTATION_PLAN.md)
**工具调用实现计划** - 工具调用功能的设计文档：
- 问题描述和根本原因分析
- 完整的实现方案
- 数据模型定义
- 适配器实现细节
- 测试计划

### [TOOL_USE_COMPLETED.md](TOOL_USE_COMPLETED.md)
**工具调用完成总结** - 工具调用功能的实现总结：
- 实现内容概览
- 功能验证清单
- 测试方法
- Claude Code CLI 兼容性说明
- 问题排查指南

## 🔍 快速导航

### 我想快速开始使用
👉 查看 [../README.md](../README.md) - 项目主文档

### 我想了解如何使用 Models API
👉 查看 [DEVELOPMENT.md](DEVELOPMENT.md) 的 "Models API 使用指南" 部分

### 我想了解工具调用功能
👉 查看 [TOOL_USE_COMPLETED.md](TOOL_USE_COMPLETED.md) - 功能总结和使用方法

### 我想了解推理内容功能
👉 查看 [REASONING_CONTENT_SUPPORT.md](REASONING_CONTENT_SUPPORT.md)

### 我想了解实现细节
👉 查看 [DEVELOPMENT.md](DEVELOPMENT.md) 的 "技术细节" 部分

### 我想查看代码示例
👉 查看 [../examples/](../examples/) 目录：
- `openai_example.py` - OpenAI SDK 使用示例
- `anthropic_example.py` - Anthropic SDK 使用示例
- `models_api_example.py` - Models API 使用示例
- `tool_use_example.py` - 工具调用完整示例
- `verify_tool_use.py` - 工具调用快速验证脚本

### 我想了解开发思路
👉 查看 [../plan.md](../plan.md) - 开发计划和思路

## 📂 文档结构

```
interface_proxy/
├── README.md                    # 项目主文档（快速开始、功能特性、使用示例）
├── plan.md                      # 开发思路和计划
└── docs/                        # 详细文档
    ├── README.md                # 本文件（文档导航）
    ├── DEVELOPMENT.md           # 开发文档（实现细节、API 文档、开发日志）
    ├── REASONING_CONTENT_SUPPORT.md      # 推理内容功能说明
    ├── TOOL_USE_IMPLEMENTATION_PLAN.md   # 工具调用设计文档
    └── TOOL_USE_COMPLETED.md             # 工具调用完成总结
```

## 🎯 文档维护原则

1. **根目录简洁** - 只保留主文档（README.md）和开发计划（plan.md）
2. **详细文档集中** - 所有详细文档放在 docs/ 文件夹
3. **按功能组织** - 每个主要功能有独立的文档
4. **保持更新** - 文档随代码实现同步更新
5. **清晰导航** - 提供多种快速导航方式

## 📝 更新记录

- **2026-02-13**: 添加工具调用功能文档
- **2026-02-13**: 添加 Models API 文档
- **2026-02-13**: 整理文档结构

---

有问题或建议？欢迎提出！
