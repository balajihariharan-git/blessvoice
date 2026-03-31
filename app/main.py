"""BlessVoice Server — Real-time voice-to-voice with streaming pipeline.

Supports three modes:
  - CPU mode (default): Uses OpenAI APIs (STT -> LLM -> TTS)
  - GPU mode: Uses PersonaPlex 7B + Llama 3.1 8B on local GPU
  - Agent mode: Samantha voice agent — Whisper + Llama (tools) + edge-tts

Mode is auto-detected based on CUDA availability, or forced via
BLESSVOICE_MODE environment variable ("gpu" or "cpu").

Agent mode is accessed via /agent (UI) and /ws/agent (WebSocket).
"""

import json
import asyncio
import logging
import os
import queue
import threading
import traceback
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

logger = logging.getLogger("blessvoice.server")

# --- Mode Detection ---

def _detect_mode() -> str:
    """Detect whether to use GPU or CPU pipeline.

    Priority:
      1. BLESSVOICE_MODE env var ("gpu" or "cpu")
      2. Auto-detect: check for CUDA + PersonaPlex model files
    """
    env_mode = os.environ.get("BLESSVOICE_MODE", "").lower().strip()
    if env_mode in ("gpu", "cpu"):
        return env_mode

    # Auto-detect GPU
    try:
        import torch
        if not torch.cuda.is_available():
            logger.info("No CUDA GPU detected. Using CPU pipeline (OpenAI APIs).")
            return "cpu"
    except ImportError:
        logger.info("PyTorch not installed. Using CPU pipeline (OpenAI APIs).")
        return "cpu"

    # Check if PersonaPlex model exists
    try:
        from app.gpu_config import PERSONAPLEX_LOCAL_DIR
        if not PERSONAPLEX_LOCAL_DIR.exists():
            logger.info(
                f"PersonaPlex model not found at {PERSONAPLEX_LOCAL_DIR}. "
                "Using CPU pipeline. Run infra/download-models.sh to download."
            )
            return "cpu"
    except ImportError:
        return "cpu"

    logger.info("CUDA GPU detected + PersonaPlex model found. Using GPU pipeline.")
    return "gpu"


MODE = _detect_mode()


# --- Pipeline Factory ---

_pipeline_instance = None
_gpu_pipeline_initialized = False


def _create_pipeline():
    """Create the appropriate pipeline based on detected mode."""
    global _gpu_pipeline_initialized

    if MODE == "gpu":
        from app.gpu_pipeline import GPUVoicePipeline
        pipeline = GPUVoicePipeline()
        if not _gpu_pipeline_initialized:
            pipeline.initialize()
            _gpu_pipeline_initialized = True
        return pipeline
    else:
        from app.pipeline import VoicePipeline
        return VoicePipeline()


# --- FastAPI App ---

app = FastAPI(title="BlessVoice")

WEB_DIR = Path(__file__).parent.parent / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": MODE,
        "gpu": MODE == "gpu",
    }


@app.get("/agent")
async def agent_page():
    """Serve the Samantha agent UI."""
    agent_html = WEB_DIR / "agent.html"
    if agent_html.exists():
        return FileResponse(str(agent_html))
    return {"error": "agent.html not found"}


# --- Agent Pipeline (Samantha) ---

_agent_pipeline = None


def _get_agent_pipeline():
    """Lazy-load Samantha agent pipeline."""
    global _agent_pipeline
    if _agent_pipeline is None:
        from app.agent_pipeline import AgentPipeline
        _agent_pipeline = AgentPipeline()
        _agent_pipeline.initialize()
    return _agent_pipeline


