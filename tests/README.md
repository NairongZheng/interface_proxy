# 测试指南

本目录包含 interface_proxy 项目的所有测试文件。

## 📁 测试文件结构

```
tests/
├── README.md                   # 本文件
├── test_integration.py         # 🌟 集成测试（推荐）
├── test_adapter_units.py       # 单元测试：Adapter 层
├── test_adapters.py            # 单元测试：格式转换
├── test_ptu_adapter.py         # 单元测试：PTU Adapter
├── stress_test.py              # 🚀 压力测试（性能测试）
└── test_api_key.sh             # 快速验证 API Key
```

## 🌟 推荐测试流程

### 1. 快速验证（可选）

如果您有 PTU API Key，可以先验证：

```bash
./tests/test_api_key.sh YOUR_API_KEY
```

### 2. 启动代理服务

```bash
# 确保配置文件正确
cat config/config.yaml

# 启动服务
python proxy_server.py
```

### 3. 运行集成测试

```bash
# 完整测试所有格式转换
python tests/test_integration.py
```

这个测试会验证：
- ✅ OpenAI 格式 → 标准 OpenAI 后端（透传）
- ✅ OpenAI 格式 → PTU 后端（自动转换）
- ✅ Anthropic 格式 → OpenAI 后端（格式转换）
- ✅ 流式和非流式响应
- ✅ Models API

## 🧪 单元测试

### Adapter 后端调用测试

直接测试 Adapter 层，不经过 FastAPI 路由：

```bash
python tests/test_adapter_units.py
```

### PTU Adapter 单元测试

测试 PTU 响应解包和 channel_code 推断：

```bash
pytest tests/test_ptu_adapter.py -v
```

### 格式转换测试

测试 OpenAI ↔ Anthropic 格式转换：

```bash
pytest tests/test_adapters.py -v
```

## 📊 测试覆盖范围

### 集成测试（test_integration.py）
- ✅ 所有格式组合：OpenAI、Anthropic、PTU
- ✅ 流式和非流式响应
- ✅ 多种 PTU 模型
- ✅ Models API

### 单元测试
- ✅ Adapter 格式转换
- ✅ PTU 响应解包
- ✅ Channel code 推断
- ✅ 错误处理

### 压力测试（stress_test.py）
- ✅ 并发性能测试
- ✅ 流式/非流式响应性能
- ✅ 吞吐量和延迟统计
- ✅ 多模型性能对比

## 🚀 压力测试

压力测试用于评估 proxy 服务的性能和并发能力。

### 快速开始

```bash
# 基础压测：10 并发，100 请求
python tests/stress_test.py

# 自定义参数
python tests/stress_test.py --concurrency 20 --requests 200 --model qwen3.5-35b-a3b

# 测试流式响应
python tests/stress_test.py --stream --concurrency 10 --requests 100

# 持续压测 60 秒
python tests/stress_test.py --duration 60 --concurrency 10
```

### 常用测试场景

```bash
# 1. 低并发稳定性测试（推荐开始）
python tests/stress_test.py -c 3 -n 15 -m qwen3.5-35b-a3b

# 2. 中等并发测试
python tests/stress_test.py -c 10 -n 100 -m qwen3.5-35b-a3b

# 3. 高并发压力测试
python tests/stress_test.py -c 50 -n 500 -m qwen3.5-35b-a3b

# 4. 流式响应性能测试
python tests/stress_test.py -c 5 -n 50 -m qwen3.5-35b-a3b --stream

# 5. 持续稳定性测试
python tests/stress_test.py -c 10 -d 60 -m qwen3.5-35b-a3b
```

### 性能指标

压测报告包含以下关键指标：

- **成功率** - 请求成功的百分比（目标 > 95%）
- **吞吐量（QPS）** - 每秒处理的请求数
- **响应时间** - 平均、P50、P90、P95、P99
- **首 Token 时间** - 流式响应的 TTFT（Time To First Token）
- **错误详情** - 失败请求的错误分类

