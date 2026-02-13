#!/usr/bin/env python3
"""
快速验证工具调用功能是否正常工作
"""

import sys
import json

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ 错误：需要安装 anthropic 库")
    print("运行：pip install anthropic")
    sys.exit(1)


def test_tool_use():
    """测试工具调用功能"""

    print("🧪 测试工具调用功能...")
    print()

    # 初始化客户端
    client = Anthropic(
        base_url="http://127.0.0.1:8080",
        api_key="dummy",
    )

    # 定义简单的工具
    tools = [
        {
            "name": "calculator",
            "description": "执行简单的数学计算",
            "input_schema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "数学运算类型",
                    },
                    "a": {"type": "number", "description": "第一个数字"},
                    "b": {"type": "number", "description": "第二个数字"},
                },
                "required": ["operation", "a", "b"],
            },
        }
    ]

    try:
        # 发送请求
        print("📤 发送请求...")
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            tools=tools,
            messages=[{"role": "user", "content": "请帮我计算 15 + 27"}],
        )

        print(f"✅ 请求成功")
        print(f"   响应 ID: {response.id}")
        print(f"   停止原因: {response.stop_reason}")
        print(f"   内容块数量: {len(response.content)}")
        print()

        # 检查是否有工具调用
        has_tool_use = False
        for block in response.content:
            if block.type == "tool_use":
                has_tool_use = True
                print(f"🔧 工具调用:")
                print(f"   工具名称: {block.name}")
                print(
                    f"   工具参数: {json.dumps(block.input, ensure_ascii=False, indent=2)}"
                )
                print()

        if has_tool_use:
            print("✅ 工具调用功能正常！")
            return True
        else:
            print("⚠️  模型没有调用工具")
            print("   这可能是因为后端模型不支持工具调用")
            return False

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Interface Proxy - 工具调用功能验证")
    print("=" * 60)
    print()

    success = test_tool_use()

    print()
    print("=" * 60)
    if success:
        print("✅ 验证通过：工具调用功能正常工作")
    else:
        print("❌ 验证失败：请检查配置")
    print("=" * 60)

    sys.exit(0 if success else 1)
