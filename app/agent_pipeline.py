"""Samantha Agent Pipeline — Whisper (STT) + Llama (brain + tools) + edge-tts (voice).

All local. No paid APIs.

Flow:
  1. User audio (PCM float32 16kHz) arrives via WebSocket
  2. faster-whisper transcribes on GPU (~0.3s)
  3. Llama 3.1 8B decides: just talk, or invoke a tool?
     - Talk: generates text response
     - Tool: returns structured tool_call JSON + spoken confirmation
  4. edge-tts converts text to speech (PCM int16 24kHz)
  5. Audio chunks + tool_call dicts placed in queue for WebSocket

The queue can contain:
  - bytes: audio PCM chunks (send as binary WebSocket)
  - dict:  tool invocations (send as JSON WebSocket)
  - None:  end-of-response sentinel
"""

import io
import json
import logging
import os
import queue
import struct
import tempfile
import threading
import time
from typing import Optional

import numpy as np

from app.agent_config import (
    LLAMA_MODEL_PATH,
    LLAMA_CONTEXT_LENGTH,
    LLAMA_MAX_TOKENS,
    LLAMA_TEMPERATURE,
    LLAMA_TOP_P,
    LLAMA_THREADS,
    LLAMA_BATCH_SIZE,
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_LANGUAGE,
    TTS_VOICE,
    TTS_RATE,
    TTS_VOLUME,
    SYSTEM_PROMPT,
    TOOLS,
    AUDIO_SAMPLE_RATE_IN,
    AUDIO_SAMPLE_RATE_OUT,
    AUDIO_CHUNK_DURATION_MS,
)

logger = logging.getLogger("samantha.agent")


