#!/bin/bash

# Interface Proxy Service - curl 请求示例脚本
# 展示如何使用 curl 命令调用代理服务

BASE_URL="http://127.0.0.1:8080"

echo "========================================================================"
echo "  Interface Proxy Service - curl 请求示例"
echo "========================================================================"
echo ""

# ==================== 1. 健康检查 ====================
echo "1. 健康检查"
echo "------------------------------------------------------------------------"
curl -s $BASE_URL/health | jq '.'
echo ""

# ==================== 2. 列出可用模型 ====================
echo "2. 列出可用模型"
echo "------------------------------------------------------------------------"
curl -s $BASE_URL/v1/models | jq '.data[] | {id, owned_by}' | head -20
echo ""

# ==================== 3. 获取特定模型详情 ====================
echo "3. 获取特定模型详情 (Doubao-1.5-pro-32k)"
echo "------------------------------------------------------------------------"
curl -s $BASE_URL/v1/models/Doubao-1.5-pro-32k | jq '{id, owned_by, created}'
echo ""

# ==================== 4. OpenAI 格式 - PTU 模型请求 ====================
echo "4. OpenAI 格式 - Doubao 模型请求（非流式）"
echo "------------------------------------------------------------------------"
curl -s -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Doubao-1.5-pro-32k",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "max_tokens": 50
  }' | jq -r '.choices[0].message.content'
echo ""

# ==================== 5. OpenAI 格式 - Qwen 模型 ====================
echo "5. OpenAI 格式 - Qwen 模型请求（非流式）"
echo "------------------------------------------------------------------------"
curl -s -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-plus",
    "messages": [
      {"role": "user", "content": "简单介绍你自己"}
    ],
    "max_tokens": 100
  }' | jq -r '.choices[0].message.content'
echo ""

# ==================== 6. OpenAI 格式 - DeepSeek 模型 ====================
echo "6. OpenAI 格式 - DeepSeek 模型请求（非流式）"
echo "------------------------------------------------------------------------"
curl -s -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "DeepSeek-V3",
    "messages": [
      {"role": "user", "content": "你叫什么名字？"}
    ],
    "max_tokens": 50
  }' | jq -r '.choices[0].message.content'
echo ""

# ==================== 7. OpenAI 格式 - 流式请求 ====================
echo "7. OpenAI 格式 - 流式请求示例"
echo "------------------------------------------------------------------------"
echo "执行命令（实时流式输出）："
echo 'curl -X POST $BASE_URL/v1/chat/completions \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"model":"Doubao-1.5-pro-32k","messages":[{"role":"user","content":"数到5"}],"stream":true,"max_tokens":50}'"'"
echo ""
echo "流式输出："
curl -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Doubao-1.5-pro-32k","messages":[{"role":"user","content":"数到5"}],"stream":true,"max_tokens":50}' 2>/dev/null
echo ""

# ==================== 8. 完整响应示例 ====================
echo "8. OpenAI 格式 - 完整响应结构（含 tokens 统计）"
echo "------------------------------------------------------------------------"
curl -s -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-plus",
    "messages": [
      {"role": "user", "content": "Hi"}
    ],
    "max_tokens": 30
  }' | jq '{
    model: .model,
    content: .choices[0].message.content,
    finish_reason: .choices[0].finish_reason,
    usage: .usage
  }'
echo ""

echo "========================================================================"
echo "  所有 curl 示例执行完成！"
echo "========================================================================"
echo ""
echo "提示："
echo "  - 使用 jq 可以格式化 JSON 输出"
echo "  - 添加 -v 参数可以查看详细的 HTTP 请求/响应信息"
echo "  - 流式请求会实时返回 SSE (Server-Sent Events) 格式数据"
echo ""
