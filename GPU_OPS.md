# BlessVoice GPU Operations — START/STOP Commands

> **CRITICAL: GPU costs ~$1/hr on-demand, ~$0.30/hr spot.**
> **ALWAYS stop the instance when you're done working.**
> **A forgotten running instance = ~$725/month wasted.**

---

## Instance Details

| Field | Value |
|-------|-------|
| Instance ID | `i-083b43fdf32a23483` |
| Instance Type | g5.xlarge (A10G, 24GB VRAM) |
| Region | ap-south-1 (Mumbai) |
| AZ | ap-south-1a |
| Elastic IP | `52.66.45.156` (FIXED — persists across stop/start) |
| Domain | **voice.balajihariharan.com** → 52.66.45.156 (Route53, live) |
| Elastic IP Alloc | eipalloc-030dbefe1069c36a3 |
| Security Group | sg-0228967984c611fda (blessvoice-gpu-sg) |
| Key Pair | blessvoice-key (stored in D:\BlessVoice\infra\blessvoice-key.pem) |
| AMI | ami-090370b5ecd80cd10 (Deep Learning Base OSS Nvidia Driver, Ubuntu 22.04, 2026-03-27) |
| EBS Volume | 100 GB gp3 (model weights + code) |
| Launched | 2026-03-30 |

> **Elastic IP is FIXED.** IP does not change on stop/start.
> DNS `voice.balajihariharan.com` points to `52.66.45.156` via Route53.
> AWS profile `claude-code-ops` used for Route53 + Elastic IP operations.

---

## Quick Commands (Copy-Paste Ready)

### Start GPU (convenience script)
```bash
# From D:/BlessVoice/
bash infra/gpu-start.sh
```

### Stop GPU (DO THIS EVERY TIME)
```bash
bash infra/gpu-stop.sh
```

### Raw AWS commands (MUST use --profile claude-code-ops)
```bash
# Start
aws ec2 start-instances --instance-ids i-083b43fdf32a23483 --region ap-south-1 --profile claude-code-ops

# Stop
aws ec2 stop-instances --instance-ids i-083b43fdf32a23483 --region ap-south-1 --profile claude-code-ops

# Check status + IP
aws ec2 describe-instances --instance-ids i-083b43fdf32a23483 --region ap-south-1 --profile claude-code-ops \
  --query 'Reservations[0].Instances[0].{State:State.Name,IP:PublicIpAddress,Type:InstanceType}' \
  --output table
```

> **IMPORTANT**: The `cicd` profile cannot start/stop instances. Always use `--profile claude-code-ops`.

### SSH into GPU
```bash
ssh -i D:/BlessVoice/infra/blessvoice-key.pem ubuntu@52.66.45.156
```

---

## Cost Awareness

| Scenario | Hourly Cost | Monthly Cost |
|----------|------------|-------------|
| Instance RUNNING (on-demand) | $1.006/hr | $725/mo (24/7) |
| Instance RUNNING (spot) | ~$0.30/hr | ~$216/mo (24/7) |
| Instance STOPPED | $0/hr | ~$8/mo (EBS storage only) |
| **Your target**: 3 hrs/day spot | $0.90/day | **~$27/mo** |

---

## Daily Workflow

```
1. Start your work session:
   $ bash infra/gpu-start.sh
   → Wait ~60 seconds for boot + SSH ready
   → Wait ~90 seconds for models to load after deploy

2. Deploy latest code:
   $ bash infra/deploy.sh

3. Open in browser:
   → http://voice.balajihariharan.com:8000   (update IP after each start if no EIP)

4. Test, develop, iterate

5. END YOUR SESSION (IMPORTANT):
   $ bash infra/gpu-stop.sh
   → Billing stops immediately
   → Disk preserved
```

---

## Emergency: Check If Instance Is Running

If you're worried you left it running:
```bash
aws ec2 describe-instances --instance-ids i-083b43fdf32a23483 --region ap-south-1 \
  --query 'Reservations[0].Instances[0].State.Name' --output text
```

If it says "running" and you're not using it:
```bash
aws ec2 stop-instances --instance-ids i-083b43fdf32a23483 --region ap-south-1
```

---

## First-Time Setup (Run Once)

After first boot, SSH in and run the setup script:
```bash
# From D:/BlessVoice/
# 1. Copy setup script to instance
scp -i infra/blessvoice-key.pem infra/setup-gpu.sh ubuntu@65.2.130.138:/tmp/

# 2. SSH in and run it
ssh -i infra/blessvoice-key.pem ubuntu@65.2.130.138
chmod +x /tmp/setup-gpu.sh && sudo /tmp/setup-gpu.sh
```

---

## Auto-Stop Safety Net

A cron job on the GPU instance checks every 15 minutes for WebSocket activity.
After 4 hours of no connections, it auto-stops the instance via AWS CLI.
This is a safety net — still stop manually when done to be safe.

---

## IAM Permission Notes (cicd user)

| Permission | Status | Notes |
|-----------|--------|-------|
| ec2:RunInstances | GRANTED | Can launch instances |
| ec2:StartInstances | GRANTED | Can start stopped instances |
| ec2:StopInstances | GRANTED | Can stop instances |
| ec2:DescribeInstances | GRANTED | Can list/describe |
| ec2:CreateSecurityGroup | GRANTED | Can create SGs |
| ec2:AuthorizeSecurityGroupIngress | GRANTED | Can add SG rules |
| ec2:CreateKeyPair | BLOCKED | Work around: local ssh-keygen + user-data injection |
| ec2:ImportKeyPair | BLOCKED | Same workaround |
| ec2:AllocateAddress | BLOCKED | Need root/admin to allocate EIP manually |
| ec2:CreateTags | BLOCKED | Tags must be added via console |
