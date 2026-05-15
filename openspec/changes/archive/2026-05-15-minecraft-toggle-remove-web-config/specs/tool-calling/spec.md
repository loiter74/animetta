## ADDED Requirements

### Requirement: Minecraft tools support runtime lifecycle
The Minecraft tool set SHALL support runtime start/stop via Socket.IO in addition to the existing boot-time `tools.yaml` config gate. When started at runtime, the bridge SHALL be initialized and tools registered without requiring a server restart.

#### Scenario: Runtime start registers tools
- **WHEN** `minecraft.start` is received and the bridge connects successfully
- **THEN** Minecraft tools (mine, place, move, attack, chat, status, set_goal) SHALL be available in the LangChain tool registry
- **THEN** the LLM SHALL be able to invoke them in subsequent conversation turns

#### Scenario: Runtime stop deregisters tools
- **WHEN** `minecraft.stop` is received and the bridge shuts down
- **THEN** Minecraft tools SHALL be removed from the LangChain tool registry
- **THEN** subsequent tool calls to Minecraft tools SHALL fail gracefully with a "Minecraft bot not connected" message

#### Scenario: Boot-time disabled but runtime started
- **WHEN** `tools.yaml` has `minecraft.enabled: false` (boot-time disabled)
- **THEN** `minecraft.start` SHALL still be able to start the bridge
- **THEN** the bridge SHALL bypass the boot-time config gate when invoked via the Socket.IO handler
