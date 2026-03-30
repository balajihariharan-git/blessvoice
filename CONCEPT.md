# BlessVoice — Concept & Architecture Document

> **Created**: 2026-03-28
> **Last Updated**: 2026-03-28 (full rewrite after prototype + architecture research)
> **Status**: Working Prototype (Phase 1) + Architecture Finalized
> **Goal**: Free, real-time AI voice conversation platform with human-level realism

---

## Vision

A real-time AI voice conversation platform where users call in over WiFi/internet and talk to an AI that sounds indistinguishable from a human — with full emotion, natural pacing, breathing, hesitation, and personality. The AI speaks in the voice the user expects (voice cloning). Fully open-source, zero paid APIs, free for all end users. The system evolves and improves through every real interaction.

---

## Core Principles

1. **Voice-to-Voice, NOT Voice-to-Text-to-Voice** — No text intermediary. Audio tokens in, audio tokens out. Every text conversion is lossy (strips emotion, tone, pacing, accent).
2. **100% Open Source** — No paid APIs, no vendor lock-in. Must be sustainable as a free service.
3. **GPU Required** — Voice-native models need GPU. No pretending CPU works. Plan for GPU from day one.
4. **Continuous Self-Improvement** — Model evolves from real conversation data via fine-tuning.
5. **Indistinguishable from Human** — The bar is "real", not "good enough".

---

## The Two Architectures

### Architecture A: Pipeline (Text Intermediary) — CURRENT PROTOTYPE

```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐
│   You    │───>│     STT     │───>│     LLM     │───>│     TTS     │───>│   You   │
│  Speak   │    │  (Whisper)  │    │ (GPT-4o-mini│    │  (OpenAI)   │    │  Hear   │
│  Audio   │    │  Audio>Text │    │  Text>Text) │    │  Text>Audio │    │  Audio  │
└─────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────┘
                   ↑                   ↑                   ↑
              LOSSY STEP          LOSSY STEP          LOSSY STEP
           (loses emotion)     (no tone info)     (re-synthesizes)

Latency: ~2-5 seconds
Cost: ~$0.005 per turn (OpenAI APIs)
Runs on: Laptop CPU (AI in cloud)
Emotion: Poor (stripped at STT, faked at TTS)
Quality: Functional but clearly not human
```

### Architecture B: Voice-Native (No Text) — THE GOAL

```
┌─────────┐    ┌──────────────────────────────────────┐    ┌─────────┐
│   You    │───>│       MOSHI / CSM / PersonaPlex      │───>│   You   │
│  Speak   │    │                                      │    │  Hear   │
│  Audio   │    │  Audio Tokens ──> Transformer ──>    │    │  Audio  │
│          │    │     (Mimi codec)    (7B brain)       │    │         │
│          │    │                                      │    │         │
│          │    │  Understands: tone, emotion, pacing  │    │         │
│          │    │  Generates: tone, emotion, pacing    │    │         │
│          │    │  Full-duplex: listens while speaking  │    │         │
└─────────┘    └──────────────────────────────────────┘    └─────────┘

Latency: ~200ms
Cost: $0 (self-hosted, open source)
Runs on: GPU server (12-24GB VRAM)
Emotion: Preserved end-to-end
Quality: Near-human
```

---

## GPU = No License Keys, No API Costs, Free Forever

**Critical insight**: With a GPU, EVERYTHING is free and self-hosted. Zero API keys, zero licenses, zero cost per call.

| Component | Model | License | API Key? | Cost per Call |
|-----------|-------|---------|----------|---------------|
| Voice-to-Voice (all-in-one) | Moshi | CC-BY 4.0 | **NO** | **$0** |
| Alternative: STT | Whisper large-v3 | MIT | **NO** | **$0** |
| Alternative: LLM Brain | Llama 3.3 70B / Qwen 72B | Apache 2.0 | **NO** | **$0** |
| Alternative: TTS | Kokoro / XTTS v2 / CSM | Apache 2.0 | **NO** | **$0** |

**You download the model weights once, run them on your GPU, and that's it.**
1 user or 1 million calls — same cost. That's how you offer it free to everyone.

### GPU Hardware Options

| Option | GPU | VRAM | Cost |
|--------|-----|------|------|
| Google Colab free | T4 | 15GB | **$0** (sessions timeout ~90min) |
| AWS g4dn.xlarge | T4 | 16GB | ~$150/mo (spot) or ~$380/mo (on-demand) |
| AWS g5.xlarge | A10G | 24GB | ~$500/mo |
| Buy used RTX 3060 | - | 12GB | **~$250 one-time** |
| Buy used RTX 3090 | - | 24GB | **~$500 one-time** |

---

## Open Source Voice-Native Models (All Free, All Need GPU)

| Model | By | Full-Duplex | Emotion | Min VRAM | License |
|-------|----|-------------|---------|----------|---------|
| **Moshi** | Kyutai | Yes | Good | 12-24GB | CC-BY 4.0 |
| **CSM** | Sesame/Meta | Near RT | Excellent | 12GB | Apache 2.0 |
| **PersonaPlex** | NVIDIA | Yes (100% interrupt) | Good | 24GB | Open weights |
| **GLM-4-Voice** | Tsinghua | Yes | Good | 12GB | Apache 2.0 |
| **Ultravox** | Fixie AI | No | Moderate | 12GB | Apache 2.0 |
| **Mini-Omni 2** | GAIR | Yes | Moderate | 12GB | MIT |
| **Hertz-Dev** | Standard AI | Yes | Good | 12GB | Apache 2.0 |

**There is NO free voice-native model that runs on CPU.** Every single one needs GPU.

