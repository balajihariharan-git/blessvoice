"""BlessVoice GPU Configuration — Model paths, VRAM allocation, inference params.

Architecture: PersonaPlex 7B (GPU, fp16) for voice I/O
             + Llama 3.1 8B (CPU, GGUF Q4_K_M) for intelligence
             on AWS g5.xlarge (A10G 24GB VRAM, 4 vCPUs, 16GB RAM)
"""

from pathlib import Path

# --- Model Paths ---
MODEL_BASE_DIR = Path("/opt/blessvoice/models")

PERSONAPLEX_MODEL_ID = "nvidia/personaplex-7b-v1"
PERSONAPLEX_LOCAL_DIR = MODEL_BASE_DIR / "personaplex-7b-v1"

LLAMA_MODEL_DIR = MODEL_BASE_DIR / "llama-3.1-8b-instruct"
LLAMA_GGUF_FILE = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
LLAMA_MODEL_PATH = LLAMA_MODEL_DIR / LLAMA_GGUF_FILE

# --- PersonaPlex Server ---
PERSONAPLEX_HOST = "127.0.0.1"
PERSONAPLEX_PORT = 8998
PERSONAPLEX_WS_URL = f"ws://{PERSONAPLEX_HOST}:{PERSONAPLEX_PORT}/api/chat"

# PersonaPlex uses Opus codec over WebSocket internally.
# We bridge to raw PCM for the BlessVoice frontend.
PERSONAPLEX_AUDIO_SAMPLE_RATE = 24000  # Mimi codec output rate
PERSONAPLEX_AUDIO_CHANNELS = 1
PERSONAPLEX_AUDIO_DTYPE = "int16"

# --- PersonaPlex Persona ---
PERSONAPLEX_TEXT_PROMPT = (
    "You are BlessVoice, a warm and helpful voice assistant. "
    "You speak naturally with emotion and personality. "
    "You are direct, friendly, and conversational. "
    "Keep responses to 1-2 sentences unless asked for more detail."
)

# Voice prompt: path to a short WAV file for voice cloning (optional).
# Set to None to use PersonaPlex's default voice.
PERSONAPLEX_VOICE_PROMPT_PATH: str | None = None

# --- Llama 3.1 8B (CPU Intelligence) ---
LLAMA_CONTEXT_LENGTH = 2048       # Keep small — we only need 1-2 sentence responses
LLAMA_MAX_TOKENS = 100            # Max tokens per response
LLAMA_TEMPERATURE = 0.7
LLAMA_TOP_P = 0.9
LLAMA_THREADS = 4                 # g5.xlarge has 4 vCPUs
LLAMA_BATCH_SIZE = 512            # Prompt processing batch size

LLAMA_SYSTEM_PROMPT = (
    "You are BlessVoice, a helpful voice assistant. Rules:\n"
    "1. Reply in 1-2 short sentences only.\n"
    "2. Be direct and natural — this will be spoken aloud.\n"
    "3. Never use markdown, lists, or formatting.\n"
    "4. No emojis. No asterisks. No bullet points.\n"
    "5. Talk like a real person on a phone call.\n"
    "6. If you don't know something, say so briefly."
)

# --- VRAM Budget ---
# PersonaPlex 7B fp16:   ~18-20 GB
# CUDA overhead/KV:      ~2-4 GB
# Total GPU:             ~20-24 GB (fills A10G)
# Llama runs on CPU:     ~6 GB system RAM
GPU_MEMORY_FRACTION = 0.95  # Let PersonaPlex use up to 95% of GPU

# --- Hybrid Pipeline Settings ---

# How to decide when to invoke Llama for a "smart" response:
# PersonaPlex handles casual conversation on its own.
# Llama is invoked when the user asks a factual/complex question.
COMPLEXITY_KEYWORDS = [
    "what is", "who is", "how does", "explain", "why does",
    "tell me about", "define", "calculate", "compare",
    "difference between", "how to", "what are", "when did",
    "where is", "how many", "how much", "can you help",
]

# Inner monologue drip-feed rate for injecting Llama's response
# into PersonaPlex. Must match Moshi's per-frame text consumption.
DRIP_FEED_CHARS_PER_TICK = 20    # Characters per tick
DRIP_FEED_TICK_MS = 80           # Milliseconds between ticks

# Fallback: if inner monologue injection is unreliable,
# gate PersonaPlex audio and use external TTS instead.
USE_TTS_FALLBACK = True           # Start with TTS fallback (more reliable)
TTS_FALLBACK_COOLDOWN_MS = 8000   # Gate PersonaPlex audio for this long

# --- Audio Codec Bridge ---
# PersonaPlex uses Opus over WebSocket.
# BlessVoice frontend expects raw PCM int16 at 24kHz.
OPUS_DECODE_ENABLED = True
OUTPUT_SAMPLE_RATE = 24000        # Match PersonaPlex output
OUTPUT_CHANNELS = 1
OUTPUT_DTYPE = "int16"
OUTPUT_CHUNK_DURATION_MS = 100    # Send audio in 100ms chunks
OUTPUT_CHUNK_SAMPLES = OUTPUT_SAMPLE_RATE * OUTPUT_CHUNK_DURATION_MS // 1000
OUTPUT_CHUNK_BYTES = OUTPUT_CHUNK_SAMPLES * 2  # 2 bytes per int16 sample

# --- Server ---
GPU_SERVER_HOST = "0.0.0.0"
GPU_SERVER_PORT = 8000
