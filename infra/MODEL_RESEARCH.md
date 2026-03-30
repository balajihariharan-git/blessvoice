# BlessVoice — GPU Model Research

> **Researched**: 2026-03-28
> **Status**: PersonaPlex IS publicly available. Architecture options documented.
> **GPU Target**: AWS g5.xlarge (NVIDIA A10G, 24GB VRAM)

---

## 1. PersonaPlex-7B-v1 (Voice Model)

### Availability: PUBLIC (Gated)

PersonaPlex-7B-v1 was released by NVIDIA on January 20, 2026. It is a 7B parameter
full-duplex speech-to-speech model built on top of the Moshi architecture (Kyutai Labs).
The weights are gated on HuggingFace — you must accept the license and use a HF token.

| Field | Value |
|-------|-------|
| HuggingFace | https://huggingface.co/nvidia/personaplex-7b-v1 |
| GitHub | https://github.com/NVIDIA/personaplex |
| Parameters | 7B |
| Architecture | Moshi (Mimi codec + Temporal/Depth Transformers) |
| License | CC-BY 4.0 (free commercial use) |
| Format | PyTorch safetensors |
| Access | Gated — requires HF token + license acceptance |
| VRAM (fp16) | ~18-20 GB |
| VRAM (int4) | ~10-12 GB (community quantized) |
| Latency | ~200ms on 24GB GPU |
| Turn switching | 0.07 seconds |

### Key Capabilities
- Full-duplex: listens and speaks simultaneously
- Voice conditioning: clone any voice from a short audio sample
- Text prompt: set persona/role/scenario via natural language
- Real-time: 200ms latency at fp16 on A10G/RTX 3090
- Inner monologue: generates text tokens alongside audio (used for transcription and knowledge injection)

### Critical Limitation: "Dumb as a Rock"
PersonaPlex is brilliant at voice I/O but has very limited factual intelligence. The 7B
backbone (Helium) was trained on synthetic dialogues focused on persona-shaping, NOT
factual knowledge relay. Key issues:

1. **Cannot relay specific facts** — training data never included "tell the user these facts" patterns
2. **Task drift** — drifts from role prompt beyond 10-15 minutes
3. **Fabricates facts** — hallucinates freely when asked knowledge questions
4. **No RAG/tool use** — no built-in mechanism for external knowledge

This is exactly why BlessVoice needs a hybrid architecture (PersonaPlex for voice + separate LLM for intelligence).