---

## VAD: How Listening Works (Sleep vs Active)

```
┌──────────────────────────────────────────────┐
│              BROWSER (always on)              │
│                                              │
│  Mic ──> Check audio level every 128ms       │
│           │                                  │
│           ├── Level > threshold ─> HEARING   │
│           │    (collecting audio chunks)      │
│           │    (sends nothing yet)            │
│           │                                  │
│           ├── Level drops for 0.8s ─> SEND   │
│           │    (silence detected, send audio) │
│           │    (API calls happen NOW)         │
│           │                                  │
│           └── Level < threshold ─> LISTENING │
│                (idle, NO data sent)           │
│                (zero API calls, zero cost)    │
│                (zero CPU usage on server)     │
└──────────────────────────────────────────────┘
```

**When nobody talks**: Mic is on but nothing leaves the browser. Zero cost, zero server load. The VAD is just comparing a number in JavaScript — effectively sleeping.

---

## Prototype Architecture Details (Phase 1 — Current)

### Hardware
- **CPU**: Intel i5-1135G7 (4 cores, 8 threads)
- **RAM**: 16GB
- **GPU**: NVIDIA MX450 (2GB VRAM — too small for any AI model)
- **OS**: Windows 11

### Stack
```
Browser (index.html)
    │
    │ WebSocket (ws://localhost:8000/ws)
    │ Binary: Float32 PCM audio (16kHz mono)
    │ JSON: {type: "speaking"/"done"/"interrupt"}
    │
    ▼
FastAPI + Uvicorn (Python)
    │
    ▼
VoicePipeline (pipeline.py)
    ├── STT: OpenAI Whisper API (~0.5-2s)
    ├── LLM: OpenAI GPT-4o-mini streaming (~0.5-2s, first sentence fast path)
    └── TTS: OpenAI TTS-1 "nova" voice, raw PCM streaming (~1-2s)
```

### Key Architectural Patterns (Learned from RealtimeVoiceChat + Pipecat)

1. **First-Sentence Fast Path**: LLM streams tokens. As soon as the first sentence completes (detects `.!?`), TTS fires immediately on just that sentence. User hears first words while LLM still generates the rest. Saves 1-3 seconds of perceived latency.

2. **Streaming PCM Playback**: TTS returns raw PCM (no WAV headers). Audio chunks are scheduled on the browser's AudioContext with precise timing (`nextPlayTime += duration`). No decode overhead, seamless playback.

3. **Interruption Handling**: Every audio frame from mic is checked. If user speaks while AI is talking:
   - Browser: stops all AudioContext sources immediately
   - Sends `{type: "interrupt"}` to server
   - Server: sets abort flag, pipeline stops LLM + TTS mid-generation
   - Server: drains audio queue, starts fresh pipeline for new input

4. **Abort Synchronization**: Pipeline uses `threading.Event` for clean abort. LLM stream and TTS both check `_abort.is_set()` between chunks. No orphaned audio leaks into next response.

### What We Tried and Rejected (Phase 1)

| Approach | Problem |
|----------|---------|
| Local Whisper tiny (CPU STT) | Works but 1-2s on CPU |
| Local Llama 1B (CPU LLM) | Loops, garbage responses |
| Local Llama 3B (CPU LLM) | OK quality, 15s per response |
| Local Phi-3 3.8B (CPU LLM) | Good quality, 25-35s per response |
| Local Silero TTS (CPU) | 2-3s per sentence, robotic voice |
| **Verdict**: CPU is not viable for real-time voice AI | Need GPU or cloud APIs |

---

## Existing Open-Source Voice Frameworks (Evaluated)

| Project | Stars | What It Does | Claude/Custom LLM? | Setup |
|---------|-------|-------------|---------------------|-------|
| **Pipecat** (Daily.co) | 10.9K | Framework for voice AI agents. Best LLM/TTS coverage. | Yes (Claude, OpenAI, Groq, etc.) | pip install, ~15 min |
| **RealtimeVoiceChat** (KoljaB) | 3.6K | Full voice chat app. Best local option with Kokoro TTS. | Ollama/OpenAI | install.bat, ~30 min |
| **LiveKit Agents** | 9.9K | Production voice pipeline on WebRTC. | Yes (Claude, OpenAI) | pip install + LiveKit server |
| **HuggingFace speech-to-speech** | 4.6K | Fully local pipeline. STT+LLM+TTS. | HF models, OpenAI | uv sync, needs GPU |
| **PyGPT** | 1.7K | Desktop AI app with voice mode. | Yes (Claude, OpenAI, Ollama) | Download .exe, 5 min |
| **Vocode** | 3.7K | Telephony-focused voice agents. | OpenAI, Anthropic | Winding down, not recommended |

### Key Patterns from These Projects

**From RealtimeVoiceChat (most relevant):**
- Speculative execution: starts LLM 350ms BEFORE silence timeout expires
- Two-stage TTS: "quick answer" (tiny chunks, fast) + "final answer" (larger chunks, smooth)
- ML-based turn detection: DistilBERT predicts sentence completion, adjusts silence threshold
- Every audio packet carries 1-bit "is TTS playing" flag for instant interruption

**From Pipecat:**
- Frame-based pipeline: typed Frame objects (SystemFrame > DataFrame > ControlFrame)
- Dual-queue priority: InterruptionFrame bypasses regular queue entirely
- Bidirectional flow: events propagate both upstream and downstream
- Direct mode: bypasses all queuing for latency-critical processors

---

## Moshi Deep Dive (Primary Production Target)

### How It Works

