"""
简单测试脚本 - 检查对话功能
"""

import asyncio
import socketio

sio = socketio.AsyncClient()

messages_received = []

@sio.event
async def connect():
    print("[OK] 已连接")

@sio.event
async def connect_error(error):
    print(f"[ERROR] 连接失败: {error}")

@sio.event
async def disconnect():
    print("[INFO] 已断开")

@sio.event
async def text(data):
    print(f"[TEXT] 收到: {data}")
    messages_received.append(('text', data))

@sio.event
async def error(data):
    print(f"[ERROR] 收到错误: {data}")
    messages_received.append(('error', data))

@sio.event
async def control(data):
    print(f"[CONTROL] 收到: {data}")
    messages_received.append(('control', data))

@sio.event
async def expression(data):
    print(f"[EXPRESSION] 收到: {data}")
    messages_received.append(('expression', data))

@sio.on('*')
async def any_event(event, data):
    if event not in ['connect', 'disconnect', 'connect_error', 'text', 'error', 'control', 'expression']:
        print(f"[{event}] 收到: {data}")

async def main():
    try:
        await sio.connect('http://localhost:12394')
        await asyncio.sleep(1)

        # 发送测试消息
        print("\n=== 发送: 你好 ===")
        await sio.emit('text_input', {'text': '你好', 'from_name': 'TestUser'})

        # 等待响应
        print("等待响应...")
        for i in range(15):
            await asyncio.sleep(1)
            print(f"  等待中... {i+1}/15 秒")
            if messages_received:
                break

        print(f"\n总共收到 {len(messages_received)} 条消息:")
        for msg_type, msg_data in messages_received:
            print(f"  - [{msg_type}]: {msg_data}")

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
