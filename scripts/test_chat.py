"""
测试文字对话功能
"""

import asyncio
import socketio
import json
import time
from loguru import logger

# 创建 Socket.IO 客户端
sio = socketio.AsyncClient(logger=True, engineio_logger=False)

@sio.event
async def connect():
    logger.info("[Client] 已连接到服务器")

@sio.event
async def connect_error(error):
    logger.error(f"[Client] 连接失败: {error}")

@sio.event
async def disconnect():
    logger.info("[Client] 已断开连接")

@sio.event
async def error(data):
    """接收错误"""
    logger.error(f"[Client] 收到错误: {data}")
    if isinstance(data, dict):
        logger.error(f"  - type: {data.get('type')}")
        logger.error(f"  - message: {data.get('message')}")

@sio.event
async def message(data):
    """接收所有消息"""
    logger.info(f"[Client] 收到消息: {data}")

@sio.event
async def text(data):
    """接收文本响应"""
    logger.info(f"[Client] 收到文本: {data}")
    if isinstance(data, dict):
        logger.info(f"  - seq: {data.get('seq')}")
        logger.info(f"  - text: {data.get('text')}")
    else:
        logger.info(f"  - content: {data}")

@sio.event
async def control(data):
    """接收控制信号"""
    logger.info(f"[Client] 收到控制信号: {data}")

@sio.event
async def transcript(data):
    """接收转录文本"""
    logger.info(f"[Client] 收到转录: {data}")

@sio.event
async def expression(data):
    """接收表情"""
    logger.info(f"[Client] 收到表情: {data}")

async def test_text_input(message: str):
    """测试文字输入"""
    logger.info(f"[Client] 发送文字: {message}")
    await sio.emit('text_input', {
        'text': message,
        'from_name': 'TestUser'
    })

async def main():
    # 连接到服务器
    server_url = 'http://localhost:12394'
    logger.info(f"[Client] 连接到 {server_url}")

    try:
        await sio.connect(server_url)
        await asyncio.sleep(1)

        # 测试 1: 简单问候
        logger.info("\n=== 测试 1: 简单问候 ===")
        await test_text_input("你好")
        await asyncio.sleep(5)

        # 测试 2: 提问
        logger.info("\n=== 测试 2: 提问 ===")
        await test_text_input("今天天气怎么样？")
        await asyncio.sleep(5)

        # 测试 3: 记忆测试
        logger.info("\n=== 测试 3: 记忆测试 ===")
        await test_text_input("我叫什么名字？")
        await asyncio.sleep(5)

    except Exception as e:
        logger.error(f"[Client] 测试失败: {e}")
    finally:
        await sio.disconnect()
        logger.info("[Client] 测试完成")

if __name__ == "__main__":
    asyncio.run(main())
