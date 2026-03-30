"""BlessVoice Pipeline — Streaming STT → LLM → TTS using OpenAI APIs.

Architecture inspired by RealtimeVoiceChat and Pipecat:
- All AI runs in cloud (OpenAI) — no CPU bottleneck
- First-sentence fast path — TTS starts on first sentence while LLM streams rest
- Streaming TTS — audio chunks sent to client as they're generated
- Interruption-ready — pipeline can be aborted mid-generation
"""

import io
import os
import time
import threading
import queue
import numpy as np
from openai import OpenAI
from app.config import LLM_MODEL, LLM_MAX_TOKENS, SYSTEM_PROMPT, TTS_MODEL, TTS_VOICE


class VoicePipeline:
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)
        self.conversation_history = []
        self._abort = threading.Event()

    def abort(self):
        """Abort current generation (for interruption handling)."""
        self._abort.set()

    def process(self, audio_pcm: bytes, audio_queue: queue.Queue):
        """Full pipeline: audio bytes → STT → LLM → TTS → audio chunks in queue.

        Audio chunks are placed in queue as they become available.
        None is placed when done.
        """
        self._abort.clear()
        pipeline_start = time.time()

        # --- Step 1: STT (OpenAI Whisper API) ---
        stt_start = time.time()
        transcript = self._transcribe(audio_pcm)
        stt_time = time.time() - stt_start

        if not transcript:
            audio_queue.put(None)
            return

        print(f"[STT] ({stt_time:.2f}s) \"{transcript}\"")

        if self._abort.is_set():
            audio_queue.put(None)
            return

        # --- Step 2+3: LLM streaming → TTS on first sentence ---
        self.conversation_history.append({"role": "user", "content": transcript})

        llm_start = time.time()
        sentence_buffer = ""
        sentence_enders = {'.', '!', '?'}
        full_response = ""
        first_sentence_done = False
        ttfb = None  # Time to first byte

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.conversation_history[-10:])

        stream = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=LLM_MAX_TOKENS,
            temperature=0.7,
            stream=True,
        )

        remaining_sentences = []

        for chunk in stream:
            if self._abort.is_set():
                break

            token = chunk.choices[0].delta.content or ""
            sentence_buffer += token
            full_response += token

            # First sentence fast path: TTS immediately
            if not first_sentence_done and any(sentence_buffer.rstrip().endswith(c) for c in sentence_enders):
                first_sentence = sentence_buffer.strip()
                if first_sentence:
                    llm_first = time.time() - llm_start
                    print(f"[LLM] First sentence ({llm_first:.2f}s): \"{first_sentence}\"")

                    # TTS the first sentence RIGHT NOW
                    if not self._abort.is_set():
                        tts_start = time.time()
                        self._synthesize_streaming(first_sentence, audio_queue)
                        if ttfb is None:
                            ttfb = time.time() - pipeline_start
                            print(f"[PIPELINE] Time to first audio: {ttfb:.2f}s")

                    first_sentence_done = True
                    sentence_buffer = ""
                    continue

            # Collect remaining sentences
            if first_sentence_done and any(sentence_buffer.rstrip().endswith(c) for c in sentence_enders):
                sentence = sentence_buffer.strip()
                if sentence:
                    remaining_sentences.append(sentence)
                sentence_buffer = ""

        # Flush remaining buffer
        if sentence_buffer.strip():
            remaining_sentences.append(sentence_buffer.strip())

        # If we never got a first sentence (very short response)
        if not first_sentence_done and full_response.strip():
            if not self._abort.is_set():
                self._synthesize_streaming(full_response.strip(), audio_queue)

        # TTS remaining sentences
        for sentence in remaining_sentences:
            if self._abort.is_set():
                break
            self._synthesize_streaming(sentence, audio_queue)

        llm_total = time.time() - llm_start
        print(f"[LLM] Total ({llm_total:.2f}s): \"{full_response[:80]}\"")

        self.conversation_history.append({"role": "assistant", "content": full_response})
        audio_queue.put(None)  # Signal done

        total = time.time() - pipeline_start
        print(f"[PIPELINE] Total: {total:.2f}s")

    def _transcribe(self, audio_pcm: bytes) -> str:
        """Transcribe PCM float32 audio using OpenAI Whisper API."""
        # Convert float32 PCM to WAV for the API
        audio_np = np.frombuffer(audio_pcm, dtype=np.float32)
        if len(audio_np) == 0:
            return ""

        # Create WAV in memory
        wav_buffer = io.BytesIO()
        import wave
        audio_int16 = (audio_np * 32767).astype(np.int16)
        with wave.open(wav_buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(audio_int16.tobytes())

        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"

        result = self.client.audio.transcriptions.create(
            model="whisper-1",
            file=wav_buffer,
            language="en",
        )
        return result.text.strip()

    def _synthesize_streaming(self, text: str, audio_queue: queue.Queue):
        """Synthesize text to audio using OpenAI TTS, streaming chunks."""
        if not text or self._abort.is_set():
            return

        tts_start = time.time()

        response = self.client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=text,
            response_format="pcm",  # Raw PCM for low latency (no WAV header overhead)
            speed=1.0,
        )

        # Stream audio chunks to queue
        chunk_size = 4800  # 0.1 seconds at 24kHz 16-bit mono
        audio_data = response.content

        # Send in small chunks for smoother streaming
        for i in range(0, len(audio_data), chunk_size):
            if self._abort.is_set():
                break
            chunk = audio_data[i:i + chunk_size]
            audio_queue.put(chunk)

        elapsed = time.time() - tts_start
        print(f"[TTS] ({elapsed:.2f}s) \"{text[:40]}...\"")

    def reset(self):
        self.conversation_history.clear()
