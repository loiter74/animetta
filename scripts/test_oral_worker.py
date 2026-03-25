"""
口语化记忆 Worker 测试脚本

演示如何使用 OralMemoryWorker 处理记忆口语化。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from loguru import logger


async def test_worker_basic():
    """测试 Worker 基本功能"""
    from anima.memory.oral_worker import OralMemoryWorker

    # 模拟 LLM 客户端
    class MockLLM:
        async def chat(self, user_input: str, system_prompt: str = None) -> str:
            # 模拟处理延迟
            await asyncio.sleep(0.1)
            # 简单返回（实际应调用真实 LLM）
            if "想学" in user_input:
                return "我记得你提到过想学这个东西"
            return f"我记得{user_input[:20]}"

    # 创建 Worker
    worker = OralMemoryWorker(
        llm_client=MockLLM(),
        batch_size=2,
    )

    await worker.start()
    logger.info("Worker 已启动")

    # 提交任务
    task_id1 = await worker.submit(
        text="**User**: 我想学 LangGraph",
        content_hash="hash123",
        session_id="test_session",
    )
    logger.info(f"任务1已提交: {task_id1}")

    task_id2 = await worker.submit(
        text="User: 今天天气怎么样",
        content_hash="hash456",
        session_id="test_session",
    )
    logger.info(f"任务2已提交: {task_id2}")

    # 等待完成
    await asyncio.sleep(1)

    # 获取结果
    result1 = await worker.get_result(task_id1)
    result2 = await worker.get_result(task_id2)

    logger.info(f"任务1结果: {result1}")
    logger.info(f"任务2结果: {result2}")

    # 检查缓存
    cached = worker.get_cached("hash123")
    logger.info(f"缓存结果: {cached}")

    # 查看统计
    logger.info(f"Worker 统计: {worker.stats}")

    await worker.stop()
    logger.info("Worker 已停止")


async def test_worker_callbacks():
    """测试 Worker 回调功能"""
    from anima.memory.oral_worker import OralMemoryWorker

    class MockLLM:
        async def chat(self, user_input: str, system_prompt: str = None) -> str:
            await asyncio.sleep(0.05)
            return "我记得你说过的"

    worker = OralMemoryWorker(llm_client=MockLLM())
    await worker.start()

    # 使用回调
    results = []

    def callback(text: str):
        results.append(text)
        logger.info(f"回调收到: {text}")

    await worker.submit(
        text="测试回调",
        content_hash="callback_test",
        callback=callback,
    )

    await asyncio.sleep(0.5)

    logger.info(f"回调结果: {results}")
    logger.info(f"Worker 统计: {worker.stats}")

    await worker.stop()


async def test_with_real_llm():
    """使用真实 LLM 测试（需要配置 API key）"""
    import os
    api_key = os.environ.get("GLM_API_KEY")

    if not api_key:
        logger.warning("未设置 GLM_API_KEY，跳过真实 LLM 测试")
        return

    from anima.memory.oral_worker import OralMemoryWorker
    from anima.services.intelligence.llm.glm_llm import GLMLLM
    from anima.config import GLMLLMConfig

    # 创建真实 LLM
    llm_config = GLMLLMConfig(
        api_key=api_key,
        model="glm-4-flash",
        temperature=0.7,
    )
    llm = GLMLLM.from_config(llm_config)

    worker = OralMemoryWorker(llm_client=llm, batch_size=1)
    await worker.start()

    # 测试
    task_id = await worker.submit(
        text="**User**: 我最近在学 Rust 编程",
        content_hash="rust_learning",
        session_id="test",
    )

    result = await worker.get_result(task_id, timeout=10)
    logger.info(f"LLM 处理结果: {result}")

    await worker.stop()


def main():
    """运行所有测试"""
    logger.info("=== 测试 1: Worker 基本功能 ===")
    asyncio.run(test_worker_basic())

    logger.info("\n=== 测试 2: Worker 回调 ===")
    asyncio.run(test_worker_callbacks())

    logger.info("\n=== 测试 3: 真实 LLM ===")
    asyncio.run(test_with_real_llm())

    logger.info("\n所有测试完成!")


if __name__ == "__main__":
    main()
