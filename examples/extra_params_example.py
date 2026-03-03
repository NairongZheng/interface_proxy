"""
extra_body 参数使用示例

演示如何通过 OpenAI SDK 的 extra_body 参数传递额外参数到后端
支持各种现代 LLM 的高级功能，如思考模式、推理模式等
"""

import os
from openai import OpenAI

# 配置 Proxy 服务地址
PROXY_BASE_URL = os.environ.get("PROXY_BASE_URL", "http://127.0.0.1:8080/v1")
PROXY_API_KEY = os.environ.get("PROXY_API_KEY", "dummy")


def example_1_enable_thinking():
    """
    示例 1: 启用思考模式

    适用场景：
    - DeepSeek 系列模型
    - 需要模型展示推理过程
    """
    print("\n" + "=" * 60)
    print("示例 1: 启用思考模式 (enable_thinking)")
    print("=" * 60)

    client = OpenAI(base_url=PROXY_BASE_URL, api_key=PROXY_API_KEY)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "为什么天空是蓝色的？"}
        ],
        # 使用 extra_body 传递额外参数
        extra_body={
            "enable_thinking": True
        }
    )

    print(f"模型: {response.model}")
    print(f"内容: {response.choices[0].message.content}")

    # 如果后端支持，可能会有 reasoning_content
    if hasattr(response.choices[0].message, 'reasoning_content'):
        print(f"推理过程: {response.choices[0].message.reasoning_content}")


def example_2_thinking_config():
    """
    示例 2: 配置思考参数

    适用场景：
    - o1 系列模型
    - 需要控制思考预算和类型
    """
    print("\n" + "=" * 60)
    print("示例 2: 配置思考参数 (thinking)")
    print("=" * 60)

    client = OpenAI(base_url=PROXY_BASE_URL, api_key=PROXY_API_KEY)

    response = client.chat.completions.create(
        model="o1-preview",
        messages=[
            {"role": "user", "content": "设计一个高效的缓存系统"}
        ],
        extra_body={
            "thinking": {
                "type": "enable",
                "budget": "high"  # 允许更多的思考时间
            }
        }
    )

    print(f"模型: {response.model}")
    print(f"内容: {response.choices[0].message.content[:200]}...")


def example_3_reasoning_mode():
    """
    示例 3: 设置推理模式

    适用场景：
    - 支持推理模式的模型
    - 需要高质量推理输出
    """
    print("\n" + "=" * 60)
    print("示例 3: 设置推理模式 (reasoning_mode)")
    print("=" * 60)

    client = OpenAI(base_url=PROXY_BASE_URL, api_key=PROXY_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": "解释量子纠缠的原理"}
        ],
        extra_body={
            "reasoning_mode": "high",  # 使用高质量推理模式
            "enable_thinking": True
        }
    )

    print(f"模型: {response.model}")
    print(f"内容: {response.choices[0].message.content[:200]}...")


def example_4_chat_template_kwargs():
    """
    示例 4: 自定义聊天模板参数

    适用场景：
    - Qwen 系列模型
    - 需要控制生成提示和其他模板参数
    """
    print("\n" + "=" * 60)
    print("示例 4: 自定义聊天模板参数 (chat_template_kwargs)")
    print("=" * 60)

    client = OpenAI(base_url=PROXY_BASE_URL, api_key=PROXY_API_KEY)

    response = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[
            {"role": "user", "content": "写一首关于春天的诗"}
        ],
        extra_body={
            "chat_template_kwargs": {
                "add_generation_prompt": True,
                "temperature": 0.9
            }
        }
    )

    print(f"模型: {response.model}")
    print(f"内容: {response.choices[0].message.content}")


def example_5_multiple_params():
    """
    示例 5: 组合多个额外参数

    适用场景：
    - 需要同时配置多个高级参数
    - 复杂的生成任务
    """
    print("\n" + "=" * 60)
    print("示例 5: 组合多个额外参数")
    print("=" * 60)

    client = OpenAI(base_url=PROXY_BASE_URL, api_key=PROXY_API_KEY)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "设计一个分布式数据库的架构"}
        ],
        # 标准参数
        temperature=0.7,
        max_tokens=500,
        # 额外参数
        extra_body={
            "enable_thinking": True,
            "reasoning_mode": "high",
            "thinking": {"type": "enable", "budget": "medium"},
            "chat_template_kwargs": {"add_generation_prompt": True},
            # 自定义参数（根据后端支持）
            "custom_param": "custom_value"
        }
    )

    print(f"模型: {response.model}")
    print(f"内容: {response.choices[0].message.content[:200]}...")
    print(f"Tokens: prompt={response.usage.prompt_tokens}, "
          f"completion={response.usage.completion_tokens}")


def example_6_streaming_with_extra_params():
    """
    示例 6: 流式输出 + 额外参数

    适用场景：
    - 需要实时输出
    - 同时使用高级功能
    """
    print("\n" + "=" * 60)
    print("示例 6: 流式输出 + 额外参数")
    print("=" * 60)

    client = OpenAI(base_url=PROXY_BASE_URL, api_key=PROXY_API_KEY)

    stream = client.chat.completions.create(
        model="qwen3.5-35b-a3b",
        messages=[
            {"role": "user", "content": "数到 5"}
        ],
        stream=True,
        extra_body={
            "enable_thinking": True
        }
    )

    print("流式输出: ", end="", flush=True)
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()  # 换行


def main():
    """
    主函数：运行所有示例

    使用方法：
    1. 启动 proxy 服务：
       $ python proxy_app/main.py

    2. 运行示例：
       $ python examples/extra_params_example.py

    3. 或者指定 proxy 地址：
       $ PROXY_BASE_URL=http://localhost:8080/v1 python examples/extra_params_example.py
    """
    print("\n" + "=" * 60)
    print("Extra Body 参数使用示例")
    print("=" * 60)
    print(f"\nProxy 地址: {PROXY_BASE_URL}")

    try:
        # 运行所有示例
        example_1_enable_thinking()
        example_2_thinking_config()
        example_3_reasoning_mode()
        example_4_chat_template_kwargs()
        example_5_multiple_params()
        example_6_streaming_with_extra_params()

        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n提示：")
        print("1. 确保 proxy 服务已启动")
        print("2. 检查后端是否支持相应的模型和参数")
        print("3. 查看服务日志获取详细信息")


if __name__ == "__main__":
    main()
