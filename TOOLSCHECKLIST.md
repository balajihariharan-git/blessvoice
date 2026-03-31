# BlessVoice — Complete Tools, Programs & Infrastructure Checklist

> **Last Updated**: 2026-03-30
> **Purpose**: Granular record of EVERY tool, component, sub-component, service, and dependency — nothing omitted

---

## 1. Infrastructure — Cloud

| Tool | Version/Detail | Purpose | Type | Cost | Status |
|------|---------------|---------|------|------|--------|
| **AWS EC2 g5.xlarge** | 4 vCPU, 16GB RAM, 1x A10G GPU | GPU compute server | Cloud VM | ~$1/hr on-demand | RUNNING |
| **AWS Elastic IP** | 52.66.45.156 (eipalloc-030dbefe1069c36a3) | Fixed public IP — persists across stop/start | Static IP | ~$3.65/mo unattached | ALLOCATED + ASSOCIATED |
| **AWS Route53** | Hosted zone Z085391579K6ZRTOZ31X | DNS management for balajihariharan.com | DNS | ~$0.50/mo | CONFIGURED |
| **AWS Route53 A Record** | voice.balajihariharan.com → 52.66.45.156 | Maps domain to GPU server | DNS Record | Included | LIVE |
| **AWS EBS Volume** | vol-060047936d47c139c, 200 GB gp3, 3000 IOPS | Persistent disk for OS + models + code | Block Storage | ~$16/mo | ATTACHED (resized from 100GB) |
| **AWS Security Group** | sg-0228967984c611fda (blessvoice-gpu-sg) | Firewall rules | Network | $0 | CONFIGURED |
| **SG Rule: SSH** | Port 22, 0.0.0.0/0 | Remote server access | Inbound | $0 | OPEN |
| **SG Rule: WebSocket** | Port 8000, 0.0.0.0/0 | BlessVoice app traffic | Inbound | $0 | OPEN |
| **SG Rule: HTTPS** | Port 443, 0.0.0.0/0 | Future SSL/TLS | Inbound | $0 | OPEN |

## 2. Infrastructure — Server OS

| Tool | Version | Purpose | License | Cost | Status |
|------|---------|---------|---------|------|--------|
| **Ubuntu** | 22.04 LTS | Operating system | Free (Canonical) | $0 | INSTALLED |
| **AWS Deep Learning AMI** | ami-090370b5ecd80cd10 (2026-03-27) | Pre-configured ML environment | AWS | $0 | BASE IMAGE |
| **Linux Kernel** | 6.8.0-1050-aws | OS kernel | GPL | $0 | RUNNING |
| **systemd** | System service manager | Manages BlessVoice as a service | LGPL | $0 | CONFIGURED |
| **SSH (OpenSSH)** | Server | Remote access to GPU instance | BSD | $0 | RUNNING |
| **screen** | Terminal multiplexer | Keep processes alive after SSH disconnect | GPL | $0 | USED |
| **Swap File** | 32 GB (/swapfile) | Extends virtual memory for model loading | N/A | $0 | ENABLED |

## 3. GPU / CUDA Stack

| Component | Version | Purpose | Provider | License | Cost | Status |
|-----------|---------|---------|----------|---------|------|--------|
| **NVIDIA A10G** | Hardware (Ampere) | GPU with 24GB GDDR6X VRAM | NVIDIA (in AWS) | Included | Included in g5.xlarge | VERIFIED |
| **NVIDIA Driver** | 580.126.09 | Communicates between OS and GPU hardware | NVIDIA | Proprietary (free) | $0 | INSTALLED |
| **CUDA Toolkit** | 12.1 | GPU parallel computing framework | NVIDIA | Proprietary (free) | $0 | INSTALLED |
| **cuDNN** | Included in AMI | Deep neural network GPU acceleration | NVIDIA | Proprietary (free) | $0 | INSTALLED |
| **PyTorch** | 2.5.1+cu121 | ML framework — loads models, runs inference on GPU | Meta (Facebook) | BSD | $0 | INSTALLED |
| **torchaudio** | 2.5.1 | Audio processing operations for PyTorch | Meta (Facebook) | BSD | $0 | INSTALLED |

## 4. AI Models — PersonaPlex (Voice)

### 4a. PersonaPlex — High Level

