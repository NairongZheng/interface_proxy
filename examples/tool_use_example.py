"""
工具调用功能测试示例

演示如何通过代理服务使用 Anthropic 工具调用功能
"""

import json
from anthropic import Anthropic


def main():
    """测试工具调用功能"""

    # 初始化客户端（指向代理服务）
    client = Anthropic(
        base_url="http://127.0.0.1:8080",
        api_key="dummy",  # 代理服务不需要真实的 API key
    )

    # 定义一个简单的工具
    tools = [
        {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、纽约",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位",
                    },
                },
                "required": ["location"],
            },
        }
    ]

    print("=" * 60)
    print("工具调用功能测试")
    print("=" * 60)
    print()

    # 测试 1: 非流式工具调用
    print("【测试 1】非流式工具调用")
    print("-" * 60)

    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            tools=tools,
            messages=[{"role": "user", "content": "北京今天天气怎么样？"}],
        )

        print(f"响应 ID: {response.id}")
        print(f"停止原因: {response.stop_reason}")
        print(f"内容块数量: {len(response.content)}")
        print()

        for i, block in enumerate(response.content):
            print(f"Content Block {i}:")
            print(f"  类型: {block.type}")

            if block.type == "text":
                print(f"  文本: {block.text}")
            elif block.type == "tool_use":
                print(f"  工具 ID: {block.id}")
                print(f"  工具名称: {block.name}")
                print(f"  工具参数: {json.dumps(block.input, ensure_ascii=False, indent=2)}")

            print()

        if response.stop_reason == "tool_use":
            print("✅ 成功：模型正确返回了工具调用")
        else:
            print("❌ 失败：模型没有返回工具调用")

    except Exception as e:
        print(f"❌ 错误: {e}")

    print()

    # 测试 2: 流式工具调用
    print("【测试 2】流式工具调用")
    print("-" * 60)

    try:
        # 收集完整的响应
        collected_blocks = []
        current_block = None

        with client.messages.stream(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            tools=tools,
            messages=[{"role": "user", "content": "上海明天天气如何？"}],
        ) as stream:
            for event in stream:
                # 打印事件类型（用于调试）
                # print(f"事件: {type(event).__name__}")

                if hasattr(event, "type"):
                    if event.type == "content_block_start":
                        # 新的 content block 开始
                        if hasattr(event, "content_block"):
                            current_block = {
                                "type": event.content_block.type,
                                "data": {},
                            }

                            if event.content_block.type == "tool_use":
                                current_block["data"]["id"] = event.content_block.id
                                current_block["data"]["name"] = event.content_block.name
                                current_block["data"]["input"] = ""

                    elif event.type == "content_block_delta":
                        # 内容增量
                        if current_block and hasattr(event, "delta"):
                            if event.delta.type == "text_delta":
                                if "text" not in current_block["data"]:
                                    current_block["data"]["text"] = ""
                                current_block["data"]["text"] += event.delta.text

                            elif event.delta.type == "input_json_delta":
                                current_block["data"]["input"] += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        # content block 结束
                        if current_block:
                            # 如果是工具调用，解析 JSON
                            if current_block["type"] == "tool_use":
                                try:
                                    current_block["data"]["input"] = json.loads(
                                        current_block["data"]["input"]
                                    )
                                except json.JSONDecodeError:
                                    pass

                            collected_blocks.append(current_block)
                            current_block = None

        print(f"收集到 {len(collected_blocks)} 个 content block:")
        print()

        for i, block in enumerate(collected_blocks):
            print(f"Content Block {i}:")
            print(f"  类型: {block['type']}")

            if block["type"] == "text":
                print(f"  文本: {block['data'].get('text', '')}")
            elif block["type"] == "tool_use":
                print(f"  工具 ID: {block['data'].get('id')}")
                print(f"  工具名称: {block['data'].get('name')}")
                print(
                    f"  工具参数: {json.dumps(block['data'].get('input', {}), ensure_ascii=False, indent=2)}"
                )

            print()

        # 检查是否有工具调用
        has_tool_use = any(block["type"] == "tool_use" for block in collected_blocks)
        if has_tool_use:
            print("✅ 成功：流式响应正确返回了工具调用")
        else:
            print("❌ 失败：流式响应没有返回工具调用")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
