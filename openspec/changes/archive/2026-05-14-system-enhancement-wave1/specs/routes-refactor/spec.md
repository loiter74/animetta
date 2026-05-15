## ADDED Requirements

### Requirement: routes.py is split by domain
The orchestrator/server/routes.py file (1377 lines) SHALL be split into multiple handler files under server/handlers/.

#### Scenario: Chat handlers extracted
- **WHEN** routes.py is refactored
- **THEN** on_text_input, on_raw_audio_data, on_mic_audio_end, on_interrupt_signal, on_fetch_history_list, on_fetch_history SHALL be in chat_handlers.py

#### Scenario: Bilibili handlers extracted
- **WHEN** routes.py is refactored
- **THEN** on_bilibili_connect, on_bilibili_disconnect, on_bilibili_update_room, _on_danmaku_from_thread, _on_bilibili_status_from_thread SHALL be in bilibili_handlers.py

#### Scenario: Live2D handlers extracted
- **WHEN** routes.py is refactored
- **THEN** _setup_live2d_callback, execute_action SHALL be in live2d_handlers.py

#### Scenario: Admin/handshake handlers extracted
- **WHEN** routes.py is refactored
- **THEN** on_connect, on_disconnect, set_global_config, set_user_settings SHALL be in admin_handlers.py

### Requirement: routes.py remains as entry point
The original routes.py SHALL remain as the registration entry point that imports and wires handlers together.

#### Scenario: All events are still registered
- **WHEN** the server starts after refactoring
- **THEN** all Socket.IO event handlers SHALL be registered and functional
- **THEN** the health endpoint SHALL still return OK

### Requirement: Handler files are under 300 lines each
Each split handler file SHALL be under 300 lines to maintain readability.

#### Scenario: Line count check
- **WHEN** each handler file is measured
- **THEN** it SHALL have fewer than 300 lines of code
