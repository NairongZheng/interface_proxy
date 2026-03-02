"""
压力测试脚本

测试 proxy 服务的并发性能，支持：
- 多并发请求
- 流式/非流式模式
- 多种模型测试
- 详细的性能统计

使用方法：
    # 基础测试（10并发，100请求）
    python tests/stress_test.py

    # 自定义并发和请求数
    python tests/stress_test.py --concurrency 50 --requests 500

    # 测试流式响应
    python tests/stress_test.py --stream

    # 测试特定模型
    python tests/stress_test.py --model Doubao-1.5-pro-32k

    # 完整压测（高并发）
    python tests/stress_test.py --concurrency 100 --requests 1000 --duration 60
"""

import argparse
import asyncio
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import httpx


class StressTestResult:
    """
    压测结果统计类

    记录并统计压测过程中的各项指标
    """

    def __init__(self):
        """初始化统计数据"""
        self.total_requests = 0
        self.success_requests = 0
        self.failed_requests = 0
        self.response_times: List[float] = []
        self.errors: Dict[str, int] = defaultdict(int)
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.first_token_times: List[float] = []  # 流式响应的首 token 时间
        self.tokens_received: List[int] = []  # 接收到的 token 数量

    def add_success(self, response_time: float, first_token_time: Optional[float] = None, tokens: Optional[int] = None):
        """
        记录成功的请求

        Args:
            response_time: 响应时间（秒）
            first_token_time: 首 token 时间（秒，仅流式）
            tokens: token 数量（仅流式）
        """
        self.total_requests += 1
        self.success_requests += 1
        self.response_times.append(response_time)

        if first_token_time is not None:
            self.first_token_times.append(first_token_time)
        if tokens is not None:
            self.tokens_received.append(tokens)

    def add_failure(self, error: str):
        """
        记录失败的请求

        Args:
            error: 错误信息
        """
        self.total_requests += 1
        self.failed_requests += 1
        self.errors[error] += 1

    def print_report(self):
        """打印压测报告"""
        if not self.start_time or not self.end_time:
            print("❌ 压测未完成，无法生成报告")
            return

        total_time = self.end_time - self.start_time

        print("\n" + "=" * 70)
        print("📊 压力测试报告")
        print("=" * 70)

        # 基本统计
        print(f"\n【基本统计】")
        print(f"  总请求数:     {self.total_requests}")
        print(f"  成功请求:     {self.success_requests} ({self.success_requests/self.total_requests*100:.1f}%)")
        print(f"  失败请求:     {self.failed_requests} ({self.failed_requests/self.total_requests*100:.1f}%)")
        print(f"  总耗时:       {total_time:.2f} 秒")
        print(f"  吞吐量:       {self.total_requests/total_time:.2f} 请求/秒")

        # 响应时间统计
        if self.response_times:
            sorted_times = sorted(self.response_times)
            avg_time = sum(sorted_times) / len(sorted_times)
            min_time = sorted_times[0]
            max_time = sorted_times[-1]
            p50 = sorted_times[int(len(sorted_times) * 0.5)]
            p90 = sorted_times[int(len(sorted_times) * 0.9)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]

            print(f"\n【响应时间】")
            print(f"  平均响应:     {avg_time:.3f} 秒")
            print(f"  最快响应:     {min_time:.3f} 秒")
            print(f"  最慢响应:     {max_time:.3f} 秒")
            print(f"  P50 (中位数): {p50:.3f} 秒")
            print(f"  P90:          {p90:.3f} 秒")
            print(f"  P95:          {p95:.3f} 秒")
            print(f"  P99:          {p99:.3f} 秒")

        # 流式响应统计
        if self.first_token_times:
            sorted_ftt = sorted(self.first_token_times)
            avg_ftt = sum(sorted_ftt) / len(sorted_ftt)
            p50_ftt = sorted_ftt[int(len(sorted_ftt) * 0.5)]
            p95_ftt = sorted_ftt[int(len(sorted_ftt) * 0.95)]

            print(f"\n【流式响应 - 首 Token 时间】")
            print(f"  平均时间:     {avg_ftt:.3f} 秒")
            print(f"  P50:          {p50_ftt:.3f} 秒")
            print(f"  P95:          {p95_ftt:.3f} 秒")

        if self.tokens_received:
            avg_tokens = sum(self.tokens_received) / len(self.tokens_received)
            total_tokens = sum(self.tokens_received)
            tokens_per_sec = total_tokens / total_time

            print(f"\n【Token 统计】")
            print(f"  总 Token 数:  {total_tokens}")
            print(f"  平均 Token:   {avg_tokens:.1f} 个/请求")
            print(f"  Token 速率:   {tokens_per_sec:.1f} 个/秒")

        # 错误统计
        if self.errors:
            print(f"\n【错误详情】")
            for error, count in sorted(self.errors.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count} 次")

        print("\n" + "=" * 70)


