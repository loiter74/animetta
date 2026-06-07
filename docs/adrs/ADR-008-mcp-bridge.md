# ADR-008: MCP Bridge Architecture

**Date:** 2026-06-07
**Status:** Accepted

## Context

Anima needs to integrate with external tools and services (web search, code execution, file operations). Direct tool registration creates tight coupling and makes it difficult to add new tools.

## Decision

Implement an MCP (Model Context Protocol) bridge that allows tools to be registered via a standard protocol:

1. **MCP Server**: Runs as a separate process, exposes tools via MCP protocol
2. **MCP Client**: Anima connects to MCP servers, discovers available tools
3. **Tool Discovery**: Tools are discovered dynamically, not hardcoded
4. **Security Boundary**: Each MCP server runs in its own process, limiting blast radius

### Architecture

```
┌─────────────────┐
│   Anima App     │
│  ┌───────────┐  │
│  │MCP Client │  │
│  └─────┬─────┘  │
└────────┼────────┘
         │ MCP Protocol
    ┌────▼────┐
    │MCP Server│
    │ (tools)  │
    └──────────┘
```

### Key Design Decisions

1. **Protocol-based**: Tools communicate via MCP protocol, not direct function calls
2. **Dynamic discovery**: New tools can be added without modifying Anima code
3. **Process isolation**: Each MCP server runs in its own process for security
4. **Standard interface**: MCP protocol is well-documented and widely supported

## Consequences

- **Positive**: Easy to add new tools (just start a new MCP server)
- **Positive**: Tools can be written in any language that supports MCP
- **Positive**: Security boundary between Anima and tools
- **Negative**: Additional process management complexity
- **Negative**: MCP protocol overhead for each tool call
