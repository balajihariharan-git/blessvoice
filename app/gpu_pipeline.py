"""BlessVoice GPU Pipeline — PersonaPlex (voice) + Llama 3.1 8B (intelligence).

Architecture:
  - PersonaPlex 7B runs on GPU (fp16, ~20GB VRAM) as a WebSocket server on :8998
  - Llama 3.1 8B runs on CPU via llama-cpp-python (GGUF Q4_K_M, ~6GB RAM)
  - This pipeline bridges both to the BlessVoice WebSocket protocol

Flow:
  1. User audio arrives via BlessVoice WebSocket (raw PCM int16, 16kHz mono)
  2. For simple conversation: forward to PersonaPlex, relay audio back
  3. For complex questions: transcribe via PersonaPlex inner monologue,
     send to Llama for intelligence, then either:
     a) Drip-feed Llama's response into PersonaPlex's inner monologue, OR
     b) Gate PersonaPlex audio and use Kokoro/edge TTS as fallback

This module provides GPUVoicePipeline with the same interface as VoicePipeline:
  - process(audio_pcm, audio_queue) — runs the pipeline
  - abort() — cancels current generation
  - reset() — clears conversation history
"""

import asyncio
import io
import json
import logging
import queue
import struct
import threading
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("blessvoice.gpu")

# Lazy imports — these are heavy and may not be installed on CPU-only machines
_llama_cpp = None
_websockets = None


def _ensure_llama():
    """Lazy-load llama-cpp-python."""
    global _llama_cpp
    if _llama_cpp is None:
        try:
            from llama_cpp import Llama
            _llama_cpp = Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python is required for GPU pipeline. "
                "Install with: pip install llama-cpp-python"
            )
    return _llama_cpp


def _ensure_websockets():
    """Lazy-load websockets."""
    global _websockets
    if _websockets is None:
        try:
            import websockets
            _websockets = websockets
        except ImportError:
            raise ImportError(
                "websockets is required for GPU pipeline. "
                "Install with: pip install websockets"
            )
    return _websockets


class LlamaIntelligence:
    """Llama 3.1 8B running on CPU via llama-cpp-python for factual intelligence."""

    def __init__(self):
        from app.gpu_config import (
            LLAMA_MODEL_PATH,
            LLAMA_CONTEXT_LENGTH,
            LLAMA_THREADS,
            LLAMA_BATCH_SIZE,
            LLAMA_SYSTEM_PROMPT,
            LLAMA_MAX_TOKENS,
            LLAMA_TEMPERATURE,
            LLAMA_TOP_P,
        )

        self._model_path = str(LLAMA_MODEL_PATH)
        self._context_length = LLAMA_CONTEXT_LENGTH
        self._threads = LLAMA_THREADS
        self._batch_size = LLAMA_BATCH_SIZE
        self._system_prompt = LLAMA_SYSTEM_PROMPT
        self._max_tokens = LLAMA_MAX_TOKENS
        self._temperature = LLAMA_TEMPERATURE
        self._top_p = LLAMA_TOP_P

        self._model: Optional[object] = None
        self._conversation_history: list[dict] = []
        self._lock = threading.Lock()

    def load(self):
        """Load Llama model into memory. Call once at startup."""
        if self._model is not None:
            return

        Llama = _ensure_llama()
        logger.info(f"Loading Llama 3.1 8B from {self._model_path}...")
        start = time.time()

        self._model = Llama(
            model_path=self._model_path,
            n_ctx=self._context_length,
            n_threads=self._threads,
            n_batch=self._batch_size,
            verbose=False,
        )

        elapsed = time.time() - start
        logger.info(f"Llama 3.1 8B loaded in {elapsed:.1f}s (CPU, {self._threads} threads)")

    def generate(self, user_text: str, abort_event: threading.Event) -> str:
        """Generate a response to user text. Blocks until complete.

        Args:
            user_text: The user's question/statement (transcribed from audio).
            abort_event: Set this to cancel generation early.

        Returns:
            The model's text response.
        """
        if self._model is None:
            raise RuntimeError("Llama model not loaded. Call load() first.")

        self._conversation_history.append({"role": "user", "content": user_text})

        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend(self._conversation_history[-10:])

        with self._lock:
            start = time.time()
            response_text = ""

            # Use streaming for abort support
            stream = self._model.create_chat_completion(
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                top_p=self._top_p,
                stream=True,
            )

            for chunk in stream:
                if abort_event.is_set():
                    logger.info("[Llama] Generation aborted")
                    break

                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    response_text += token

            elapsed = time.time() - start
            tokens = len(response_text.split())
            logger.info(
                f"[Llama] Generated {tokens} words in {elapsed:.2f}s: "
                f'"{response_text[:60]}..."'
            )

        if response_text:
            self._conversation_history.append(
                {"role": "assistant", "content": response_text}
            )

        return response_text

    def reset(self):
        """Clear conversation history."""
        self._conversation_history.clear()


