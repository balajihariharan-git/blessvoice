# MLLM — Multi-LLM Smart Router Concept

> **Created**: 2026-03-30
> **Status**: Idea / Pre-Concept
> **Origin**: Evolved from BlessVoice architecture discussions
> **Relationship**: Independent product. BlessVoice is the first customer.

---

## Vision

A free, self-hosted smart router that hosts multiple open-source LLMs on a single GPU and automatically routes each query to the BEST model for that specific task. Users get one API key, and every request is answered by whichever model is strongest at that type of question.

**Nobody is offering this for free today.**

```
User sends: "Write a Python sorting algorithm"
    │
    ▼
┌─────────────────────────────────────────────┐
│              SMART ROUTER                    │
│                                             │
│  Classifier analyzes query type:            │
│  → "This is a CODING question"              │
│  → Route to Qwen Coder (best at coding)     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
            Qwen Coder responds
            (best possible answer for this query type)
```

```
User sends: "Solve this differential equation"
    │
    ▼
┌─────────────────────────────────────────────┐
│              SMART ROUTER                    │
│                                             │
│  Classifier analyzes query type:            │
│  → "This is a MATH/REASONING question"      │
│  → Route to DeepSeek R1 (best at reasoning) │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
            DeepSeek R1 responds
            (best possible answer for this query type)
```

---

## The Problem This Solves

Today, users must CHOOSE which LLM to use. But no single model is best at everything:

| Task | Best Free Model | 2nd Best |
|------|----------------|----------|
| Coding | **Qwen 2.5 Coder** | DeepSeek Coder |
| Math/reasoning | **DeepSeek R1** | Qwen 72B |
| General English | **Llama 3.3 70B** | Qwen 72B |
| Multilingual (Tamil, Hindi) | **Qwen 72B** | Llama 3.3 70B |
| European languages | **Mistral Large** | Llama 3.3 70B |
| Creative writing | **Llama 3.3 70B** | Mistral |
| Chinese | **Qwen 72B** | DeepSeek |

**Users don't know this. They pick one model and get suboptimal answers for half their questions.**

MLLM fixes this: one endpoint, always the best model, automatically.

---

## How It Works — Technical Architecture

### Approach A: Small Models Always Loaded (Recommended for Start)

```
Single GPU: 48GB (L40S) or 24GB (A10G)

Always loaded in memory:
┌──────────────────────────────────────┐
│  Router Classifier (~100 MB)          │  Tiny model that categorizes queries
│  Llama 3.1 8B Q4   (~5 GB)          │  General English
│  Qwen 2.5 7B Q4    (~5 GB)          │  Coding + multilingual
│  DeepSeek 7B Q4    (~5 GB)          │  Reasoning + math
│  Mistral 7B Q4     (~5 GB)          │  European languages
│                     ─────            │
│  Total:            ~20 GB            │  Fits on 24GB GPU!
└──────────────────────────────────────┘

All four models loaded simultaneously.
Router picks best one per query. Zero switching delay.
Response in <1 second.
```

### Approach B: Large Models Load on Demand (Better Quality)

```
Single GPU: 48GB (L40S)

Loaded on demand (10-30 second switch):
  Coding query    → Load Qwen Coder 32B  (~20 GB)
  Reasoning query → Load DeepSeek R1 70B (~35 GB)
  General query   → Load Llama 70B       (~35 GB)

Better answers but slower model switching.
Best for batch/async workloads, not real-time chat.
```

### Approach C: Hybrid (Best of Both)

```
Always loaded: 4x 7-8B models (for instant responses)
Background: Pre-load the 70B version if query needs deeper thinking

User asks simple question → 7B model responds instantly (<1s)
User asks complex question → 7B gives quick answer,
                              70B refines it in background,
                              sends improved answer
```

---

## The Smart Router — How It Classifies Queries

### Option 1: Tiny Classifier Model (~100MB)

```python
# Fine-tuned DistilBERT or similar small model
# Trained on labeled dataset of query types

categories = {
    "coding":     → route to Qwen Coder
    "math":       → route to DeepSeek
    "reasoning":  → route to DeepSeek
    "general":    → route to Llama
    "creative":   → route to Llama
    "multilingual": → route to Qwen
    "european":   → route to Mistral
}

# Classification takes <10ms. Negligible overhead.
```

### Option 2: Keyword + Heuristic Rules (Simpler, No ML)

```python
if contains_code_keywords(query):      → Qwen Coder
elif contains_math_symbols(query):     → DeepSeek
elif detected_language != "english":   → Qwen (multilingual)
elif is_reasoning_question(query):     → DeepSeek
else:                                  → Llama (default)
```

### Option 3: Let the Models Vote (Highest Quality, Slower)

```
Send query to ALL models simultaneously
Each model responds
Pick the BEST response (by confidence score or length/quality heuristic)

Pro: Always the best answer
Con: 4x GPU compute, 4x slower, 4x power usage
Only viable for non-real-time use cases
```

---

## What Exists Today (Competitive Landscape)

