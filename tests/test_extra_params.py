"""
单元测试：测试 extra_body 参数支持

测试 OpenAI SDK 的 extra_body 参数能否正确传递到后端
包括参数提取、合并、端到端验证
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from proxy_app.adapters.openai_adapter import OpenAIAdapter
from proxy_app.adapters.ptu_adapter import PTUAdapter
from proxy_app.models.openai_models import ChatCompletionRequest, ChatMessage


class TestExtraParamsExtraction:
    """测试额外参数提取功能"""

    def test_adapt_request_extracts_extra_params(self):
        """测试 adapt_request 方法能够提取 __pydantic_extra__ 中的额外参数"""
        adapter = OpenAIAdapter(backend_url="http://test.com", api_key="test")

        # 创建请求对象
        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[ChatMessage(role="user", content="Test")]
        )

        # 模拟 Pydantic 的 __pydantic_extra__ 字段
        # 这些参数来自 OpenAI SDK 的 extra_body
        request.__pydantic_extra__ = {
            "enable_thinking": True,
            "reasoning_mode": "high",
            "chat_template_kwargs": {"temperature": 0.8}
        }

        # 转换为内部格式
        internal = adapter.adapt_request(request)

        # 验证额外参数被正确提取
        assert "extra_params" in internal
        assert internal["extra_params"]["enable_thinking"] is True
        assert internal["extra_params"]["reasoning_mode"] == "high"
        assert internal["extra_params"]["chat_template_kwargs"]["temperature"] == 0.8

    def test_adapt_request_without_extra_params(self):
        """测试没有额外参数时的行为"""
        adapter = OpenAIAdapter(backend_url="http://test.com", api_key="test")

        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[ChatMessage(role="user", content="Test")]
        )

        # 不设置 __pydantic_extra__
        internal = adapter.adapt_request(request)

        # 验证不会有 extra_params 字段
        assert "extra_params" not in internal

    def test_adapt_request_with_empty_extra_params(self):
        """测试额外参数为空时的行为"""
        adapter = OpenAIAdapter(backend_url="http://test.com", api_key="test")

        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[ChatMessage(role="user", content="Test")]
        )

        # 设置空的 __pydantic_extra__
        request.__pydantic_extra__ = {}

        internal = adapter.adapt_request(request)

        # 验证不会有 extra_params 字段
        assert "extra_params" not in internal


class TestExtraParamsMerging:
    """测试额外参数合并功能"""

    def test_build_openai_request_merges_extra_params(self):
        """测试 _build_openai_request 方法能够合并额外参数到请求顶层"""
        adapter = OpenAIAdapter(backend_url="http://test.com", api_key="test")

        # 构造包含额外参数的内部请求
        internal_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
            "stream": False,
            "extra_params": {
                "enable_thinking": True,
                "thinking": {"type": "enable", "budget": "high"},
                "reasoning_mode": "high"
            }
        }

        # 构建 OpenAI 请求
        openai_request = adapter._build_openai_request(internal_request)

        # 验证额外参数被合并到顶层
        assert openai_request["enable_thinking"] is True
        assert openai_request["thinking"]["type"] == "enable"
        assert openai_request["thinking"]["budget"] == "high"
        assert openai_request["reasoning_mode"] == "high"

        # 验证标准参数仍然存在
        assert openai_request["model"] == "gpt-4"
        assert openai_request["messages"][0]["content"] == "Test"
        assert openai_request["stream"] is False

    def test_build_openai_request_without_extra_params(self):
        """测试没有额外参数时的正常构建"""
        adapter = OpenAIAdapter(backend_url="http://test.com", api_key="test")

        internal_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
            "stream": False
        }

        openai_request = adapter._build_openai_request(internal_request)

        # 验证标准请求正常构建
        assert openai_request["model"] == "gpt-4"
        assert openai_request["messages"][0]["content"] == "Test"
        assert openai_request["stream"] is False

        # 验证没有额外的参数
        assert "enable_thinking" not in openai_request
        assert "reasoning_mode" not in openai_request

    def test_build_ptu_request_merges_extra_params(self):
        """测试 _build_ptu_request 方法能够合并额外参数到 PTU 请求"""
        adapter = PTUAdapter(
            backend_url="http://test.com",
            api_key="test"
        )

        # 构造包含额外参数的内部请求
        internal_request = {
            "model": "qwen3.5-35b",
            "messages": [{"role": "user", "content": "Test"}],
            "stream": False,
            "extra_params": {
                "enable_thinking": True,
                "chat_template_kwargs": {"add_generation_prompt": True}
            }
        }

        # 构建 PTU 请求
        ptu_request = adapter._build_ptu_request(internal_request)

        # 验证额外参数被合并到顶层
        assert ptu_request["enable_thinking"] is True
        assert ptu_request["chat_template_kwargs"]["add_generation_prompt"] is True

        # 验证 PTU 特有参数存在
        assert ptu_request["model"] == "qwen3.5-35b"
        assert ptu_request["server_name"] == "test"
        assert "transaction_id" in ptu_request
        assert "channel_code" in ptu_request


class TestEndToEndExtraParams:
    """端到端测试：从请求到后端"""

    def test_full_pipeline_with_extra_params(self):
        """测试完整的参数传递管道"""
        adapter = OpenAIAdapter(backend_url="http://test.com", api_key="test")

        # 步骤 1: 创建原始请求（带额外参数）
        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[ChatMessage(role="user", content="Explain quantum physics")],
            temperature=0.7,
            max_tokens=100
        )

        # 模拟 extra_body 参数
        request.__pydantic_extra__ = {
            "enable_thinking": True,
            "thinking": {"type": "enable"},
            "reasoning_mode": "high"
        }

        # 步骤 2: 适配请求（提取额外参数）
        internal = adapter.adapt_request(request)

        # 验证内部格式包含额外参数
        assert "extra_params" in internal
        assert len(internal["extra_params"]) == 3

        # 步骤 3: 构建后端请求（合并额外参数）
        backend_request = adapter._build_openai_request(internal)

        # 验证最终请求包含所有参数
        assert backend_request["model"] == "gpt-4"
        assert backend_request["temperature"] == 0.7
        assert backend_request["max_tokens"] == 100
        assert backend_request["enable_thinking"] is True
        assert backend_request["thinking"]["type"] == "enable"
        assert backend_request["reasoning_mode"] == "high"

    def test_various_extra_param_types(self):
        """测试各种类型的额外参数"""
        adapter = OpenAIAdapter(backend_url="http://test.com", api_key="test")

        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[ChatMessage(role="user", content="Test")]
        )

        # 测试不同类型的参数
        request.__pydantic_extra__ = {
            "bool_param": True,
            "int_param": 42,
            "float_param": 3.14,
            "str_param": "test",
            "list_param": [1, 2, 3],
            "dict_param": {"nested": {"deep": "value"}},
            "null_param": None
        }

        internal = adapter.adapt_request(request)
        backend_request = adapter._build_openai_request(internal)

        # 验证所有类型的参数都能正确传递
        assert backend_request["bool_param"] is True
        assert backend_request["int_param"] == 42
        assert backend_request["float_param"] == 3.14
        assert backend_request["str_param"] == "test"
        assert backend_request["list_param"] == [1, 2, 3]
        assert backend_request["dict_param"]["nested"]["deep"] == "value"
        assert backend_request["null_param"] is None


if __name__ == "__main__":
    """
    运行测试：

    方法 1 - 使用 pytest（推荐）：
    $ pytest tests/test_extra_params.py -v

    方法 2 - 直接运行：
    $ python tests/test_extra_params.py
    """
    pytest.main([__file__, "-v"])
