#!/bin/bash
# BlessVoice GPU Start Script
# Starts the GPU instance and waits until SSH is ready.
#
# Usage: ./infra/gpu-start.sh

set -e

INSTANCE_ID="i-083b43fdf32a23483"
REGION="ap-south-1"
KEY_PATH="$(dirname "$0")/blessvoice-key.pem"
REMOTE_USER="ubuntu"

echo "=== BlessVoice GPU Start ==="
echo "Instance: ${INSTANCE_ID} (${REGION})"

# Check current state
CURRENT_STATE=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" --profile claude-code-ops \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text 2>&1)

echo "Current state: ${CURRENT_STATE}"

if [ "$CURRENT_STATE" = "running" ]; then
    echo "Instance is already running."
elif [ "$CURRENT_STATE" = "stopping" ]; then
    echo "Instance is stopping — waiting for it to stop first..."
    aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID" --region "$REGION" --profile claude-code-ops
    echo "Stopped. Starting now..."
    aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$REGION" --profile claude-code-ops --output text > /dev/null
elif [ "$CURRENT_STATE" = "stopped" ]; then
    echo "Starting instance..."
    aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$REGION" --profile claude-code-ops --output text > /dev/null
else
    echo "ERROR: Unexpected state: ${CURRENT_STATE}"
    echo "Check in AWS console."
    exit 1
fi

# Wait for running state
echo "Waiting for instance to reach running state..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION" --profile claude-code-ops
echo "Instance is running."

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" --profile claude-code-ops \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "Public IP: ${PUBLIC_IP}"

# Wait for SSH to be ready (max 3 minutes)
echo "Waiting for SSH to be ready..."
chmod 600 "$KEY_PATH"
MAX_WAIT=180
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if ssh -i "$KEY_PATH" \
        -o ConnectTimeout=5 \
        -o StrictHostKeyChecking=accept-new \
        -o BatchMode=yes \
        "${REMOTE_USER}@${PUBLIC_IP}" "echo ready" > /dev/null 2>&1; then
        echo "SSH ready."
        break
    fi
    printf "  ...%ds elapsed\r" $ELAPSED
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "WARNING: SSH not ready after ${MAX_WAIT}s. Instance may still be booting."
fi

echo ""
echo "=== Instance Ready ==="
echo "  IP:      ${PUBLIC_IP}"
echo "  SSH:     ssh -i ${KEY_PATH} ${REMOTE_USER}@${PUBLIC_IP}"
echo "  App:     http://${PUBLIC_IP}:8000"
echo "  STOP IT when done: ./infra/gpu-stop.sh"
echo ""

# Show GPU status if accessible
ssh -i "$KEY_PATH" \
    -o ConnectTimeout=10 \
    -o StrictHostKeyChecking=accept-new \
    "${REMOTE_USER}@${PUBLIC_IP}" \
    "nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo '(NVIDIA driver loading...)'"\
    2>/dev/null || true
