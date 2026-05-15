## 1. Test Infrastructure & Fixes

- [x] 1.1 Install pydub + audioop-lts (Python 3.13 compat) dependencies
- [x] 1.2 Fix test_audio_analyzer.py — all 14 test functions previously failed due to missing pydub (now installed)
- [x] 1.3 Fix test_memory_entry_store.py — TestRelation tests previously failed due to missing memory_relations table DDL (added to MemoryEntryStore.ddl())
- [x] 1.4 Add shared test fixtures: mock_embedding(), mock_chroma(), mock_mcp_client(), mock_minecraft_bridge(), mock_bilibili_client() in tests/conftest.py

## 2. Core Module Tests

- [x] 2.1 Create tests/core/test_service_pool.py — ServicePool.init/get_context/shutdown/is_ready lifecycle with mocked ServiceContext
- [x] 2.2 Create tests/core/test_service_context.py — ServiceContext.load_from_config sequencing, load_cache reuse, init_* factory methods, close cleanup
- [x] 2.3 Create tests/core/test_socketio_server.py — get_asgi_app factory, parse_server_args, _setup_checkpointer
- [x] 2.4 Create tests/core/test_redis_checkpoint.py — AsyncRedisSaver CRUD operations with mock redis client

## 3. Configuration System Tests

- [x] 3.1 Create tests/config/test_app_config.py — AppConfig.from_yaml loading, env var expansion, get_persona, get_system_prompt, validate
- [x] 3.2 Create tests/config/test_registry.py — ProviderRegistry.register/register_service/create_service/create_union_type/list_services
- [x] 3.3 Create tests/config/test_persona.py — PersonaConfig.load, build_system_prompt with personality traits and behavior rules
- [x] 3.4 Create tests/config/test_user_settings.py — UserSettings.save/load cycle
- [x] 3.5 Create tests/config/test_live2d_config.py — Live2DConfig loading and motion index mapping

## 4. Service Provider Interface Tests

- [x] 4.1 Create tests/services/test_llm_providers.py — All LLM providers: from_config factory, chat/chat_stream interface contract, mock fallback
- [x] 4.2 Create tests/services/test_asr_providers.py — All ASR providers: from_config factory, transcribe interface contract, mock fallback
- [x] 4.3 Create tests/services/test_tts_providers.py — All TTS providers: factory create, synthesize interface contract, mock fallback
- [x] 4.4 Create tests/services/test_vad_providers.py — VADFactory.create_from_config, SileroVAD detect_speech, VADState machine
- [x] 4.5 Create tests/services/test_llm_factory.py — LLMFactory.create_from_config with all config types, fallback chain
- [x] 4.6 Create tests/services/test_glm_message_converter.py — GLMMessageConverter and GLMToolConverter format conversion
- [x] 4.7 Create tests/services/test_langchain_adapter.py — create_chat_model_from_service wrapping LLMInterface as BaseChatModel

## 5. Graph Node Tests

- [x] 5.1 Create tests/orchestration/graph/test_asr_node.py — asr_node audio processing, state updates
- [x] 5.2 Create tests/orchestration/graph/test_personality_node.py — personality_node mode/mood detection
- [x] 5.3 Create tests/orchestration/graph/test_tool_node.py — tool_node execution flow, tool call routing
- [x] 5.4 Create tests/orchestration/graph/test_tool_manager.py — ToolManager.load_tools with built-in/MCP/Minecraft tools
- [x] 5.5 Create tests/orchestration/graph/test_builder.py — build_graph node wiring, conditional edge routing
- [x] 5.6 Create tests/orchestration/graph/test_interrupt_handler.py — InterruptHandler set/clear/interrupt lifecycle
- [x] 5.7 Create tests/orchestration/graph/test_node_error.py — node_error retry logic, error propagation
- [x] 5.8 Create tests/orchestration/graph/test_observability.py — ObservabilityManager singleton, callback initialization
- [x] 5.9 Create tests/orchestration/graph/test_scheduler.py — AsyncScheduler task registration, scheduling, lifecycle
- [x] 5.10 Create tests/orchestration/graph/test_state.py — AgentState create_initial_state, message helper functions
- [x] 5.11 Create tests/orchestration/graph/test_translation_state.py — TranslationState configuration

## 6. WebSocket Server Tests

