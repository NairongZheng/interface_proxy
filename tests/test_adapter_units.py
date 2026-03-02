"""
单元测试：测试 Adapter 的后端调用功能

直接测试 Adapter 层，不经过 FastAPI 路由
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from proxy_app.adapters.openai_adapter import OpenAIAdapter
from proxy_app.adapters.ptu_adapter import PTUAdapter
from proxy_app.adapters.anthropic_adapter import AnthropicAdapter
from proxy_app.models.common import InternalRequest


async def test_openai_adapter():
    """测试 OpenAIAdapter 后端调用"""
    print("\n" + "=" * 60)
    print("测试 OpenAIAdapter")
    print("=" * 60)

    adapter = OpenAIAdapter(
        backend_url="http://127.0.0.1:8000",  # 假设这是标准 OpenAI 后端
        api_key=None,
        timeout=60.0,
    )

    internal_request: InternalRequest = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": False,
        "max_tokens": 30,
    }

    try:
        print("\n调用 OpenAI 后端（非流式）...")
        internal_response = await adapter.forward(internal_request)
        print(f"✅ 成功！内容: {internal_response['content']}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    finally:
        await adapter.close()


async def test_ptu_adapter():
    """测试 PTUAdapter 后端调用"""
    print("\n" + "=" * 60)
    print("测试 PTUAdapter")
    print("=" * 60)

    adapter = PTUAdapter(
        backend_url="http://api.schedule.mtc.sensetime.com",
        api_key="REMOVED_API_KEY",
        timeout=60.0,
    )

    # 测试非流式
    internal_request: InternalRequest = {
        "model": "Doubao-1.5-pro-32k",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": False,
        "max_tokens": 30,
    }

    try:
        print("\n调用 PTU 后端（非流式）...")
        internal_response = await adapter.forward(internal_request)
        print(f"✅ 成功！")
        print(f"   模型: {internal_response['model']}")
        print(f"   内容: {internal_response['content']}")
        print(f"   Tokens: {internal_response.get('usage', {})}")
    except Exception as e:
        print(f"❌ 失败: {e}")

    # 测试流式
    internal_request["stream"] = True
    internal_request["messages"] = [{"role": "user", "content": "数到3"}]

    try:
        print("\n调用 PTU 后端（流式）...")
        print("流式输出: ", end="", flush=True)

        async for chunk in adapter.forward_stream(internal_request):
            if chunk.get("delta_content"):
                print(chunk["delta_content"], end="", flush=True)

        print("\n✅ 流式成功！")
    except Exception as e:
        print(f"❌ 流式失败: {e}")
    finally:
        await adapter.close()


async def test_anthropic_adapter():
    """测试 AnthropicAdapter 后端调用"""
    print("\n" + "=" * 60)
    print("测试 AnthropicAdapter")
    print("=" * 60)

    # AnthropicAdapter 继承自 OpenAIAdapter
    # 它会将 Anthropic 格式转换为 OpenAI 格式后调用标准后端
    adapter = AnthropicAdapter(
        backend_url="http://127.0.0.1:8000",  # OpenAI 格式后端
        api_key=None,
        timeout=60.0,
    )

    internal_request: InternalRequest = {
        "model": "claude-3-opus-20240229",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": False,
        "max_tokens": 30,
    }

    try:
        print("\n调用 OpenAI 后端（Anthropic Adapter）...")
        internal_response = await adapter.forward(internal_request)
        print(f"✅ 成功！内容: {internal_response['content']}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    finally:
        await adapter.close()


async def main():
    """主函数"""
    print("\n🧪 Adapter 单元测试")
    print("\n说明：直接测试 Adapter 的后端调用功能")

    # 只测试 PTU，因为其他后端可能不可用
    await test_ptu_adapter()

    print("\n✅ 单元测试完成！\n")


if __name__ == "__main__":
    asyncio.run(main())