@app.on_event("startup")
async def startup():
    mode_label = "GPU (PersonaPlex + Llama)" if MODE == "gpu" else "CPU (OpenAI APIs)"
    print(f"\n=== BlessVoice Ready [{mode_label}] ===")
    print("=== Samantha Agent: http://localhost:8000/agent ===")
    print("=== Open http://localhost:8000 ===\n")

    if MODE == "gpu":
        # Pre-initialize the GPU pipeline at startup so the first
        # WebSocket connection doesn't wait for model loading.
        try:
            global _pipeline_instance
            _pipeline_instance = _create_pipeline()
            logger.info("GPU pipeline pre-initialized at startup.")
        except Exception as e:
            logger.error(f"GPU pipeline startup failed: {e}")
            logger.error("Falling back to CPU mode for this session.")

    # Pre-initialize Samantha agent pipeline at startup
    # so the first WebSocket connection doesn't wait for model loading.
    try:
        _get_agent_pipeline()
        logger.info("Samantha agent pipeline pre-initialized at startup.")
    except Exception as e:
        logger.error(f"Samantha agent startup failed: {e}")
        logger.error("Agent will retry on first /ws/agent connection.")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info(f"[WS] Client connected (mode={MODE})")

    # Create or reuse pipeline
    if MODE == "gpu" and _pipeline_instance is not None:
        pipeline = _pipeline_instance
    else:
        pipeline = _create_pipeline()

    current_thread = None

    try:
        while True:
            data = await ws.receive()

            if "bytes" in data:
                audio_bytes = data["bytes"]

                # ALWAYS abort previous pipeline before starting new one
                if current_thread and current_thread.is_alive():
                    logger.info("[WS] Aborting previous pipeline")
                    pipeline.abort()
                    current_thread.join(timeout=3)

                # Drain any leftover chunks from previous queue
                if 'audio_q' in dir():
                    while not audio_q.empty():
                        try:
                            audio_q.get_nowait()
                        except queue.Empty:
                            break

                # Fresh queue for this request
                audio_q = queue.Queue()

                # Run pipeline in background thread
                def run_pipeline():
                    try:
                        pipeline.process(audio_bytes, audio_q)
                    except Exception as e:
                        logger.error(f"[Pipeline Error] {e}")
                        traceback.print_exc()
                        audio_q.put(None)

                current_thread = threading.Thread(target=run_pipeline, daemon=True)
                current_thread.start()

                # Stream audio chunks to client as they arrive
                await ws.send_text(json.dumps({"type": "speaking"}))

                loop = asyncio.get_event_loop()
                while True:
                    chunk = await loop.run_in_executor(None, audio_q.get)
                    if chunk is None:
                        break
                    await ws.send_bytes(chunk)

                await ws.send_text(json.dumps({"type": "done"}))

            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "reset":
                    pipeline.reset()
                elif msg.get("type") == "interrupt":
                    if current_thread and current_thread.is_alive():
                        pipeline.abort()

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected")
        pipeline.abort()
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        traceback.print_exc()
    finally:
        # Clean up GPU pipeline on disconnect if not shared
        if MODE == "gpu" and pipeline is not _pipeline_instance:
            pipeline.shutdown()


# --- Samantha Agent WebSocket ---

@app.websocket("/ws/agent")
async def agent_websocket(ws: WebSocket):
    """Samantha agent WebSocket — supports audio + tool_call dispatch."""
    await ws.accept()
    logger.info("[Agent WS] Samantha client connected")

    try:
        pipeline = _get_agent_pipeline()
    except Exception as e:
        logger.error(f"[Agent WS] Failed to load agent pipeline: {e}")
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "Samantha is waking up... please try again in a moment."
        }))
        await ws.close()
        return

    current_thread = None
    audio_q = None

    try:
        while True:
            data = await ws.receive()

            if "bytes" in data:
                audio_bytes = data["bytes"]

                # Abort previous pipeline run
                if current_thread and current_thread.is_alive():
                    logger.info("[Agent WS] Aborting previous pipeline")
                    pipeline.abort()
                    current_thread.join(timeout=3)

                # Drain leftover queue items
                if audio_q is not None:
                    while not audio_q.empty():
                        try:
                            audio_q.get_nowait()
                        except queue.Empty:
                            break

                # Fresh queue
                audio_q = queue.Queue()

                def run_agent():
                    try:
                        pipeline.process(audio_bytes, audio_q)
                    except Exception as e:
                        logger.error(f"[Agent Pipeline Error] {e}")
                        traceback.print_exc()
                        audio_q.put(None)

                current_thread = threading.Thread(target=run_agent, daemon=True)
                current_thread.start()

                # Notify client that Samantha is responding
                await ws.send_text(json.dumps({"type": "speaking"}))

                # Stream responses: audio chunks (bytes) and tool calls (dicts)
                loop = asyncio.get_event_loop()
                while True:
                    item = await loop.run_in_executor(None, audio_q.get)
                    if item is None:
                        break
                    if isinstance(item, dict):
                        # Tool call — send as JSON
                        await ws.send_text(json.dumps(item))
                    elif isinstance(item, bytes):
                        # Audio chunk — send as binary
                        await ws.send_bytes(item)

                await ws.send_text(json.dumps({"type": "done"}))

            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "reset":
                    pipeline.reset()
                elif msg.get("type") == "interrupt":
                    if current_thread and current_thread.is_alive():
                        pipeline.abort()

    except WebSocketDisconnect:
        logger.info("[Agent WS] Samantha client disconnected")
        pipeline.abort()
    except RuntimeError as e:
        if "disconnect" in str(e).lower():
            logger.info("[Agent WS] Client already disconnected")
        else:
            logger.error(f"[Agent WS] Runtime error: {e}")
            traceback.print_exc()
        pipeline.abort()
    except Exception as e:
        logger.error(f"[Agent WS] Error: {e}")
        traceback.print_exc()
        pipeline.abort()
