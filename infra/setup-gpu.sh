#!/bin/bash
# BlessVoice GPU Setup Script
# Run this ONCE on the GPU instance after first boot:
#   ssh -i D:/BlessVoice/infra/blessvoice-key.pem ubuntu@52.66.45.156
#   chmod +x /tmp/setup-gpu.sh && sudo /tmp/setup-gpu.sh

set -e
export DEBIAN_FRONTEND=noninteractive

LOG=/var/log/blessvoice-setup.log
exec > >(tee -a $LOG) 2>&1
echo "=== BlessVoice GPU Setup: $(date) ==="

# ─── 1. System update ───────────────────────────────────────────────────────
echo "[1/8] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    curl wget git htop nvtop \
    build-essential libssl-dev \
    software-properties-common \
    rsync unzip jq

# ─── 2. Verify NVIDIA drivers ────────────────────────────────────────────────
echo "[2/8] Verifying NVIDIA drivers..."
if nvidia-smi > /dev/null 2>&1; then
    echo "NVIDIA driver OK:"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
else
    echo "WARNING: nvidia-smi failed — drivers may not be ready yet. Check after reboot."
fi

# ─── 3. Python 3.12 ──────────────────────────────────────────────────────────
echo "[3/8] Installing Python 3.12..."
if ! python3.12 --version > /dev/null 2>&1; then
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y -qq python3.12 python3.12-dev python3.12-venv
    # Note: python3.12-distutils does not exist in Ubuntu 22.04 deadsnakes PPA
    # distutils is bundled into python3.12 itself for versions >= 3.12
fi
# Install pip for 3.12
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
python3.12 --version
echo "Python 3.12 installed."

# ─── 4. System Python aliases ────────────────────────────────────────────────
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
echo "python3 -> python3.12"

# ─── 5. Pip packages ─────────────────────────────────────────────────────────
echo "[4/8] Installing pip packages (this may take 10-20 min for torch+vllm)..."
python3.12 -m pip install --upgrade pip setuptools wheel

# PyTorch with CUDA 12.1 (matches A10G on Deep Learning AMI)
python3.12 -m pip install \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

# Core serving stack
python3.12 -m pip install \
    fastapi \
    "uvicorn[standard]" \
    websockets \
    numpy \
    scipy \
    soundfile \
    librosa

# vLLM for Llama 8B serving
echo "Installing vLLM (large package, may take 5-10 min)..."
python3.12 -m pip install vllm

echo "All pip packages installed."

# ─── 6. Verify GPU accessible from Python ────────────────────────────────────
echo "[5/8] Verifying PyTorch GPU access..."
python3.12 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
" || echo "WARNING: PyTorch GPU check failed — may need reboot."

# ─── 7. Create /opt/blessvoice directory ─────────────────────────────────────
echo "[6/8] Setting up /opt/blessvoice..."
mkdir -p /opt/blessvoice
mkdir -p /opt/blessvoice/models
mkdir -p /opt/blessvoice/logs
chown -R ubuntu:ubuntu /opt/blessvoice
echo "Directory created: /opt/blessvoice"

# ─── 8. Systemd service ──────────────────────────────────────────────────────
echo "[7/8] Creating BlessVoice systemd service..."
cat > /etc/systemd/system/blessvoice.service << 'SERVICE_EOF'
[Unit]
Description=BlessVoice AI Voice Platform
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/blessvoice
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/blessvoice"
ExecStart=/usr/bin/python3.12 /opt/blessvoice/run.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/opt/blessvoice/logs/blessvoice.log
StandardError=append:/opt/blessvoice/logs/blessvoice.log

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable blessvoice
echo "Systemd service created and enabled."

# ─── 9. Auto-stop cron (safety net: stop after 4 hours idle) ─────────────────
echo "[8/8] Setting up auto-stop cron job..."
cat > /usr/local/bin/blessvoice-auto-stop.sh << 'AUTOSTOP_EOF'
#!/bin/bash
# Auto-stop BlessVoice instance after 4 hours of no WebSocket connections
# Runs every 15 minutes via cron

IDLE_FILE="/tmp/blessvoice-last-activity"
IDLE_HOURS=4
IDLE_SECONDS=$((IDLE_HOURS * 3600))

# Check if any WebSocket connections active on port 8000
WS_CONNECTIONS=$(ss -tn state established '( dport = :8000 or sport = :8000 )' | wc -l)

if [ "$WS_CONNECTIONS" -gt 0 ]; then
    # Active connections — update last activity timestamp
    date +%s > "$IDLE_FILE"
    exit 0
fi

# No active connections — check idle duration
if [ ! -f "$IDLE_FILE" ]; then
    date +%s > "$IDLE_FILE"
    exit 0
fi

LAST_ACTIVITY=$(cat "$IDLE_FILE")
NOW=$(date +%s)
IDLE_DURATION=$((NOW - LAST_ACTIVITY))

if [ "$IDLE_DURATION" -gt "$IDLE_SECONDS" ]; then
    echo "$(date): No activity for ${IDLE_HOURS}h — auto-stopping instance" \
        >> /var/log/blessvoice-auto-stop.log
    # Use instance metadata to get instance ID, then stop via AWS CLI
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
    aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --region "$REGION" 2>&1 \
        >> /var/log/blessvoice-auto-stop.log
fi
AUTOSTOP_EOF

chmod +x /usr/local/bin/blessvoice-auto-stop.sh

# Add cron job — check every 15 minutes
(crontab -l 2>/dev/null; echo "*/15 * * * * /usr/local/bin/blessvoice-auto-stop.sh") | crontab -

echo "Auto-stop cron configured (checks every 15 minutes, stops after 4h idle)."

# ─── Install AWS CLI for auto-stop script ─────────────────────────────────────
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    curl -sS "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
    unzip -q /tmp/awscliv2.zip -d /tmp/
    /tmp/aws/install
    rm -rf /tmp/awscliv2.zip /tmp/aws/
    echo "AWS CLI installed: $(aws --version)"
fi

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "=== BlessVoice GPU Setup Complete: $(date) ==="
echo ""
echo "Next steps:"
echo "  1. Copy code:  rsync -av -e 'ssh -i blessvoice-key.pem' D:/BlessVoice/ ubuntu@52.66.45.156:/opt/blessvoice/"
echo "  2. Start svc:  sudo systemctl start blessvoice"
echo "  3. View logs:  tail -f /opt/blessvoice/logs/blessvoice.log"
echo "  4. GPU check:  nvidia-smi"
echo ""
nvidia-smi 2>/dev/null || echo "(Run nvidia-smi manually to verify GPU)"