| Field | Value |
|-------|-------|
| **Full Name** | PersonaPlex-7B-v1 |
| **Created By** | NVIDIA |
| **Built On** | Moshi architecture (Kyutai Labs) |
| **Released** | January 20, 2026 |
| **Parameters** | 7 billion |
| **Size on Disk** | ~16 GB (fp16 safetensors) |
| **VRAM Usage** | ~14 GB (fp16 loaded on GPU) |
| **License** | CC-BY 4.0 (free commercial use, attribution required) |
| **HuggingFace** | nvidia/personaplex-7b-v1 (gated, accepted) |
| **Purpose** | Full-duplex voice-to-voice conversation |
| **Key Feature** | 100% interrupt handling (vs Moshi's 60.6%) |
| **Latency** | ~200ms on A10G GPU |
| **Turn Switching** | 0.07 seconds |
| **Languages** | English only |
| **Voices** | 2 built-in (Moshiko male, Moshika female) + voice cloning |

### 4b. PersonaPlex — Internal Sub-Components

PersonaPlex is NOT a single model. It contains these internal components that work together:

| Sub-Component | Parameters | Purpose | How It Works |
|---------------|-----------|---------|-------------|
| **Mimi Codec (Encoder)** | ~50M | Converts incoming audio waveform into audio tokens | Neural audio codec. Takes raw audio (24kHz) and compresses it into discrete tokens at 12.5 Hz using 8 codebook streams (RVQ — Residual Vector Quantization). First codebook captures semantic meaning, remaining codebooks capture acoustic details (pitch, tone, emotion). |
| **Mimi Codec (Decoder)** | ~50M | Converts audio tokens back into audio waveform | Reverses the encoding. Takes predicted audio tokens and reconstructs the waveform with emotion, prosody, and natural pacing preserved. |
| **Helium Temporal Transformer** | ~7B | The "brain" — processes conversation context over time | Main language model. Processes BOTH the user's audio tokens AND PersonaPlex's own previous audio tokens simultaneously (dual-stream). Predicts what audio token should come next. This is where conversation understanding, turn-taking, and personality live. |
| **Depth Transformer** | ~300M | Handles multi-codebook prediction at each time step | Smaller model that predicts across the 8 codebook streams at each frame. Ensures consistency between semantic and acoustic layers. |
| **Inner Monologue** | Text channel | Internal text representation alongside speech | PersonaPlex generates text tokens corresponding to its own speech. Used for: transcription, knowledge injection from external LLM, and improving generation quality. |
| **Tokenizer (SentencePiece)** | 32K vocab | Text tokenization for inner monologue | SPM tokenizer with 32,000 token vocabulary. File: tokenizer_spm_32k_3.model |

### 4c. PersonaPlex — Downloaded Files

| File | Size | Contents |
|------|------|----------|
| model.safetensors | ~15.6 GB | Helium Temporal Transformer + Depth Transformer weights (fp16) |
| tokenizer-e351c8d8-checkpoint125.safetensors | ~200 MB | Mimi Codec encoder + decoder weights |
| tokenizer_spm_32k_3.model | ~1 MB | SentencePiece text tokenizer vocabulary |
| config.json | <1 KB | Model type and version metadata |
| dist.tgz | ~50 MB | Distribution package (serving utilities) |
| voices.tgz | ~20 MB | Pre-built voice embeddings (Moshiko, Moshika) |

### 4d. PersonaPlex — Audio Pipeline Flow

```
User speaks into microphone
    │
    ▼ Raw audio (16kHz PCM, mono)
    │
    ▼ [Browser WebSocket] ────────────────────── Network
    │
    ▼ Raw audio arrives at GPU server
    │
    ▼ ┌─────────────────────────────┐
      │  MIMI ENCODER               │
      │  Audio waveform → tokens    │
      │  24kHz → 12.5 Hz tokens    │
      │  8 codebook streams (RVQ)   │
      │  Frame size: 80ms           │
      │  Bandwidth: 1.1 kbps        │
      └──────────┬──────────────────┘
                 │ Audio tokens (12.5 per second)
                 ▼
      ┌─────────────────────────────┐
      │  HELIUM TEMPORAL TRANSFORMER│
      │  (7B parameters)            │
      │                             │
      │  Input: User audio tokens   │
      │       + Own previous tokens │
      │  (dual-stream, full-duplex) │
      │                             │
      │  Generates:                 │
      │  - Next audio token         │
      │  - Inner monologue text     │
      │                             │
      │  Understands:               │
      │  - Tone, emotion, sarcasm   │
      │  - When to speak/listen     │
      │  - Conversation context     │
      └──────────┬──────────────────┘
                 │ Predicted audio tokens
                 ▼
      ┌─────────────────────────────┐
      │  DEPTH TRANSFORMER          │
      │  (~300M parameters)         │
      │                             │
      │  Predicts across all 8      │
      │  codebook layers for each   │
      │  time step                  │
      └──────────┬──────────────────┘
                 │ Complete multi-codebook tokens
                 ▼
      ┌─────────────────────────────┐
      │  MIMI DECODER               │
      │  Tokens → audio waveform   │
      │  12.5 Hz → 24kHz audio     │
      │  Preserves emotion, prosody│
      └──────────┬──────────────────┘
                 │ Audio waveform (24kHz PCM)
                 ▼
    [GPU WebSocket] ──────────────────────── Network
    │
    ▼ Browser plays audio through speakers
```

## 5. AI Models — Llama (Intelligence Brain)

| Field | Value |
|-------|-------|
| **Full Name** | Meta-Llama-3.1-8B-Instruct |
| **Created By** | Meta (Facebook) |
| **Parameters** | 8 billion |
| **Quantization** | Q4_K_M (4-bit quantized GGUF) |
| **Size on Disk** | 4.6 GB |
| **RAM Usage** | ~6 GB (runs on CPU, not GPU) |
| **License** | Llama 3.1 Community License (free under 700M monthly users) |
| **HuggingFace** | bartowski/Meta-Llama-3.1-8B-Instruct-GGUF |
| **Purpose** | Provides factual knowledge and reasoning — the "brain" |
| **Inference** | CPU via llama-cpp-python (~20 tokens/sec) |
| **Context Window** | 8,192 tokens |
| **Why CPU?** | PersonaPlex uses all 24GB VRAM. Llama runs on the 16GB system RAM. |

## 6. AI Models — Evaluated But Not Used

| Model | By | Why Evaluated | Why Not Used | License |
|-------|-----|--------------|-------------|---------|
| **Moshi 7B** | Kyutai Labs | Original voice-to-voice model | PersonaPlex is improved version of Moshi | CC-BY 4.0 |
| **CSM** | Sesame/Meta | Best voice quality | No full-duplex (can't interrupt) | Apache 2.0 |
| **GLM-4-Voice** | Tsinghua University | Chinese + English support | Less mature, smaller community | Apache 2.0 |
| **Mini-Omni 2** | GAIR | End-to-end voice | Lower quality than PersonaPlex | MIT |
| **Hertz-Dev** | Standard AI | Conversational audio | Less tested | Apache 2.0 |
| **Ultravox** | Fixie AI | Audio understanding | TTS still needed separately | Apache 2.0 |
| **Spirit LM / Tribe** | Meta | Multimodal speech model | Research license, not production-ready | Research only |
| **Phi-3 mini 3.8B** | Microsoft | Tested as local LLM | Too slow on CPU (25-35s per response) | MIT |
| **Llama 3.2 1B** | Meta | Tested as local LLM | Too dumb (loops, garbage output) | Community |
| **Llama 3.2 3B** | Meta | Tested as local LLM | OK quality but 15s per response on CPU | Community |
| **Silero TTS v3** | Silero | Tested as local TTS | Robotic voice, 2-3s per sentence | Apache 2.0 |
| **GPT4All (various)** | Nomic AI | Tested as local LLM runtime | Needed for CPU; replaced by cloud APIs | MIT |
| **Qwen 2.5 72B** | Alibaba | Considered for MLLM | Future — multi-LLM router concept | Apache 2.0 |
| **DeepSeek R1** | DeepSeek | Considered for MLLM | Future — best at reasoning | MIT |
| **Mistral Large** | Mistral AI | Considered for MLLM | Future — best for European languages | Apache 2.0 |

## 7. Serving Framework

| Component | Tool | Purpose | Detail |
|-----------|------|---------|--------|
| **PersonaPlex Server** | moshi Python package (v0.2.13) | Loads and serves PersonaPlex model | Runs as `python3 -m moshi.server` on port 8998. Handles audio WebSocket connections, Mimi encoding/decoding, transformer inference. This is the Kyutai-built serving framework that NVIDIA's PersonaPlex runs on top of. |
| **Llama Server** | llama-cpp-python | Loads and serves Llama 8B | C++ inference engine with Python bindings. Runs Llama GGUF on CPU with ~20 tokens/sec. |
| **BlessVoice Server** | FastAPI + Uvicorn | WebSocket bridge between browser and models | Receives browser audio, routes to PersonaPlex, streams audio back. Also routes knowledge queries to Llama. |

## 8. Backend — Python Packages (Complete)

| Package | Version | Purpose | Provider | License | Cost | Status |
|---------|---------|---------|----------|---------|------|--------|
| **Python** | 3.12.13 (laptop), 3.10 (GPU server) | Programming language | Python.org | PSF | $0 | INSTALLED |
| **moshi** | 0.2.13 | PersonaPlex serving framework | Kyutai Labs | MIT | $0 | INSTALLED (GPU) |
| **llama-cpp-python** | latest | Llama GGUF inference on CPU | Andrei Betlen | MIT | $0 | INSTALLED (GPU) |
| **fastapi** | 0.135.2 | Async web framework + WebSocket | Sebastián Ramírez | MIT | $0 | INSTALLED |
| **uvicorn** | latest | ASGI server (runs FastAPI) | Encode | BSD | $0 | INSTALLED |
| **websockets** | latest | WebSocket protocol implementation | Aymeric Augustin | BSD | $0 | INSTALLED |
| **numpy** | latest | Numerical array operations | NumPy | BSD | $0 | INSTALLED |
| **huggingface_hub** | 0.36.2 | Download models from HuggingFace | Hugging Face | Apache 2.0 | $0 | INSTALLED |
| **safetensors** | 0.7.0 | Safe, fast model weight file loading | Hugging Face | Apache 2.0 | $0 | INSTALLED |
| **sentencepiece** | 0.2.1 | Text tokenizer (SentencePiece model) | Google | Apache 2.0 | $0 | INSTALLED |
| **aiohttp** | 3.11.18 | Async HTTP client (dependency of moshi) | aiohttp | Apache 2.0 | $0 | INSTALLED |
| **einops** | 0.8.2 | Tensor operations (dependency of moshi) | Alex Rogozhnikov | MIT | $0 | INSTALLED |
| **bitsandbytes** | 0.49.2 | Quantization support | Tim Dettmers | MIT | $0 | INSTALLED |
| **sphn** | 0.2.1 | Audio processing for Moshi | Kyutai Labs | MIT | $0 | INSTALLED |
| **sounddevice** | 0.5.0 | Audio I/O (dependency of moshi) | Matthias Geier | MIT | $0 | INSTALLED |
| **openai** | latest | Phase 1 CPU pipeline (STT/LLM/TTS APIs) | OpenAI | MIT | API costs | INSTALLED (laptop only) |

## 9. Frontend — Browser Technologies

| Technology | API/Standard | Purpose | Detail |
|-----------|-------------|---------|--------|
| **HTML5** | W3C Standard | Page structure | Single-page app: orb UI, no framework |
| **CSS3** | W3C Standard | Styling + animations | Orb pulse/breathe animations, dark theme, responsive |
| **JavaScript ES6+** | ECMA Standard | Client-side logic | VAD, WebSocket, audio processing, state management |
| **Web Audio API** | AudioContext, ScriptProcessorNode | Microphone capture + audio playback | Captures mic at 16kHz mono, plays back PCM at 24kHz |
| **WebSocket API** | Browser built-in | Real-time bidirectional audio streaming | Binary (PCM audio) + JSON (control messages) |
| **MediaDevices API** | navigator.mediaDevices.getUserMedia | Microphone access | Requests mic permission, configures echo cancellation + noise suppression |
| **AudioContext** | Playback scheduling | Seamless audio chunk playback | Schedules PCM chunks with precise nextPlayTime for gap-free audio |

### Frontend Audio Format

| Direction | Format | Sample Rate | Bit Depth | Channels |
|-----------|--------|-------------|-----------|----------|
| Browser → Server | Float32 PCM | 16,000 Hz | 32-bit float | Mono |
| Server → Browser | Int16 PCM | 24,000 Hz | 16-bit signed | Mono |

### Frontend VAD (Voice Activity Detection)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Silence threshold | 0.012 | Audio level below this = silence |
| Silence duration | 800 ms | Duration of silence before sending audio |
| Min speech duration | 300 ms | Ignore sounds shorter than this |
| Buffer size | 2048 samples | ScriptProcessorNode buffer (128ms at 16kHz) |
| Echo cancellation | Enabled | Browser built-in |
| Noise suppression | Enabled | Browser built-in |
| Auto gain control | Enabled | Browser built-in |

## 10. DNS & Networking

| Component | Value | Purpose | Status |
|-----------|-------|---------|--------|
| **Domain** | voice.balajihariharan.com | Public URL for BlessVoice | LIVE |
| **Parent Domain** | balajihariharan.com | Hosted in Route53 | ACTIVE |
| **Elastic IP** | 52.66.45.156 | Fixed IP | ASSOCIATED |
| **EIP Allocation** | eipalloc-030dbefe1069c36a3 | AWS resource ID | ALLOCATED |
| **EIP Association** | eipassoc-069aaa443fad89225 | Links EIP to instance | ACTIVE |
| **Route53 Record Type** | A Record | IPv4 address mapping | LIVE |
| **Route53 TTL** | 300 seconds | DNS cache duration | SET |
| **Security Group** | sg-0228967984c611fda | Firewall rules | CONFIGURED |
| **Port 22** | SSH | Server management | OPEN |
| **Port 8000** | HTTP/WebSocket | BlessVoice application | OPEN |
| **Port 443** | HTTPS | Future SSL/TLS | OPEN |
| **Port 8998** | Internal | PersonaPlex model server (localhost only) | INTERNAL |
| **Protocol: Browser↔Server** | WebSocket (ws://) | Real-time audio streaming | IMPLEMENTED |
| **Protocol: Server↔PersonaPlex** | WebSocket (ws://localhost:8998) | Internal model communication | IMPLEMENTED |

## 11. Development Tools

| Tool | Version | Purpose | License | Cost | Status |
|------|---------|---------|---------|------|--------|
| **Git** | latest | Version control | GPL v2 | $0 | USED |
| **GitHub** | github.com | Code hosting + issue tracking | Free tier | $0 | REPO LIVE |
| **GitHub CLI (gh)** | latest | Issue creation, repo management | MIT | $0 | USED |
| **AWS CLI v2** | latest | Cloud infrastructure management | Apache 2.0 | $0 | CONFIGURED |
| **SSH** | OpenSSH | GPU server access | BSD | $0 | CONFIGURED |
| **SCP** | OpenSSH | File transfer to GPU | BSD | $0 | USED |
| **screen** | latest | Terminal multiplexer on GPU | GPL | $0 | USED |
| **Claude Code CLI** | Opus 4.6 (1M context) | AI-assisted development | Anthropic Max | $200/mo | ACTIVE |
| **rsync** | latest | Code deployment to GPU | GPL | $0 | USED |
| **curl** | latest | HTTP testing | MIT | $0 | USED |
| **nslookup** | latest | DNS verification | ISC | $0 | USED |

## 12. AWS Profiles & IAM

| Profile | IAM User | Permissions | Used For |
|---------|---------|------------|---------|
| **default (cicd)** | arn:aws:iam::476887127594:user/cicd | EC2 describe, RunInstances, security groups | Read operations, initial instance launch |
| **claude-code-ops** | (admin-level) | EC2 full, Route53, Elastic IP, all write | Start/stop GPU, DNS, EIP, resize volumes |
| **claude-code-readonly** | (read-only) | Read only across services | Monitoring |

### IAM Permission Map (cicd user)

| Permission | Status |
|-----------|--------|
| ec2:RunInstances | GRANTED |
| ec2:DescribeInstances | GRANTED |
| ec2:CreateSecurityGroup | GRANTED |
| ec2:AuthorizeSecurityGroupIngress | GRANTED |
| ec2:StartInstances | BLOCKED (use claude-code-ops) |
| ec2:StopInstances | BLOCKED (use claude-code-ops) |
| ec2:AllocateAddress | BLOCKED (use claude-code-ops) |
| ec2:CreateKeyPair | BLOCKED (workaround: ssh-keygen local) |
| ec2:CreateTags | BLOCKED (use console or claude-code-ops) |
| route53:* | BLOCKED (use claude-code-ops) |

## 13. Accounts & Authentication

| Service | Account/Identity | Purpose | Auth Method | Cost |
|---------|-----------------|---------|-------------|------|
| **AWS** | 476887127594 | GPU infrastructure | IAM access keys | Pay-per-use |
| **GitHub** | balajihariharan-git | Code repo + issues | HTTPS token (gh CLI) | $0 |
| **HuggingFace** | balajihariharan | Model downloads | API token (hf_uFTM...Emmz, Read-only) | $0 |
| **Git (local repo)** | balajihariharan-git / balajihariharan.git@gmail.com | Commits | Local config | $0 |
| **SSH Key** | blessvoice-key.pem (RSA 4096) | GPU server access | Private key file | $0 |

## 14. File Structure

### Local (D:\BlessVoice\)

```
D:\BlessVoice\
├── .git/                    # Git repository
├── .gitignore               # Excludes models, .pem, data, __pycache__
├── CLAUDE.md                # Claude Code agent instructions
├── CONCEPT.md               # Product bible (architecture, decisions, roadmap)
├── GPU_OPS.md               # GPU start/stop commands and cost awareness
├── MLLM_CONCEPT.md          # Multi-LLM router concept (future product)
├── TOOLSCHECKLIST.md         # THIS FILE
├── requirements.txt          # Python dependencies
├── run.py                   # Entry point (--gpu / --cpu / auto-detect)
├── app/
│   ├── __init__.py
│   ├── config.py            # Server config (VAD thresholds, model settings)
│   ├── pipeline.py          # Phase 1: CPU pipeline (OpenAI APIs)
│   ├── gpu_pipeline.py      # Phase 2: GPU pipeline (PersonaPlex + Llama)
│   ├── gpu_config.py        # GPU model paths, VRAM allocation
│   └── main.py              # FastAPI server (auto-detects GPU/CPU mode)
├── web/
│   └── index.html           # Browser UI (orb, VAD, PCM streaming)
├── infra/
│   ├── blessvoice-key.pem   # SSH private key (GITIGNORED)
│   ├── blessvoice-key.pem.pub # SSH public key (GITIGNORED)
│   ├── setup-gpu.sh         # One-time GPU server setup
│   ├── deploy.sh            # Deploy code to GPU via rsync
│   ├── download-models.sh   # Download PersonaPlex + Llama from HuggingFace
│   ├── gpu-start.sh         # Start GPU instance (uses claude-code-ops profile)
│   ├── gpu-stop.sh          # Stop GPU instance
│   └── MODEL_RESEARCH.md    # PersonaPlex availability research findings
└── models/                  # Local models (GITIGNORED, ~20GB)
```

### GPU Server (/opt/blessvoice/)

```
/opt/blessvoice/
├── app/                     # Deployed from local via rsync
├── web/                     # Deployed from local via rsync
├── run.py                   # Deployed from local
├── requirements.txt         # Deployed from local
└── models/
    ├── personaplex-7b-v1/   # ~16 GB
    │   ├── model.safetensors              # 15.6 GB — Helium + Depth Transformer weights
    │   ├── tokenizer-e351c8d8-checkpoint125.safetensors  # ~200 MB — Mimi Codec weights
    │   ├── tokenizer_spm_32k_3.model      # ~1 MB — SentencePiece tokenizer
    │   ├── config.json                    # Model metadata
    │   ├── dist.tgz                       # Serving utilities
    │   └── voices.tgz                     # Voice embeddings (Moshiko, Moshika)
    └── llama-8b/
        └── Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf  # 4.6 GB — Quantized Llama weights
```

## 15. Monthly Cost Summary

| Item | Detail | Cost |
|------|--------|------|
| GPU compute (3 hrs/day, on-demand) | g5.xlarge × $1.006/hr × 3hr × 30d | ~$90/mo |
| GPU compute (3 hrs/day, spot) | g5.xlarge × $0.30/hr × 3hr × 30d | ~$27/mo |
| GPU compute (stopped) | No compute charges | $0/mo |
| EBS storage | 200 GB gp3 × $0.08/GB-month | ~$16/mo |
| Elastic IP (attached to running instance) | No charge when attached | $0 |
| Elastic IP (instance stopped) | $0.005/hr × 24 × 30 | ~$3.65/mo |
| Route53 hosted zone | Per zone | $0.50/mo |
| Route53 queries | Per million queries | ~$0.01/mo |
| All software + models | Open source | **$0** |
| **Total (active dev, spot, 3hrs/day)** | | **~$47/mo** |
| **Total (idle, GPU stopped)** | | **~$20/mo** |
| **Total (production 24/7, on-demand)** | | **~$740/mo** |

## 16. Version History

| Date | Change |
|------|--------|
| 2026-03-28 | Project created. Phase 1 prototype (OpenAI APIs on laptop) |
| 2026-03-30 | Decision: PersonaPlex + Llama hybrid. AWS GPU setup. GitHub repo. 20 issues. |
| 2026-03-30 | EBS resized 100GB → 200GB. Instance type tested g5.2xlarge (no capacity). |
| 2026-03-30 | Swap-based model loading in progress on g5.xlarge. |
