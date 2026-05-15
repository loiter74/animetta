## ADDED Requirements

### Requirement: Built-in tool execution
Built-in tools SHALL execute and return correct results.

#### Scenario: calculator evaluates expressions
- **WHEN** calculator is called with "2+2"
- **THEN** it SHALL return "4"

#### Scenario: calculator handles errors gracefully
- **WHEN** calculator is called with invalid expression
- **THEN** it SHALL return an error message

#### Scenario: get_weather returns result
- **WHEN** get_weather is called with a city name
- **THEN** it SHALL return a weather string

#### Scenario: get_current_time returns time string
- **WHEN** get_current_time is called with a timezone
- **THEN** it SHALL return a formatted time string

### Requirement: Tool config loading
Tool config loader SHALL correctly parse tools.yaml settings.

#### Scenario: load config parses MCP server configs
- **WHEN** config is loaded from tools.yaml
- **THEN** MCP server configurations SHALL be parsed correctly

#### Scenario: load config respects builtin_tools filter
- **WHEN** builtin_tools list is provided
- **THEN** only listed tools SHALL be enabled

#### Scenario: load config applies tool settings
- **WHEN** tool_settings are provided
- **THEN** max_tool_calls_per_turn and timeout SHALL be applied

### Requirement: MCP bridge connection
MCP bridge SHALL handle connection lifecycle and tool conversion.

#### Scenario: MCPManager connects to stdio server
- **WHEN** load() is called with stdio config
- **THEN** it SHALL start the MCP server subprocess

#### Scenario: MCPClient lists tools
- **WHEN** connected
- **THEN** it SHALL list available tools from the MCP server

#### Scenario: tool conversion produces StructuredTool
- **WHEN** MCP tool info is converted via mcp_tool_to_langchain
- **THEN** it SHALL return a valid LangChain StructuredTool

### Requirement: Minecraft tools
Minecraft bridge SHALL manage Mineflayer subprocess lifecycle.

#### Scenario: MinecraftBridge connects to server
- **WHEN** connect() is called with server address
- **THEN** it SHALL start a Mineflayer subprocess

#### Scenario: rules engine validates actions
- **WHEN** validate_action() is called with action data
- **THEN** it SHALL return validation result

#### Scenario: world state tracks environment
- **WHEN** world state is updated
- **THEN** block/entity positions SHALL be tracked correctly
