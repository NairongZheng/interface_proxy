"""
集成测试：完整测试所有格式转换场景

测试场景：
1. OpenAI → OpenAI：标准 OpenAI 格式调用
2. OpenAI → PTU：用 OpenAI SDK 调用 PTU 模型（自动转换）
3. Anthropic → OpenAI：用 Anthropic SDK 调用，后端是 OpenAI 格式
4. 流式和非流式测试

需要：
- 代理服务已启动：python proxy_server.py
- 后端配置正确：config/config.yaml
"""

import sys
import os

# 设置 PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from anthropic import Anthropic


def print_section(title):
    """打印测试章节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_openai_standard():
    """测试 1: OpenAI → 标准后端"""
    print_section("测试 1: OpenAI 格式 → 标准 OpenAI 后端（透传）")

    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy",
    )

    try:
        # 非流式
        print("\n[非流式] 调用 gpt-3.5-turbo...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=30,
        )
        print(f"✅ 成功！响应: {response.choices[0].message.content}")

        # 流式
        print("\n[流式] 调用 gpt-3.5-turbo...")
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "数到3"}],
            max_tokens=20,
            stream=True,
        )
        print("流式输出: ", end="", flush=True)
        for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n✅ 流式成功！")

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


def test_openai_to_ptu():
    """测试 2: OpenAI → PTU 后端"""
    print_section("测试 2: OpenAI 格式 → PTU 后端（自动转换）")

    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy",
    )

    # 测试多个 PTU 模型
    ptu_models = [
        "Doubao-1.5-pro-32k",
        "qwen3.5-plus",
        "DeepSeek-V3",
    ]

    for model in ptu_models:
        try:
            print(f"\n[非流式] 调用 {model}...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "你好，请用一句话介绍你自己"}],
                max_tokens=50,
                temperature=0.7,
            )
            print(f"✅ {model} 成功！")
            print(f"   响应: {response.choices[0].message.content}")
            print(f"   Tokens: {response.usage.total_tokens}")

        except Exception as e:
            print(f"❌ {model} 失败: {e}")

    # 测试流式
    try:
        print(f"\n[流式] 调用 Doubao-1.5-pro-32k...")
        stream = client.chat.completions.create(
            model="Doubao-1.5-pro-32k",
            messages=[{"role": "user", "content": "数到5"}],
            max_tokens=30,
            stream=True,
        )
        print("流式输出: ", end="", flush=True)
        for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n✅ PTU 流式成功！")

    except Exception as e:
        print(f"❌ PTU 流式失败: {e}")


def test_anthropic_to_openai():
    """测试 3: Anthropic → OpenAI 后端"""
    print_section("测试 3: Anthropic 格式 → OpenAI 后端（格式转换）")

    client = Anthropic(
        base_url="http://127.0.0.1:8080",
        api_key="dummy",
    )

    try:
        # 非流式
        print("\n[非流式] 调用 claude-3-opus-20240229...")
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=30,
            messages=[{"role": "user", "content": "你好"}],
        )
        print(f"✅ 成功！响应: {response.content[0].text}")

        # 流式
        print("\n[流式] 调用 claude-3-opus-20240229...")
        print("流式输出: ", end="", flush=True)
        with client.messages.stream(
            model="claude-3-opus-20240229",
            max_tokens=20,
            messages=[{"role": "user", "content": "数到3"}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
        print("\n✅ Anthropic 流式成功！")

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


def test_models_api():
    """测试 4: Models API"""
    print_section("测试 4: Models API（模型列表）")

    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy",
    )

    try:
        # 列出所有模型
        print("\n列出所有可用模型...")
        models = client.models.list()

        print(f"\n共有 {len(models.data)} 个可用模型：")

        # 按类型分组
        openai_models = []
        anthropic_models = []
        ptu_models = []

        for model in models.data:
            if "claude" in model.id.lower():
                anthropic_models.append(model.id)
            elif any(x in model.id for x in ["Doubao", "qwen", "DeepSeek"]):
                ptu_models.append(model.id)
            else:
                openai_models.append(model.id)

        print(f"\n  OpenAI 模型 ({len(openai_models)}): {', '.join(openai_models)}")
        print(f"  Anthropic 模型 ({len(anthropic_models)}): {', '.join(anthropic_models)}")
        print(f"  PTU 模型 ({len(ptu_models)}): {', '.join(ptu_models[:3])}{'...' if len(ptu_models) > 3 else ''}")

        print("\n✅ Models API 测试成功！")

    except Exception as e:
        print(f"❌ 失败: {e}")


def main():
    """主函数"""
    print("\n" + "🚀 " * 35)
    print("  Interface Proxy Service - 集成测试")
    print("🚀 " * 35)

    print("\n测试架构说明：")
    print("  1. 用户使用标准 SDK（OpenAI/Anthropic）调用代理服务")
    print("  2. 代理服务自动识别格式并选择对应的 Adapter")
    print("  3. Adapter 负责格式转换和后端调用")
    print("  4. 响应自动转换回用户期望的格式")

    # 执行所有测试
    test_models_api()
    test_openai_standard()
    test_openai_to_ptu()
    test_anthropic_to_openai()

    print("\n" + "=" * 70)
    print("  所有测试完成！")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
