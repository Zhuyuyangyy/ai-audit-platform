# REPRODUCE.md - ai-audit-platform (AgentShield V1)

## Prerequisites

- **Python**: 3.10+
- **OS**: Linux / macOS / Windows
- **GPU**: Not required

## Install

```bash
cd ai-audit-platform
pip install -r requirements.txt
```

Dependencies: fastapi, uvicorn, pydantic, sqlalchemy, aiosqlite, httpx, jinja2, python-multipart

## Smoke Test

```bash
cd backend
python -m pytest tests/ -v
```

## Run Server

```bash
python main.py
```

Or:
```bash
cd backend
python app.py
```

## Run Demo

```bash
# Demo evidence scripts
python docs/demo_evidence/init_db.py
python docs/demo_evidence/run_demo.py
python docs/demo_evidence/verify_fixed.py
```

## Expected Outputs

- AI output compliance audit system
- Hallucination detection + RAG evidence tracing
- Risk entropy scoring + hard risk gating
- Human review routing + audit log retention
- Hard gate test: 5/5 pass (85.0/human_review for high-risk, 0.0/allow for low-risk)

## Known Issues

- Multiple files reference `D:\ZYY Project` paths (docs scripts)
- SQLite database auto-created on first run
- `start.sh` contains hardcoded paths
