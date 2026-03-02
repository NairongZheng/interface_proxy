# 压力测试指南

本文档介绍如何使用压测脚本测试 proxy 服务的性能和并发能力。

## 📋 目录

- [快速开始](#快速开始)
- [使用说明](#使用说明)
- [测试场景](#测试场景)
- [性能指标说明](#性能指标说明)
- [常见问题](#常见问题)

## 🚀 快速开始

### 1. 启动 Proxy 服务

```bash
python proxy_server.py --reload
```

### 2. 运行基础压测

```bash
# 基础测试：10 并发，100 请求
python tests/stress_test.py
```

### 3. 查看测试报告

脚本会自动生成详细的性能报告，包括：
- 成功率和失败率
- 响应时间统计（平均、P50、P90、P95、P99）
- 吞吐量（QPS）
- 错误详情

## 📖 使用说明

### 命令行参数

```bash
python tests/stress_test.py [OPTIONS]
```

**主要参数：**

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | - | `http://127.0.0.1:8080/v1` | 服务基础 URL |
| `--api-key` | - | `dummy` | API Key |
| `--concurrency` | `-c` | `10` | 并发数 |
| `--requests` | `-n` | `100` | 总请求数 |
| `--duration` | `-d` | - | 持续时间（秒），优先于 `--requests` |
| `--model` | `-m` | `gpt-3.5-turbo` | 模型名称 |
| `--stream` | `-s` | `False` | 使用流式响应 |
| `--timeout` | `-t` | `60` | 请求超时时间（秒） |

### 查看帮助

```bash
python tests/stress_test.py --help
```

## 🎯 测试场景

### 1. 基础并发测试

测试 proxy 在正常负载下的表现：

```bash
python tests/stress_test.py --concurrency 10 --requests 100 --model qwen3.5-35b-a3b
```

**预期结果：**
- 成功率 > 95%
- 平均响应时间 < 5 秒
- P95 响应时间 < 10 秒

### 2. 高并发测试

测试 proxy 的并发上限：

```bash
python tests/stress_test.py --concurrency 50 --requests 500 --model qwen3.5-35b-a3b
```

**注意事项：**
- 可能会遇到后端限流
- 建议使用 PTU 模型测试（无需真实 API Key）

### 3. 持续压力测试

持续一段时间的稳定性测试：

```bash
python tests/stress_test.py --concurrency 20 --duration 60 --model qwen3.5-35b-a3b
```

**用途：**
- 发现内存泄漏
- 测试长时间运行稳定性
- 评估资源使用情况

### 4. 流式响应测试

测试流式 API 的性能：

```bash
python tests/stress_test.py --stream --concurrency 10 --requests 100 --model qwen3.5-35b-a3b
```

**特殊指标：**
- 首 Token 时间（TTFT - Time To First Token）
- Token 生成速率

### 5. 不同模型对比测试

对比不同模型的性能：

```bash
# PTU 模型
python tests/stress_test.py -c 10 -n 50 -m qwen3.5-35b-a3b

# Doubao 模型
python tests/stress_test.py -c 10 -n 50 -m Doubao-1.5-pro-32k

# DeepSeek 模型
python tests/stress_test.py -c 10 -n 50 -m DeepSeek-V3
```

### 6. 极限压测

测试 proxy 的极限承载能力：

```bash
python tests/stress_test.py --concurrency 100 --requests 1000 --model qwen3.5-35b-a3b --timeout 120
```

**警告：**
- 可能会导致服务暂时不可用
- 建议在测试环境运行
- 需要增加超时时间

## 📊 性能指标说明

### 基本统计

| 指标 | 说明 | 目标值 |
|------|------|--------|
| 总请求数 | 发送的请求总数 | - |
| 成功请求 | 成功完成的请求数 | > 95% |
| 失败请求 | 失败的请求数 | < 5% |
| 总耗时 | 整个压测过程的时间 | - |
| 吞吐量（QPS） | 每秒处理的请求数 | 取决于并发和后端性能 |

### 响应时间指标

| 指标 | 说明 | 参考值 |
|------|------|--------|
| 平均响应时间 | 所有成功请求的平均时间 | < 5 秒 |
| 最快响应 | 最快的请求响应时间 | - |
| 最慢响应 | 最慢的请求响应时间 | < 10 秒 |
| P50（中位数） | 50% 的请求响应时间低于此值 | < 4 秒 |
| P90 | 90% 的请求响应时间低于此值 | < 8 秒 |
| P95 | 95% 的请求响应时间低于此值 | < 10 秒 |
| P99 | 99% 的请求响应时间低于此值 | < 15 秒 |

### 流式响应特有指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| 首 Token 时间 | 收到第一个 token 的时间 | < 2 秒 |
| Token 总数 | 生成的 token 总数 | - |
| Token 速率 | 每秒生成的 token 数 | 取决于模型 |

## 🔍 常见问题

### Q1: 为什么成功率很低？

**可能原因：**
1. **并发数过高** - 超过了后端服务的限制
   - **解决方案**：降低 `--concurrency` 参数
2. **后端服务不可用** - 真实 API 需要有效的 Key
   - **解决方案**：使用 PTU 模型进行测试
3. **网络问题** - 连接超时
   - **解决方案**：增加 `--timeout` 参数

### Q2: 如何提高吞吐量？

**方法：**
1. **增加并发数** - `--concurrency` 参数
2. **优化后端** - 确保后端服务性能良好
3. **使用连接池** - 脚本已内置，无需额外配置
4. **减少请求复杂度** - 使用更小的 `max_tokens`

### Q3: 流式响应的 Token 数量为 0？

**原因：**
- 脚本统计的是 SSE 事件数，不是实际 token 数
- 需要解析每个事件的 JSON 内容才能准确统计

**影响：**
- 不影响首 Token 时间测试
- Token 速率指标可能不准确

### Q4: HTTP 500 错误是什么原因？

**常见原因：**
1. **后端服务错误** - PTU Gateway 返回错误
2. **请求过载** - 并发请求导致后端压力过大
3. **配置问题** - 模型不可用或参数错误

**排查步骤：**
1. 查看 proxy 服务日志
2. 降低并发数重试
3. 使用 `curl` 命令单独测试

### Q5: 如何对比 proxy 和直接调用后端的性能？

**方法：**
```bash
# 测试 proxy
python tests/stress_test.py --url http://127.0.0.1:8080/v1 -c 10 -n 100 -m qwen3.5-35b-a3b

# 测试直接调用（需修改 URL 为后端地址）
python tests/stress_test.py --url http://backend-url/v1 -c 10 -n 100 -m qwen3.5-35b-a3b
```

**对比指标：**
- 响应时间差异（proxy 的开销）
- 成功率变化
- 吞吐量对比

### Q6: 压测时 CPU/内存占用过高怎么办？

**优化建议：**
1. **降低并发数** - 从小到大逐步增加
2. **监控资源** - 使用 `top` 或 `htop` 查看
3. **优化代码** - 检查是否有性能瓶颈
4. **增加资源** - 升级服务器配置

## 📈 性能基准参考

基于测试结果的性能基准（仅供参考）：

### PTU 模型（qwen3.5-35b-a3b）

| 并发数 | 成功率 | 平均响应时间 | P95 响应时间 | 吞吐量 |
|--------|--------|--------------|--------------|--------|
| 3 | 86.7% | 3.5 秒 | 6.1 秒 | 0.83 QPS |
| 5 | 75.0% | 4.3 秒 | 8.5 秒 | 1.18 QPS |
| 10 | 60-70% | 5-6 秒 | 10-12 秒 | 1.5-2 QPS |

**结论：**
- 推荐并发数：3-5
- PTU 后端对并发有限制
- 流式响应成功率更高

## 🛠️ 高级用法

### 1. 自定义测试消息

修改 `tests/stress_test.py` 中的 `test_messages` 列表：

```python
self.test_messages = [
    {"role": "user", "content": "Your custom message 1"},
    {"role": "user", "content": "Your custom message 2"},
    # ...
]
```

### 2. 测试工具调用

添加 tools 参数到请求 payload：

```python
payload = {
    "model": self.model,
    "messages": messages,
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {...}
            }
        }
    ],
    "tool_choice": "auto",
    # ...
}
```

### 3. 导出测试结果

将结果保存到文件：

```bash
python tests/stress_test.py -c 10 -n 100 > results.txt
```

### 4. 并行测试多个场景

使用 shell 脚本：

```bash
#!/bin/bash
# test_suite.sh

echo "测试场景 1: 低并发"
python tests/stress_test.py -c 5 -n 50 -m qwen3.5-35b-a3b

echo "测试场景 2: 中并发"
python tests/stress_test.py -c 10 -n 100 -m qwen3.5-35b-a3b

echo "测试场景 3: 流式响应"
python tests/stress_test.py -c 5 -n 50 -m qwen3.5-35b-a3b --stream
```

## 📝 最佳实践

1. **从小规模开始** - 先用低并发测试，确认服务正常
2. **逐步增加压力** - 找到性能临界点
3. **多次测试取平均** - 避免偶然因素影响
4. **监控服务状态** - 观察 CPU、内存、网络使用情况
5. **测试不同场景** - 流式/非流式、不同模型、不同消息长度
6. **记录测试结果** - 建立性能基准，对比优化效果

## 🔗 相关文档

- [架构文档](ARCHITECTURE.md)
- [开发文档](DEVELOPMENT.md)
- [测试指南](../tests/README.md)

---

最后更新：2026-03-02