- [x] 6.1 Create tests/orchestration/server/test_routes.py — RouteHandlers event registration, on_text_input, on_raw_audio_data, on_mic_audio_end, on_interrupt_signal routing logic (mock Socket.IO)
- [x] 6.2 Create tests/orchestration/server/test_session.py — SessionManager.get_or_create_context with ServicePool reuse, get_or_create_orchestrator, cleanup_session
- [x] 6.3 Create tests/orchestration/server/test_websocket.py — WebSocketServer init, setup_routes, setup_lifecycle, prewarm_services
- [x] 6.4 Create tests/orchestration/server/test_lifecycle.py — LifecycleManager signal handling, cleanup callbacks
- [x] 6.5 Create tests/orchestration/server/test_stats_api.py — FastAPI route handlers: /health, /api/stats/overview, /api/stats/nodes, /api/stats/traces
- [x] 6.6 Create tests/orchestration/server/test_desktop.py — DesktopClientManager client registration by type
- [x] 6.7 Create tests/orchestration/server/test_live2d_server.py — Live2DManager action enqueue lifecycle

## 7. Memory System Tests

- [x] 7.1 Create tests/memory/test_system.py — MemorySystem.store_turn chain, retrieve_context with hybrid search, start/stop lifecycle
- [x] 7.2 Create tests/memory/test_config.py — MemoryConfig, ChunkConfig, SearchConfig, EmbeddingConfig defaults
- [x] 7.3 Create tests/memory/test_fuzzy_layer.py — FuzzyLayer.build_fuzzy_context tiered narratives, 5-min TTL cache
- [x] 7.4 Create tests/memory/test_user_profile.py — UserProfile static+dynamic profile, profile merging
- [x] 7.5 Create tests/memory/test_manager.py — MemoryManager index/sync operations
- [x] 7.6 Create tests/memory/test_tools.py — memory_search and memory_get tool schemas and execution
- [x] 7.7 Create tests/memory/wiki/test_manager.py — WikiManager CRUD operations, page_type routing, rebuild_index
- [x] 7.8 Create tests/memory/wiki/test_models.py — PageType enum, WikiPage dataclass with frontmatter parsing, wikilinks
- [x] 7.9 Create tests/memory/wiki/test_ingestor.py — WikiIngestor.ingest_turn full workflow: write raw, extract entities/concepts, update source summary
- [x] 7.10 Create tests/memory/wiki/test_organizer.py — WikiOrganizer page organization, relationship graph, LLM merge + rule-based fallback
- [x] 7.11 Create tests/memory/wiki/test_query.py — WikiQuery.search, build_context_for_llm, search_turns conversion
- [x] 7.12 Create tests/memory/wiki/test_lint.py — WikiLint broken link detection, orphan pages, index drift
- [x] 7.13 Create tests/memory/learner/test_engine.py — PeriodicLearner scheduled tasks, task registration, lifecycle
- [x] 7.14 Create tests/memory/learner/test_summarizer.py — ConversationSummarizer LLM-driven + rule-based summarization
- [x] 7.15 Create tests/memory/learner/test_fact_extractor.py — LearnerFactExtractor batch extraction, wiki writing
- [x] 7.16 Create tests/memory/learner/test_pattern_extractor.py — PatternExtractor LLM-driven + frequency-based pattern discovery
- [x] 7.17 Create tests/memory/learner/test_meme_discovery.py — MemeDiscoverer candidate generation, template fallback
- [x] 7.18 Create tests/memory/learner/test_persona_optimizer.py — PersonaOptimizer performance analysis, suggestion YAML
- [x] 7.19 Create tests/memory/meme/test_engine.py — MemePool time-decay scoring, resurrection, context-aware selection
- [x] 7.20 Create tests/memory/meme/test_store.py — MemeStore wiki-backed CRUD operations
- [x] 7.21 Create tests/memory/meme/test_models.py — Meme, CognitiveAnalysis, MemeSource data models
- [x] 7.22 Create tests/memory/fuzzy/test_models.py — FuzzyMemory model granularity levels
- [x] 7.23 Create tests/memory/search/test_scorer.py — MemoryScorer importance scoring, emotion-weighted scoring, exponential decay
- [x] 7.24 Create tests/memory/stores/test_short_term.py — ShortTermMemory FIFO append, max_turns eviction, get_context

## 8. Avatar & Expression Tests

- [x] 8.1 Create tests/avatar/test_llm_tag_analyzer.py — StandaloneLLMTagAnalyzer: [emotion] tag parsing, cleaned text, multiple tags, neutral fallback
- [x] 8.2 Create tests/avatar/test_keyword_analyzer.py — KeywordAnalyzer: happy/sad/neutral keyword matching, confidence scoring
- [x] 8.3 Create tests/avatar/test_audio_analyzer.py (expand) — compute_volume_envelope with valid WAV, gain amplification, silent audio
- [x] 8.4 Create tests/avatar/test_factory.py — EmotionAnalyzerFactory and TimelineStrategyFactory: create, unknown type raises
- [x] 8.5 Create tests/avatar/test_prompts.py — EmotionPromptBuilder system prompt generation, tag format guide
- [x] 8.6 Create tests/avatar/test_emotion_param_mapper.py — EmotionParamMapper: 12 emotion presets, intensity scaling, random variance
- [x] 8.7 Create tests/avatar/mappers/test_base.py — IEmotionParamMapper interface, ParameterState/ExpressionFrame models
- [x] 8.8 Create tests/avatar/test_position_strategy.py — PositionBasedStrategy even time distribution
- [x] 8.9 Create tests/avatar/test_duration_strategy.py — DurationBasedStrategy emotion-type weighting
- [x] 8.10 Create tests/avatar/test_intensity_strategy.py — IntensityBasedStrategy intensity-based weighting, configurable factor

