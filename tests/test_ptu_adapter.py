"""
PTU 适配器单元测试

测试 PTU 适配器的核心功能：
1. PTU 响应解包
2. channel_code 推断
3. 错误处理
4. 继承关系验证
"""

import pytest
from proxy_app.adapters.ptu_adapter import PTUAdapter


class TestPTUAdapter:
    """PTU 适配器测试类"""

    # ==================== 测试 PTU 响应解包 ====================

    def test_unwrap_ptu_response_success(self):
        """
        测试成功的 PTU 响应解包

        验证能正确提取 response_content 字段
        """
        # 模拟 PTU 成功响应
        ptu_response = {
            "code": 10000,
            "msg": "成功",
            "data": {
                "task_id": 58857509,
                "response_content": {
                    "id": "chatcmpl-123",
                    "model": "Doubao-1.5-pro-32k",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "你好！"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                    },
                },
            },
        }

        # 解包
        openai_response = PTUAdapter.unwrap_ptu_response(ptu_response)

        # 验证
        assert openai_response["id"] == "chatcmpl-123"
        assert openai_response["model"] == "Doubao-1.5-pro-32k"
        assert openai_response["choices"][0]["message"]["content"] == "你好！"
        assert openai_response["usage"]["total_tokens"] == 15

    def test_unwrap_ptu_response_error_code(self):
        """
        测试 PTU 错误码处理

        验证 code != 10000 时抛出 ValueError
        """
        # 模拟 PTU 错误响应
        ptu_response = {
            "code": 10001,
            "msg": "业务错误:the requested model does not support function calling",
            "data": {},
        }

        # 验证抛出异常
        with pytest.raises(ValueError) as exc_info:
            PTUAdapter.unwrap_ptu_response(ptu_response)

        assert "PTU 后端错误 (code=10001)" in str(exc_info.value)
        assert "does not support function calling" in str(exc_info.value)

    def test_unwrap_ptu_response_missing_data(self):
        """
        测试缺少 data 字段的情况

        验证缺少必要字段时抛出 ValueError
        """
        # 缺少 data 字段
        ptu_response = {"code": 10000, "msg": "成功"}

        with pytest.raises(ValueError) as exc_info:
            PTUAdapter.unwrap_ptu_response(ptu_response)

        assert "response_content" in str(exc_info.value)

    def test_unwrap_ptu_response_missing_response_content(self):
        """
        测试缺少 response_content 字段的情况
        """
        # data 存在但缺少 response_content
        ptu_response = {"code": 10000, "msg": "成功", "data": {"task_id": 123}}

        with pytest.raises(ValueError) as exc_info:
            PTUAdapter.unwrap_ptu_response(ptu_response)

        assert "response_content" in str(exc_info.value)

    # ==================== 测试 channel_code 推断 ====================

    def test_infer_channel_code_doubao(self):
        """
        测试 Doubao 系列模型的 channel_code 推断

        Doubao 系列应返回 'doubao'
        """
        assert PTUAdapter.infer_channel_code("Doubao-1.5-pro-32k") == "doubao"
        assert PTUAdapter.infer_channel_code("Doubao-1.5-thinking-pro") == "doubao"
        assert (
            PTUAdapter.infer_channel_code("Doubao-1.5-pro-32k-character-250228")
            == "doubao"
        )

    def test_infer_channel_code_deepseek(self):
        """
        测试 DeepSeek 系列模型的 channel_code 推断

        DeepSeek 系列应返回 'doubao'
        """
        assert PTUAdapter.infer_channel_code("DeepSeek-R1") == "doubao"
        assert PTUAdapter.infer_channel_code("DeepSeek-V3") == "doubao"
        assert (
            PTUAdapter.infer_channel_code("DeepSeek-R1-distill-qwen-32b") == "doubao"
        )

    def test_infer_channel_code_qwen(self):
        """
        测试 Qwen 系列模型的 channel_code 推断

        Qwen 系列应返回 'ali'
        """
        assert PTUAdapter.infer_channel_code("qwen3.5-plus") == "ali"
        assert PTUAdapter.infer_channel_code("qwen3.5-flash") == "ali"
        assert PTUAdapter.infer_channel_code("qwen3.5-plus-thinking") == "ali"

    def test_infer_channel_code_gpt(self):
        """
        测试 GPT 系列模型的 channel_code 推断

        GPT 系列应返回 'azure'
        """
        assert PTUAdapter.infer_channel_code("gpt-4") == "azure"
        assert PTUAdapter.infer_channel_code("gpt-3.5-turbo") == "azure"
        assert PTUAdapter.infer_channel_code("gpt-4-turbo") == "azure"

    def test_infer_channel_code_unknown(self):
        """
        测试未知模型的 channel_code 推断

        未知模型应返回默认值 'doubao'
        """
        assert PTUAdapter.infer_channel_code("unknown-model") == "doubao"
        assert PTUAdapter.infer_channel_code("some-random-model") == "doubao"

    def test_infer_channel_code_case_insensitive(self):
        """
        测试 channel_code 推断的大小写不敏感性

        验证不同大小写的模型名称能正确识别
        """
        assert PTUAdapter.infer_channel_code("DOUBAO-1.5-pro-32k") == "doubao"
        assert PTUAdapter.infer_channel_code("deepseek-r1") == "doubao"
        assert PTUAdapter.infer_channel_code("QWEN3.5-plus") == "ali"
        assert PTUAdapter.infer_channel_code("GPT-4") == "azure"

    # ==================== 测试适配器继承关系 ====================

    def test_adapter_inheritance(self):
        """
        测试 PTUAdapter 继承自 OpenAIAdapter

        验证继承关系和方法可用性
        """
        from proxy_app.adapters.openai_adapter import OpenAIAdapter

        adapter = PTUAdapter()

        # 验证继承关系
        assert isinstance(adapter, OpenAIAdapter)
        assert isinstance(adapter, PTUAdapter)

        # 验证方法存在
        assert hasattr(adapter, "adapt_request")
        assert hasattr(adapter, "adapt_response")
        assert hasattr(adapter, "adapt_streaming_response")
        assert hasattr(adapter, "unwrap_ptu_response")
        assert hasattr(adapter, "infer_channel_code")

    def test_get_format_name(self):
        """
        测试 get_format_name 方法

        验证返回正确的格式名称
        """
        adapter = PTUAdapter()
        assert adapter.get_format_name() == "ptu"

    # ==================== 测试请求适配（继承自 OpenAIAdapter）====================

    def test_adapt_request(self):
        """
        测试请求适配

        PTUAdapter 的 adapt_request 应该与 OpenAIAdapter 相同
        """
        from proxy_app.models.openai_models import ChatCompletionRequest, ChatMessage

        adapter = PTUAdapter()

        # 构造 OpenAI 格式请求
        request = ChatCompletionRequest(
            model="Doubao-1.5-pro-32k",
            messages=[ChatMessage(role="user", content="你好")],
            temperature=0.7,
        )

        # 适配请求
        internal_request = adapter.adapt_request(request)

        # 验证内部格式
        assert internal_request["model"] == "Doubao-1.5-pro-32k"
        assert len(internal_request["messages"]) == 1
        assert internal_request["messages"][0]["role"] == "user"
        assert internal_request["messages"][0]["content"] == "你好"
        assert internal_request["temperature"] == 0.7

    # ==================== 测试响应适配（继承自 OpenAIAdapter）====================

    def test_adapt_response(self):
        """
        测试响应适配

        PTUAdapter 的 adapt_response 应该与 OpenAIAdapter 相同
        """
        adapter = PTUAdapter()

        # 构造内部格式响应
        internal_response = {
            "id": "chatcmpl-123",
            "created": 1234567890,
            "model": "Doubao-1.5-pro-32k",
            "content": "你好！我是 AI 助手。",
            "role": "assistant",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        # 适配响应
        external_response = adapter.adapt_response(internal_response)

        # 验证 OpenAI 格式
        assert external_response.id == "chatcmpl-123"
        assert external_response.model == "Doubao-1.5-pro-32k"
        assert external_response.choices[0].message.content == "你好！我是 AI 助手。"
        assert external_response.choices[0].finish_reason == "stop"
        assert external_response.usage.total_tokens == 30


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
