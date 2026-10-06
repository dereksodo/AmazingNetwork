# Connect — Campus Social Network (AI1220 Assignment 1)

Connect is a social network for the university community: students and groups share updates, hold discussions, co-write announcements and events, and control who sees their content. Moderators handle reports, with help from an AI triage assistant.

| What | Where |
|---|---|
| Report (PDF, submitted) | [`docs/report/Connect_Report.pdf`](docs/report/Connect_Report.pdf) — source: [`docs/report/report.md`](docs/report/report.md) |
| Diagram sources (Mermaid) | [`docs/diagrams/`](docs/diagrams/) |
| Architecture decision records | [`docs/adr/`](docs/adr/) |
| Interface contract used by the PoC | [`shared/contracts/openapi.yaml`](shared/contracts/openapi.yaml) |
| Proof of concept — backend | [`backend/`](backend/) (FastAPI) |
| Proof of concept — frontend | [`frontend/`](frontend/) (plain HTML + JS) |
| 3-minute demo script | [`docs/demo-script.md`](docs/demo-script.md) |
| Team decisions log | [`DECISIONS.md`](DECISIONS.md) |

## Proof of concept: setup and run

Requirements: Python 3.11+ and a web browser. No paid API keys, no database — all data is fictional and kept in memory.

**1. Backend** (terminal 1)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --port 8000
```

Check it: open http://127.0.0.1:8000/api/v1/health (should show `{"status":"ok"}`). Interactive API docs: http://127.0.0.1:8000/docs.

**2. Frontend** (terminal 2)

```bash
cd frontend
python3 -m http.server 5173
```

Open http://localhost:5173. Pick a fictional user, create a post, then fetch it or switch user to see audience rules in action.

**3. Tests** (terminal 1, inside `backend/` with the venv active)

```bash
pytest
```

The tests include a contract test that fails if the backend drifts from `shared/contracts/openapi.yaml`.

### Fictional users

| `X-Demo-User` | Who | Memberships |
|---|---|---|
| `aisha` | Student | Robotics Club (1) |
| `omar` | Student | Chess Society (2); follows Aisha |
| `lina` | Officer | Robotics Club (1) |
| `sam` | Moderator | — (can view all posts) |

### What the PoC simplifies (see report §4)

| Planned architecture | Proof of concept |
|---|---|
| React + TipTap rich-text editor | Plain HTML page; rich text typed as HTML in a textarea |
| University SSO (OIDC) + session token | Mock header `X-Demo-User` |
| PostgreSQL | In-memory repository with the same methods |
| Redis, WebSocket gateway, worker, LLM | Not included |
| Rate limiting, audit log | Not included |

## Rebuilding the report PDF

The report is written in Markdown and the diagrams in Mermaid. After editing either:

```bash
pip install markdown
python docs/report/build.py      # needs Google Chrome; writes docs/report/Connect_Report.pdf
```

## Configuration and secrets

Configuration comes from environment variables; see [`.env.example`](.env.example). Real values go in `.env`, which is git-ignored. The browser never receives secrets: the LLM key (Assignment 2) is read only by the backend worker.

## Repository layout

```
backend/            FastAPI app (app/api, app/policy.py, app/store.py) and tests/
frontend/           PoC browser client (React app in Assignment 2)
shared/contracts/   OpenAPI contract shared by frontend and backend
docs/report/        report.md → Connect_Report.pdf
docs/diagrams/      Mermaid sources for C4, sequence and ER diagrams
docs/adr/           Architecture decision records
infra/              Local infrastructure config (docker-compose in Assignment 2)
.github/            CI workflow, CODEOWNERS, PR template
```
