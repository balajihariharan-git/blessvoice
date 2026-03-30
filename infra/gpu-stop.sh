#!/bin/bash
# BlessVoice GPU Stop Script
# Stops the GPU instance immediately. Run this when done working.
#
# Usage: ./infra/gpu-stop.sh

INSTANCE_ID="i-083b43fdf32a23483"
REGION="ap-south-1"

echo "=== BlessVoice GPU Stop ==="
echo "Instance: ${INSTANCE_ID} (${REGION})"

# Check current state
CURRENT_STATE=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" --profile claude-code-ops \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text 2>&1)

echo "Current state: ${CURRENT_STATE}"

if [ "$CURRENT_STATE" = "stopped" ]; then
    echo "Instance is already stopped. No action needed."
    echo "EBS storage cost: ~$0.80/day (100GB gp3)"
    exit 0
elif [ "$CURRENT_STATE" = "running" ]; then
    echo "Stopping instance..."
    aws ec2 stop-instances \
        --instance-ids "$INSTANCE_ID" \
        --region "$REGION" --profile claude-code-ops \
        --output text > /dev/null
    echo "Stop initiated. Billing stops within seconds."
elif [ "$CURRENT_STATE" = "stopping" ]; then
    echo "Instance is already stopping."
else
    echo "WARNING: Unexpected state: ${CURRENT_STATE}"
    echo "Check in AWS console: https://ap-south-1.console.aws.amazon.com/ec2/home?region=ap-south-1#Instances:"
    exit 1
fi

# Wait for stopped confirmation
echo "Waiting for stopped state..."
aws ec2 wait instance-stopped \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" --profile claude-code-ops

echo ""
echo "=== Instance Stopped ==="
echo "  On-demand billing: $0.00/hr (stopped)"
echo "  EBS storage only: ~$0.80/day (100GB gp3 @ $0.096/GB-month)"
echo ""
echo "  To start again: ./infra/gpu-start.sh"
