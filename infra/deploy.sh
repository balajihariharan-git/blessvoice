#!/bin/bash
# BlessVoice Deploy Script
# Run FROM your laptop to sync code and restart the service on the GPU instance.
#
# Usage:
#   ./infra/deploy.sh
#   ./infra/deploy.sh --no-restart     (sync code only, skip service restart)

set -e

INSTANCE_IP="52.66.45.156"
KEY_PATH="$(dirname "$0")/blessvoice-key.pem"
REMOTE_USER="ubuntu"
REMOTE_DIR="/opt/blessvoice"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Parse args
NO_RESTART=false
for arg in "$@"; do
    case $arg in
        --no-restart) NO_RESTART=true ;;
    esac
done

echo "=== BlessVoice Deploy ==="
echo "Target:    ${REMOTE_USER}@${INSTANCE_IP}:${REMOTE_DIR}"
echo "Source:    ${LOCAL_DIR}"
echo "Restart:   $([[ $NO_RESTART == true ]] && echo 'no' || echo 'yes')"
echo ""

# Verify SSH key exists
if [ ! -f "$KEY_PATH" ]; then
    echo "ERROR: SSH key not found at $KEY_PATH"
    exit 1
fi
chmod 600 "$KEY_PATH"

# Check instance is reachable
echo "[1/3] Checking instance connectivity..."
if ! ssh -i "$KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
    "${REMOTE_USER}@${INSTANCE_IP}" "echo OK" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to ${INSTANCE_IP}"
    echo "  Is the instance running? Check: aws ec2 describe-instances --instance-ids i-083b43fdf32a23483 --region ap-south-1 --query 'Reservations[0].Instances[0].State.Name' --output text"
    exit 1
fi
echo "  Connected."

# Sync code (exclude heavy/generated files)
echo "[2/3] Syncing code to GPU instance..."
rsync -av --progress \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.git/' \
    --exclude='models/' \
    --exclude='infra/' \
    --exclude='.venv/' \
    --exclude='venv/' \
    --exclude='*.log' \
    --exclude='data/' \
    --exclude='recordings/' \
    --exclude='adapters/' \
    --exclude='.env' \
    -e "ssh -i ${KEY_PATH} -o StrictHostKeyChecking=accept-new" \
    "${LOCAL_DIR}/" \
    "${REMOTE_USER}@${INSTANCE_IP}:${REMOTE_DIR}/"

echo "  Sync complete."

# Restart service
if [ "$NO_RESTART" = false ]; then
    echo "[3/3] Restarting BlessVoice service..."
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=accept-new \
        "${REMOTE_USER}@${INSTANCE_IP}" \
        "sudo systemctl restart blessvoice && sleep 2 && sudo systemctl status blessvoice --no-pager -l"
    echo ""
    echo "=== Deploy complete. Logs: ==="
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=accept-new \
        "${REMOTE_USER}@${INSTANCE_IP}" \
        "tail -20 ${REMOTE_DIR}/logs/blessvoice.log 2>/dev/null || echo '(no logs yet)'"
else
    echo "[3/3] Skipping restart (--no-restart)."
fi

echo ""
echo "=== Done ==="
echo "  App URL: http://${INSTANCE_IP}:8000"
echo "  SSH:     ssh -i ${KEY_PATH} ${REMOTE_USER}@${INSTANCE_IP}"
