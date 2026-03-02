#!/bin/bash
# 测试 PTU API Key 是否有效

API_KEY="${1:-REMOVED_API_KEY}"

echo "测试 API Key: $API_KEY"
echo "==========================================="

curl -X POST 'https://api.ppchat.vip/v1/chat/completions' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model":"Doubao-1.5-pro-32k",
    "messages":[{"role":"user","content":"你好"}],
    "channel_code":"doubao",
    "transaction_id":"test-123",
    "max_tokens":10
  }' 2>&1

echo ""
echo "==========================================="
echo "如果出现 '无效的令牌' 错误，请提供正确的 API Key"
echo "用法: ./test_api_key.sh YOUR_API_KEY"
