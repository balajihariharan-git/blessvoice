"""BlessVoice Server — Real-time voice-to-voice with streaming pipeline."""

import json
import asyncio
import queue
import threading
import traceback
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.pipeline import VoicePipeline

app = FastAPI(title="BlessVoice")

WEB_DIR = Path(__file__).parent.parent / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    print("\n=== BlessVoice Ready ===")
    print("=== Open http://localhost:8000 ===\n")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("[WS] Client connected")

    pipeline = VoicePipeline()
    current_thread = None

    try:
        while True:
            data = await ws.receive()

            if "bytes" in data:
                audio_bytes = data["bytes"]

                # ALWAYS abort previous pipeline before starting new one
                if current_thread and current_thread.is_alive():
                    print("[WS] Aborting previous pipeline")
                    pipeline.abort()
                    current_thread.join(timeout=3)

                # Drain any leftover chunks from previous queue
                if 'audio_q' in dir():
                    while not audio_q.empty():
                        try: audio_q.get_nowait()
                        except: break

                # Fresh queue for this request
                audio_q = queue.Queue()

                # Run pipeline in background thread
                def run_pipeline():
                    try:
                        pipeline.process(audio_bytes, audio_q)
                    except Exception as e:
                        print(f"[Pipeline Error] {e}")
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
        print("[WS] Client disconnected")
        pipeline.abort()
    except Exception as e:
        print(f"[WS] Error: {e}")
        traceback.print_exc()
