"""
LangGraph tool manager
Responsible for tool loading (built-in + MCP) and ChatModel creation
"""

from typing import Any, Dict, List, Optional
from loguru import logger


class ToolManager:
    """LangGraph tool manager"""

    def __init__(self, session_id: str, service_context: Any):
        self.session_id = session_id
        self.service_context = service_context
        self.tools: List[Any] = []
        self.tools_map: Dict[str, Any] = {}
        self.chat_model: Optional[Any] = None
        self._mcp_manager: Optional[Any] = None

    async def load_tools(self, tools_config: Dict[str, Any]) -> bool:
        """Load tools and create ChatModel"""
        try:
            logger.info(f"[{self.session_id}] [ToolManager] Starting tool loading...")

            # 1. Load built-in/LangChain/custom tools (sync)
            from anima.tools.base import load_tools_from_config
            self.tools, self.tools_map = load_tools_from_config(tools_config)

            # 2. Load MCP tools (async)
            mcp_servers = tools_config.get("mcp_servers", [])
            if mcp_servers:
                from anima.tools.mcp_bridge import MCPManager
                self._mcp_manager = MCPManager()
                mcp_tools = await self._mcp_manager.load(mcp_servers)
                self.tools.extend(mcp_tools)
                self.tools_map.update({t.name: t for t in mcp_tools})

            logger.info(f"[{self.session_id}] [ToolManager] Loaded {len(self.tools)} tools total")

            # 3. Create ChatModel and bind tools
            self.chat_model = await self._create_chat_model()
            if self.chat_model and self.tools:
                self.chat_model = self.chat_model.bind_tools(self.tools)
                logger.info(f"[{self.session_id}] [ToolManager] ChatModel bound to {len(self.tools)} tools")

            return True

        except Exception as e:
            logger.error(f"[{self.session_id}] [ToolManager] Tool loading failed: {e}")
            return False

    async def _create_chat_model(self) -> Optional[Any]:
        """Create LangChain ChatModel"""
        try:
            from anima.services.intelligence.llm.langchain_adapter import create_chat_model_from_service
            chat_model = create_chat_model_from_service(
                llm_service=self.service_context.llm_engine,
                enable_tooling=True,
            )
            logger.info(f"[{self.session_id}] [ToolManager] ChatModel created successfully")
            return chat_model
        except Exception as e:
            logger.error(f"[{self.session_id}] [ToolManager] ChatModel creation failed: {e}")
            return None

    def get_config(self) -> Dict[str, Any]:
        """Get tool config, for injecting into LangGraph config"""
        return {
            "tools": self.tools,
            "tools_map": self.tools_map,
            "chat_model": self.chat_model,
            "enable_tools": True,
        }

    def is_loaded(self) -> bool:
        return len(self.tools) > 0 and self.chat_model is not None

    async def cleanup(self):
        """Clean up resources"""
        if self._mcp_manager:
            await self._mcp_manager.close_all()
            self._mcp_manager = None
