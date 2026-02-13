"""
HTTP 客户端辅助模块
提供 HTTP 请求的辅助函数
"""

from typing import Any, Dict, Optional

import httpx


async def post_json(
    client: httpx.AsyncClient,
    url: str,
    data: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None
) -> httpx.Response:
    """
    发送 JSON POST 请求

    Args:
        client: httpx 异步客户端实例
        url: 目标 URL
        data: 要发送的 JSON 数据（字典）
        headers: 可选的 HTTP 请求头
        timeout: 可选的超时时间（秒）

    Returns:
        HTTP 响应对象

    Raises:
        httpx.HTTPError: HTTP 请求失败
    """
    # 设置默认请求头
    if headers is None:
        headers = {}

    # 确保 Content-Type 为 application/json
    headers.setdefault("Content-Type", "application/json")

    # 发送 POST 请求
    response = await client.post(
        url,
        json=data,
        headers=headers,
        timeout=timeout
    )

    # 检查响应状态
    response.raise_for_status()

    return response


def parse_sse_line(line: str) -> Optional[Dict[str, str]]:
    """
    解析单行 SSE（Server-Sent Events）数据

    SSE 格式说明：
    - 每行格式为 "field: value"
    - 常见字段：event, data, id, retry
    - 空行表示消息结束

    Args:
        line: SSE 数据行（去除换行符）

    Returns:
        解析后的字典 {"field": "value"}，如果是空行或无效行则返回 None

    Examples:
        >>> parse_sse_line("data: {\"text\": \"hello\"}")
        {"data": "{\"text\": \"hello\"}"}
        >>> parse_sse_line("event: message_start")
        {"event": "message_start"}
        >>> parse_sse_line("")
        None
    """
    # 空行表示消息结束
    if not line or line.isspace():
        return None

    # 查找冒号分隔符
    if ":" not in line:
        return None

    # 分割字段和值
    field, _, value = line.partition(":")

    # 去除字段和值的前后空格
    field = field.strip()
    value = value.strip()

    return {field: value}
