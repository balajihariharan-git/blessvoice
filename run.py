"""BlessVoice — Entry point.

Usage:
    python run.py          # Auto-detect mode (GPU if available, else CPU)
    python run.py --gpu    # Force GPU mode (PersonaPlex + Llama)
    python run.py --cpu    # Force CPU mode (OpenAI APIs)
"""

import argparse
import logging
import os
import sys

import uvicorn
from app.config import HOST, PORT


def main():
    parser = argparse.ArgumentParser(description="BlessVoice — Real-time AI Voice")
    parser.add_argument(
        "--gpu", action="store_true",
        help="Force GPU mode (PersonaPlex + Llama on local GPU)"
    )
    parser.add_argument(
        "--cpu", action="store_true",
        help="Force CPU mode (OpenAI APIs)"
    )
    parser.add_argument(
        "--log-level", default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level (default: info)"
    )
    args = parser.parse_args()

    # Set mode via environment variable (read by app/main.py)
    if args.gpu:
        os.environ["BLESSVOICE_MODE"] = "gpu"
    elif args.cpu:
        os.environ["BLESSVOICE_MODE"] = "cpu"

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    mode = os.environ.get("BLESSVOICE_MODE", "auto-detect")

    print(r"""
    ____  __                _    __      _
   / __ )/ /__  _________ | |  / /___  (_)________
  / __  / / _ \/ ___/ ___/| | / / __ \/ / ___/ _ \
 / /_/ / /  __(__  |__  ) | |/ / /_/ / / /__/  __/
/_____/_/\___/____/____/  |___/\____/_/\___/\___/

    Real-time AI Voice Assistant
    """)

    if mode == "gpu":
        print("    Mode: GPU (PersonaPlex 7B + Llama 3.1 8B)")
        print("    GPU:  NVIDIA A10G (24GB VRAM)")
    elif mode == "cpu":
        print("    Mode: CPU (OpenAI APIs)")
    else:
        print("    Mode: Auto-detect")

    print()

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