## 9. Tools System Tests

- [x] 9.1 Create tests/tools/test_base.py — Built-in tools: calculator expression evaluation, error handling, get_weather, get_current_time
- [x] 9.2 Create tests/tools/test_config.py — ToolConfig parsing: MCP servers, builtin_tools filter, tool_settings
- [x] 9.3 Create tests/tools/test_custom_tools.py — Custom tool definitions, registration, execution
- [x] 9.4 Create tests/tools/test_langchain_tools.py — LangChain tool adapter creation
- [x] 9.5 Create tests/tools/test_mcp_bridge.py (expand) — MCPClient connection, tool listing, mcp_tool_to_langchain conversion
- [x] 9.6 Create tests/tools/minecraft/test_bridge.py — MinecraftBridge subprocess lifecycle, JSON-RPC communication
- [x] 9.7 Create tests/tools/minecraft/test_config.py — MinecraftConfig model validation
- [x] 9.8 Create tests/tools/minecraft/test_planner.py — MinecraftPlanner task decomposition, plan step generation
- [x] 9.9 Create tests/tools/minecraft/test_autonomous.py — AutonomousLoop perception→decision→execution cycle

## 10. Live2D Service Tests

- [x] 10.1 Create tests/services/test_live2d_action_queue.py — Live2DActionQueue enqueue/dequeue, APPEND/REPLACE/INTERRUPT policies, DROP_OLDEST/NEWEST overflow, ActionFactory type creation
- [x] 10.2 Create tests/services/test_live2d_preset_loader.py — PresetLoader YAML loading, emote/gesture/react preset creation
- [x] 10.3 Create tests/services/test_live2d_viseme_sync.py — VisemeLipSync FFT analysis, viseme→mouth mapping, SimpleLipSync fallback, factory engine selection

## 11. Bilibili & Meme Service Tests

- [x] 11.1 Create tests/services/test_bilibili_danmaku.py — BilibiliDanmakuClient connect/disconnect/reconnect lifecycle, message handling, heartbeat
- [x] 11.2 Create tests/services/meme/test_analyzer.py — MemeCognitiveAnalyzer humor mechanism analysis, persona fit scoring
- [x] 11.3 Create tests/services/meme/test_bilibili_collector.py — BilibiliMemeCollector scraped data parsing, trend extraction
- [x] 11.4 Create tests/services/meme/test_bilibili_interaction.py — BilibiliInteraction danmaku processing, reply generation

## 12. Audio Processor Tests

- [x] 12.1 Create tests/services/audio/test_processor.py — AudioProcessorInterface contract
- [x] 12.2 Create tests/services/audio/test_vad_processor.py — VADAudioProcessor chunk buffering, speech_start/speech_end callbacks, 30s timeout
- [x] 12.3 Create tests/services/audio/test_simple_vad_processor.py — SimpleVADProcessor speech/silence threshold logic

## 13. Tracing & Utils Tests

- [x] 13.1 Create tests/tracing/test_bootstrap.py — init_tracing() with observability.yaml, TracerProvider setup
- [x] 13.2 Create tests/tracing/test_context.py — attach/detach_trace_context, span context propagation
- [x] 13.3 Create tests/tracing/test_exporter.py — StatsSpanExporter span→StatsStore mapping, batch async write
- [x] 13.4 Create tests/tracing/test_proxy.py — TracingProxy dynamic service wrapping, auto-span creation
- [x] 13.5 Create tests/utils/test_auto_config.py — AutoConfig environment detection, GPU check, path resolution
- [x] 13.6 Create tests/utils/test_env_helper.py — EnvHelper platform detection, WSL/Windows/Linux path mapping
- [x] 13.7 Create tests/utils/test_logger_manager.py — LoggerManager loguru configuration, level setting

## 14. Final Coverage Verification

- [x] 14.1 Run full test suite: PYTHONPATH=src python -m pytest tests/ --cov=src/anima --cov-report=term-missing
- [~] 14.2 Verify 100% statement coverage across all modules (NON-GOAL: 100% is aspirational; currently ~830+ tests pass)
- [~] 14.3 Update CI coverage threshold (fail_under) in pyproject.toml to 100 (deferred — would break CI without first achieving 100%)
- [x] 14.4 Run full test suite one final time to confirm zero failures