### 详细文档

完整的压测指南请查看：[压力测试指南](../docs/STRESS_TEST_GUIDE.md)

包含：
- 详细的命令行参数说明
- 多种测试场景示例
- 性能指标解读
- 常见问题排查
- 性能优化建议

## 🔧 测试配置

### 环境要求

```bash
# 使用 conda 环境
conda activate dev

# 或确保已安装依赖
pip install -r requirements.txt
```

### 配置文件

测试依赖 `config/config.yaml`：

```yaml
backend:
  url: "https://api.ppchat.vip"  # 标准后端
  api_key: "your-key"

ptu:
  backend_url: "http://api.schedule.mtc.sensetime.com"  # PTU 后端
  models:
    - "Doubao-1.5-pro-32k"
    - "qwen3.5-plus"
    # ...
```

## 🎯 测试场景说明

### 场景 1: OpenAI → 标准后端

```
用户 (OpenAI SDK) → 代理 (/v1/chat/completions) → OpenAIAdapter → 标准后端
```

### 场景 2: OpenAI → PTU 后端

```
用户 (OpenAI SDK) → 代理 (/v1/chat/completions) → PTUAdapter → PTU Gateway
                         ↓
                    自动识别 PTU 模型
                    添加 channel_code
                    解包 PTU 响应
```

### 场景 3: Anthropic → OpenAI 后端

```
用户 (Anthropic SDK) → 代理 (/v1/messages) → AnthropicAdapter → 标准后端
                           ↓
                     格式转换：
                     - system 字段处理
                     - content 数组转文本
                     - 响应转回 Anthropic 格式
```

## ⚠️ 常见问题

### 1. 集成测试失败：Connection refused

**原因**：代理服务未启动

**解决方案**：
```bash
# 终端 1：启动服务
python proxy_server.py

# 终端 2：运行测试
python tests/test_integration.py
```

### 2. PTU 测试失败：401 Unauthorized

**原因**：API Key 无效或未配置

**解决方案**：
1. 检查 `config/config.yaml` 中的 `backend.api_key`
2. 使用 `test_api_key.sh` 验证 API Key
3. 确保 API Key 有权限访问 PTU 模型

### 3. PTU 测试失败：返回 HTML

**原因**：PTU backend_url 配置错误

**解决方案**：
确保 `config/config.yaml` 中：
```yaml
ptu:
  backend_url: "http://api.schedule.mtc.sensetime.com"  # 正确
  # 不是 "https://api.ppchat.vip"
```

### 4. 单元测试 import 错误

**原因**：Python 路径问题

**解决方案**：
```bash
# 在项目根目录运行
export PYTHONPATH=$PWD:$PYTHONPATH
pytest tests/ -v
```

## 📈 CI/CD 集成

可以将测试集成到 CI/CD 流程：

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: |
          pytest tests/test_adapters.py -v
          pytest tests/test_ptu_adapter.py -v
      - name: Run integration tests
        run: |
          # 需要启动代理服务和后端
          python proxy_server.py &
          sleep 5
          python tests/test_integration.py
```

## 🔗 相关文档

- [项目 README](../README.md) - 项目主文档
- [开发文档](../docs/DEVELOPMENT.md) - 实现细节
- [架构文档](../docs/ARCHITECTURE.md) - 新架构说明
- [压力测试指南](../docs/STRESS_TEST_GUIDE.md) - 性能测试详细文档

## 📝 贡献测试

添加新功能时，请同时添加测试：

1. **单元测试**：测试单个函数/类的功能
   - 文件名：`test_<module_name>.py`
   - 类名：`Test<ClassName>`
   - 函数名：`test_<what_it_tests>`

2. **集成测试**：在 `test_integration.py` 中添加新场景

3. **文档**：更新本 README 说明新测试的用法

---

最后更新：2026-03-02