| Product | What It Does | Free? | Self-Hosted? | Open Source? |
|---------|-------------|-------|-------------|-------------|
| **OpenRouter** | Routes to 100+ models (cloud APIs) | No ($) | No | No |
| **Martian** | Smart model routing startup | No ($) | No | No |
| **Not Diamond** | Picks optimal model per query | No ($) | No | No |
| **LiteLLM** | Unified API proxy for any LLM | Yes | Yes | **Yes (MIT)** |
| **vLLM** | Serve multiple models efficiently | Yes | Yes | **Yes (Apache 2.0)** |
| **Ollama** | Run local models easily | Yes | Yes | **Yes (MIT)** |
| **MLLM (us)** | **Smart router + free API keys + self-hosted** | **Yes** | **Yes** | **Yes** |

**Gap in the market**: Nobody offers a FREE, self-hosted smart router that automatically picks the best open-source model per query AND provides free API keys to users.

---

## The User Experience

### For Developers (API Users)

```
# Get a free API key from mllm.yourdomain.com
# Use it like OpenAI's API — same format, drop-in replacement

from openai import OpenAI

client = OpenAI(
    base_url="https://mllm.yourdomain.com/v1",
    api_key="free_key_abc123"
)

response = client.chat.completions.create(
    model="auto",              # ← MLLM picks the best model
    messages=[{"role": "user", "content": "Write a Python web scraper"}]
)

# Behind the scenes: MLLM detected "coding" → routed to Qwen Coder
# User doesn't need to know which model answered
```

### For BlessVoice (Internal Customer)

```
BlessVoice voice pipeline
    │
    │ User asks a complex question via voice
    │
    ▼
MLLM Router (same GPU)
    │
    ├── "What is quantum computing?" → Llama (general knowledge)
    ├── "Write me a poem in Tamil" → Qwen (multilingual + creative)
    ├── "Solve 2x + 5 = 15" → DeepSeek (math)
    │
    ▼
Best model responds → PersonaPlex speaks it in natural voice
```

---

## Cost Structure

### Infrastructure (Same GPU as BlessVoice)

| Setup | GPU | VRAM | What Fits | Monthly Cost |
|-------|-----|------|-----------|-------------|
| Dev/test | A10G | 24GB | 4x 7B models + router | $27/mo (spot, 3hrs/day) |
| Production | L40S | 48GB | 4x 7B + 1x 70B on demand | $50/mo (spot, 3hrs/day) |
| Scale | 2x A10G | 48GB | More concurrent users | $54/mo (spot) |

### Revenue Model (If Commercialized)

```
Free tier:    100 requests/day per API key ($0)
              → Funded by: same GPU you already run for BlessVoice
              → Cost per free user: negligible (queries take milliseconds)

Premium tier: Unlimited requests + priority routing ($5-10/month)
              → For developers building apps on your API

Enterprise:   Dedicated GPU, SLA, custom models ($100+/month)
```

---

## Models Comparison — Full Benchmark Table

| Model | Params | Owner | MMLU | Coding | Math | Multilingual | License | Free? |
|-------|--------|-------|------|--------|------|-------------|---------|-------|
| Llama 3.3 70B | 70B | Meta (USA) | ~86% | Good | Good | English-focused | Community | Yes |
| Qwen 2.5 72B | 72B | Alibaba (China) | ~88% | **Best** | Great | **Best** (100+ langs) | Apache 2.0 | Yes |
| DeepSeek V3 | 671B MoE | DeepSeek (China) | ~88% | Great | **Best** | Good | MIT | Yes |
| DeepSeek R1 | 671B MoE | DeepSeek (China) | ~90% | Great | **Best** | Good | MIT | Yes |
| Mistral Large 2 | 123B | Mistral (France) | ~84% | Good | Good | European best | Apache 2.0 | Yes |

All free. All self-hostable. All forkable. Zero license fees.

### Why Each Model Wins in Its Category

**Qwen (Alibaba) — Best at Coding + Multilingual**
- Trained on massive Chinese + English + multilingual corpus
- Alibaba cloud infrastructure = huge training budget
- Apache 2.0 = most permissive license, zero restrictions

**DeepSeek — Best at Reasoning + Math**
- Mixture-of-Experts architecture (only activates relevant parts = efficient)
- R1 model uses chain-of-thought (thinks step by step before answering)
- MIT license = most permissive, zero restrictions

**Llama (Meta) — Best General English + Largest Community**
- Backed by Meta's $130B/year revenue
- Largest open-source community (most tools, tutorials, fine-tunes)
- Community License (free under 700M users)

**Mistral (France) — Best for European Languages**
- French company, trained with European language focus
- Strong at French, German, Spanish, Italian
- Apache 2.0

---

## Relationship to BlessVoice

```
BlessVoice (Voice Product)
    │
    │  Uses MLLM as its "brain"
    │  PersonaPlex handles voice
    │  MLLM handles intelligence
    │
MLLM (Intelligence Layer)
    │
    │  Can also be offered as standalone API
    │  Free API keys for developers
    │  BlessVoice is just one consumer
    │
    ▼
Two products, one GPU, shared infrastructure
```

---

## Open Questions

1. **Name**: What do we call this product?
2. **Priority**: Build MLLM before or after BlessVoice voice is working?
3. **API compatibility**: OpenAI-compatible API format? (enables drop-in replacement)
4. **Router training data**: How to build the query classification dataset?
5. **Rate limiting**: How many free requests per user per day?

---

## Next Steps (If We Pursue This)

1. Build router classifier (keyword-based first, ML-based later)
2. Set up vLLM to serve 4 models on single GPU
3. Build OpenAI-compatible API wrapper
4. Create API key management system
5. Deploy on same AWS GPU as BlessVoice
6. Open for free public beta
