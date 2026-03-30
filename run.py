"""BlessVoice — Entry point."""

import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    print(r"""
    ____  __                _    __      _
   / __ )/ /__  _________ | |  / /___  (_)________
  / __  / / _ \/ ___/ ___/| | / / __ \/ / ___/ _ \
 / /_/ / /  __(__  |__  ) | |/ / /_/ / / /__/  __/
/_____/_/\___/____/____/  |___/\____/_/\___/\___/

    Real-time AI Voice Assistant (Prototype)
    """)

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