class AgentPipeline:
    """Samantha voice agent: understands speech, thinks, acts, speaks back."""

    def __init__(self):
        self._whisper_model = None
        self._llama_model = None
        self._conversation_history: list[dict] = []
        self._abort = threading.Event()
        self._initialized = False
        self._llama_lock = threading.Lock()

    def initialize(self):
        """Load models. Call once at startup."""
        if self._initialized:
            return

        start = time.time()
        logger.info("=== Initializing Samantha Agent Pipeline ===")

        # Load Whisper
        self._load_whisper()

        # Load Llama
        self._load_llama()

        elapsed = time.time() - start
        logger.info(f"=== Samantha ready in {elapsed:.1f}s ===")
        self._initialized = True

    def _load_whisper(self):
        """Load faster-whisper model on GPU."""
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper ({WHISPER_MODEL_SIZE}) on {WHISPER_DEVICE}...")
            t = time.time()
            self._whisper_model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            logger.info(f"Whisper loaded in {time.time() - t:.1f}s")
        except ImportError:
            raise ImportError(
                "faster-whisper required: pip install faster-whisper"
            )

    def _load_llama(self):
        """Load Llama 3.1 8B on CPU."""
        try:
            from llama_cpp import Llama
            logger.info(f"Loading Llama from {LLAMA_MODEL_PATH}...")
            t = time.time()
            self._llama_model = Llama(
                model_path=str(LLAMA_MODEL_PATH),
                n_ctx=LLAMA_CONTEXT_LENGTH,
                n_threads=LLAMA_THREADS,
                n_batch=LLAMA_BATCH_SIZE,
                chat_format="llama-3",
                verbose=False,
            )
            logger.info(f"Llama loaded in {time.time() - t:.1f}s")
        except ImportError:
            raise ImportError(
                "llama-cpp-python required: pip install llama-cpp-python"
            )

    def abort(self):
        """Abort current generation."""
        self._abort.set()

    def process(self, audio_pcm: bytes, audio_queue: queue.Queue):
        """Full pipeline: user audio -> STT -> Llama (tools) -> TTS -> audio + tools in queue.

        Args:
            audio_pcm: Raw PCM float32 audio from browser (16kHz mono).
            audio_queue: Queue for response. Items can be:
                         - bytes: audio chunks (PCM int16 24kHz)
                         - dict: tool invocations
                         - None: end sentinel
        """
        self._abort.clear()
        pipeline_start = time.time()

        if not self._initialized:
            logger.error("Pipeline not initialized")
            audio_queue.put(None)
            return

        # --- Step 1: STT ---
        stt_start = time.time()
        transcript = self._transcribe(audio_pcm)
        stt_time = time.time() - stt_start

        if not transcript:
            audio_queue.put(None)
            return

        logger.info(f'[STT] ({stt_time:.2f}s) "{transcript}"')

        if self._abort.is_set():
            audio_queue.put(None)
            return

        # --- Step 2: Llama with tools ---
        llm_start = time.time()
        self._conversation_history.append({"role": "user", "content": transcript})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self._conversation_history[-10:])

        response = self._llama_generate(messages)
        llm_time = time.time() - llm_start

        if self._abort.is_set():
            audio_queue.put(None)
            return

        # --- Step 3: Process response (tool calls and/or text) ---
        tool_calls = response.get("tool_calls", [])
        text_content = response.get("content", "")

        logger.info(
            f'[LLM] ({llm_time:.2f}s) text="{text_content[:80]}" '
            f'tools={[tc["name"] for tc in tool_calls]}'
        )

        # Send tool calls to browser
        for tc in tool_calls:
            if self._abort.is_set():
                break
            tool_msg = {
                "type": "tool_call",
                "tool": tc["name"],
                "params": tc.get("arguments", {}),
            }
            audio_queue.put(tool_msg)
            logger.info(f'[TOOL] {tc["name"]}({tc.get("arguments", {})})')

        # --- Step 4: TTS ---
        if text_content and not self._abort.is_set():
            tts_start = time.time()
            self._synthesize(text_content, audio_queue)
            tts_time = time.time() - tts_start
            logger.info(f"[TTS] ({tts_time:.2f}s)")

        # Update conversation history
        if text_content:
            self._conversation_history.append(
                {"role": "assistant", "content": text_content}
            )

        audio_queue.put(None)

        total = time.time() - pipeline_start
        logger.info(f"[PIPELINE] Total: {total:.2f}s")

    def _transcribe(self, audio_pcm: bytes) -> str:
        """Transcribe PCM float32 audio using faster-whisper on GPU."""
        audio_np = np.frombuffer(audio_pcm, dtype=np.float32)
        if len(audio_np) == 0:
            return ""

        segments, info = self._whisper_model.transcribe(
            audio_np,
            language=WHISPER_LANGUAGE,
            beam_size=1,
            vad_filter=True,
        )

        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text

    def _llama_generate(self, messages: list[dict]) -> dict:
        """Generate response with Llama, including tool calling.

        Tries native tool calling first. If unsupported (old llama-cpp-python),
        falls back to prompt-based tool extraction.

        Returns:
            dict with keys:
                "content": str (text response, may be empty if tool-only)
                "tool_calls": list of {"name": str, "arguments": dict}
        """
        # Use prompt-based tool extraction — more reliable than native
        # tool calling on quantized GGUF models which often ignore the
        # tools parameter and respond with plain text instead.
        return self._llama_generate_fallback(messages)

    def _parse_tool_response(self, response: dict) -> dict:
        """Parse a native tool-calling response from Llama."""
        choice = response["choices"][0]["message"]
        content = choice.get("content", "") or ""
        tool_calls_raw = choice.get("tool_calls", []) or []

        tool_calls = []
        for tc in tool_calls_raw:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args_str = fn.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}
            if name:
                tool_calls.append({"name": name, "arguments": args})

        return {"content": content.strip(), "tool_calls": tool_calls}

    def _llama_generate_fallback(self, messages: list[dict]) -> dict:
        """Fallback: inject tool descriptions into the prompt and parse output.

        When native tool calling isn't available, we instruct the model to
        output [TOOL:name:json_args] markers in its response text.
        """
        tool_prompt = (
            "\n\n## TOOLS — MANDATORY FORMAT\n"
            "You MUST use tools when the user asks you to DO something.\n"
            "Format: [TOOL:tool_name:{\"param\":\"value\"}]\n"
            "You MUST include the [TOOL:...] marker in your response when using a tool.\n"
            "Always include a brief spoken response alongside the tool marker.\n\n"
            "EXAMPLES:\n"
            'User: "Set a timer for 5 minutes"\n'
            'You: "Sure, starting a 5 minute timer for you. [TOOL:set_timer:{\"seconds\":300,\"label\":\"5 minute timer\"}]"\n\n'
            'User: "Play some jazz music"\n'
            'You: "I\'ve got just the thing. [TOOL:play_youtube:{\"query\":\"jazz music playlist\"}]"\n\n'
            'User: "Search for flights to Delhi"\n'
            'You: "Let me look that up for you. [TOOL:web_search:{\"query\":\"flights to Delhi\"}]"\n\n'
            'User: "Close that" or "Go back"\n'
            'You: "Sure thing. [TOOL:dismiss_layer:{}]"\n\n'
            "Available tools:\n"
        )
        for t in TOOLS:
            fn = t["function"]
            params = fn.get("parameters", {}).get("properties", {})
            param_list = ", ".join(f'{k}' for k in params.keys())
            tool_prompt += f'- {fn["name"]}({param_list}): {fn["description"]}\n'

        tool_prompt += (
            "\nIMPORTANT: If the user asks to play, search, set timer, or dismiss — "
            "you MUST include [TOOL:...] in your response. Do NOT just describe the action.\n"
        )

        # Inject tool instructions into system message
        fallback_messages = list(messages)
        if fallback_messages and fallback_messages[0]["role"] == "system":
            fallback_messages[0] = {
                "role": "system",
                "content": fallback_messages[0]["content"] + tool_prompt,
            }

        try:
            response = self._llama_model.create_chat_completion(
                messages=fallback_messages,
                max_tokens=LLAMA_MAX_TOKENS,
                temperature=LLAMA_TEMPERATURE,
                top_p=LLAMA_TOP_P,
            )
        except Exception as e:
            logger.error(f"Llama fallback generation failed: {e}")
            return {"content": "Sorry, I had trouble with that.", "tool_calls": []}

        content = response["choices"][0]["message"].get("content", "") or ""

        # Extract [TOOL:name:args] markers — flexible regex for LLM variations
        import re
        tool_calls = []

        # Match [TOOL:name:{...}] with optional spaces
        patterns = [
            re.compile(r'\[TOOL:\s*(\w+)\s*:\s*(\{.*?\})\s*\]', re.DOTALL),
            re.compile(r'\[TOOL:\s*(\w+)\s*\((\{.*?\})\)\s*\]', re.DOTALL),  # [TOOL:name({...})]
            re.compile(r'\[TOOL:\s*(\w+)\s*\]'),  # [TOOL:name] with no args
        ]

        matched_spans = []
        for pattern in patterns:
            for match in pattern.finditer(content):
                name = match.group(1)
                try:
                    args = json.loads(match.group(2)) if match.lastindex >= 2 else {}
                except (json.JSONDecodeError, IndexError):
                    args = {}
                if name:
                    tool_calls.append({"name": name, "arguments": args})
                    matched_spans.append(match.span())

        # Remove tool markers from spoken text
        clean_content = content
        for start, end in sorted(matched_spans, reverse=True):
            clean_content = clean_content[:start] + clean_content[end:]
        clean_content = clean_content.strip()

        return {"content": clean_content, "tool_calls": tool_calls}

    def _synthesize(self, text: str, audio_queue: queue.Queue):
        """Convert text to speech using edge-tts, stream PCM chunks to queue."""
        if not text or self._abort.is_set():
            return

        try:
            import edge_tts
            import asyncio
        except ImportError:
            raise ImportError("edge-tts required: pip install edge-tts")

        # edge-tts is async — run in a new event loop
        async def _generate():
            communicate = edge_tts.Communicate(
                text, TTS_VOICE, rate=TTS_RATE, volume=TTS_VOLUME
            )

            # Collect all audio data (MP3 format from edge-tts)
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if self._abort.is_set():
                    return
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])

            if not audio_data or self._abort.is_set():
                return

            # Decode MP3 to PCM
            pcm_data = self._decode_mp3_to_pcm(bytes(audio_data))
            if pcm_data is None:
                return

            # Send in chunks
            chunk_bytes = AUDIO_SAMPLE_RATE_OUT * 2 * AUDIO_CHUNK_DURATION_MS // 1000
            for i in range(0, len(pcm_data), chunk_bytes):
                if self._abort.is_set():
                    break
                audio_queue.put(pcm_data[i:i + chunk_bytes])

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_generate())
        finally:
            loop.close()

    def _decode_mp3_to_pcm(self, mp3_data: bytes) -> Optional[bytes]:
        """Decode MP3 bytes to PCM int16 at 24kHz mono."""
        try:
            import subprocess
            # Use ffmpeg to convert MP3 to raw PCM
            proc = subprocess.run(
                [
                    "ffmpeg", "-i", "pipe:0",
                    "-f", "s16le",
                    "-acodec", "pcm_s16le",
                    "-ar", str(AUDIO_SAMPLE_RATE_OUT),
                    "-ac", "1",
                    "pipe:1",
                ],
                input=mp3_data,
                capture_output=True,
                timeout=10,
            )
            if proc.returncode != 0:
                logger.error(f"ffmpeg decode failed: {proc.stderr[:200]}")
                return None
            return proc.stdout
        except FileNotFoundError:
            logger.error("ffmpeg not found — install with: apt install ffmpeg")
            return None
        except Exception as e:
            logger.error(f"MP3 decode error: {e}")
            return None

    def reset(self):
        """Clear conversation history."""
        self._conversation_history.clear()

    def shutdown(self):
        """Clean shutdown."""
        logger.info("Samantha agent shutting down.")
