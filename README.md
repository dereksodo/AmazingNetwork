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

Requirements: Python 3.11+ and a web browser. Nothing else needs to be installed by hand: no database, no paid API keys. All data is fictional and kept in memory.

### Quick start (macOS / Linux)

```bash
git clone https://github.com/dereksodo/AmazingNetwork.git
cd AmazingNetwork
./run.sh
```

`run.sh` does everything for you:

1. checks that Python is 3.11 or newer;
2. on the first run, creates `backend/.venv` and installs the packages from `backend/requirements-dev.txt` (FastAPI, uvicorn, nh3, pytest, …). This takes about a minute and needs internet. Later runs skip this step unless the requirements files change;
3. starts the backend on port 8000 and serves the frontend on port 5173.

Then open:

- http://localhost:5173: the PoC client. Pick a fictional user, create a post, then fetch it or switch user to see the audience rules.
- http://127.0.0.1:8000/docs: interactive API docs.
- http://127.0.0.1:8000/api/v1/health: should show `{"status":"ok"}`.

Press **Ctrl+C** to stop both servers.

Run the tests (29 tests, including a contract test that fails if the backend drifts from `shared/contracts/openapi.yaml`):

```bash
./run.sh test
```

### Manual setup (Windows, or if you prefer)

**Terminal 1: backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS / Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --port 8000
```

**Terminal 2: frontend**

```bash
cd frontend
python -m http.server 5173
```

**Tests**: inside `backend/`, with the venv active, run `pytest`.

### Troubleshooting

| Problem | Fix |
|---|---|
| `Python 3.11 or newer is required` | Install a recent Python, or run `PYTHON=python3.12 ./run.sh` |
| `Address already in use` | Another program is using port 8000 or 5173; stop it, or close an old `run.sh` |
| Frontend says "Is the backend running?" | Start the backend first and check the health URL above |
| `permission denied: ./run.sh` | `chmod +x run.sh` or `bash run.sh` |
| Packages look broken | Delete `backend/.venv` and run `./run.sh` again |

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
run.sh              One-command local start (installs dependencies)
backend/            FastAPI app (app/api, app/policy.py, app/store.py) and tests/
frontend/           PoC browser client (React app in Assignment 2)
shared/contracts/   OpenAPI contract shared by frontend and backend
docs/report/        report.md → Connect_Report.pdf
docs/diagrams/      Mermaid sources for C4, sequence and ER diagrams
docs/adr/           Architecture decision records
infra/              Local infrastructure config (docker-compose in Assignment 2)
.github/            CI workflow, CODEOWNERS, PR template
```
