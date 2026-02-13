"""
基础功能测试

测试适配器的基本转换功能
"""

import pytest

from proxy_app.adapters.openai_adapter import OpenAIAdapter
from proxy_app.models.openai_models import ChatCompletionRequest, ChatMessage


class TestOpenAIAdapter:
    """测试 OpenAI 适配器"""

    def test_adapt_request_basic(self):
        """测试基本请求转换"""
        # 创建适配器
        adapter = OpenAIAdapter()

        # 创建 OpenAI 请求
        request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[
                ChatMessage(role="system", content="You are helpful."),
                ChatMessage(role="user", content="Hello!"),
            ],
            temperature=0.7,
            max_tokens=100,
        )

        # 转换为内部格式
        internal = adapter.adapt_request(request)

        # 验证转换结果
        assert internal["model"] == "gpt-3.5-turbo"
        assert len(internal["messages"]) == 2
        assert internal["messages"][0]["role"] == "system"
        assert internal["messages"][0]["content"] == "You are helpful."
        assert internal["messages"][1]["role"] == "user"
        assert internal["messages"][1]["content"] == "Hello!"
        assert internal["temperature"] == 0.7
        assert internal["max_tokens"] == 100
        assert internal["stream"] is False

    def test_adapt_request_with_stream(self):
        """测试流式请求转换"""
        adapter = OpenAIAdapter()

        request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[ChatMessage(role="user", content="Test")],
            stream=True,
        )

        internal = adapter.adapt_request(request)

        assert internal["stream"] is True

    def test_adapt_request_with_stop_sequences(self):
        """测试带停止序列的请求转换"""
        adapter = OpenAIAdapter()

        # 停止序列为字符串
        request1 = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[ChatMessage(role="user", content="Test")],
            stop="END",
        )

        internal1 = adapter.adapt_request(request1)
        assert internal1["stop"] == ["END"]

        # 停止序列为列表
        request2 = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[ChatMessage(role="user", content="Test")],
            stop=["END", "STOP"],
        )

        internal2 = adapter.adapt_request(request2)
        assert internal2["stop"] == ["END", "STOP"]

    def test_adapt_response_basic(self):
        """测试基本响应转换"""
        adapter = OpenAIAdapter()

        # 创建内部格式响应
        internal_response = {
            "id": "chatcmpl-123",
            "created": 1234567890,
            "model": "gpt-3.5-turbo",
            "content": "Hello! How can I help you?",
            "role": "assistant",
            "finish_reason": "stop",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

        # 转换为 OpenAI 格式
        response = adapter.adapt_response(internal_response)

        # 验证转换结果
        assert response.id == "chatcmpl-123"
        assert response.created == 1234567890
        assert response.model == "gpt-3.5-turbo"
        assert response.object == "chat.completion"
        assert len(response.choices) == 1
        assert response.choices[0].message.content == "Hello! How can I help you?"
        assert response.choices[0].message.role == "assistant"
        assert response.choices[0].finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30

    def test_get_format_name(self):
        """测试获取格式名称"""
        adapter = OpenAIAdapter()
        assert adapter.get_format_name() == "openai"


if __name__ == "__main__":
    """
    运行测试

    安装 pytest:
        pip install pytest pytest-asyncio

    运行测试:
        pytest tests/test_adapters.py -v
    """
    pytest.main([__file__, "-v"])