class StressTester:
    """
    压力测试器

    支持并发测试、流式测试、不同模型测试
    """

    def __init__(
        self,
        base_url: str,
        api_key: str = "dummy",
        concurrency: int = 10,
        total_requests: int = 100,
        duration: Optional[int] = None,
        model: str = "gpt-3.5-turbo",
        stream: bool = False,
        timeout: int = 60,
    ):
        """
        初始化压测器

        Args:
            base_url: 服务基础 URL（例如：http://127.0.0.1:8080/v1）
            api_key: API Key
            concurrency: 并发数
            total_requests: 总请求数（如果指定了 duration，则忽略此参数）
            duration: 持续时间（秒），如果指定则持续发送请求
            model: 模型名称
            stream: 是否使用流式响应
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.concurrency = concurrency
        self.total_requests = total_requests
        self.duration = duration
        self.model = model
        self.stream = stream
        self.timeout = timeout
        self.result = StressTestResult()

        # 测试用的消息
        self.test_messages = [
            {"role": "user", "content": "Say hello!"},
            {"role": "user", "content": "Count from 1 to 5."},
            {"role": "user", "content": "What is 2+2?"},
            {"role": "user", "content": "Tell me a short joke."},
            {"role": "user", "content": "Translate 'Hello' to Chinese."},
        ]

    async def send_request(self, client: httpx.AsyncClient, request_id: int) -> None:
        """
        发送单个请求

        Args:
            client: HTTP 客户端
            request_id: 请求 ID
        """
        # 轮询使用不同的测试消息
        messages = [self.test_messages[request_id % len(self.test_messages)]]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": self.stream,
            "max_tokens": 100,
        }

        start_time = time.time()
        first_token_time = None
        tokens_count = 0

        try:
            if self.stream:
                # 流式请求
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=self.timeout,
                ) as response:
                    response.raise_for_status()

                    first_chunk = True
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue

                        # 记录首 token 时间
                        if first_chunk:
                            first_token_time = time.time() - start_time
                            first_chunk = False

                        data = line[6:]  # 去掉 "data: "
                        if data == "[DONE]":
                            break

                        tokens_count += 1

                response_time = time.time() - start_time
                self.result.add_success(response_time, first_token_time, tokens_count)

            else:
                # 非流式请求
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                response_time = time.time() - start_time
                self.result.add_success(response_time)

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            self.result.add_failure(error_msg)

        except httpx.TimeoutException:
            self.result.add_failure("Timeout")

        except Exception as e:
            self.result.add_failure(f"{type(e).__name__}: {str(e)[:50]}")

    async def run_worker(self, client: httpx.AsyncClient, request_queue: asyncio.Queue) -> None:
        """
        工作协程，从队列中获取请求 ID 并执行

        Args:
            client: HTTP 客户端
            request_queue: 请求队列
        """
        while True:
            try:
                request_id = await asyncio.wait_for(request_queue.get(), timeout=1.0)
                await self.send_request(client, request_id)
                request_queue.task_done()
            except asyncio.TimeoutError:
                # 队列为空且超时，检查是否应该退出
                if request_queue.empty():
                    break
            except Exception as e:
                print(f"⚠️ Worker 异常: {e}")

    async def run(self) -> StressTestResult:
        """
        运行压测

        Returns:
            压测结果
        """
        print("\n" + "=" * 70)
        print("🚀 开始压力测试")
        print("=" * 70)
        print(f"  目标服务:     {self.base_url}")
        print(f"  模型名称:     {self.model}")
        print(f"  并发数:       {self.concurrency}")

        if self.duration:
            print(f"  测试模式:     持续测试 {self.duration} 秒")
        else:
            print(f"  总请求数:     {self.total_requests}")

        print(f"  流式模式:     {'是' if self.stream else '否'}")
        print(f"  超时设置:     {self.timeout} 秒")
        print("=" * 70 + "\n")

        # 创建请求队列
        request_queue = asyncio.Queue()

        # 如果是持续测试模式，创建一个任务持续添加请求
        if self.duration:
            async def enqueue_requests():
                """持续添加请求到队列"""
                request_id = 0
                end_time = time.time() + self.duration
                while time.time() < end_time:
                    await request_queue.put(request_id)
                    request_id += 1
                    # 控制队列大小，避免内存占用过高
                    while request_queue.qsize() > self.concurrency * 10:
                        await asyncio.sleep(0.1)

            enqueue_task = asyncio.create_task(enqueue_requests())
        else:
            # 固定请求数模式，直接添加所有请求
            for i in range(self.total_requests):
                await request_queue.put(i)
            enqueue_task = None

        # 记录开始时间
        self.result.start_time = time.time()

        # 创建 HTTP 客户端
        limits = httpx.Limits(
            max_keepalive_connections=self.concurrency,
            max_connections=self.concurrency * 2,
        )

        async with httpx.AsyncClient(
            limits=limits,
            headers={"Authorization": f"Bearer {self.api_key}"},
        ) as client:
            # 创建工作协程
            workers = [
                asyncio.create_task(self.run_worker(client, request_queue))
                for _ in range(self.concurrency)
            ]

            # 等待所有请求完成
            if self.duration:
                # 持续测试模式：等待 enqueue_task 完成，然后等待队列清空
                await enqueue_task
                await request_queue.join()
            else:
                # 固定请求数模式：等待队列清空
                await request_queue.join()

            # 取消所有工作协程
            for worker in workers:
                worker.cancel()

            # 等待工作协程结束
            await asyncio.gather(*workers, return_exceptions=True)

        # 记录结束时间
        self.result.end_time = time.time()

        return self.result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Proxy 服务压力测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础测试（10并发，100请求）
  python tests/stress_test.py

  # 高并发测试
  python tests/stress_test.py --concurrency 50 --requests 500

  # 持续测试 60 秒
  python tests/stress_test.py --concurrency 20 --duration 60

  # 测试流式响应
  python tests/stress_test.py --stream --concurrency 20 --requests 200

  # 测试 PTU 模型
  python tests/stress_test.py --model Doubao-1.5-pro-32k --concurrency 10
        """,
    )

    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8080/v1",
        help="服务基础 URL（默认：http://127.0.0.1:8080/v1）",
    )
    parser.add_argument(
        "--api-key",
        default="dummy",
        help="API Key（默认：dummy）",
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=10,
        help="并发数（默认：10）",
    )
    parser.add_argument(
        "-n", "--requests",
        type=int,
        default=100,
        help="总请求数（默认：100）",
    )
    parser.add_argument(
        "-d", "--duration",
        type=int,
        help="持续测试时间（秒），如果指定则忽略 --requests",
    )
    parser.add_argument(
        "-m", "--model",
        default="gpt-3.5-turbo",
        help="模型名称（默认：gpt-3.5-turbo）",
    )
    parser.add_argument(
        "-s", "--stream",
        action="store_true",
        help="使用流式响应",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=60,
        help="请求超时时间（秒，默认：60）",
    )

    args = parser.parse_args()

    # 创建压测器
    tester = StressTester(
        base_url=args.url,
        api_key=args.api_key,
        concurrency=args.concurrency,
        total_requests=args.requests,
        duration=args.duration,
        model=args.model,
        stream=args.stream,
        timeout=args.timeout,
    )

    # 运行压测
    try:
        result = await tester.run()
        result.print_report()

        # 根据成功率返回退出码
        if result.success_requests / result.total_requests >= 0.95:
            print("\n✅ 压测成功（成功率 >= 95%）")
            return 0
        else:
            print("\n⚠️ 压测完成，但成功率较低")
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断测试")
        return 130

    except Exception as e:
        print(f"\n❌ 压测失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