```
Audio waveform (user speaking)
     |
     v
┌─────────────────────────────┐
│  Mimi Codec (Neural Audio)  │  <-- Encodes audio into tokens
│  8 codebook streams         │      12.5 Hz token rate (extremely low)
│  1.1 kbps bandwidth         │      80ms frame size
└──────────┬──────────────────┘
           |
           v
┌─────────────────────────────┐
│  Helium Transformer (7B)    │  <-- Processes audio tokens directly
│  Depth transformer for      │      "Thinks" in sound, not text
│  multi-stream prediction    │      Inner monologue (text) improves quality
│  Full-duplex: 2 streams     │      User stream + Moshi stream simultaneously
└──────────┬──────────────────┘
           |
           v
┌─────────────────────────────┐
│  Mimi Decoder               │  <-- Generates audio tokens back
│  Audio token > Waveform     │      Preserves emotion, prosody
└──────────┬──────────────────┘
           |
           v
    Audio waveform out (with emotion, natural pacing)
```

No text anywhere in the real-time path. Audio tokens in, audio tokens out.

### Moshi Risk Assessment

| Factor | Level | Detail |
|--------|-------|--------|
| License on current code | Safe | MIT + Apache 2.0 (code), CC-BY 4.0 (weights) — irrevocable |
| Future relicensing | Medium | CLA allows it. Core team now at Gradium ($70M startup) |
| Maintenance | Medium | Reduced commit velocity since team left for Gradium |
| English only | High | No multilingual support |
| Session limit | Medium | 5 min on Rust/MLX backends |
| Hardware | 12-24GB VRAM | Cannot run on CPU |

### Kyutai Ecosystem

| Project | Stars | What It Does | CPU? |
|---------|-------|-------------|------|
| **moshi** | ~10K | Full-duplex voice-to-voice dialogue | GPU only |
| **pocket-tts** | ~3.6K | Lightweight TTS, designed for CPU | YES |
| **unmute** | ~1.2K | Makes any text LLM listen and speak via Mimi | GPU |
| **hibiki** | ~1.4K | Real-time speech translation | GPU |
| **moshi-finetune** | ~417 | Fine-tuning toolkit for Moshi | GPU |

### NVIDIA PersonaPlex-7B (Better Moshi)

