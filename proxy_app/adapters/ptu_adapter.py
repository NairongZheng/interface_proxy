"""
PTU 适配器

处理 PTU 后端的特殊格式：
- 请求：使用 PTU Gateway API (/gateway/chatTask/callResult)
- 响应：解包 PTU 包装格式，提取内层响应
"""

import time
import json
import getpass
from typing import AsyncGenerator

from proxy_app.adapters.openai_adapter import OpenAIAdapter
from proxy_app.models.common import InternalRequest, InternalResponse, InternalStreamChunk
from proxy_app.utils.logger import logger


class PTUAdapter(OpenAIAdapter):
    """
    PTU 适配器，继承自 OpenAI 适配器

    PTU 后端特点：
    1. API 端点不同：/gateway/chatTask/callResult（不是 /v1/chat/completions）
    2. 请求格式不同：需要 server_name, transaction_id, channel_code 等参数
    3. 响应格式：外层 PTU 包装 + 内层 OpenAI 格式
    4. 认证方式：使用 api-key header（不是 Authorization Bearer）

    适配器职责：
    - 请求转换：标准 OpenAI 格式（用户侧）
    - 后端调用：PTU 特定格式（后端侧）
    - 响应解包：PTU 包装 → OpenAI 格式
    """

    async def forward(self, internal_request: InternalRequest) -> InternalResponse:
        """
        转发请求到 PTU 后端（非流式）

        流程：
        1. 构造 PTU 请求格式
        2. 调用 PTU Gateway API
        3. 解包 PTU 响应
        4. 解析为内部格式

        Args:
            internal_request: 内部统一格式的请求

        Returns:
            内部统一格式的响应

        Raises:
            Exception: PTU 后端调用失败
        """
        # 构造 PTU 请求
        ptu_request = self._build_ptu_request(internal_request)

        # 调用 PTU 后端
        client = await self.get_client()
        url = f"{self.backend_url}/gateway/chatTask/callResult"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        logger.info(f"调用 PTU 后端: {url}")
        logger.debug(f"PTU 请求参数: model={ptu_request['model']}, transaction_id={ptu_request['transaction_id']}")

        try:
            response = await client.post(url, json=ptu_request, headers=headers)
            response.raise_for_status()

            logger.info(f"PTU 响应状态码: {response.status_code}")

            # 打印原始响应（用于调试）
            response_text = response.text
            logger.info(f"PTU 响应长度: {len(response_text)} 字符")
            logger.info(f"PTU 响应前500字符: {response_text[:500]}")

            if not response_text:
                raise ValueError("PTU 返回空响应")

            ptu_response = response.json()

            # 解包 PTU 响应
            openai_response = self.unwrap_ptu_response(ptu_response)

            # 解析为内部格式（复用父类的解析逻辑）
            return self._parse_openai_response(openai_response)

        except Exception as e:
            logger.error(f"PTU 后端调用失败: {e}", exc_info=True)
            raise

    async def forward_stream(
        self, internal_request: InternalRequest
    ) -> AsyncGenerator[InternalStreamChunk, None]:
        """
        转发请求到 PTU 后端（流式）

        流程：
        1. 构造 PTU 请求格式（stream=true）
        2. 调用 PTU Gateway API
        3. 逐块解包 PTU 响应
        4. 解析为内部流式格式

        Args:
            internal_request: 内部统一格式的请求

        Yields:
            内部统一格式的流式响应块

        Raises:
            Exception: PTU 后端调用失败
        """
        # 构造 PTU 请求
        ptu_request = self._build_ptu_request(internal_request)

        # 调用 PTU 后端（流式）
        client = await self.get_client()
        url = f"{self.backend_url}/gateway/chatTask/callResult"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        logger.info(f"调用 PTU 后端（流式）: {url}")
        logger.debug(f"PTU 请求参数: model={ptu_request['model']}, stream=true")

        try:
            async with client.stream("POST", url, json=ptu_request, headers=headers) as response:
                response.raise_for_status()

                # 读取 SSE 流
                async for line in response.aiter_lines():
                    line = line.strip()

                    # 跳过空行和注释
                    if not line or line.startswith(":"):
                        continue

                    # 解析 SSE 格式：data: {...}
                    if line.startswith("data: "):
                        data_str = line[6:]  # 去掉 "data: " 前缀

                        # 检查结束标记
                        if data_str == "[DONE]":
                            logger.debug("PTU 流式响应结束")
                            break

                        try:
                            # 解析 JSON 数据
                            ptu_chunk = json.loads(data_str)

                            # 解包 PTU 包装（如果存在）
                            if "code" in ptu_chunk:
                                # PTU 包装格式
                                openai_chunk = self.unwrap_ptu_response(ptu_chunk)
                            else:
                                # 已经是 OpenAI 格式
                                openai_chunk = ptu_chunk

                            # 解析为内部流式格式（复用父类逻辑）
                            internal_chunk = self._parse_openai_stream_chunk(openai_chunk)

                            yield internal_chunk

                        except json.JSONDecodeError as e:
                            logger.warning(f"解析 PTU 流式数据失败: {e}, data: {data_str}")
                            continue

        except Exception as e:
            logger.error(f"PTU 流式调用失败: {e}", exc_info=True)
            raise

    def _build_ptu_request(self, internal_request: InternalRequest) -> dict:
        """
        构造 PTU 请求格式

        PTU 请求格式：
        {
          "server_name": "test",
          "model": "Doubao-1.5-pro-32k",
          "messages": [...],
          "transaction_id": "user-model-timestamp",
          "channel_code": "doubao|ali|azure",
          "stream": true|false,
          "tools": [...],  // 可选
          "temperature": 0.7,  // 可选
          "max_tokens": 100,  // 可选
          ...
        }

        新增功能：支持将 extra_params 传递到 PTU 后端
        额外参数（如 enable_thinking, reasoning_mode 等）会被合并到请求的顶层

        Args:
            internal_request: 内部统一格式的请求

        Returns:
            PTU 格式的请求字典，如果有 extra_params，
            会将其合并到请求的顶层
        """
        model = internal_request["model"]

        # 基础参数
        ptu_request = {
            "server_name": "test",
            "model": model,
            "messages": internal_request["messages"],
            "transaction_id": f"{getpass.getuser()}-{model}-{int(time.time())}",
            "channel_code": self.infer_channel_code(model),
        }

        # 可选参数
        if "stream" in internal_request:
            ptu_request["stream"] = internal_request["stream"]
        if "temperature" in internal_request:
            ptu_request["temperature"] = internal_request["temperature"]
        if "max_tokens" in internal_request:
            ptu_request["max_tokens"] = internal_request["max_tokens"]
        if "top_p" in internal_request:
            ptu_request["top_p"] = internal_request["top_p"]
        if "stop" in internal_request:
            ptu_request["stop"] = internal_request["stop"]
        if "tools" in internal_request and internal_request["tools"]:
            ptu_request["tools"] = internal_request["tools"]
        if "tool_choice" in internal_request:
            ptu_request["tool_choice"] = internal_request["tool_choice"]

        # ========== 新增：合并额外参数 ==========
        # PTU 后端也需要支持额外参数（如 enable_thinking, reasoning_mode 等）
        # 将 extra_params 合并到 PTU 请求的顶层
        # PTU Gateway 会将这些参数传递给下游模型服务
        if "extra_params" in internal_request and internal_request["extra_params"]:
            extra_params = internal_request["extra_params"]

            logger.debug(
                f"合并 {len(extra_params)} 个额外参数到 PTU 后端请求: {list(extra_params.keys())}"
            )

            # 步骤 1: 直接合并到顶层
            # 与 OpenAI 适配器的行为保持一致
            ptu_request.update(extra_params)

        return ptu_request

    @staticmethod
    def unwrap_ptu_response(ptu_response: dict) -> dict:
        """
        解包 PTU 响应，提取内部的 OpenAI 格式

        PTU 响应格式：
        {
          "code": 10000,  // 10000=成功，10001=错误
          "msg": "成功",
          "data": {
            "task_id": 12345,
            "response_content": {
              // 内层是标准 OpenAI 格式
              "choices": [...],
              "model": "...",
              "usage": {...}
            }
          }
        }

        Args:
            ptu_response: PTU 包装格式响应

        Returns:
            OpenAI 格式响应字典

        Raises:
            ValueError: PTU 返回错误或格式不正确
        """
        # 检查 PTU 状态码
        code = ptu_response.get("code")
        if code != 10000:
            msg = ptu_response.get("msg", "未知错误")
            error_msg = f"PTU 后端错误 (code={code}): {msg}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 提取 response_content
        data = ptu_response.get("data", {})
        response_content = data.get("response_content")

        if not response_content:
            raise ValueError("PTU 响应缺少 response_content 字段")

        return response_content

    @staticmethod
    def infer_channel_code(model: str) -> str:
        """
        根据模型名称推断 channel_code

        PTU 后端需要 channel_code 参数指定供应商：
        - doubao: Doubao, DeepSeek 系列
        - ali: Qwen 系列
        - azure: GPT 系列

        Args:
            model: 模型名称

        Returns:
            channel_code 字符串
        """
        model_lower = model.lower()

        if "doubao" in model_lower or "deepseek" in model_lower:
            return "doubao"
        elif "qwen" in model_lower:
            return "ali"
        elif "gpt" in model_lower:
            return "azure"
        else:
            # 默认使用 doubao
            logger.warning(f"无法推断模型 {model} 的 channel_code，使用默认值 'doubao'")
            return "doubao"

    def _parse_openai_response(self, openai_response: dict) -> InternalResponse:
        """
        解析 OpenAI 格式响应为内部格式

        复用父类 OpenAIAdapter 的解析逻辑

        Args:
            openai_response: OpenAI 格式的响应

        Returns:
            内部统一格式的响应
        """
        # 提取关键信息
        choices = openai_response.get("choices", [])
        if not choices:
            raise ValueError("OpenAI 响应缺少 choices 字段")

        first_choice = choices[0]
        message = first_choice.get("message", {})

        # 构造内部格式
        internal_response: InternalResponse = {
            "id": openai_response.get("id", "unknown"),
            "created": openai_response.get("created", int(time.time())),
            "model": openai_response.get("model", "unknown"),
            "role": message.get("role", "assistant"),
            "content": message.get("content", ""),
            "finish_reason": first_choice.get("finish_reason"),
            "usage": openai_response.get("usage", {}),
        }

        # 可选字段
        if "reasoning_content" in message:
            internal_response["reasoning_content"] = message["reasoning_content"]
        if "tool_calls" in message:
            internal_response["tool_calls"] = message["tool_calls"]

        return internal_response

    def _parse_openai_stream_chunk(self, openai_chunk: dict) -> InternalStreamChunk:
        """
        解析 OpenAI 流式响应块为内部格式

        Args:
            openai_chunk: OpenAI 格式的流式响应块

        Returns:
            内部统一格式的流式响应块
        """
        choices = openai_chunk.get("choices", [])
        if not choices:
            return {
                "id": openai_chunk.get("id", "unknown"),
                "delta_content": None,
                "delta_role": None,
                "finish_reason": None,
            }

        first_choice = choices[0]
        delta = first_choice.get("delta", {})

        # 构造内部流式格式
        internal_chunk: InternalStreamChunk = {
            "id": openai_chunk.get("id", "unknown"),
            "delta_content": delta.get("content"),
            "delta_role": delta.get("role"),
            "finish_reason": first_choice.get("finish_reason"),
        }

        # 可选字段
        if "reasoning_content" in delta:
            internal_chunk["delta_reasoning_content"] = delta["reasoning_content"]
        if "tool_calls" in delta:
            internal_chunk["delta_tool_calls"] = delta["tool_calls"]

        return internal_chunk
