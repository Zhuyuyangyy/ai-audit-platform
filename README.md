<div align="center">

# AgentShield -- AI Compliance Audit Platform

**Risk Entropy Scoring + Hard Gate Circuit Breaker for Generative AI Output Safety**

Hallucination Detection | RAG Policy Traceability | Risk Fuse Controller | Audit Trail

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-Persistent-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/Coverage-85%25-brightgreen)](tests/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker&logoColor=white)](Dockerfile)

</div>

---

## Overview

AgentShield is a compliance audit middleware for generative AI applications, designed to prevent high-risk hallucinated outputs, unsubstantiated policy conclusions, and non-compliant content from being automatically released. It operates as a safety backstop layer between LLM outputs and end users, implementing a novel **hard gate** mechanism that overrides score-based decisions when critical risk signals (hallucination, unverified claims) are detected.

**Key Differentiators:**
- Hard gate mechanism prevents risk dilution through weighted averaging
- Multi-dimensional risk entropy model (5 dimensions: secret, privacy, hallucination, policy error, social engineering)
- RAG policy evidence traceability with 4+ built-in regulatory frameworks
- Session-level circuit breaker with escalating responses
- SQLite-backed audit trail for full traceability

## Key Features

- **Hallucination Detection** -- Identifies when LLM outputs contain fabricated facts or unverifiable claims; triggers hard gate escalation to human review
- **RAG Policy Evidence Traceability** -- Links audit conclusions to specific regulatory provisions (Personal Information Protection Law, Cybersecurity Law, Data Security Law, Generative AI Measures)
- **Risk Entropy Scoring** -- Multi-dimensional coupling model computing a 0-100 risk score with score floor protection (hallucination alone >= 70, hallucination + unverified >= 85)
- **Hard Gate Circuit Breaker** -- Three priority levels: hallucination + unverified claim forces human_review at 85+, hallucination alone at 70+, unverified claim alone triggers human_review
- **Risk Fuse Controller** -- 6-tier response: allow / warn / mask / refuse / human_review / block; session-level persistent state with automatic escalation after 3 consecutive high-risk interactions
- **Audit Logger** -- SQLite-backed persistent logging of all audit decisions, risk scores, and fuse actions
- **Prompt Risk Detector** -- Pre-screening of user inputs for secret queries, social engineering attempts, and policy manipulation

## Architecture

```
                         +---------------------------+
                         |   Vue3 Frontend           |
                         |   (index.html)            |
                         +-------------+-------------+
                                       |
                                       | HTTP / REST
                                       v
                         +-------------+-------------+
                         |   FastAPI Backend         |
                         |   (Port 8014)             |
                         +-------------+-------------+
                                       |
                    +------------------+------------------+
                    |                  |                  |
          +---------v--------+ +------v------+ +--------v---------+
          | Prompt Risk      | | Output      | | RAG Tracer       |
          | Detector         | | Compliance  | | (Policy Evidence)|
          |                  | | Checker     | |                  |
          +--------+---------+ +------+------+ +--------+---------+
                   |                |                    |
                   +-------+--------+--------------------+
                           |
                +----------v----------+
                | Audit Risk Scorer   |
                | (5-Dim Entropy)     |
                +----------+----------+
                           |
                +----------v----------+
                | Risk Fuse Controller|
                | (Hard Gate + Score) |
                +----------+----------+
                           |
                +----------v----------+
                | Model Audit Logger  |
                | (SQLite Persist)    |
                +---------------------+
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend Framework | FastAPI + Uvicorn | Async REST API server |
| Frontend | Vue3 (Single File) | Browser-based dashboard |
| Database | SQLite + SQLAlchemy | Persistent audit storage |
| Data Validation | Pydantic 2.0+ | Request/response schemas |
| HTTP Client | httpx | Async external API calls |
| Testing | pytest + pytest-cov | Unit & integration tests |
| CI/CD | GitHub Actions | Lint + test + Docker pipeline |
| Containerization | Docker + Docker Compose | Deployment & orchestration |
| Language | Python 3.12+ | Core runtime |

## Quick Start

### Prerequisites

- Python 3.12 or higher
- pip (Python package manager)

### Installation

```bash
git clone https://github.com/<your-org>/ai-audit-platform.git
cd ai-audit-platform
pip install -r requirements.txt
```

### Run the Backend

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8014 --reload
```

