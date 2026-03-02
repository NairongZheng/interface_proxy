"""
PTU 模型调用示例

演示如何使用标准 OpenAI SDK 调用 PTU 模型。
系统会自动识别 PTU 模型并处理格式转换，对用户完全透明。

使用前提：
1. 代理服务已启动（python proxy_server.py）
2. 后端服务支持 PTU 格式

运行方式：
    python examples/ptu_example.py
"""

import openai

# ==================== 配置 ====================

# 配置代理服务地址
openai.api_base = "http://localhost:8080/v1"
openai.api_key = "dummy"  # 代理服务不需要真实 key

# ==================== 示例 1：基本文本生成 ====================


def example_basic_chat():
    """
    基本聊天示例

    使用 PTU 模型进行简单的对话
    """
    print("\n" + "=" * 60)
    print("示例 1: 基本文本生成（PTU 模型 - Doubao-1.5-pro-32k）")
    print("=" * 60)

    response = openai.ChatCompletion.create(
        model="Doubao-1.5-pro-32k",  # PTU 模型
        messages=[{"role": "user", "content": "你好，请介绍一下你自己"}],
        temperature=0.7,
    )

    print(f"\n模型: {response['model']}")
    print(f"内容: {response['choices'][0]['message']['content']}")
    print(f"Token 使用: {response['usage']}")


# ==================== 示例 2：流式响应 ====================


def example_streaming_chat():
    """
    流式响应示例

    使用 PTU 模型进行流式对话
    """
    print("\n" + "=" * 60)
    print("示例 2: 流式响应（PTU 模型 - DeepSeek-V3）")
    print("=" * 60)

    print("\n模型回复：")

    response = openai.ChatCompletion.create(
        model="DeepSeek-V3",  # PTU 模型
        messages=[{"role": "user", "content": "写一首关于春天的短诗"}],
        stream=True,
    )

    for chunk in response:
        if chunk["choices"][0].get("delta", {}).get("content"):
            content = chunk["choices"][0]["delta"]["content"]
            print(content, end="", flush=True)

    print("\n")


# ==================== 示例 3：推理内容（Thinking 模型）====================


def example_thinking_model():
    """
    推理模型示例

    使用支持推理内容的 PTU 模型（如 Doubao-1.5-thinking-pro）
    """
    print("\n" + "=" * 60)
    print("示例 3: 推理内容（PTU 模型 - Doubao-1.5-thinking-pro）")
    print("=" * 60)

    response = openai.ChatCompletion.create(
        model="Doubao-1.5-thinking-pro",  # PTU 推理模型
        messages=[{"role": "user", "content": "解释一下量子纠缠的原理"}],
        temperature=0.7,
    )

    print(f"\n模型: {response['model']}")

    # 检查是否有推理内容
    message = response["choices"][0]["message"]
    if "reasoning_content" in message:
        print(f"\n推理过程:\n{message['reasoning_content']}")

    print(f"\n回答内容:\n{message['content']}")
    print(f"\nToken 使用: {response['usage']}")


# ==================== 示例 4：多模型对比 ====================


def example_multi_model():
    """
    多模型对比示例

    同时调用多个 PTU 模型，对比回答
    """
    print("\n" + "=" * 60)
    print("示例 4: 多模型对比")
    print("=" * 60)

    question = "请用一句话解释什么是机器学习"
    models = ["Doubao-1.5-pro-32k", "DeepSeek-V3", "qwen3.5-plus"]

    print(f"\n问题: {question}\n")

    for model in models:
        try:
            response = openai.ChatCompletion.create(
                model=model, messages=[{"role": "user", "content": question}]
            )

            answer = response["choices"][0]["message"]["content"]
            print(f"{model}:")
            print(f"  {answer}\n")

        except Exception as e:
            print(f"{model}: 调用失败 - {e}\n")


# ==================== 示例 5：错误处理 ====================


def example_error_handling():
    """
    错误处理示例

    演示如何处理 PTU 后端可能返回的错误
    """
    print("\n" + "=" * 60)
    print("示例 5: 错误处理")
    print("=" * 60)

    # 尝试使用不支持工具调用的模型调用工具
    try:
        response = openai.ChatCompletion.create(
            model="Doubao-1.5-pro-32k-character-250228",  # 不支持工具调用
            messages=[{"role": "user", "content": "今天天气怎么样？"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "获取天气信息",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "城市名称"}
                            },
                        },
                    },
                }
            ],
        )

        print("调用成功（如果模型支持）")
        print(response["choices"][0]["message"])

    except Exception as e:
        print(f"预期的错误: {e}")
        print("提示：某些 PTU 模型不支持工具调用功能")


# ==================== 主函数 ====================


def main():
    """
    运行所有示例
    """
    print("\n" + "=" * 60)
    print("PTU 模型调用示例")
    print("=" * 60)
    print("\n注意：")
    print("1. 确保代理服务已启动（python proxy_server.py）")
    print("2. 确保后端服务支持 PTU 格式")
    print("3. PTU 模型调用与标准 OpenAI 模型完全相同")
    print()

    try:
        # 运行各个示例
        example_basic_chat()
        example_streaming_chat()
        example_thinking_model()
        example_multi_model()
        example_error_handling()

        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n运行示例时出错: {e}")
        print("请检查代理服务是否正常运行")


if __name__ == "__main__":
    main()