### Inner Monologue Injection (Workaround)
There IS a documented workaround for injecting external knowledge:
- PersonaPlex has an "inner monologue" text channel
- You can drip-feed text at ~20 characters per 80ms (matching Moshi's per-frame consumption)
- Burst injection (300+ chars at once) breaks the temporal alignment and degenerates output
- This is fragile and undocumented by NVIDIA — community-discovered

### Known Workaround: Talker-Reasoner Architecture
The community has built a "Talker-Reasoner" pattern (based on DeepMind's "Thinking Fast and Slow"):
- **System 1 (Talker)**: PersonaPlex handles voice I/O, fast responses
- **System 2 (Reasoner)**: External LLM (Llama, etc.) handles factual reasoning
- Server gates PersonaPlex audio during reasoner responses
- Plays clean TTS from the reasoner instead, with ~500ms to first audio
- PersonaPlex receives knowledge through the inner monologue channel

---

## 2. Moshi (Fallback / Base Architecture)

PersonaPlex IS available, so Moshi is not needed as primary. However, understanding
Moshi is useful since PersonaPlex is built on top of it.

| Field | Value |
|-------|-------|
| GitHub | https://github.com/kyutai-labs/moshi |
| HuggingFace | https://huggingface.co/kyutai/moshiko-pytorch-bf16 |
| Parameters | 7B |
| License | CC-BY 4.0 |
| Backends | PyTorch (200ms/24GB), Rust (180ms/8GB), MLX (250ms/macOS) |
| Language | English only (multilingual planned Q1 2026) |

---

## 3. Llama 3.1 8B Instruct (Intelligence Model)

| Field | Value |
|-------|-------|
| HuggingFace (AWQ) | https://huggingface.co/hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4 |
| HuggingFace (GGUF) | https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF |
| Parameters | 8B |
| License | Llama 3.1 Community License (free under 700M users) |
| VRAM (fp16) | ~16 GB |
| VRAM (AWQ INT4) | ~4-5 GB |
| VRAM (GGUF Q4_K_M) | ~5-6 GB |
| Performance (vLLM AWQ) | ~68 tok/s single stream, ~485 tok/s at 10 concurrent |

---

## 4. VRAM Budget on A10G (24 GB)

### Option A: Both Models on GPU (Requires Quantization)

```
PersonaPlex 7B (INT4 quantized)    ~10-12 GB
Llama 3.1 8B (AWQ INT4)            ~4-5 GB
CUDA overhead / KV cache            ~3-4 GB
─────────────────────────────────────────────
Total                               ~17-21 GB  (TIGHT but feasible)
```

**Verdict**: Feasible ONLY if PersonaPlex is quantized to INT4. No headroom for
concurrent users or large KV caches. Latency may increase ~20-30% from quantization.

### Option B: PersonaPlex on GPU (fp16), Llama on CPU (RECOMMENDED FOR START)

```
PersonaPlex 7B (fp16)              ~18-20 GB
CUDA overhead / KV cache            ~2-4 GB
─────────────────────────────────────────────
GPU Total                           ~20-24 GB  (fills the A10G)

Llama 3.1 8B (GGUF Q4_K_M)        ~6 GB RAM (CPU via llama.cpp)
```

**Verdict**: PersonaPlex gets full GPU quality. Llama runs on CPU with llama.cpp
at ~15-25 tok/s — slower but acceptable since the LLM only generates 1-2 sentences
(~30-80 tokens) per turn. That's 1-3 seconds for the text, which is hidden by
the TTS latency anyway.

### Option C: PersonaPlex Only, Inner Monologue Drip-Feed

```
PersonaPlex 7B (fp16)              ~18-20 GB
─────────────────────────────────────────────
GPU Total                           ~18-20 GB
```

**Verdict**: Simplest setup. Use PersonaPlex alone for basic conversations. For
knowledge-heavy questions, pause PersonaPlex audio, run Llama on CPU, drip-feed
the answer through the inner monologue channel. Fragile but documented in community.

---

## 5. Serving Framework Recommendation

### PersonaPlex: Native PyTorch (via NVIDIA's own server)
- PersonaPlex ships with `python -m moshi.server` which runs a WebSocket server on port 8998
- Uses Opus codec for audio streaming
- This is the ONLY supported serving method — vLLM does not support speech-to-speech models
- We wrap this server with our own FastAPI WebSocket proxy

### Llama 3.1 8B: llama.cpp (CPU) or vLLM (GPU)
- **If running on CPU (Option B)**: `llama-cpp-python` with GGUF Q4_K_M weights
  - ~15-25 tok/s on g5.xlarge CPU (4 vCPUs, 16 GB RAM)
  - Good enough for 1-2 sentence responses
- **If running on GPU (Option A)**: vLLM with AWQ INT4
  - ~68 tok/s, much faster
  - But requires PersonaPlex to be quantized too

### Recommended Architecture for v1

```
┌──────────────────────────────────────────────────────────────────┐
│                        BlessVoice Server                         │
│                                                                  │
│  ┌─────────────────┐     ┌──────────────────┐                   │
│  │   FastAPI + WS   │────>│  PersonaPlex 7B  │  GPU (fp16)      │
│  │   (port 8000)    │<────│  (port 8998)     │  ~20 GB VRAM     │
│  └────────┬─────────┘     └──────────────────┘                   │
│           │                                                      │
│           │ (for knowledge-heavy questions)                       │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Llama 3.1 8B   │  CPU (llama.cpp, GGUF Q4_K_M)             │
│  │  (in-process)   │  ~6 GB RAM, ~20 tok/s                     │
│  └─────────────────┘                                            │
│                                                                  │
│  Pipeline: User audio → PersonaPlex (voice) → response audio    │
│            If complex question detected → Llama generates text   │
│            → drip-fed to PersonaPlex inner monologue             │
│            OR → TTS fallback while PersonaPlex audio gated       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Download URLs Summary

| Model | URL | Size |
|-------|-----|------|
| PersonaPlex 7B v1 | `nvidia/personaplex-7b-v1` (HuggingFace, gated) | ~14 GB |
| Llama 3.1 8B Instruct GGUF | `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` (Q4_K_M) | ~4.9 GB |
| Llama 3.1 8B Instruct AWQ | `hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4` | ~4.5 GB |

---

## 7. Open Questions / Risks

1. **PersonaPlex quantization quality** — INT4 quantization of speech models can degrade audio quality significantly. Need to test before committing to Option A.
2. **Inner monologue stability** — The drip-feed injection is a community hack, not officially supported. May break with model updates.
3. **WebSocket protocol bridging** — PersonaPlex uses Opus-over-WebSocket on port 8998. BlessVoice uses raw PCM on port 8000. Need a codec bridge.
4. **Concurrent users** — With ~20GB VRAM used, there's no room for batched inference. The A10G setup is single-user only.
5. **g5.xlarge CPU** — Only 4 vCPUs. llama.cpp may be slow. If unacceptable, upgrade to g5.2xlarge (8 vCPUs, 32 GB RAM) for ~$0.50/hr more.

---

## Sources

- [PersonaPlex HuggingFace](https://huggingface.co/nvidia/personaplex-7b-v1)
- [PersonaPlex GitHub](https://github.com/NVIDIA/personaplex)
- [PersonaPlex Research Page](https://research.nvidia.com/labs/adlr/personaplex/)
- [PersonaPlex "Dumb as a Rock" Analysis](https://pub.towardsai.net/nvidia-personaplex-incredible-achievement-but-dumb-as-f-278384ac1bbe)
- [Talker-Reasoner VAOS Voice Bridge](https://gist.github.com/jmanhype/5aefd67d9e67b37a8b408abdab39b6d3)
- [Moshi GitHub](https://github.com/kyutai-labs/moshi)
- [Llama 3.1 8B AWQ](https://huggingface.co/hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4)
- [Llama 3.1 8B GGUF](https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF)
- [vLLM Llama Deployment Guide](https://simplismart.ai/blog/deploy-llama-3-1-8b-using-vllm)
- [DataCamp PersonaPlex Tutorial](https://www.datacamp.com/tutorial/nvidia-personaplex-tutorial)
