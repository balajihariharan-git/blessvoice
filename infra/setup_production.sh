#!/bin/bash
# BlessVoice Production Setup
# Caddy serves BlessVoice UI on HTTPS (port 443)
# PersonaPlex runs internally on port 8998 (localhost only)
# BlessVoice FastAPI bridges them on port 8000 (localhost only)
set -e

echo "=== Setting up BlessVoice Production ==="

# 1. Ensure code is deployed
if [ ! -f /opt/blessvoice/run.py ]; then
    echo "ERROR: Code not deployed to /opt/blessvoice/"
    exit 1
fi

# 2. Install BlessVoice Python deps
pip3 install --quiet fastapi uvicorn websockets numpy openai 2>/dev/null

# 3. Configure Caddy — serves BlessVoice UI + proxies WebSocket to FastAPI
cat > /tmp/Caddyfile << 'CEOF'
voice.balajihariharan.com {
    # Serve BlessVoice frontend
    root * /opt/blessvoice/web
    file_server

    # Proxy WebSocket to BlessVoice FastAPI server
    handle /ws {
        reverse_proxy 127.0.0.1:8000 {
            flush_interval -1
        }
    }

    # Proxy API calls to FastAPI
    handle /health {
        reverse_proxy 127.0.0.1:8000
    }

    # Proxy PersonaPlex internal API (for voice WebSocket)
    handle /api/* {
        reverse_proxy 127.0.0.1:8998 {
            flush_interval -1
        }
    }
}
CEOF
sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile
sudo systemctl restart caddy
echo "Caddy configured with HTTPS"

# 4. Start BlessVoice FastAPI server
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1
cd /opt/blessvoice
nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/blessvoice.log 2>&1 &
disown
echo "BlessVoice FastAPI started on :8000"

echo "=== Production Setup Complete ==="
echo "Open: https://voice.balajihariharan.com"
