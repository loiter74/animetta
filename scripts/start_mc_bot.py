#!/usr/bin/env python3
"""
Persistent Minecraft Bot launcher.
Keeps AnimettaBot connected to the MC server indefinitely.
"""
import asyncio
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from loguru import logger

logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")

async def main():
    logger.info("Starting persistent Minecraft bot...")
    
    config = MinecraftConfig(**{
        "enabled": True,
        "bot": {
            "host": "localhost",
            "port": 25565,
            "username": "AnimettaBot"
        },
        "safety": {
            "no_griefing": True,
            "auto_heal": True,
            "max_distance": 500
        }
    })
    
    bridge = MinecraftBridge(config, autonomous=True)
    ok = await bridge.start()
    
    if not ok:
        logger.error("✗ Bridge failed to start")
        return
    
    # Wait for login
    await asyncio.sleep(3)
    
    if bridge.is_running:
        logger.info("✓ AnimettaBot is now connected to Minecraft!")
        logger.info("  Press Ctrl+C to disconnect")
    else:
        logger.error("✗ Bot failed to connect")
        return
    
    # Keep alive
    try:
        while bridge.is_running:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down Minecraft bot...")
        await bridge.stop()
        logger.info("Bot disconnected")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
