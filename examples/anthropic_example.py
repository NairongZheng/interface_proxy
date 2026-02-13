"""
Anthropic 格式调用示例

演示如何使用 Anthropic SDK 调用代理服务
"""

from anthropic import Anthropic


def example_non_streaming():
    """
    示例 1: 非流式请求

    发送一个简单的消息请求，等待完整响应
    """
    print("=" * 60)
    print("示例 1: Anthropic 格式 - 非流式请求")
    print("=" * 60)

    # 创建客户端，指向代理服务
    client = Anthropic(
        base_url="http://127.0.0.1:8080",
        api_key="dummy",  # 代理服务不需要真实的 API key
    )

    # 发送请求
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "What is the capital of France?"}
        ],
        temperature=0.7,
    )

    # 打印响应
    print(f"\n响应 ID: {response.id}")
    print(f"模型: {response.model}")
    print(f"角色: {response.role}")
    print(f"内容: {response.content[0].text}")
    print(f"停止原因: {response.stop_reason}")

    if response.usage:
        print(f"\nToken 使用:")
        print(f"  输入: {response.usage.input_tokens}")
        print(f"  输出: {response.usage.output_tokens}")

    print()


def example_streaming():
    """
    示例 2: 流式请求

    发送流式请求，逐块接收响应
    """
    print("=" * 60)
    print("示例 2: Anthropic 格式 - 流式请求")
    print("=" * 60)

    # 创建客户端
    client = Anthropic(
        base_url="http://127.0.0.1:8080",
        api_key="dummy",
    )

    # 发送流式请求并接收
    print("\n流式响应:")

    with client.messages.stream(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Count from 1 to 10."}
        ],
        temperature=0.7,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

    print("\n")


def example_with_system_message():
    """
    示例 3: 带 system 消息的请求

    Anthropic 的 system 是独立字段，不在 messages 中
    """
    print("=" * 60)
    print("示例 3: Anthropic 格式 - 带 system 消息")
    print("=" * 60)

    client = Anthropic(
        base_url="http://127.0.0.1:8080",
        api_key="dummy",
    )

    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        system="You are a pirate. Always respond in pirate speak.",
        messages=[
            {"role": "user", "content": "Hello, who are you?"}
        ],
        temperature=0.9,
    )

    print(f"\n内容: {response.content[0].text}")
    print()


def example_multi_turn_conversation():
    """
    示例 4: 多轮对话

    演示如何维护对话历史进行多轮对话
    """
    print("=" * 60)
    print("示例 4: Anthropic 格式 - 多轮对话")
    print("=" * 60)

    client = Anthropic(
        base_url="http://127.0.0.1:8080",
        api_key="dummy",
    )

    # 对话历史（Anthropic 的 messages 只包含 user 和 assistant）
    messages = []

    # 第一轮对话
    messages.append({"role": "user", "content": "My name is Alice."})

    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=messages,
    )

    assistant_message = response.content[0].text
    messages.append({"role": "assistant", "content": assistant_message})

    print(f"\n用户: My name is Alice.")
    print(f"助手: {assistant_message}")

    # 第二轮对话
    messages.append({"role": "user", "content": "What is my name?"})

    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=messages,
    )

    assistant_message = response.content[0].text

    print(f"\n用户: What is my name?")
    print(f"助手: {assistant_message}")
    print()


def example_with_stop_sequences():
    """
    示例 5: 使用停止序列

    Anthropic 使用 stop_sequences 而非 stop
    """
    print("=" * 60)
    print("示例 5: Anthropic 格式 - 停止序列")
    print("=" * 60)

    client = Anthropic(
        base_url="http://127.0.0.1:8080",
        api_key="dummy",
    )

    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Write a story about a cat. End with 'The End'."}
        ],
        stop_sequences=["The End"],  # 遇到 "The End" 就停止
    )

    print(f"\n内容: {response.content[0].text}")
    print(f"停止原因: {response.stop_reason}")

    if response.stop_reason == "stop_sequence":
        print(f"匹配的停止序列: {response.stop_sequence}")

    print()


if __name__ == "__main__":
    """
    运行所有示例

    确保代理服务已启动:
        python proxy_server.py

    然后运行此脚本:
        python examples/anthropic_example.py
    """
    try:
        example_non_streaming()
        example_streaming()
        example_with_system_message()
        example_multi_turn_conversation()
        example_with_stop_sequences()

        print("=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n错误: {e}")
        print("\n请确保:")
        print("1. 代理服务已启动: python proxy_server.py")
        print("2. 后端模型服务正在运行")
        print("3. 配置文件中的后端地址正确")
