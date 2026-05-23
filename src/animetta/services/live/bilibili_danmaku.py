"""
Bilibili Live Danmaku Service

Receives danmaku (bullet comments) from a Bilibili live room using
the bilibili-api-python library. Runs in a separate thread with its
own asyncio event loop to avoid blocking the main server loop.

Usage:
    service = BilibiliDanmakuService(room_id=123456, sessdata="...")
    service.set_callback(lambda msg: ...)
    service.start()
    # ... later ...
    service.stop()
"""

import asyncio
import json
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, Dict, Any, List, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from animetta import $$$


@dataclass
class DanmakuMessage:
    """Parsed danmaku message from Bilibili live room"""
    text: str
    user_name: str
    user_id: int
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DanmakuReply:
    """AI reply to a danmaku message"""
    danmaku_text: str
    reply_text: str
    user_name: str
    character_name: str = "AI"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BilibiliDanmakuService:
    """
    Bilibili live danmaku receiver service.

    Runs bilibili-api's LiveDanmaku in a dedicated thread with its own asyncio
    event loop. Danmaku messages are placed into an asyncio.Queue and consumed
    by the main thread via the provided callback.

    Attributes:
        room_id: Bilibili live room ID to connect to
        sessdata: Optional SESSDATA cookie for authenticated connection
        max_queue_size: Maximum number of queued messages (oldest dropped when exceeded)
        max_retries: Maximum reconnection attempts
    """

    def __init__(
        self,
        room_id: int,
        sessdata: str = "",
        max_queue_size: int = 100,
        max_retries: int = 5,
    ):
        self.room_id = room_id
        self.sessdata = sessdata
        self.max_queue_size = max_queue_size
        self.max_retries = max_retries

        # Threading
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False

        # Queue for cross-thread message passing
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)

        # Callback set by the consumer (RouteHandlers)
        self._on_danmaku: Optional[Callable[[DanmakuMessage], None]] = None
        self._on_status_change: Optional[Callable[[bool, str], None]] = None

        # bilibili-api client (created inside the thread)
        self._monitor = None

        # DanmakuBuffer for meme collection pipeline
        self._danmaku_buffer: Optional[DanmakuBuffer] = None

        # Connection state
        self._connected = False
        self._reconnect_delay = 1.0  # starts at 1s, doubles each retry

    # ========================================
    # Public API
    # ========================================

    def set_callback(self, callback: Callable[[DanmakuMessage], None]) -> None:
        """Register callback for incoming danmaku messages."""
        self._on_danmaku = callback

    def set_status_callback(self, callback: Callable[[bool, str], None]) -> None:
        """Register callback for connection status changes."""
        self._on_status_change = callback

    def set_buffer(self, buffer: DanmakuBuffer) -> None:
        """Attach a DanmakuBuffer to receive copies of all incoming danmaku.

        The buffer receives the same danmaku messages forwarded to the
        on_danmaku callback, enabling the meme collection pipeline to
        consume real-time chat data.
        """
        self._danmaku_buffer = buffer

    @property
    def is_connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        """Start the Bilibili danmaku service in a background thread."""
        if self._running:
            logger.warning("[BilibiliDanmaku] Already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_event_loop,
            name="bilibili-danmaku",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"[BilibiliDanmaku] Started for room {self.room_id}")

    def stop(self) -> None:
        """Stop the Bilibili danmaku service gracefully."""
        logger.info("[BilibiliDanmaku] Stopping...")
        self._running = False

        if self._loop and self._loop.is_running():
            try:
                # Schedule disconnect on the event loop and wake it up
                asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
            except Exception as e:
                logger.warning(f"[BilibiliDanmaku] Error during disconnect: {e}")

        if self._thread:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("[BilibiliDanmaku] Thread did not stop in time")
            self._thread = None

        self._connected = False
        logger.info("[BilibiliDanmaku] Stopped")

    # ========================================
    # Internal: Thread entry point
    # ========================================

    def _run_event_loop(self) -> None:
        """Create and run the asyncio event loop for this thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._run())
        except Exception as e:
            logger.error(f"[BilibiliDanmaku] Event loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None

    async def _run(self) -> None:
        """Main async coroutine: connect, listen, and auto-reconnect."""
        retries = 0

        while self._running and retries <= self.max_retries:
            try:
                await self._connect_and_listen()
                # If we get here, connection was cleanly closed
                retries = 0
                self._reconnect_delay = 1.0
            except Exception as e:
                retries += 1
                logger.error(f"[BilibiliDanmaku] Connection error (attempt {retries}/{self.max_retries}): {e}")

                if not self._running:
                    break

                if retries > self.max_retries:
                    logger.error("[BilibiliDanmaku] Max retries reached, giving up")
                    self._notify_status(False, f"Max retries reached: {e}")
                    break

                # Exponential backoff
                wait = self._reconnect_delay
                self._reconnect_delay = min(self._reconnect_delay * 2, 60.0)
                logger.info(f"[BilibiliDanmaku] Reconnecting in {wait:.1f}s...")
                self._notify_status(False, f"Reconnecting in {wait:.1f}s...")
                await asyncio.sleep(wait)

    async def _connect_and_listen(self) -> None:
        """
        Connect to Bilibili live room and listen for danmaku.

        Uses bilibili-api-python's LiveDanmaku class with event callbacks.
        """
        try:
            from bilibili_api import live, Credential
        except ImportError:
            logger.error("[BilibiliDanmaku] bilibili-api-python not installed. Run: pip install bilibili-api-python")
            raise

        # Build credential if sessdata is provided
        credential = None
        if self.sessdata:
            credential = Credential(sessdata=self.sessdata)

        # Create LiveDanmaku monitor
        self._monitor = live.LiveDanmaku(
            room_display_id=self.room_id,
            credential=credential,
            max_retry=3,
        )

        # Register event handlers
        @self._monitor.on('DANMU_MSG')
        async def on_danmaku(event):
            try:
                data_info = event["data"]["info"]
                content = data_info[1]  # danmaku text
                user_id = data_info[2][0]  # sender UID
                user_name = data_info[2][1]  # sender nickname

                msg = DanmakuMessage(
                    text=content,
                    user_name=user_name,
                    user_id=user_id,
                )

                logger.debug(f"[BilibiliDanmaku] 弹幕 {user_name}: {content}")

                # Put into queue for cross-thread consumption
                await self._queue.put(msg)
            except Exception as e:
                logger.error(f"[BilibiliDanmaku] Error parsing DANMU_MSG: {e}")

        @self._monitor.on('SEND_GIFT')
        async def on_gift(event):
            try:
                gift_data = event["data"]["data"]
                user_name = gift_data.get("uname", "未知")
                gift_name = gift_data.get("giftName", "礼物")
                gift_num = gift_data.get("num", 1)
                content = f"感谢 {user_name} 送出的 {gift_num} 个 {gift_name}"

                msg = DanmakuMessage(
                    text=content,
                    user_name=user_name,
                    user_id=gift_data.get("uid", 0),
                )

                await self._queue.put(msg)
            except Exception as e:
                logger.error(f"[BilibiliDanmaku] Error parsing SEND_GIFT: {e}")

        @self._monitor.on('SUPER_CHAT_MESSAGE')
        async def on_sc(event):
            try:
                sc_data = event["data"]["data"]
                user_name = sc_data.get("user_info", {}).get("uname", "未知")
                price = sc_data.get("price", 0)
                message = sc_data.get("message", "")
                content = f"SC ¥{price}: {message}"

                msg = DanmakuMessage(
                    text=content,
                    user_name=user_name,
                    user_id=sc_data.get("uid", 0),
                )

                await self._queue.put(msg)
            except Exception as e:
                logger.error(f"[BilibiliDanmaku] Error parsing SUPER_CHAT: {e}")

        @self._monitor.on('INTERACT_WORD_V2')
        async def on_interact(event):
            try:
                data = event["data"]["data"]
                decoded = data.get("pb_decoded", {})
                user_name = decoded.get("uname", "某人")
                content = f"欢迎 {user_name} 进入直播间"

                msg = DanmakuMessage(
                    text=content,
                    user_name=user_name,
                    user_id=decoded.get("uid", 0),
                )

                await self._queue.put(msg)
            except Exception as e:
                logger.error(f"[BilibiliDanmaku] Error parsing INTERACT_WORD: {e}")

        # Start consumer task (drains queue → calls callback)
        consumer_task = asyncio.create_task(self._consume_queue())

        # Notify connected
        self._connected = True
        self._notify_status(True, "Connected")
        logger.info(f"[BilibiliDanmaku] Connected to room {self.room_id}")

        try:
            # This blocks until disconnected
            await self._monitor.connect()
        finally:
            self._connected = False
            self._notify_status(False, "Disconnected")

            # Cancel consumer
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

            # Clean up monitor
            try:
                await self._monitor.disconnect()
            except Exception:
                pass
            self._monitor = None

    # ========================================
    # Internal: Queue consumer
    # ========================================

    async def _consume_queue(self) -> None:
        """
        Drain the message queue and invoke the callback.

        Runs as a background task within the same event loop.
        Messages are forwarded to the main thread via the registered callback.
        """
        while self._running:
            try:
                # Wait for a message with timeout so we can check _running
                msg = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Forward to main thread via callback
                if self._on_danmaku:
                    self._on_danmaku(msg)

                # Push to DanmakuBuffer for meme collection pipeline
                if self._danmaku_buffer:
                    self._danmaku_buffer.add(msg.text, self.room_id)

                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[BilibiliDanmaku] Queue consumer error: {e}")

    # ========================================
    # Internal: Helpers
    # ========================================

    async def _disconnect(self) -> None:
        """Disconnect from Bilibili live room."""
        self._connected = False
        if self._monitor:
            try:
                await self._monitor.disconnect()
            except Exception as e:
                logger.debug(f"[BilibiliDanmaku] Disconnect error: {e}")
            self._monitor = None

    def _notify_status(self, connected: bool, message: str) -> None:
        """Notify listeners of connection status change."""
        self._connected = connected
        if self._on_status_change:
            self._on_status_change(connected, message)
