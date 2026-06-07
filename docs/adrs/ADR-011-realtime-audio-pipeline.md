# ADR-011: Real-time Audio Pipeline

**Date:** 2026-06-07
**Status:** Accepted

## Context

Anima needs to process audio in real-time for live interactions (VTuber streaming, voice chat). The pipeline must handle ASR, VAD, and audio processing with minimal latency.

## Decision

Implement a real-time audio pipeline using Web Audio API:

1. **ASR Node**: Processes audio chunks for speech recognition
2. **VAD Node**: Voice Activity Detection to identify speech segments
3. **AudioProcessor**: Handles audio effects and transformations

### Pipeline

```
Audio Input → VAD → Speech Detection
                ↓
            ASR → Text
                ↓
        AudioProcessor → Output
```

### Key Design Decisions

1. **ScriptProcessorNode vs AudioWorklet**: Use AudioWorklet for better performance (runs on audio thread)
2. **Chunk-based processing**: Process audio in small chunks (10-50ms) for low latency
3. **VAD-first**: Only send audio to ASR when speech is detected (reduces compute)
4. **Async pipeline**: Each stage processes asynchronously, no blocking

## Consequences

- **Positive**: Low-latency audio processing
- **Positive**: Efficient compute (only process speech segments)
- **Positive**: Modular pipeline (easy to add/remove stages)
- **Negative**: AudioWorklet requires modern browsers
- **Negative**: Complex state management for async pipeline