class PersonaPlexBridge:
    """Bridge to PersonaPlex WebSocket server running on localhost:8998.

    PersonaPlex runs as a separate process (`python -m moshi.server`).
    This bridge connects to it, sends user audio, and receives response audio.
    Audio goes in/out as Opus-encoded frames over WebSocket.
    """

    def __init__(self):
        from app.gpu_config import (
            PERSONAPLEX_WS_URL,
            PERSONAPLEX_TEXT_PROMPT,
            PERSONAPLEX_VOICE_PROMPT_PATH,
            OUTPUT_CHUNK_BYTES,
        )

        self._ws_url = PERSONAPLEX_WS_URL
        self._text_prompt = PERSONAPLEX_TEXT_PROMPT
        self._voice_prompt_path = PERSONAPLEX_VOICE_PROMPT_PATH
        self._chunk_bytes = OUTPUT_CHUNK_BYTES
        self._ws = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._connected = threading.Event()

    def connect(self):
        """Start the async event loop and connect to PersonaPlex in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Wait for connection (up to 10 seconds)
        if not self._connected.wait(timeout=10.0):
            raise ConnectionError(
                f"Could not connect to PersonaPlex at {self._ws_url}. "
                "Is the PersonaPlex server running? "
                "Start it with: python -m moshi.server"
            )

    def _run_loop(self):
        """Run the asyncio event loop for WebSocket communication."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_listen())

    async def _connect_and_listen(self):
        """Connect to PersonaPlex WebSocket and maintain the connection."""
        websockets = _ensure_websockets()

        retry_delay = 1.0
        max_retries = 5

        for attempt in range(max_retries):
            try:
                async with websockets.connect(
                    self._ws_url,
                    max_size=10 * 1024 * 1024,  # 10MB max message
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._connected.set()
                    logger.info(f"Connected to PersonaPlex at {self._ws_url}")

                    # Send initial handshake with persona config
                    await self._send_handshake()

                    # Keep connection alive
                    try:
                        async for message in ws:
                            # Messages are handled by send_audio_and_receive
                            pass
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("PersonaPlex WebSocket closed")

            except Exception as e:
                logger.warning(
                    f"PersonaPlex connection attempt {attempt + 1}/{max_retries} "
                    f"failed: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2

        self._connected.clear()
        logger.error("Failed to connect to PersonaPlex after all retries")

    async def _send_handshake(self):
        """Send initial handshake with text prompt and voice prompt."""
        if self._ws is None:
            return

        handshake = {
            "type": "handshake",
            "text_prompt": self._text_prompt,
        }

        # If voice prompt file exists, send it as base64 audio
        if self._voice_prompt_path:
            try:
                import base64
                with open(self._voice_prompt_path, "rb") as f:
                    voice_data = base64.b64encode(f.read()).decode("ascii")
                handshake["voice_prompt"] = voice_data
            except FileNotFoundError:
                logger.warning(
                    f"Voice prompt file not found: {self._voice_prompt_path}"
                )

        await self._ws.send(json.dumps(handshake))
        logger.info("Sent PersonaPlex handshake with persona config")

    def send_audio_receive_stream(
        self,
        audio_pcm: bytes,
        audio_queue: queue.Queue,
        abort_event: threading.Event,
    ):
        """Send user audio to PersonaPlex and stream response audio to queue.

        This is a BLOCKING call that runs until PersonaPlex finishes responding
        or abort_event is set.

        Args:
            audio_pcm: Raw PCM int16 audio from the user (16kHz mono).
            audio_queue: Queue to put response audio chunks into (PCM int16 24kHz).
            abort_event: Set to cancel.
        """
        if self._loop is None or self._ws is None:
            logger.error("PersonaPlex not connected")
            audio_queue.put(None)
            return

        future = asyncio.run_coroutine_threadsafe(
            self._send_and_receive(audio_pcm, audio_queue, abort_event),
            self._loop,
        )

        try:
            future.result(timeout=30.0)
        except Exception as e:
            logger.error(f"PersonaPlex send/receive error: {e}")
            audio_queue.put(None)

    async def _send_and_receive(
        self,
        audio_pcm: bytes,
        audio_queue: queue.Queue,
        abort_event: threading.Event,
    ):
        """Async implementation of send and receive."""
        if self._ws is None:
            audio_queue.put(None)
            return

        try:
            # Send audio to PersonaPlex as binary WebSocket message
            # PersonaPlex expects Opus-encoded audio, but we send raw PCM
            # and let the server's Mimi encoder handle it.
            # Format: type byte (0x01 = audio) + raw PCM bytes
            audio_message = b'\x01' + audio_pcm
            await self._ws.send(audio_message)

            # Receive response audio chunks
            while not abort_event.is_set():
                try:
                    message = await asyncio.wait_for(
                        self._ws.recv(), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    break

                if isinstance(message, bytes):
                    if len(message) == 0:
                        break

                    # First byte is message type
                    msg_type = message[0] if len(message) > 0 else 0
                    payload = message[1:] if len(message) > 1 else b""

                    if msg_type == 0x01:  # Audio data
                        # Send in chunks for smooth streaming
                        for i in range(0, len(payload), self._chunk_bytes):
                            if abort_event.is_set():
                                break
                            chunk = payload[i:i + self._chunk_bytes]
                            audio_queue.put(chunk)

                    elif msg_type == 0x02:  # Text (inner monologue)
                        text = payload.decode("utf-8", errors="replace")
                        logger.debug(f"[PersonaPlex transcript] {text}")

                    elif msg_type == 0xFF:  # End of response
                        break

                elif isinstance(message, str):
                    # JSON control message
                    try:
                        ctrl = json.loads(message)
                        if ctrl.get("type") == "done":
                            break
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            logger.error(f"PersonaPlex stream error: {e}")

        audio_queue.put(None)

    def inject_inner_monologue(self, text: str, abort_event: threading.Event):
        """Drip-feed text into PersonaPlex's inner monologue channel.

        This injects knowledge from Llama into PersonaPlex so it can
        incorporate the information into its spoken response.

        IMPORTANT: Must drip-feed at ~20 chars / 80ms to avoid breaking
        Moshi's temporal alignment. Burst injection degenerates output.

        Args:
            text: The full text to inject (from Llama response).
            abort_event: Set to cancel.
        """
        from app.gpu_config import DRIP_FEED_CHARS_PER_TICK, DRIP_FEED_TICK_MS

        if self._loop is None or self._ws is None:
            return

        async def _drip():
            for i in range(0, len(text), DRIP_FEED_CHARS_PER_TICK):
                if abort_event.is_set():
                    break
                chunk = text[i:i + DRIP_FEED_CHARS_PER_TICK]
                # Type 0x02 = text injection
                msg = b'\x02' + chunk.encode("utf-8")
                if self._ws is not None:
                    await self._ws.send(msg)
                await asyncio.sleep(DRIP_FEED_TICK_MS / 1000.0)

        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(_drip(), self._loop)

    def disconnect(self):
        """Close the PersonaPlex WebSocket connection."""
        if self._ws is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)


class GPUVoicePipeline:
    """Hybrid voice pipeline: PersonaPlex (voice) + Llama (intelligence).

    Same interface as VoicePipeline for drop-in replacement.

    Modes:
      1. VOICE_ONLY: PersonaPlex handles everything (fast, but limited intelligence)
      2. HYBRID: PersonaPlex for voice, Llama for complex questions
         a. Inner monologue injection (experimental)
         b. TTS fallback — gate PersonaPlex audio, use TTS for Llama response

    For v1, we use HYBRID with TTS fallback (most reliable).
    """

    def __init__(self):
        from app.gpu_config import (
            COMPLEXITY_KEYWORDS,
            USE_TTS_FALLBACK,
        )

        self._complexity_keywords = COMPLEXITY_KEYWORDS
        self._use_tts_fallback = USE_TTS_FALLBACK
        self._abort = threading.Event()

        # Initialize components
        self._personaplex = PersonaPlexBridge()
        self._llama = LlamaIntelligence()
        self._initialized = False

    def initialize(self):
        """Load models and establish connections. Call once at startup."""
        if self._initialized:
            return

        logger.info("=== Initializing GPU Voice Pipeline ===")
        start = time.time()

        # Load Llama on CPU
        self._llama.load()

        # Connect to PersonaPlex (must be running separately)
        self._personaplex.connect()

        elapsed = time.time() - start
        logger.info(f"=== GPU Pipeline ready in {elapsed:.1f}s ===")
        self._initialized = True

    def abort(self):
        """Abort current generation (for interruption handling)."""
        self._abort.set()

    def process(self, audio_pcm: bytes, audio_queue: queue.Queue):
        """Full pipeline: user audio -> response audio chunks in queue.

        Audio chunks are placed in queue as they become available.
        None is placed when done.

        Args:
            audio_pcm: Raw PCM float32 audio from frontend (16kHz mono).
            audio_queue: Queue for response audio chunks (PCM int16 24kHz).
        """
        self._abort.clear()
        pipeline_start = time.time()

        if not self._initialized:
            logger.error("Pipeline not initialized. Call initialize() first.")
            audio_queue.put(None)
            return

        # Convert float32 PCM to int16 for PersonaPlex
        try:
            audio_np = np.frombuffer(audio_pcm, dtype=np.float32)
            if len(audio_np) == 0:
                audio_queue.put(None)
                return
            audio_int16 = (audio_np * 32767).astype(np.int16).tobytes()
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            audio_queue.put(None)
            return

        # Strategy: Send to PersonaPlex first for voice-native response.
        # PersonaPlex will generate audio AND an inner monologue transcript.
        # If we detect a complex question from the transcript, we can
        # augment the response with Llama intelligence.
        #
        # For v1, we use a simpler approach:
        # - Always let PersonaPlex handle the voice I/O
        # - The quality of responses is limited to PersonaPlex's 7B brain
        # - Llama augmentation is available but experimental
        logger.info(f"[GPU Pipeline] Processing {len(audio_int16)} bytes of audio")

        self._personaplex.send_audio_receive_stream(
            audio_int16, audio_queue, self._abort
        )

        elapsed = time.time() - pipeline_start
        logger.info(f"[GPU Pipeline] Total: {elapsed:.2f}s")

    def process_with_intelligence(
        self, audio_pcm: bytes, audio_queue: queue.Queue
    ):
        """Enhanced pipeline that uses Llama for complex questions.

        This is the HYBRID mode. Flow:
        1. Convert audio to int16 for PersonaPlex
        2. Also transcribe (using a lightweight local ASR or PersonaPlex transcript)
        3. If question is complex, generate Llama response
        4. Either drip-feed into PersonaPlex or use TTS fallback

        NOTE: This requires a local ASR model (like Whisper) for transcription
        before PersonaPlex. For v1, we use PersonaPlex-only mode and plan to
        add hybrid in v2 once the inner monologue injection is validated.

        Args:
            audio_pcm: Raw PCM float32 audio from frontend.
            audio_queue: Queue for response audio chunks.
        """
        self._abort.clear()
        pipeline_start = time.time()

        if not self._initialized:
            logger.error("Pipeline not initialized")
            audio_queue.put(None)
            return

        # Convert float32 to int16
        try:
            audio_np = np.frombuffer(audio_pcm, dtype=np.float32)
            if len(audio_np) == 0:
                audio_queue.put(None)
                return
            audio_int16 = (audio_np * 32767).astype(np.int16).tobytes()
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            audio_queue.put(None)
            return

        # For v1: direct PersonaPlex passthrough
        # TODO(v2): Add transcription -> complexity detection -> Llama augmentation
        #
        # The v2 flow would be:
        #   1. Send audio to a lightweight ASR (faster-whisper) for transcript
        #   2. Check transcript against COMPLEXITY_KEYWORDS
        #   3. If complex:
        #      a. Run Llama generate(transcript) in parallel
        #      b. When Llama responds, either drip-feed or TTS-fallback
        #   4. If simple: let PersonaPlex handle natively
        #
        # Why not v1: PersonaPlex's inner monologue gives us a transcript,
        # but it arrives AFTER the response starts. We need the transcript
        # BEFORE deciding to invoke Llama. This requires a separate ASR step.

        self._personaplex.send_audio_receive_stream(
            audio_int16, audio_queue, self._abort
        )

        elapsed = time.time() - pipeline_start
        logger.info(f"[GPU Pipeline Hybrid] Total: {elapsed:.2f}s")

    def _is_complex_question(self, transcript: str) -> bool:
        """Determine if a transcript requires Llama intelligence.

        Simple heuristic: check for knowledge-seeking keywords.
        Future: use a small classifier model for better accuracy.
        """
        lower = transcript.lower().strip()
        return any(kw in lower for kw in self._complexity_keywords)

    def _generate_tts_fallback(
        self, text: str, audio_queue: queue.Queue
    ):
        """Generate TTS audio for Llama's response (fallback mode).

        When PersonaPlex can't handle the knowledge, we:
        1. Gate PersonaPlex audio (mute it)
        2. Generate TTS from Llama's text response
        3. Send TTS audio to the client instead

        For v1, this uses edge-tts (free Microsoft TTS API).
        For v2, this should use Kokoro or Mimi TTS (self-hosted).
        """
        # TODO: Implement edge-tts or Kokoro TTS
        # For now, log the limitation
        logger.warning(
            f"[TTS Fallback] Not yet implemented. Text: {text[:60]}..."
        )

    def reset(self):
        """Reset conversation state."""
        self._llama.reset()

    def shutdown(self):
        """Clean shutdown of all components."""
        logger.info("Shutting down GPU pipeline...")
        self._personaplex.disconnect()
        logger.info("GPU pipeline shut down.")
