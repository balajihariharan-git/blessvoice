from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Server
HOST = "0.0.0.0"
PORT = 8000

# VAD (Voice Activity Detection)
SILENCE_THRESHOLD = 0.012       # Audio level below this = silence
SILENCE_DURATION_MS = 800       # ms of silence before sending (was 1500)
MIN_SPEECH_DURATION_MS = 300    # Ignore very short sounds

# LLM
LLM_MODEL = "gpt-4o-mini"
LLM_MAX_TOKENS = 80
SYSTEM_PROMPT = """You are BlessVoice, a helpful voice assistant. Rules:
1. Reply in 1-2 short sentences only.
2. Be direct and natural.
3. Never repeat yourself.
4. No markdown, no lists, no formatting.
5. Talk like a real person on a phone call."""

# TTS
TTS_MODEL = "tts-1"             # OpenAI TTS (fast mode)
TTS_VOICE = "nova"              # Options: alloy, echo, fable, onyx, nova, shimmer
