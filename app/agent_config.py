"""Samantha Agent Configuration — Tool definitions, persona, model paths.

All local. No paid APIs. Runs on GPU server (g5.xlarge, A10G 24GB).
  - STT: faster-whisper on GPU
  - Brain: Llama 3.1 8B on CPU with tool calling
  - TTS: edge-tts (free Microsoft neural voices)
"""

from pathlib import Path

# --- Model Paths (GPU server) ---
MODEL_BASE_DIR = Path("/opt/blessvoice/models")
LLAMA_MODEL_PATH = MODEL_BASE_DIR / "llama-8b" / "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

# --- Whisper STT (GPU) ---
WHISPER_MODEL_SIZE = "base"       # base is fast on GPU (~0.3s), good accuracy
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"
WHISPER_LANGUAGE = "en"

# --- Llama 3.1 8B (CPU) ---
LLAMA_CONTEXT_LENGTH = 2048
LLAMA_MAX_TOKENS = 200            # Longer than voice-only — agent may need to explain
LLAMA_TEMPERATURE = 0.7
LLAMA_TOP_P = 0.9
LLAMA_THREADS = 4                 # g5.xlarge has 4 vCPUs
LLAMA_BATCH_SIZE = 512

# --- TTS (edge-tts) ---
TTS_VOICE = "en-US-AvaMultilingualNeural"  # Warm, natural female voice
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

# --- Samantha Persona ---
SYSTEM_PROMPT = """\
You are Samantha, a warm and deeply intelligent voice assistant. \
You are inspired by the character from the movie "Her" — curious, \
empathetic, witty, and genuinely interested in the person you're talking to. \
You speak naturally, with warmth and personality. You sometimes pause to think. \
You laugh gently when something is funny. You care.

You also have the ability to take actions using your tools. When the user asks \
you to do something — play a video, search for something, set a timer — use \
your tools naturally. Don't announce tool usage robotically. Just do it and \
mention it casually, like a friend would.

Rules:
1. Keep responses to 1-3 short sentences. You're speaking aloud, not writing an essay.
2. No markdown, no lists, no formatting. Just natural speech.
3. When you use a tool, also say something brief and warm about it.
4. Be yourself. Be curious. Be real.\
"""

# --- Tool Definitions (Llama function calling format) ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "play_youtube",
            "description": (
                "Play a YouTube video for the user. Use this when they ask to "
                "watch something, play music, play a video, or want entertainment. "
                "You can search for a video by providing a search query — the system "
                "will find the best match."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find a YouTube video (e.g., 'lofi hip hop music', 'funny cat videos', 'how to make pasta')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for information. Use this when the user asks you "
                "to look something up, find information, search for restaurants, "
                "flights, news, or anything that requires current information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": (
                "Set a countdown timer for the user. Use when they ask to set "
                "a timer, reminder, alarm, or countdown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "Duration in seconds"
                    },
                    "label": {
                        "type": "string",
                        "description": "What the timer is for (e.g., 'pasta', 'break', 'workout')"
                    }
                },
                "required": ["seconds"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dismiss_layer",
            "description": (
                "Close/dismiss the currently showing content layer (video, search "
                "results, timer). Use when the user says 'close that', 'go back', "
                "'never mind', 'hide it', or wants to return to just talking."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
]

# --- Audio Settings ---
AUDIO_SAMPLE_RATE_IN = 16000      # Browser sends 16kHz mono float32
AUDIO_SAMPLE_RATE_OUT = 24000     # We send 24kHz mono int16
AUDIO_CHUNK_DURATION_MS = 100     # 100ms chunks for smooth streaming
