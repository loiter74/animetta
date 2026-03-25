"""
完整的后端测试脚本
"""

import asyncio
import subprocess
import time
import socketio

sio = socketio.AsyncClient()

messages = []

@sio.event
async def connect():
    print("[OK] 已连接")

@sio.event
async def text(data):
    print(f"[TEXT] {data}")
    messages.append(('text', data))

@sio.event
async def error(data):
    print(f"[ERROR] {data}")
    messages.append(('error', data))

@sio.event
async def control(data):
    print(f"[CONTROL] {data}")
    messages.append(('control', data))

async def test_chat():
    await sio.connect('http://localhost:12394')
    await asyncio.sleep(1)

    await sio.emit('text_input', {'text': '你好', 'from_name': 'Test'})
    await asyncio.sleep(10)

    await sio.disconnect()
    return messages

async def main():
    # 启动后端
    print("启动后端...")
    import os
    env = os.environ.copy()
    env['PYTHONPATH'] = 'C:/Users/30262/Project/Anima/src'

    backend = subprocess.Popen(
        ['python', '-m', 'anima.core.socketio_server'],
        cwd='C:/Users/30262/Project/Anima',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )

    # 等待后端启动
    await asyncio.sleep(8)

    # 运行测试
    print("\n运行测试...")
    try:
        result = await asyncio.wait_for(test_chat(), timeout=20)
        print(f"\n测试完成，收到 {len(result)} 条消息")
    except Exception as e:
        print(f"测试失败: {e}")

    # 停止后端
    print("\n停止后端...")
    backend.terminate()

    # 打印后端日志
    print("\n后端日志:")
    for line in backend.stdout.readlines()[-50:]:
        print(line.strip())

if __name__ == "__main__":
    asyncio.run(main())