Or use the startup script:

```bash
# Windows
start.bat

# Linux/macOS
bash start.sh
```

API documentation: `http://localhost:8014/docs`
Frontend dashboard: `http://localhost:8014/frontend`

### Run Tests

```bash
# Run all tests with coverage
cd backend
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_prompt_risk_detector.py -v

# Run regression tests
python test_hard_gate.py
```

### Docker

```bash
# Build and run with Docker
docker build -t ai-audit-platform .
docker run -p 8014:8014 ai-audit-platform

# Or use Docker Compose
docker-compose up -d
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/audit_prompt` | POST | Pre-screen user prompt for risks |
| `/api/v1/audit_output` | POST | Audit LLM output for compliance |
| `/api/v1/audit_interaction` | POST | Full round-trip audit (prompt + output) |
| `/api/v1/add_policy_doc` | POST | Add policy document to RAG knowledge base |
| `/api/v1/get_policy_docs` | GET | List all policy documents |
| `/api/v1/get_audit_log/{log_id}` | GET | Get specific audit log |
| `/api/v1/get_audit_report/{session_id}` | GET | Get session audit report |
| `/api/v1/get_session_audit_logs/{session_id}` | GET | Get all session audit logs |
| `/api/v1/health` | GET | Health check |
| `/compliance/risk_heatmap` | POST | Generate document risk heatmap |
| `/compliance/policy_search` | GET | Semantic policy search |
| `/compliance/impact_assessment` | POST | Regulatory impact assessment |
| `/compliance/dashboard_stats` | GET | Dashboard statistics |
| `/docs` | GET | Swagger API documentation |
| `/redoc` | GET | ReDoc API documentation |

## Project Structure

```
ai-audit-platform/
|-- backend/
|   |-- app/
|   |   |-- main.py                       # FastAPI application entry
|   |   |-- api/
|   |   |   +-- routes.py                 # API route handlers
|   |   |-- core/
|   |   |   +-- database.py               # SQLite initialization
|   |   |-- models/
|   |   |   +-- schemas.py                # Pydantic data models
|   |   |-- rules/
|   |   |   +-- ai_compliance_rules.json  # Compliance rule definitions
|   |   +-- services/
|   |       |-- prompt_risk_detector.py    # Input risk pre-screening
|   |       |-- output_compliance_checker.py # Output compliance check
|   |       |-- rag_tracer.py             # RAG policy evidence tracer
|   |       |-- audit_risk_scorer.py      # 5-dimension risk entropy scorer
|   |       |-- risk_fuse_controller.py   # Hard gate + circuit breaker
|   |       |-- model_audit_logger.py     # SQLite audit persistence
|   |       +-- report_generator.py       # Audit report generation
|   |-- test_hard_gate.py                 # Hard gate regression tests
|   +-- requirements.txt
|-- frontend/
|   +-- index.html                        # Vue3 dashboard
|-- tests/
|   |-- __init__.py
|   |-- conftest.py                       # Test fixtures
|   |-- test_prompt_risk_detector.py      # Prompt detector tests
|   |-- test_output_compliance_checker.py # Output checker tests
|   |-- test_risk_fuse_controller.py      # Fuse controller tests
|   |-- test_audit_risk_scorer.py         # Risk scorer tests
|   |-- test_rag_tracer.py                # RAG tracer tests
|   |-- test_model_audit_logger.py        # Audit logger tests
|   |-- test_report_generator.py          # Report generator tests
|   |-- test_api_routes.py                # API endpoint tests
|   +-- test_smoke.py                     # Basic smoke tests
|-- docs/
|   |-- ARCHITECTURE.md                   # System architecture
|   |-- API.md                            # API documentation
|   |-- AgentShield_V1_技术说明.md          # Technical documentation
|   |-- AgentShield_V1.1_技术说明.md        # V1.1 technical docs
|   |-- DEMO_GUIDE.md                     # Demo walkthrough
|   |-- SCI_Abstract.md                   # Research paper abstract
|   |-- SCI_Method.md                     # Research methodology
|   |-- demo_evidence/                    # Test evidence and logs
|   +-- reproducibility/                  # Reproducibility artifacts
|-- .github/workflows/
|   |-- ci.yml                            # CI pipeline
|   +-- test.yml                          # Test workflow
|-- docker-compose.yml                    # Docker Compose config
|-- Dockerfile                            # Docker build file
|-- TODO.md                               # Innovation suggestions
|-- INNOVATION_ROADMAP.md                 # Patent directions
|-- OPTIMIZATION_REPORT.md                # Optimization report
|-- .gitignore
+-- README.md
```

