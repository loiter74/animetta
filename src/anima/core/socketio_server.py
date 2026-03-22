"""
Socket.IO 服务端入口点
使用 server/ 模块组件构建服务器
"""

import os
import sys
from pathlib import Path

# 修复模块导入路径：将 src 目录添加到 Python 路径
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent  # C:\Users\30262\Project\Anima\src
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from loguru import logger

# 加载 .env 文件中的环境变量（必须在其他导入之前）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
        logger.info(f"[OK] 已加载环境变量文件: {env_path}")
        glm_key = os.getenv("GLM_API_KEY")
        if glm_key:
            logger.info(f"[OK] GLM_API_KEY 已从 .env 加载: {glm_key[:20]}... (长度: {len(glm_key)})")
        else:
            logger.error("[WARNING] .env 文件已加载，但 GLM_API_KEY 仍未设置！")
    else:
        logger.warning(f".env 文件不存在: {env_path}，将使用系统环境变量")
except ImportError:
    logger.info("python-dotenv 未安装，使用系统环境变量")

# 最终验证关键环境变量
glm_key = os.getenv("GLM_API_KEY")
if glm_key:
    logger.info(f"[OK] GLM_API_KEY 在运行时可用: {glm_key[:20]}...")
else:
    logger.error("[WARNING] GLM_API_KEY 在运行时不可用，GLM将降级到MockLLM")

import uvicorn
import asyncio

from anima.config import AppConfig
from anima.config.user_settings import UserSettings
from anima.utils.logger_manager import logger_manager
from anima.orchestration.server import WebSocketServer, create_server


# 全局配置
global_config: AppConfig = None

# 用户配置
user_settings = UserSettings(Path(__file__).parent.parent.parent)

# 应用用户配置的日志级别
initial_log_level = user_settings.get_log_level()
logger_manager.set_level(initial_log_level)
logger.info(f"应用用户日志级别配置: {initial_log_level}")


def init_config(config_path: str = None) -> None:
    """
    初始化全局配置

    Args:
        config_path: YAML 配置文件路径（可选）
    """
    global global_config

    if config_path:
        global_config = AppConfig.from_yaml(config_path)
    else:
        global_config = AppConfig.load()

    logger.info(f"配置加载完成: {global_config.system.host}:{global_config.system.port}")


def run_server():
    """运行服务器 using uvicorn (ASGI mode)"""
    import atexit

    # 初始化配置
    init_config(None)

    # 创建服务器
    server = create_server(global_config)
    server.set_user_settings(user_settings)

    # 注册退出时的清理函数
    def cleanup_on_exit():
        logger.info("服务器关闭中...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.stop())
            loop.close()
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")
        logger.info("服务器已关闭")

    atexit.register(cleanup_on_exit)

    logger.info("=" * 50)
    logger.info("启动 Socket.IO 服务器...")
    logger.info(f"Host: {global_config.system.host}")
    logger.info(f"Port: {global_config.system.port}")
    logger.info(f"Socket.IO async_mode: asgi (uvicorn)")
    logger.info("=" * 50)
    logger.info(f"访问 http://{global_config.system.host}:{global_config.system.port} 测试")
    logger.info(f"WebSocket URL: ws://{global_config.system.host}:{global_config.system.port}/socket.io/")

    # Run uvicorn server - use factory function to ensure proper initialization
    uvicorn.run(
        "anima.socketio_server:get_asgi_app",
        host=global_config.system.host,
        port=global_config.system.port,
        log_level="info",
        factory=True
    )


# 创建 ASGI 应用（供 uvicorn 导入）
_server: WebSocketServer = None
asgi_app = None


def get_asgi_app():
    """获取 ASGI 应用（延迟初始化）"""
    global _server, asgi_app, global_config, user_settings

    if asgi_app is None:
        # 初始化配置
        init_config(None)

        # 创建服务器
        _server = create_server(global_config)
        _server.set_user_settings(user_settings)

        asgi_app = _server.get_app()

    return asgi_app


if __name__ == '__main__':
    run_server()
