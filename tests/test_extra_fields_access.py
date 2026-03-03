"""
测试额外字段的属性访问功能

测试 Pydantic 模型的额外字段可以通过属性访问，
使得 API 行为与 OpenAI SDK 保持一致。
"""

import pytest
from proxy_app.models.openai_models import (
    ChatCompletionMessage,
    DeltaMessage,
    ChatCompletionResponse,
    ChatCompletionChunk,
    Choice,
)


class TestMessageExtraFieldAccess:
    """测试 ChatCompletionMessage 的额外字段访问"""

    def test_message_extra_field_attribute_access(self):
        """测试通过属性访问 message 的额外字段"""
        # 创建包含额外字段的消息
        message = ChatCompletionMessage(
            role="assistant",
            content="Hello",
            custom_field="custom_value",
            another_field={"nested": "data"}
        )

        # 测试属性访问
        assert message.custom_field == "custom_value"
        assert message.another_field == {"nested": "data"}

    def test_message_nonexistent_field_raises_error(self):
        """测试访问不存在的字段会抛出 AttributeError"""
        message = ChatCompletionMessage(
            role="assistant",
            content="Hello"
        )

        # 测试访问不存在的字段会抛出 AttributeError
        with pytest.raises(AttributeError) as exc_info:
            _ = message.nonexistent_field

        assert "nonexistent_field" in str(exc_info.value)

    def test_message_with_reasoning_content(self):
        """测试 reasoning_content 字段仍然正常工作"""
        message = ChatCompletionMessage(
            role="assistant",
            content="Answer",
            reasoning_content="Thinking process"
        )

        # 标准字段可以直接访问
        assert message.reasoning_content == "Thinking process"

    def test_extra_fields_and_standard_fields(self):
        """测试标准字段和额外字段共存"""
        message = ChatCompletionMessage(
            role="assistant",
            content="Content",
            reasoning_content="Reasoning",
            custom_1="value1",
            custom_2="value2"
        )

        # 标准字段
        assert message.role == "assistant"
        assert message.content == "Content"
        assert message.reasoning_content == "Reasoning"

        # 额外字段
        assert message.custom_1 == "value1"
        assert message.custom_2 == "value2"

    def test_message_extra_field_via_setattr(self):
        """测试通过 setattr 动态设置额外字段"""
        message = ChatCompletionMessage(
            role="assistant",
            content="Hello"
        )

        # 动态设置额外字段
        setattr(message, "dynamic_field", "dynamic_value")

        # 通过属性访问
        assert message.dynamic_field == "dynamic_value"


class TestDeltaMessageExtraFieldAccess:
    """测试 DeltaMessage 的额外字段访问"""

    def test_delta_message_extra_field_attribute_access(self):
        """测试通过属性访问 delta message 的额外字段"""
        delta = DeltaMessage(
            content="Hello",
            custom_field="custom_value"
        )

        # 测试属性访问
        assert delta.custom_field == "custom_value"

    def test_delta_message_nonexistent_field_raises_error(self):
        """测试访问不存在的字段会抛出 AttributeError"""
        delta = DeltaMessage(
            content="Hello"
        )

        with pytest.raises(AttributeError) as exc_info:
            _ = delta.nonexistent_field

        assert "nonexistent_field" in str(exc_info.value)

    def test_delta_message_with_reasoning_content(self):
        """测试 delta message 的 reasoning_content 字段"""
        delta = DeltaMessage(
            content="Answer",
            reasoning_content="Thinking"
        )

        # 标准字段可以直接访问
        assert delta.reasoning_content == "Thinking"

    def test_delta_message_extra_and_standard_fields(self):
        """测试 delta message 的标准字段和额外字段共存"""
        delta = DeltaMessage(
            role="assistant",
            content="Content",
            reasoning_content="Reasoning",
            custom_field="custom_value"
        )

        # 标准字段
        assert delta.role == "assistant"
        assert delta.content == "Content"
        assert delta.reasoning_content == "Reasoning"

        # 额外字段
        assert delta.custom_field == "custom_value"


class TestResponseAndMessageSeparation:
    """测试响应和消息的额外字段分别存储"""

    def test_response_and_message_extra_fields_separate(self):
        """测试响应和消息的额外字段分别存储"""
        # 创建带额外字段的 message
        message = ChatCompletionMessage(
            role="assistant",
            content="Hello",
            message_custom="message_value"
        )

        choice = Choice(
            index=0,
            message=message,
            finish_reason="stop"
        )

        # 创建带额外字段的 response
        response = ChatCompletionResponse(
            id="test-id",
            created=123456,
            model="test-model",
            choices=[choice],
            response_custom="response_value"
        )

        # 验证字段分别存储
        assert message.message_custom == "message_value"
        assert response.response_custom == "response_value"

    def test_message_and_response_both_have_extra_fields(self):
        """测试 message 和 response 都有额外字段时不会冲突"""
        # 创建带多个额外字段的 message
        message = ChatCompletionMessage(
            role="assistant",
            content="Hello",
            field1="message_value1",
            field2="message_value2"
        )

        choice = Choice(
            index=0,
            message=message,
            finish_reason="stop"
        )

        # 创建带多个额外字段的 response
        response = ChatCompletionResponse(
            id="test-id",
            created=123456,
            model="test-model",
            choices=[choice],
            field1="response_value1",  # 与 message 字段同名
            field3="response_value3"
        )

        # 验证字段分别存储，不会相互影响
        assert message.field1 == "message_value1"
        assert message.field2 == "message_value2"
        assert response.field1 == "response_value1"
        assert response.field3 == "response_value3"


class TestChunkExtraFieldAccess:
    """测试流式响应块的额外字段访问"""

    def test_chunk_extra_field_attribute_access(self):
        """测试通过属性访问 chunk 的额外字段"""
        from proxy_app.models.openai_models import StreamChoice

        delta = DeltaMessage(
            content="Hello",
            delta_custom="delta_value"
        )

        stream_choice = StreamChoice(
            index=0,
            delta=delta,
            finish_reason=None
        )

        # 创建带额外字段的 chunk
        chunk = ChatCompletionChunk(
            id="test-id",
            created=123456,
            model="test-model",
            choices=[stream_choice],
            chunk_custom="chunk_value"
        )

        # 验证字段访问
        assert delta.delta_custom == "delta_value"
        assert chunk.chunk_custom == "chunk_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