- Built directly ON TOP of Moshi's architecture
- **100% interrupt handling** success rate (vs Moshi's 60.6%)
- Better turn-taking and conversation flow
- Released Jan 2026 by NVIDIA, open weights
- Should be evaluated as primary Moshi alternative

---

## Continuous Learning Pipeline

Since voice-native models work with audio tokens, fine-tuning happens directly on audio:

```
Real conversation audio (from actual calls)
        |
        v
Extract audio token sequences (via Mimi codec / CSM tokenizer)
        |
        v
Quality filter:
  - Was the user engaged? (long conversation = good signal)
  - Did they hang up early? (bad signal)
  - Did they interrupt/re-ask? (confusion signal)
  - Implicit feedback from user behavior
        |
        v
LoRA fine-tune on the base model
  - Personality refinement
  - Emotional response patterns
  - Conversational rhythm
  - Domain knowledge
        |
        v
A/B deploy updated model weights
        |
        v
Measure naturalness score > Promote or rollback
```

---

## Voice Cloning Strategy

| Model | Sample Needed | Quality | License |
|-------|--------------|---------|---------|
| **XTTS v2** (Coqui) | 6 seconds | Very natural | MPL 2.0 |
| **OpenVoice v2** | 10 seconds | Good | MIT |
| **GPT-SoVITS** | 1 minute | Excellent | MIT |
| **Fish Speech** | 15 seconds | Very natural | Apache 2.0 |

---

## Phased Roadmap

### Phase 1: Laptop Prototype (DONE)
```
Browser <--WebSocket--> FastAPI <--APIs--> OpenAI (Whisper + GPT-4o-mini + TTS)
```
- **Status**: Working
- **Latency**: ~3-5s to first audio
- **Cost**: ~$0.005/turn (OpenAI APIs)
- **Quality**: Functional, not human-like
- **Purpose**: Validate UX, conversation flow, interruption handling

### Phase 2: GPU — True Voice-to-Voice
```
Browser <--WebSocket--> FastAPI <--local--> Moshi/CSM (single GPU)
```
- **Hardware**: 1x GPU (Colab free / AWS g4dn / RTX 3060)
- **Model**: Moshi or CSM or PersonaPlex
- **Latency**: ~200-400ms
- **Cost**: $0 per call (self-hosted)
- **Quality**: Near-human, emotional, full-duplex

### Phase 3: Continuous Learning + Voice Cloning
- Fine-tune on real conversations (LoRA)
- Voice cloning: users provide 6-60s sample
- A/B deployment of improved models
- Quality metrics from user engagement data

### Phase 4: Free Service for Everyone
- GPU cluster (scale based on users)
- Multi-language support
- Multiple voice personas
- $0 for end users, funded by GPU infrastructure

---

## Project Structure

```
D:\BlessVoice\
├── app/
│   ├── __init__.py
│   ├── config.py        # Configuration (VAD thresholds, model names)
│   ├── pipeline.py      # Streaming STT > LLM > TTS pipeline
│   └── main.py          # FastAPI + WebSocket server
├── web/
│   └── index.html       # Full frontend (orb UI, VAD, PCM playback)
├── models/              # Downloaded model files (local models, 2.5GB+)
├── run.py               # Entry point
├── requirements.txt
└── CONCEPT.md           # This document
```

---

## How AI Models Work — No Storage, No Database, Pure Math

### What IS a Model?

A model is NOT a database of stored conversations. It is a compressed pattern of understanding.

```
A HUMAN BRAIN                          AN AI MODEL
─────────────                          ───────────
You read 1000 books as a child    →    Model was trained on millions of conversations
You don't remember every word     →    Model doesn't store any conversations
But you LEARNED language patterns →    Model LEARNED speech patterns
You can now speak fluently        →    Model can now speak fluently

Your brain weighs ~1.4 kg        →    Moshi weighs ~14 GB (one file)
You don't need the books anymore  →    Model doesn't need the training data anymore
```

### What You Download vs What Was Used to Train It

```
TRAINING (done by Kyutai/NVIDIA/Sesame — NOT by you)
═══════════════════════════════════════════════════════
    Millions of hours of speech audio (Common Crawl, etc.)
    + Thousands of GPUs running for months
    + $10-100 million in compute costs
              │
              │  Training COMPRESSES all of this
              │  into mathematical patterns (weights)
              │
              ▼
    ┌──────────────────────────┐
    │   MODEL WEIGHTS FILE     │
    │   (e.g., moshi-7b.bin)   │
    │   Size: ~14 GB           │
    │                          │
    │   Contains: PATTERNS     │
    │   (billions of numbers)  │
    │                          │
    │   Does NOT contain:      │
    │   - Any original audio   │
    │   - Any conversations    │
    │   - Any stored data      │
    │                          │
    │   It predicts: "given    │
    │   this sound, what       │
    │   sound comes next?"     │
    └──────────────────────────┘
              │
              │  You download just THIS file (free, one time)
              ▼
YOUR GPU (what you run)
═══════════════════════
    User speaks → audio tokens go IN
                      │
              ┌───────▼────────┐
              │  Weights file  │  ← Numbers NEVER change during use
              │  predicts next │     No storage growing
              │  audio token   │     No database filling up
              └───────┬────────┘
                      │
              Audio tokens come OUT → user hears response
```

### Do You Need Storage for Intelligence?

| What | Size | Grows Over Time? | You Need to Store It? |
|------|------|-----------------|----------------------|
| Model weights (the intelligence) | ~14 GB | NO — fixed file, never changes | Yes — one file on GPU server |
| Training data (Common Crawl, etc.) | Petabytes | N/A — you never have this | NO — creators used it, you don't need it |
| User conversations | Depends | Only if you save them | ONLY if you CHOOSE to (for fine-tuning) |
| Fine-tuned adapter (LoRA) | ~500 MB | Only when you retrain | Yes — tiny file alongside main weights |

### Your Complete Infrastructure

```
YOUR SERVER (total ~15 GB, that's it, forever)
├── /models/moshi-7b.bin          14 GB  ← The brain (FIXED, never changes)
├── /app/main.py                   5 KB  ← Your server code
├── /app/pipeline.py              10 KB  ← Your audio pipeline
├── /web/index.html               8 KB  ← Browser UI
└── (optional) /data/recordings/   ??   ← ONLY if saving calls for fine-tuning

No database. No growing storage. No maintenance of "intelligence."
The intelligence IS the weights file. Static. Permanent.
```

---

## LoRA Fine-Tuning — Customizing for Your Culture and Languages

### What is LoRA?

LoRA (Low-Rank Adaptation) lets you teach the model new things WITHOUT retraining it from scratch.

```
Training from scratch = Building a car factory to make a car ($10M+, impossible alone)
Fine-tuning with LoRA = Taking a car and customizing the interior ($0, doable on 1 GPU)
```

### How Fine-Tuning Works

```
ORIGINAL MODEL (14 GB, English-only, general knowledge)
    │
    │  You provide: 100-1000 hours of Tamil/Hindi/regional audio
    │  You run: LoRA fine-tuning on your 1 GPU (takes hours/days, not months)
    │
    ▼
ORIGINAL WEIGHTS (14 GB)  ←── UNCHANGED, never modified
         +
LORA ADAPTER (500 MB)     ←── NEW file, YOUR customizations
         =
YOUR CUSTOM MODEL         ←── Speaks Tamil, knows your culture

After fine-tuning, you can DELETE the training audio.
The knowledge is now compressed into the 500 MB LoRA adapter.
```

### Language Expansion Roadmap

| Phase | Language | What You Need | Effort |
|-------|----------|--------------|--------|
| Phase 1 | English | Base model as-is | Zero — already works |
| Phase 2 | Tamil | ~100-500 hours Tamil conversation audio + LoRA fine-tune | Medium — 1 GPU, days of training |
| Phase 3 | Hindi | ~100-500 hours Hindi conversation audio + LoRA fine-tune | Medium — same process |
| Phase 4 | More languages | Same pattern — collect audio, fine-tune, deploy | Repeatable |

### Where to Get Training Audio for Your Languages

| Source | Languages | Cost | Quality |
|--------|-----------|------|---------|
| Mozilla Common Voice | 100+ languages (Tamil, Hindi included) | Free | Good (volunteer recorded) |
| LibriSpeech | English | Free | Excellent |
| VoxPopuli | 23 languages | Free | Good (EU Parliament) |
| FLEURS | 102 languages | Free | Good (Google) |
| Your own user conversations | Any | Free (with consent) | Best (real interactions) |

### LoRA Adapters Are Stackable

```
Base Model: Moshi (English)
    ├── + tamil_adapter.bin (500 MB)  → Speaks Tamil
    ├── + hindi_adapter.bin (500 MB)  → Speaks Hindi
    ├── + culture_adapter.bin (500 MB) → Knows Indian customs, festivals, food
    └── + persona_adapter.bin (500 MB) → Has specific personality traits

Load any combination at runtime. Swap in seconds.
User selects Tamil? Load tamil_adapter. Done.
```

---

## Why Not Just Moshi? — Full Model Comparison for Decision

### The Honest Comparison

| Feature | Moshi | PersonaPlex | CSM | GLM-4-Voice |
|---------|-------|------------|-----|-------------|
| **Voice quality** | Good | Good | BEST (most natural) | Good |
| **Full-duplex** (talk over it) | Yes | Yes (BEST: 100%) | No | Yes |
| **Interrupt handling** | 60.6% | 100% | N/A | Unknown |
| **Latency** | ~200ms | ~200ms | ~300ms | ~300ms |
| **Languages** | English only | English only | English only | English + Chinese |
| **Fine-tuning toolkit** | Yes (moshi-finetune) | No official toolkit | No official toolkit | No |
| **License** | CC-BY 4.0 | Open weights | Apache 2.0 | Apache 2.0 |
| **Can you fork + modify?** | Yes | Yes | Yes | Yes |
| **Can they revoke license?** | No (irrevocable) | No | No | No |
| **Active development** | Declining (team left) | Active (NVIDIA) | Unknown | Active |
| **Min VRAM** | 12-24 GB | 24 GB | 12 GB | 12 GB |
| **Community size** | Large (~10K stars) | Growing | Medium | Medium |
| **Production ready?** | Yes | Newer, less tested | Newer, less tested | Less tested |

### Which Model for What

| Your Need | Best Model | Why |
|-----------|-----------|-----|
| Start prototyping NOW | **Moshi** | Most mature, fine-tuning toolkit exists, largest community |
| Best conversation flow | **PersonaPlex** | 100% interrupt handling, built on Moshi (familiar architecture) |
| Most natural voice | **CSM** | Uncanny human-like quality, laughter, breathing, hesitation |
| Multilingual (Chinese) | **GLM-4-Voice** | Only model with non-English native support |
| Adding Tamil/Hindi later | **Moshi** (then fine-tune) | Only one with official fine-tuning toolkit |

### The Strategy: Don't Pick One — Test All, Commit to Best

```
Week 1: Set up Moshi on GPU (Google Colab free)
         ├── Test voice quality
         ├── Test conversation flow
         └── Test interruption handling

Week 2: Set up PersonaPlex on same GPU
         ├── Compare side by side with Moshi
         └── Test interrupt handling (should be better)

Week 3: Set up CSM on same GPU
         ├── Compare voice quality
         └── Evaluate for production

Week 4: DECIDE which model to build on
         ├── Fine-tune chosen model with LoRA
         └── Begin language expansion
```

Your WebSocket server, browser UI, and audio pipeline are MODEL-AGNOSTIC.
Swapping models = changing one file. The rest stays the same.

---

## Ownership and Maintenance — Can You Run This Forever?

### License Safety (Every Model)

| Model | License | Can you sell product built on it? | Can they revoke? | Can you fork + maintain? |
|-------|---------|----------------------------------|-----------------|-------------------------|
| Moshi | CC-BY 4.0 (weights), MIT (code) | Yes (credit Kyutai) | No — irrevocable | Yes |
| PersonaPlex | Open weights (NVIDIA) | Yes | No | Yes |
| CSM | Apache 2.0 | Yes | No | Yes |
| GLM-4-Voice | Apache 2.0 | Yes | No | Yes |
| Whisper | MIT | Yes | No | Yes |
| Llama 3.3 | Community License | Yes (under 700M users) | No | Yes |
| Kokoro TTS | Apache 2.0 | Yes | No | Yes |

### What "Irrevocable" Means

```
Today: You download Moshi v0.2 (CC-BY 4.0)
Tomorrow: Kyutai changes v0.3 to paid license
You: Still running v0.2 forever. Legally. They CANNOT touch it.
You can: Fork v0.2, modify it, improve it, build on it.
You cannot: Use v0.3. But you don't need it.
```

### Can You Maintain It Yourself?

| Task | Difficulty | What's Involved |
|------|-----------|-----------------|
| Run the model on GPU | Easy | Python script, already built |
| Update dependencies | Easy | pip install, routine |
| Fix bugs in serving code | Medium | You or any Python developer |
| Fine-tune with LoRA | Medium | 1 GPU + training audio + toolkit |
| Add new languages via LoRA | Medium | Collect audio data + fine-tune |
| Improve model architecture | Very Hard | Needs ML research team |
| Train completely new model from scratch | Impossible alone | Thousands of GPUs, $10M+, research team |

**You can maintain and improve it forever. You CANNOT rebuild it from scratch.**
But you never need to — fine-tuning is enough.

### Your Ongoing Maintenance

| Task | Frequency | Effort | Cost |
|------|-----------|--------|------|
| Keep GPU running | Always | Electricity or cloud bill | $150-500/mo |
| Update Python packages | Monthly | 5 minutes | $0 |
| Fix bugs in your code | As needed | Developer time | $0 |
| Store anything growing? | NO | Model is fixed size | $0 |
| Pay anyone for licenses? | NEVER | All open source | $0 |
| Manage a database? | NO | No database needed | $0 |
| Fine-tune to improve | Optional, quarterly | Collect audio, run LoRA | $0 (your GPU) |

---

## Moshi Cons (Full Transparency)

### Critical Issues

| Con | Impact | Workaround |
|-----|--------|------------|
| English only | Cannot speak Tamil, Hindi, or others | LoRA fine-tune with target language audio |
| 5-minute session limit | Conversation cuts off (Rust/MLX backends) | Reconnect, or use PyTorch backend (degrades over time) |
| Core team left | Founders started Gradium ($70M startup). Reduced development | Fork repo, maintain yourself, or switch to PersonaPlex |
| Only 2 voices | Moshiko (male) and Moshika (female) | Fine-tune with custom voice data |
| 60.6% interrupt handling | Doesn't always stop when you talk over it | Use PersonaPlex instead (100%) |

### Technical Concerns

| Con | Impact | Workaround |
|-----|--------|------------|
| No tool calling | Cannot search web, check calendar, call APIs | Hybrid: Moshi for voice + separate agent for actions |
| No memory across sessions | Forgets previous conversations | Build external memory, inject as context |
| 1 GPU = ~1 user | Each call needs full GPU | Queue system, or multiple GPUs for scale |
| No built-in multi-tenancy | No user management or routing | Build this yourself |

---

---

## DECISION: PersonaPlex as Base Model (Decided 2026-03-30)

### Why PersonaPlex and Not Moshi or CSM

**Core reasoning: Full-duplex cannot be added later. Voice quality CAN be improved later.**

```
Kyutai built Moshi          → Fixed 60% of problems
NVIDIA built PersonaPlex    → Fixed interrupt handling → 100%
WE build BlessVoice         → Fix voice quality + add languages + add personality

Each layer builds on the previous. No wasted effort.
```

#### Why not start from Moshi?

NVIDIA already did the hard work of fixing Moshi's biggest flaw (interrupt handling: 60% → 100%). Redoing that ourselves is wasted effort. Start from PersonaPlex = start from an already-improved Moshi.

#### Why not start from CSM?

CSM has the best voice quality in the world. BUT:

```
Voice quality    = Training data problem → FIXABLE with LoRA later
Full-duplex      = Architecture problem  → NOT fixable with LoRA ever
```

LoRA changes what the model KNOWS (how it sounds, what it says).
LoRA does NOT change the model's ARCHITECTURE (how it processes input/output).

CSM is turn-based — user speaks, waits, AI responds. No interruption possible.
PersonaPlex is full-duplex — real phone conversation, talk over it, interrupt naturally.

| Feature | Can you ADD it with LoRA? |
|---------|--------------------------|
| Better voice quality | YES — fine-tune on studio-quality speech |
| New languages (Tamil, Hindi) | YES — fine-tune on language audio data |
| New personality | YES — fine-tune on personality conversations |
| Full-duplex conversation | NO — architecture change, impossible with LoRA |
| Interrupt handling | NO — architecture change, impossible with LoRA |

**Build something that FEELS like a conversation first. Make it SOUND perfect second.**

#### The User Experience Difference

```
With PersonaPlex (full-duplex) — CHOSEN:
  User: "Hey can you tell me—"
  AI: "Sure, what would you—"
  User: "—a Tamil recipe for sambar"
  AI: [immediately stops, processes new request]
  AI: "Of course! Start by soaking toor dal..."
  Feels like: A REAL phone conversation. Natural. Fluid.

With CSM (turn-based) — REJECTED:
  User: "Hey can you tell me a Tamil recipe for sambar"
  [silence while AI processes]
  AI: "Of course! Start by soaking toor dal..."
  [sounds INCREDIBLY human, but user CANNOT interrupt]
  Feels like: Listening to a beautiful recording. Not a conversation.
```

### The BlessVoice Build Strategy

```
PersonaPlex (NVIDIA's improved Moshi — free, open weights)
    │
    │  Already has:
    │  ✓ 100% interrupt handling
    │  ✓ Full-duplex (listen + speak simultaneously)
    │  ✓ Better turn-taking than Moshi
    │  ✓ Same Mimi codec (audio tokens)
    │  ✓ Same 7B transformer architecture
    │  ✓ Forkable and LoRA-fine-tunable
    │
    │  WE add via LoRA fine-tuning:
    │
    ├── Layer 1: Voice Quality adapter (~500 MB)
    │   Train on: High-quality studio speech (LibriSpeech, etc.)
    │   Result: Smoother, more natural English voice
    │
    ├── Layer 2: Tamil adapter (~500 MB)
    │   Train on: Mozilla Common Voice Tamil + Tamil podcasts
    │   Result: Speaks Tamil fluently
    │
    ├── Layer 3: Hindi adapter (~500 MB)
    │   Train on: Mozilla Common Voice Hindi + Hindi conversations
    │   Result: Speaks Hindi fluently
    │
    ├── Layer 4: Culture adapter (~500 MB)
    │   Train on: Conversations about Indian customs, food, festivals
    │   Result: Culturally aware responses
    │
    └── Layer 5: Personality adapter (~500 MB)
        Train on: Conversations with desired personality traits
        Result: Unique BlessVoice character
    │
    ▼
BlessVoice = PersonaPlex + YOUR 5 LoRA adapters
           = Moshi's architecture (Kyutai)
           + NVIDIA's interrupt fix
           + YOUR voice quality improvement
           + YOUR languages (Tamil, Hindi, more)
           + YOUR cultural knowledge
           + YOUR personality
```

### What You Ship

```
BlessVoice Server
├── personaplex-7b.bin        14 GB    ← NVIDIA's model (free, open)
├── voice-quality-lora.bin   500 MB    ← YOUR voice improvement
├── tamil-lora.bin           500 MB    ← YOUR Tamil language
├── hindi-lora.bin           500 MB    ← YOUR Hindi language
├── culture-lora.bin         500 MB    ← YOUR cultural knowledge
├── personality-lora.bin     500 MB    ← YOUR BlessVoice character
├── app/                               ← YOUR server code
└── web/                               ← YOUR frontend

Total: ~17 GB. Runs on 1 GPU. Free forever.
Nobody else has your LoRA adapters — that's YOUR competitive advantage.
```

### Building the Fine-Tuning Toolkit for PersonaPlex

PersonaPlex has no official fine-tuning toolkit. But building one is ~3 days of work:

| Step | What You Write | Complexity | Time |
|------|---------------|-----------|------|
| Data loader | Load audio → convert to Mimi tokens | Easy | 1 day |
| LoRA config | Which layers to adapt, rank, alpha | Copy from moshi-finetune, adjust | 1 hour |
| Training loop | Standard PyTorch + PEFT library | ~100 lines | 1 day |
| Eval script | Test fine-tuned model | Play audio, listen | Half day |
| **Total** | **~500 lines of Python** | | **~3 days** |

Cost of building toolkit: **$0** (Python + PEFT library + PyTorch = all free)
Cost of running fine-tuning: **$0** (same GPU you already run the model on)

Since PersonaPlex is built on Moshi's architecture (same Mimi codec, same transformer),
the moshi-finetune repo is a near-direct reference. Adapt, don't reinvent.

### Free Audio Data Sources for Fine-Tuning

| Source | Languages | Hours Available | Cost |
|--------|-----------|----------------|------|
| Mozilla Common Voice | Tamil, Hindi, English + 100 more | 10,000+ hours total | $0 |
| LibriSpeech | English | 1,000 hours | $0 |
| VoxPopuli | 23 languages | 400,000+ hours | $0 |
| FLEURS | 102 languages | 350+ hours per language | $0 |
| IndicVoices | 22 Indian languages | 7,000+ hours | $0 |
| Your own user conversations | Any | Grows over time | $0 (with consent) |

### Future-Proofing

```
If CSM releases full-duplex support → evaluate switching base model
If a better model appears → swap base, keep your LoRA adapters
If PersonaPlex improves → update base weights, LoRA adapters still work

Your LoRA adapters (languages, culture, personality) are YOUR investment.
They survive base model upgrades. They are YOUR moat.
```

---

## How AI Models Work — No Storage, No Database, Pure Math

(This section explains the fundamentals for anyone reading this document.)

### A model is NOT a database. It's compressed understanding.

```
A HUMAN BRAIN                          AN AI MODEL
─────────────                          ───────────
You read 1000 books as a child    →    Trained on millions of conversations
You don't remember every word     →    Doesn't store any conversations
But you LEARNED language patterns →    LEARNED speech patterns
You can now speak fluently        →    Can now speak fluently
Your brain weighs ~1.4 kg        →    Model weighs ~14 GB (one file)
You don't need the books anymore  →    Doesn't need training data anymore
```

### How prediction works (no storage needed)

```
You say: "Hello, how are you?"

Step 1: Audio becomes tokens:  [HE] [LLO] [HOW] [ARE] [YOU]
Step 2: Model predicts next token based on learned patterns
Step 3: Model outputs: [I'M] → [DO] → [ING] → [WELL]
Step 4: Tokens become audio: "I'm doing well!"

NOTHING STORED. NOTHING LOOKED UP.
Pure mathematical prediction — like autocomplete but for audio.
```

### Your maintenance obligations

| Task | Frequency | Effort | Cost |
|------|-----------|--------|------|
| Keep GPU running | Always | Electricity or cloud bill | $150-500/mo |
| Update Python packages | Monthly | 5 minutes | $0 |
| Fix bugs in code | As needed | Developer time | $0 |
| Store anything growing? | **NO** | Model is fixed 14 GB | $0 |
| Pay licenses? | **NEVER** | All open source | $0 |
| Manage a database? | **NO** | No database needed | $0 |
| Fine-tune to improve | Optional, quarterly | Collect audio, run LoRA | $0 (same GPU) |

---

## Complete Cost Table — Everything, Nothing Hidden

### Software (ALL free, forever)

| Tool | Purpose | License | API Key? | Cost |
|------|---------|---------|----------|------|
| PersonaPlex 7B | The AI brain + voice (all-in-one) | Open weights | NO | $0 |
| Mimi codec | Audio ↔ token conversion | MIT | NO | $0 |
| PEFT / LoRA | Fine-tuning library | Apache 2.0 | NO | $0 |
| PyTorch | ML framework | BSD | NO | $0 |
| FastAPI | Web server | MIT | NO | $0 |
| Python | Programming language | PSF | NO | $0 |
| Common Voice | Training audio data | CC-0 | NO | $0 |
| **TOTAL SOFTWARE** | | | | **$0** |

### Hardware (the ONLY cost)

| Option | GPU | VRAM | Cost | Best For |
|--------|-----|------|------|----------|
| Google Colab free | T4 | 15GB | $0 | Testing (90min sessions) |
| Used RTX 3060 | - | 12GB | ~$250 one-time | Home server |
| Used RTX 3090 | - | 24GB | ~$500 one-time | Best local option |
| AWS g4dn.xlarge | T4 | 16GB | ~$150/mo spot | Cloud, reliable |
| AWS g5.xlarge | A10G | 24GB | ~$500/mo | Cloud, premium |

### Per-User Cost at Scale

| Users | GPUs Needed | Monthly Cost | Cost Per User |
|-------|------------|-------------|---------------|
| 1-5 | 1 | $150-500 | $30-100 |
| 10-20 | 2-3 | $300-1500 | $15-75 |
| 100+ | Queue system, 5-10 GPUs | $750-5000 | $7-50 |

---

---

## AWS GPU — Start/Stop Billing (Pay Only When Working)

AWS GPU instances work like a light switch. You pay per second while running, $0 when stopped.

```
Instance RUNNING  → You pay per second
Instance STOPPED  → $0 compute ($4/mo disk storage to keep your model)

Example week:
  Monday 8pm-11pm:    Start, test 3 hours, stop.
  Tuesday-Friday:     Stopped. $0.
  Saturday 2pm-6pm:   Start, test 4 hours, stop.
  You paid for: 7 hours only.
```

### Start/Stop is Simple

```
Start (takes ~90 seconds to be ready):
  $ aws ec2 start-instances --instance-ids i-1234567890
  → Boots in 30s → Model loads in 60s → Ready to talk

Stop (billing stops immediately):
  $ aws ec2 stop-instances --instance-ids i-1234567890
  → Disk preserved, model weights saved, $4/mo storage

Or just click Start/Stop in the AWS web console. No terminal needed.
```

### Real Cost by Usage Pattern

#### On-Demand (pay as you go)

| Instance | GPU | VRAM | Per Hour | 3 hrs/day | 8 hrs/day | 24/7 |
|----------|-----|------|----------|-----------|-----------|------|
| g4dn.xlarge | T4 | 16GB | $0.526 | ~$47/mo | ~$126/mo | $379/mo |
| g5.xlarge | A10G | 24GB | $1.006 | ~$90/mo | ~$241/mo | $725/mo |

#### Spot Instances (same GPU, 60-70% cheaper)

| Instance | Per Hour | 3 hrs/day | 8 hrs/day |
|----------|----------|-----------|-----------|
| g4dn.xlarge spot | ~$0.16 | **~$14/mo** | ~$38/mo |
| g5.xlarge spot | ~$0.30 | **~$27/mo** | ~$72/mo |

#### When Instance is Stopped

| What | Size | Cost |
|------|------|------|
| EBS disk (model + code) | 50 GB | **~$4/month** |
| Compute | - | **$0** |

### Smart Prototyping Progression

```
Phase 1: Google Colab (FREE)
  → Test PersonaPlex, validate quality
  → $0 cost, sessions timeout after ~90 min

Phase 2: AWS Spot Instance (CHEAP)
  → 2-3 hours/day for serious testing
  → g4dn.xlarge spot: ~$14/month + $4 storage
  → Start when working, stop when done

Phase 3: Production
  → Option A: AWS 24/7 (~$380/mo) for real users
  → Option B: Buy RTX 3090 (~$500 one-time, then just electricity)
```

---

## 5-Minute Session Limit — Status in PersonaPlex

### The Problem (from Moshi)

Moshi has a 5-minute session limit on Rust and MLX backends due to a fixed audio buffer that doesn't discard old entries. On the PyTorch backend, there's no hard limit but quality degrades over time as the context fills up.

### Is It Fixed in PersonaPlex?

**This needs to be verified during Colab testing.** PersonaPlex's improvements focused on interrupt handling and turn-taking, not session length. Since PersonaPlex uses the same Mimi codec and similar architecture, the buffer limitation likely still exists.

### How to Fix It (If It's Still There)

This is a **code fix, not a model fix**. The 5-minute limit is in the serving code, not the model weights.

| Fix Approach | Difficulty | What's Involved |
|-------------|-----------|-----------------|
| Sliding window buffer | Easy | Discard oldest audio tokens, keep recent context. Modify serving code (~50 lines). Standard technique. |
| Session reconnect | Easy | Auto-reconnect every 4.5 minutes with conversation summary. Frontend handles seamlessly. |
| KV-cache compression | Medium | Compress the transformer's key-value cache periodically. Keeps quality while reducing memory. |
| Chunked context | Medium | Process conversation in overlapping chunks. Used by many long-context systems. |

```
Sliding window fix (simplest):

Before:  [token1][token2][token3]...[token_5min] → BUFFER FULL → crash/degrade
After:   [          keep last 3 min          ] → old tokens discarded
         Buffer never fills up. Conversation runs forever.
         Trade-off: model "forgets" what was said 3+ minutes ago.
```

**This is a serving code change (~50 lines of Python/Rust), not a model change.** No retraining, no LoRA, no GPU time. Just fix the buffer management.

### Verification Plan

```
During Colab testing (Phase 1):
  1. Start PersonaPlex conversation
  2. Keep talking for 5+ minutes
  3. Note when/if quality degrades or session drops
  4. If it does → implement sliding window fix
  5. If it doesn't → PersonaPlex already fixed it
```

---

## Open Questions

1. **Language priority**: English first, then Tamil? Hindi? What order?
2. **Conversation domain**: General companion? Specific use case?
3. **Voice persona**: Default personality? Multiple personas?
4. **GPU procurement**: Colab (free test) → AWS spot (dev) → production?
5. **Scale target**: How many simultaneous users for free service?
6. **Data privacy**: How to handle voice data for LoRA training?
7. **5-min limit**: Verify during Colab testing if PersonaPlex has this issue

---

## Next Steps

1. **Test PersonaPlex on Google Colab** (free T4 GPU) — validate voice quality + 5-min limit test
2. **Compare with Moshi** side by side on same hardware
3. **Decide GPU strategy**: Colab → AWS spot ($14/mo) → production
4. **Build fine-tuning toolkit** for PersonaPlex (~3 days)
5. **Fix 5-min limit** if present (sliding window, ~1 day)
6. **LoRA fine-tune** for better English voice quality
7. **Begin Tamil expansion** with Common Voice + IndicVoices + LoRA
8. **Begin Hindi expansion** same approach
9. **Launch free service**
