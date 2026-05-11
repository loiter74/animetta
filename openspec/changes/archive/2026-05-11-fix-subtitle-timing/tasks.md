## 1. Implement Audio-Driven Subtitle Timing

- [x] 1.1 In `frontend/src/composables/useSubtitle.ts`, add `audio_with_expression` socket listener: parse base64 data, calculate raw bytes, estimate audio duration
- [x] 1.2 Modify `scheduleHide` call in the `is_complete` handler: on `audio_with_expression`, cancel the 6s timer and schedule hide based on estimated audio duration + 1s safety buffer
- [x] 1.3 Add minimum floor of 3 seconds for very short audio clips
- [x] 1.4 Add defensive handling for empty/malformed audio data — fall back to 3s minimum
- [x] 1.5 Clean up socket listener in `onUnmounted` to prevent memory leak

## 2. Verify Behavior

- [x] 2.1 Confirm subtitle stays visible through entire normal conversation turn with various audio lengths
- [x] 2.2 Confirm interrupt (`stop_audio`) still hides subtitle in 1.5s
- [x] 2.3 Confirm `subtitle.translation` event still resets timer
- [x] 2.4 Run `pnpm vue-tsc --noEmit` type check passes
