"""
Silero VAD implementation
Based on Open-LLM-VTuber's VADEngine and StateMachine implementation
"""

from collections import deque
from typing import Union
import numpy as np
from loguru import logger

from .interface import VADInterface, VADState, VADResult
from anima.config.core.registry import ProviderRegistry


@ProviderRegistry.register_service("vad", "silero")
class SileroVAD(VADInterface):
    """
    Silero-based voice activity detection implementation

    Uses a state machine to detect speech start and end:
    - IDLE -> ACTIVE: Speech start detected
    - ACTIVE -> INACTIVE: Speech pause detected
    - INACTIVE -> ACTIVE: Speech continues
    - INACTIVE -> IDLE: Speech fully ended, output accumulated audio
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        prob_threshold: float = 0.15,
        db_threshold: int = -100,
        required_hits: int = 6,
        required_misses: int = 2,
        smoothing_window: int = 12,
    ):
        # Save configuration parameters
        self.sample_rate = sample_rate
        self.prob_threshold = prob_threshold
        self.db_threshold = db_threshold
        self.required_hits = required_hits
        self.required_misses = required_misses
        self.smoothing_window = smoothing_window

        # Window size: 512 samples at 16kHz (approx 32ms)
        self.window_size_samples = 512 if sample_rate == 16000 else 256

        # Load model
        self.model = self._load_vad_model()

        # State machine
        self.state_machine = SileroStateMachine(self)

        # Diagnostic log flags (prevent duplicate logs)
        self._vad_logged = False
        self._vad_int16_logged = False
        self._vad_normalized_logged = False

        logger.info(f"✅ Silero VAD initialization complete")
        logger.info(f"   - Sample rate: {sample_rate} Hz")
        logger.info(f"   - Probability threshold: {prob_threshold}")
        logger.info(f"   - Decibel threshold: {db_threshold}")
        logger.info(f"   - Required hits: {required_hits}")
        logger.info(f"   - Required misses: {required_misses}")

    @classmethod
    def from_config(cls, config, **kwargs):
        """Create instance from configuration"""
        return cls(
            sample_rate=config.sample_rate,
            prob_threshold=config.prob_threshold,
            db_threshold=config.db_threshold,
            required_hits=config.required_hits,
            required_misses=config.required_misses,
            smoothing_window=config.smoothing_window,
        )

    def _load_vad_model(self):
        """Load Silero VAD model"""
        try:
            from silero_vad import load_silero_vad
            logger.info("Loading Silero-VAD model...")
            model = load_silero_vad()
            logger.info("Silero-VAD model loaded successfully")
            return model
        except ImportError:
            logger.warning("silero-vad is not installed, please run: pip install silero-vad")
            raise
        except Exception as e:
            logger.error(f"Failed to load Silero-VAD model: {e}")
            raise

    async def preload(self) -> None:
        """Preload is safe to call multiple times (model loaded eagerly in __init__)"""
        if self.model is not None:
            logger.debug("Silero-VAD model already loaded, skipping preload")
            return

        logger.info("Loading Silero-VAD model...")
        import asyncio
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(None, self._load_vad_model)
        logger.info("Silero-VAD model preloaded")

    def detect_speech(self, audio_data: Union[list, np.ndarray]) -> VADResult:
        """
        Detect voice activity in audio data

        Processing flow:
        1. Split audio into chunks (512 samples each)
        2. Calculate speech probability for each chunk
        3. Use state machine to determine speech start/end

        Args:
            audio_data: Audio data (float32 list or numpy array, range [-1.0, 1.0] or int16 PCM)

        Returns:
            VADResult: Detection result
        """
        import torch

        # Convert to numpy array with smart normalization
        audio_np = np.array(audio_data, dtype=np.float32)

        # Diagnostic: record original audio data range (only first chunk, avoid flooding)
        if not hasattr(self, '_vad_logged'):
            if len(audio_np) > 0:
                orig_min = float(np.min(audio_np))
                orig_max = float(np.max(audio_np))
                orig_abs_max = float(np.max(np.abs(audio_np)))
            self._vad_logged = True
        elif len(audio_np) > 0:
            orig_min = float(np.min(audio_np))
            orig_max = float(np.max(audio_np))
            orig_abs_max = float(np.max(np.abs(audio_np)))
        else:
            orig_min = orig_max = orig_abs_max = 0.0

        # Check if int16 PCM data (value range exceeds [-1.0, 1.0])
        is_int16 = False
        if len(audio_np) > 0 and np.max(np.abs(audio_np)) > 1.0:
            # int16 PCM data, normalize to [-1.0, 1.0]
            if not hasattr(self, '_vad_int16_logged'):
                logger.info(f"[VAD] ✅ Detected int16 PCM data format, will auto-normalize")
                self._vad_int16_logged = True
            audio_np = audio_np / 32767.0
            is_int16 = True

        # Print normalized signal amplitude (only once)
        if not hasattr(self, '_vad_normalized_logged'):
            norm_min = float(np.min(audio_np)) if len(audio_np) > 0 else 0
            norm_max = float(np.max(audio_np)) if len(audio_np) > 0 else 0
            norm_rms = float(np.sqrt(np.mean(audio_np**2))) if len(audio_np) > 0 else 0
            logger.info(f"[VAD] 📊 Normalized signal range: [{norm_min:.4f}, {norm_max:.4f}], RMS: {norm_rms:.4f}")
            logger.info(f"[VAD] 💡 Tip: Silero VAD works well when RMS > 0.01, current RMS: {norm_rms:.4f}")
            self._vad_normalized_logged = True

        # Critical fix: record all events, return the last important event
        # Do not return on first event, process all chunks
        speech_start_event = None
        speech_end_event = None

        # Chunk processing
        for i in range(0, len(audio_np), self.window_size_samples):
            chunk_np = audio_np[i: i + self.window_size_samples]

            # Fix: do not skip incomplete chunks, process them too
            if len(chunk_np) < self.window_size_samples:
                # Last chunk may be incomplete, pad with zeros
                padded_chunk = np.zeros(self.window_size_samples, dtype=np.float32)
                padded_chunk[:len(chunk_np)] = chunk_np
                chunk_np = padded_chunk

            # Convert to torch tensor
            chunk_tensor = torch.Tensor(chunk_np)

            # Calculate speech probability
            with torch.no_grad():
                speech_prob = self.model(chunk_tensor, self.sample_rate).item()

            # Process through state machine
            result = self.state_machine.process(speech_prob, chunk_np)

            # Record events without immediately returning
            if result is not None:
                if result.is_speech_start:
                    speech_start_event = result
                elif result.is_speech_end:
                    speech_end_event = result

        # Return highest priority event: speech_end > speech_start > normal state
        if speech_end_event is not None:
            # Only log at DEBUG level to avoid flooding
            logger.debug(f"[VAD] Speech ended, audio length: {len(speech_end_event.audio_data)} bytes")
            return speech_end_event
        elif speech_start_event is not None:
            return speech_start_event

        # No special events, return current state
        return VADResult(
            audio_data=b"",
            is_speech_start=False,
            is_speech_end=False,
            state=self.state_machine.state
        )

    def reset(self) -> None:
        """Reset state machine"""
        self.state_machine = SileroStateMachine(self)
        logger.debug("VAD state machine has been reset")

    def get_current_state(self) -> VADState:
        """Get current state"""
        return self.state_machine.state

    async def close(self) -> None:
        """Clean up resources"""
        self.reset()
        logger.info("Silero VAD resources released")


class SileroStateMachine:
    """
    Silero VAD State Machine

    State transitions:
    IDLE -> ACTIVE: Consecutive hits reaching required_hits
    ACTIVE -> INACTIVE: Consecutive misses reaching required_misses
    INACTIVE -> ACTIVE: Consecutive hits reaching required_hits
    INACTIVE -> IDLE: Consecutive misses reaching required_misses (output audio)
    """

    def __init__(self, vad_instance):
        self.state = VADState.IDLE
        self.vad = vad_instance  # Reference to SileroVAD instance

        # Counters
        self.hit_count = 0
        self.miss_count = 0

        # Accumulated audio data
        self.probs = []
        self.dbs = []
        self.bytes = bytearray()

        # Smoothing window
        self.prob_window = deque(maxlen=vad_instance.smoothing_window)
        self.db_window = deque(maxlen=vad_instance.smoothing_window)

        # Pre-buffer (saves some audio before speech starts)
        self.pre_buffer = deque(maxlen=20)

        # Diagnostic counter
        self._chunk_count = 0

        # INACTIVE state timeout mechanism (seconds)
        self._inactive_start_time = None
        self._inactive_timeout = 1.0  # Force end if INACTIVE exceeds 1 second

    @staticmethod
    def calculate_db(audio_data: np.ndarray) -> float:
        """Calculate audio decibel value"""
        # Avoid sqrt warning on empty or all-zero arrays
        if audio_data is None or len(audio_data) == 0:
            return -np.inf
        mean_square = np.mean(np.square(audio_data))
        if mean_square <= 0:
            return -np.inf
        rms = np.sqrt(mean_square)
        return 20 * np.log10(rms + 1e-7)

    def get_smoothed_values(self, prob: float, db: float) -> tuple:
        """Get smoothed probability and decibel values"""
        self.prob_window.append(prob)
        self.db_window.append(db)
        return np.mean(self.prob_window), np.mean(self.db_window)

    def update(self, chunk_bytes: bytes, prob: float, db: float) -> None:
        """Update accumulated data"""
        self.probs.append(prob)
        self.dbs.append(db)
        self.bytes.extend(chunk_bytes)

    def reset_buffers(self) -> None:
        """Reset buffers"""
        self.probs.clear()
        self.dbs.clear()
        self.bytes.clear()

    def process(self, prob: float, float_chunk_np: np.ndarray) -> Union[VADResult, None]:
        """
        Process an audio chunk

        Args:
            prob: Speech probability
            float_chunk_np: float32 audio chunk

        Returns:
            VADResult or None (when no special event)
        """
        # Convert to int16 bytes
        int_chunk_np = (float_chunk_np * 32767).astype(np.int16)
        chunk_bytes = int_chunk_np.tobytes()

        # Calculate decibel value
        db = self.calculate_db(int_chunk_np)

        # Smoothing
        smoothed_prob, smoothed_db = self.get_smoothed_values(prob, db)

        # Diagnostic log: determine if speech
        # Use only prob for judgment, not db (because db may be -inf)
        is_speech = smoothed_prob >= self.vad.prob_threshold
        # is_speech = (
        #     smoothed_prob >= self.vad.prob_threshold and
        #     smoothed_db >= self.vad.db_threshold
        # )

        self._chunk_count += 1

        # Diagnostic log: print every 100 chunks (approx 3 seconds)
        if self._chunk_count % 100 == 1:
            logger.debug(f"[VAD] #{self._chunk_count}: state={self.state.value}, prob={smoothed_prob:.3f}/{self.vad.prob_threshold:.3f}, speech={is_speech}")

        # State machine processing
        if self.state == VADState.IDLE:
            # Idle state: waiting for speech to start
            self.pre_buffer.append(chunk_bytes)

            if is_speech:
                self.hit_count += 1
                if self.hit_count >= self.vad.required_hits:
                    # Speech start detected
                    self.state = VADState.ACTIVE
                    self.update(chunk_bytes, smoothed_prob, smoothed_db)
                    self.hit_count = 0
                    logger.debug(f"[VAD] Speech started")
                    return VADResult(
                        audio_data=b"",
                        is_speech_start=True,
                        is_speech_end=False,
                        state=VADState.ACTIVE
                    )
            else:
                self.hit_count = 0

        elif self.state == VADState.ACTIVE:
            # Active state: currently speaking
            self.update(chunk_bytes, smoothed_prob, smoothed_db)

            if is_speech:
                self.miss_count = 0
            else:
                self.miss_count += 1
                # Print miss_count status every 50 chunks
                if self._chunk_count % 50 == 0 and self.miss_count > 0:
                    logger.info(f"[VAD] ACTIVE: miss_count={self.miss_count}/{self.vad.required_misses}, prob={smoothed_prob:.3f}")
                if self.miss_count >= self.vad.required_misses:
                    # Speech pause detected
                    self.state = VADState.INACTIVE
                    self.miss_count = 0
                    self._inactive_start_time = None  # Reset timeout timer
                    logger.info(f"[VAD] Speech paused (ACTIVE→INACTIVE)")

        elif self.state == VADState.INACTIVE:
            # Inactive state: waiting for speech to continue or end
            self.update(chunk_bytes, smoothed_prob, smoothed_db)

            # Timeout check: force end if INACTIVE exceeds timeout
            import time
            if self._inactive_start_time is None:
                self._inactive_start_time = time.time()
                logger.debug(f"[VAD] Entered INACTIVE state, starting timeout timer")

            inactive_duration = time.time() - self._inactive_start_time
            
            # Print status every 0.5 seconds
            if not hasattr(self, "_last_logged_duration") or inactive_duration - self._last_logged_duration >= 0.5:
                logger.info(f"[VAD] INACTIVE state has lasted {inactive_duration:.1f}s (timeout threshold: {self._inactive_timeout}s)")
                self._last_logged_duration = inactive_duration
            
            if inactive_duration > self._inactive_timeout:
                # Timeout, force end
                logger.info(f"[VAD] INACTIVE timeout ({inactive_duration:.2f}s), forcing end")
                self.state = VADState.IDLE
                self._inactive_start_time = None
                self.miss_count = 0

                # Merge pre-buffer and main buffer audio
                pre_bytes = b"".join(self.pre_buffer)
                audio_data = pre_bytes + bytes(self.bytes)

                self.reset_buffers()
                self.pre_buffer.clear()

                # Check if audio length is sufficient (at least 0.5s, approx 8000 bytes)
                if len(audio_data) > 8000:
                    logger.debug(f"[VAD] Speech ended (timeout), audio: {len(audio_data)} bytes")
                    return VADResult(
                        audio_data=audio_data,
                        is_speech_start=False,
                        is_speech_end=True,
                        state=VADState.IDLE
                    )
                else:
                    logger.debug(f"[VAD] Audio too short ({len(audio_data)} bytes), discarding")
                    return None

            if is_speech:
                self.hit_count += 1
                # Significantly raised threshold: need 10 consecutive speech frames to return to ACTIVE (approx 0.3s)
                # This prevents state cycling caused by noise
                if self.hit_count >= 10:
                    # Speech continues
                    self.state = VADState.ACTIVE
                    self.hit_count = 0
                    self.miss_count = 0
                    self._inactive_start_time = None
                    logger.info(f"[VAD] Speech continued (INACTIVE→ACTIVE), hit_count={self.hit_count}")
                # Print status every 100 chunks
                elif self._chunk_count % 100 == 0:
                    logger.info(f"[VAD] INACTIVE: hit_count={self.hit_count}/{self.vad.required_hits * 2}, prob={smoothed_prob:.3f}")
            else:
                self.hit_count = 0
                self.miss_count += 1
                # Print miss_count every 50 chunks
                if self._chunk_count % 50 == 0 and self.miss_count > 0:
                    logger.info(f"[VAD] INACTIVE: miss_count={self.miss_count}/8, prob={smoothed_prob:.3f}")
                # Lowered threshold: 8 times (approx 0.25s) instead of 16
                if self.miss_count >= 8:
                    # Speech fully ended
                    self.state = VADState.IDLE
                    self.miss_count = 0
                    self._inactive_start_time = None

                    # Merge pre-buffer and main buffer audio
                    pre_bytes = b"".join(self.pre_buffer)
                    audio_data = pre_bytes + bytes(self.bytes)

                    self.reset_buffers()
                    self.pre_buffer.clear()

                    # Check if audio length is sufficient (at least 0.5s, approx 8000 bytes)
                    if len(audio_data) > 8000:
                        logger.debug(f"[VAD] Speech ended (INACTIVE→IDLE), audio: {len(audio_data)} bytes")
                        return VADResult(
                            audio_data=audio_data,
                            is_speech_start=False,
                            is_speech_end=True,
                            state=VADState.IDLE
                        )
                    else:
                        logger.debug(f"[VAD] Audio too short ({len(audio_data)} bytes), discarding")

        return None
