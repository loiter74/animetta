"""
Socket.IO server entry point
Uses server/ module components to build the server
"""

import os
import sys
from pathlib import Path

# Fix module import path: add src directory to Python path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent  # C:\Users\30262\Project\Anima\src
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from loguru import logger

# Load environment variables from .env file (must be before other imports)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
        logger.info(f"[OK] Environment variables loaded from: {env_path}")
        glm_key = os.getenv("GLM_API_KEY")
        if glm_key:
            logger.info(f"[OK] GLM_API_KEY loaded from .env: {glm_key[:20]}... (length: {len(glm_key)})")
        else:
            logger.error("[WARNING] .env file loaded, but GLM_API_KEY is still not set!")
    else:
        logger.warning(f".env file not found: {env_path}, using system environment variables")
except ImportError:
    logger.info("python-dotenv not installed, using system environment variables")

# Final verification of key environment variables
glm_key = os.getenv("GLM_API_KEY")
if glm_key:
    logger.info(f"[OK] GLM_API_KEY available at runtime: {glm_key[:20]}...")
else:
    logger.error("[WARNING] GLM_API_KEY not available at runtime, GLM will fall back to MockLLM")

import uvicorn
import asyncio

from anima.config import AppConfig
from anima.config.user_settings import UserSettings
from anima.utils.logger_manager import logger_manager
from anima.orchestration.server import WebSocketServer, create_server


# Global configuration
global_config: AppConfig = None

# User settings
user_settings = UserSettings(Path(__file__).parent.parent.parent)

# Apply user-configured log level
initial_log_level = user_settings.get_log_level()
logger_manager.set_level(initial_log_level)
logger.info(f"Applying user log level configuration: {initial_log_level}")


def init_config(config_path: str = None) -> None:
    """
    Initialize global configuration

    Args:
        config_path: YAML configuration file path (optional)
    """
    global global_config

    if config_path:
        global_config = AppConfig.from_yaml(config_path)
    else:
        global_config = AppConfig.load()

    logger.info(f"Configuration loaded: {global_config.system.host}:{global_config.system.port}")


def run_server():
    """Run the server using uvicorn (ASGI mode)"""
    import atexit

    # Initialize configuration
    init_config()

    # Create server
    _server = create_server(global_config)
    _server.set_user_settings(user_settings)

    # Register cleanup function on exit
    def cleanup_on_exit():
        logger.info("Server shutting down...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_server.stop())
            loop.close()
        except NameError:
            pass  # server not initialized
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")
        logger.info("Server shut down")

    atexit.register(cleanup_on_exit)

    logger.info("=" * 50)
    logger.info("Starting Socket.IO server...")
    logger.info(f"Host: {global_config.system.host}")
    logger.info(f"Port: {global_config.system.port}")
    logger.info(f"Socket.IO async_mode: asgi (uvicorn)")
    logger.info("=" * 50)
    logger.info(f"Visit http://{global_config.system.host}:{global_config.system.port} to test")
    logger.info(f"WebSocket URL: ws://{global_config.system.host}:{global_config.system.port}/socket.io/")

    # Run uvicorn server - use factory function to ensure proper initialization
    uvicorn.run(
        "anima.core.socketio_server:get_asgi_app",
        host=global_config.system.host,
        port=global_config.system.port,
        log_level="info",
        factory=True
    )


# Create ASGI application (for uvicorn import)
_server: WebSocketServer = None
asgi_app = None


def get_asgi_app():
    """Get ASGI application (lazy initialization)"""
    global _server, asgi_app, global_config, user_settings

    if asgi_app is None:
        # Ensure config is loaded (needed when run as uvicorn subprocess)
        global global_config
        if global_config is None:
            init_config()

        # Create server
        _server = create_server(global_config)
        _server.set_user_settings(user_settings)

        # Start background model warmup (non-blocking - models load while server accepts connections)
        # warmup() is safe to call even if no services are registered yet
        logger.info("Starting background model warmup...")
        asyncio.ensure_future(_server.model_manager.warmup())

        # Pre-warm all services so the first real user request doesn't pay cold-start cost.
        # This creates a throwaway ServiceContext that triggers all imports and model loading.
        logger.info("Starting service pre-warmup (cold-start mitigation)...")
        asyncio.ensure_future(_server.prewarm_services())

        asgi_app = _server.get_app()

    return asgi_app


if __name__ == '__main__':
    run_server()
