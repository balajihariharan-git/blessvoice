# BlessVoice — Claude Code Instructions

## Session Startup — MANDATORY
1. Read this file first
2. Read CONCEPT.md for full project context
3. Check `gh issue list -R balajihariharan-git/blessvoice` for current work
4. Set local git identity before any commits (see Git section)

## What is BlessVoice?
Real-time AI voice conversation platform. Users talk to an AI that speaks back with emotion, in real-time, for free. Built on PersonaPlex (NVIDIA's improved Moshi) with LoRA fine-tuning for multiple languages.

## Architecture
- **Phase 1 (current)**: Pipeline prototype — OpenAI Whisper API + GPT-4o-mini + OpenAI TTS
- **Phase 2 (target)**: PersonaPlex on GPU — true voice-to-voice, no text intermediary
- See CONCEPT.md for full architecture details

## Project Structure
```
D:\BlessVoice\
├── app/
│   ├── __init__.py      # Package init
│   ├── config.py        # Configuration (VAD, model settings)
│   ├── pipeline.py      # Streaming STT → LLM → TTS (Phase 1)
│   └── main.py          # FastAPI + WebSocket server
├── web/
│   └── index.html       # Frontend (orb UI, VAD, PCM playback)
├── models/              # Downloaded model files (GITIGNORED, ~2.5GB+)
├── run.py               # Entry point
├── requirements.txt     # Python dependencies
├── CONCEPT.md           # Product bible — architecture, decisions, roadmap
├── CLAUDE.md            # This file
└── .gitignore
```

## Git Identity — CRITICAL
This repo uses the `balajihariharan-git` GitHub account.
```
git config user.name "balajihariharan-git"
git config user.email "balajihariharan.git@gmail.com"
```
**NEVER commit as errakaaram or shackleai to this repo.**

## Git Workflow
- PR workflow mandatory — never push directly to main
- Branch naming: `feature/description`, `fix/description`, `infra/description`
- Commit messages: conventional commits (feat:, fix:, docs:, infra:, ml:)

## Agent Assignments
| Domain | Agent |
|--------|-------|
| Infrastructure (AWS, Docker, deploy) | devops-engineer |
| Backend (FastAPI, WebSocket, pipeline) | platform-engineer |
| ML (PersonaPlex, LoRA, fine-tuning) | platform-engineer |
| Frontend (browser UI, audio) | frontend-engineer |
| Data pipeline (audio processing) | database-architect |
| Testing | test-engineer |
| Docs | docs-writer |
| Code review | code-reviewer |
| Issue management | issue-architect |

## Key Decisions
- **Base model**: PersonaPlex (NVIDIA's improved Moshi) — full-duplex, 100% interrupt
- **Fine-tuning**: LoRA adapters for voice quality, Tamil, Hindi, culture, personality
- **No paid APIs in production**: GPU self-hosted, all open-source models
- **Phase 1 uses OpenAI APIs** for prototyping only (costs ~$0.005/turn)

## Running the Prototype
```bash
cd D:\BlessVoice
python run.py
# Open http://localhost:8000
# Requires OPENAI_API_KEY in environment
```
