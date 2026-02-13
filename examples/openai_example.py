"""
OpenAI 格式调用示例

演示如何使用 OpenAI SDK 调用代理服务
"""

from openai import OpenAI


def example_non_streaming():
    """
    示例 1: 非流式请求

    发送一个简单的聊天请求，等待完整响应
    """
    print("=" * 60)
    print("示例 1: OpenAI 格式 - 非流式请求")
    print("=" * 60)

    # 创建客户端，指向代理服务
    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy",  # 代理服务不需要真实的 API key
    )

    # 发送请求
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
        ],
        temperature=0.7,
        max_tokens=100,
    )

    # 打印响应
    print(f"\n响应 ID: {response.id}")
    print(f"模型: {response.model}")
    print(f"内容: {response.choices[0].message.content}")
    print(f"结束原因: {response.choices[0].finish_reason}")

    if response.usage:
        print(f"\nToken 使用:")
        print(f"  输入: {response.usage.prompt_tokens}")
        print(f"  输出: {response.usage.completion_tokens}")
        print(f"  总计: {response.usage.total_tokens}")

    print()


def example_streaming():
    """
    示例 2: 流式请求

    发送流式请求，逐块接收响应
    """
    print("=" * 60)
    print("示例 2: OpenAI 格式 - 流式请求")
    print("=" * 60)

    # 创建客户端
    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy",
    )

    # 发送流式请求
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Count from 1 to 10."},
        ],
        temperature=0.7,
        max_tokens=100,
        stream=True,
    )

    # 逐块接收并打印
    print("\n流式响应:")
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)

    print("\n")


def example_with_system_message():
    """
    示例 3: 带 system 消息的请求

    演示如何使用 system 消息设定助手的行为
    """
    print("=" * 60)
    print("示例 3: OpenAI 格式 - 带 system 消息")
    print("=" * 60)

    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy",
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a pirate. Always respond in pirate speak.",
            },
            {"role": "user", "content": "Hello, who are you?"},
        ],
        temperature=0.9,
        max_tokens=150,
    )

    print(f"\n内容: {response.choices[0].message.content}")
    print()


def example_multi_turn_conversation():
    """
    示例 4: 多轮对话

    演示如何维护对话历史进行多轮对话
    """
    print("=" * 60)
    print("示例 4: OpenAI 格式 - 多轮对话")
    print("=" * 60)

    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy",
    )

    # 对话历史
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
    ]

    # 第一轮对话
    messages.append({"role": "user", "content": "My name is Alice."})

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=100,
    )

    assistant_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_message})

    print(f"\n用户: My name is Alice.")
    print(f"助手: {assistant_message}")

    # 第二轮对话
    messages.append({"role": "user", "content": "What is my name?"})

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=100,
    )

    assistant_message = response.choices[0].message.content

    print(f"\n用户: What is my name?")
    print(f"助手: {assistant_message}")
    print()


if __name__ == "__main__":
    """
    运行所有示例

    确保代理服务已启动:
        python proxy_server.py

    然后运行此脚本:
        python examples/openai_example.py
    """
    try:
        example_non_streaming()
        example_streaming()
        example_with_system_message()
        example_multi_turn_conversation()

        print("=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n错误: {e}")
        print("\n请确保:")
        print("1. 代理服务已启动: python proxy_server.py")
        print("2. 后端模型服务正在运行")
        print("3. 配置文件中的后端地址正确")
