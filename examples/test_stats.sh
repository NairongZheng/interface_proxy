#!/bin/bash
# 流量统计功能测试脚本

BASE_URL="http://127.0.0.1:8080"

echo "=========================================="
echo "流量统计功能测试"
echo "=========================================="
echo ""

# 1. 查询初始统计
echo "1. 查询初始统计（24h）:"
curl -s "${BASE_URL}/api/stats?time_range=24h" | python3 -m json.tool
echo ""

# 2. 发送测试请求
echo "2. 发送测试请求..."
curl -s -X POST ${BASE_URL}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"测试1"}],"stream":false}' > /dev/null
echo "   - gpt-4 请求已发送"

curl -s -X POST ${BASE_URL}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"测试2"}],"stream":false}' > /dev/null
echo "   - gpt-3.5-turbo 请求已发送"

curl -s -X POST ${BASE_URL}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"测试3"}],"stream":false}' > /dev/null
echo "   - gpt-4 请求已发送"
echo ""

# 3. 查询统计（24h）
sleep 1
echo "3. 查询统计（24h）:"
curl -s "${BASE_URL}/api/stats?time_range=24h" | python3 -m json.tool
echo ""

# 4. 按模型过滤
echo "4. 查询 gpt-4 模型统计:"
curl -s "${BASE_URL}/api/stats?time_range=24h&model=gpt-4" | python3 -m json.tool
echo ""

# 5. 查询模型列表
echo "5. 查询所有使用过的模型:"
curl -s "${BASE_URL}/api/stats/models" | python3 -m json.tool
echo ""

# 6. 查询 7 天统计
echo "6. 查询 7 天统计:"
curl -s "${BASE_URL}/api/stats?time_range=7d" | python3 -m json.tool
echo ""

# 7. 查询 30 天统计
echo "7. 查询 30 天统计:"
curl -s "${BASE_URL}/api/stats?time_range=30d" | python3 -m json.tool
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
