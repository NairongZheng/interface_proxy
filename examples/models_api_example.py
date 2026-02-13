#!/usr/bin/env python3
"""
Models API 测试示例

演示如何使用新增的 Models API 端点
"""

import requests
from openai import OpenAI


def test_root_endpoint():
    """
    测试根路由 - 获取服务信息
    """
    print("=" * 60)
    print("测试 1: 根路由 (GET /)")
    print("=" * 60)

    response = requests.get("http://127.0.0.1:8080/")

    print(f"状态码: {response.status_code}")
    print("响应内容:")
    print(response.json())
    print()


def test_list_models_raw():
    """
    测试列出所有模型 - 原始 HTTP 请求
    """
    print("=" * 60)
    print("测试 2: 列出所有模型 (GET /v1/models) - 原始请求")
    print("=" * 60)

    response = requests.get("http://127.0.0.1:8080/v1/models")

    print(f"状态码: {response.status_code}")
    print("响应内容:")

    data = response.json()
    print(f"模型总数: {len(data['data'])}")
    print("\n可用模型列表:")
    for model in data["data"]:
        print(f"  - {model['id']} (owned_by: {model['owned_by']})")
    print()


def test_get_model_raw():
    """
    测试获取特定模型详情 - 原始 HTTP 请求
    """
    print("=" * 60)
    print("测试 3: 获取模型详情 (GET /v1/models/{model_id}) - 原始请求")
    print("=" * 60)

    # 测试存在的模型
    model_id = "gpt-3.5-turbo"
    print(f"查询模型: {model_id}")

    response = requests.get(f"http://127.0.0.1:8080/v1/models/{model_id}")

    print(f"状态码: {response.status_code}")
    print("响应内容:")

    data = response.json()
    print(f"  模型 ID: {data['id']}")
    print(f"  所有者: {data['owned_by']}")
    print(f"  创建时间: {data['created']}")
    print()

    # 测试不存在的模型
    model_id = "non-existent-model"
    print(f"查询不存在的模型: {model_id}")

    response = requests.get(f"http://127.0.0.1:8080/v1/models/{model_id}")

    print(f"状态码: {response.status_code}")
    if response.status_code == 404:
        print("响应内容:")
        print(f"  错误信息: {response.json()['detail']}")
    print()


def test_with_openai_sdk():
    """
    测试使用 OpenAI SDK 访问 Models API
    """
    print("=" * 60)
    print("测试 4: 使用 OpenAI SDK")
    print("=" * 60)

    # 创建客户端，指向代理服务
    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy",  # 代理服务不需要真实的 API key
    )

    # 列出所有模型
    print("列出所有模型:")
    models = client.models.list()

    print(f"模型总数: {len(models.data)}")
    print("\n可用模型列表:")
    for model in models.data:
        print(f"  - {model.id} (owned_by: {model.owned_by})")
    print()

    # 获取特定模型信息
    model_id = "gpt-4"
    print(f"获取模型详情: {model_id}")

    model = client.models.retrieve(model_id)

    print(f"  模型 ID: {model.id}")
    print(f"  所有者: {model.owned_by}")
    print(f"  创建时间: {model.created}")
    print(f"  对象类型: {model.object}")
    print()


def test_health_check():
    """
    测试健康检查接口
    """
    print("=" * 60)
    print("测试 5: 健康检查 (GET /health)")
    print("=" * 60)

    response = requests.get("http://127.0.0.1:8080/health")

    print(f"状态码: {response.status_code}")
    print("响应内容:")
    print(response.json())
    print()


def main():
    """
    主函数 - 运行所有测试
    """
    print("\n" + "=" * 60)
    print("Models API 测试")
    print("=" * 60)
    print("确保代理服务已启动: python proxy_server.py")
    print("=" * 60 + "\n")

    try:
        # 测试各个端点
        test_root_endpoint()
        test_list_models_raw()
        test_get_model_raw()
        test_health_check()
        test_with_openai_sdk()

        print("=" * 60)
        print("所有测试完成！")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n错误: 无法连接到代理服务")
        print("请确保服务已启动: python proxy_server.py")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