## Innovation Highlights

### Hard Gate Mechanism

Traditional risk scoring uses weighted averages that can dilute critical risk signals. AgentShield introduces hard gates that override score-based decisions:

| Signal Combination | Score Floor | Action |
|---|---|---|
| Hallucination + Unverified Claim | 85 | human_review |
| Hallucination Only | 70 | human_review |
| Unverified Claim Only | 60 | human_review |

**Validation Results** (from `test_hard_gate.py`, 5/5 passing):

| Test Case | Before Fix | After Fix |
|-----------|-----------|-----------|
| High-risk hallucination output | 30.5 / `allow` (false release) | **85.0 / `human_review`** (hard gate triggered) |
| Low-risk compliant output | 4.5 / `allow` | **0.0 / `allow`** (no false positive) |

### Multi-Dimension Risk Entropy Model

Computes risk across 5 weighted dimensions:
- **Secret** (0.25): Classified information leakage risk
- **Privacy** (0.20): Personal data exposure risk
- **Hallucination** (0.25): Fabricated content risk
- **Policy Error** (0.20): Regulatory misinterpretation risk
- **Social Engineering** (0.10): Manipulation attempt risk

## Benchmarks

| Metric | Value |
|--------|-------|
| Hard gate regression pass rate | 5/5 (100%) |
| False release rate (high-risk) | 0% (post-fix) |
| False positive rate (low-risk) | 0% |
| RAG evidence chain coverage | 4 regulatory frameworks |
| Audit log persistence | SQLite (survives restarts) |
| Test coverage | 85%+ |

## Research

This project implements research concepts from:
- Information entropy applied to AI output safety assessment
- Circuit breaker patterns adapted for AI compliance
- Multi-dimensional risk coupling models

**Related Publications:**
- `docs/GovShield_Audit_SCI_Draft_v2_IEEE.md` -- IEEE-format draft
- `docs/SCI_Abstract.md` -- Research abstract
- `docs/SCI_Method.md` -- Methodology description

## Roadmap

- [x] V1.0: Core audit engine with hard gate mechanism
- [x] V1.1: RAG policy evidence traceability
- [ ] V2.0: Dual-channel audit (output + tool call) with shadow simulation
- [ ] V2.1: ToolCallRequest interception and DatabaseShadowSimulator
- [ ] V3.0: Multi-model ensemble audit (cross-model consistency check)
- [ ] V3.1: Real-time streaming audit for token-by-token output
- [ ] V3.2: Federated audit across multiple deployment sites

## Contributing

Contributions are welcome. Please open an issue first to discuss proposed changes.

### Development Setup

```bash
# Clone repository
git clone https://github.com/<your-org>/ai-audit-platform.git
cd ai-audit-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov=app

# Run linting
ruff check .
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions, collaboration, or enterprise inquiries, please open a GitHub issue or contact the maintainers.
