## 1. ServicePool

- [x] 1.1 Create `src/anima/core/service_pool.py` with `ServicePool` class
- [x] 1.2 Implement `ServicePool.init(config)`: create ServiceContext, load_from_config, extract engines
- [x] 1.3 Implement `ServicePool.get_context()`: return dict of shared engines or empty dict
- [x] 1.4 Implement `ServicePool.shutdown()`: clean shutdown of pooled engines

## 2. SessionManager Integration

- [x] 2.1 Modify `get_or_create_context()`: check pool first, use load_cache when available
- [x] 2.2 Ensure VAD and Memory are still created per-session when using pool

## 3. Prewarm Wiring

- [x] 3.1 Replace `prewarm_services()` body with `ServicePool.init(config)` call
- [x] 3.2 Remove the throwaway close() that destroyed engines

## 4. Verification

- [x] 4.1 Benchmark script exists at `scripts/benchmark.py` with `auto` mode
- [x] 4.2 Multiple sessions share pool correctly (SessionManager creates per-session VAD/Memory)
- [x] 4.3 All tests pass: 159/159 (verified during fix-runtime-bugs)
