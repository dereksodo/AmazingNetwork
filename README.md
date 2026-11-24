# Connect: Campus Social Network (AI1220)

Students and student groups share updates, discuss, co-write announcements and events, and control who sees their content. Moderators handle reports with an advisory AI assistant.

| What | Where |
|---|---|
| Summary of Assignment 2 (PDF) | [docs/summary.pdf](docs/summary.pdf) |
| API specification | [docs/openapi.json](docs/openapi.json), live at http://127.0.0.1:8000/docs |
| WebSocket channels | [docs/websocket.md](docs/websocket.md) |
| Requirements status and traceability | [docs/requirements-status.md](docs/requirements-status.md) |
| Diagrams, decisions | [docs/diagrams/](docs/diagrams/), [docs/adr/](docs/adr/) |
| How the code is organized | [backend/README.md](backend/README.md), [frontend/README.md](frontend/README.md) |
| Demonstration | [docs/demo-script.md](docs/demo-script.md) |
| Assignment 1 report | [docs/report/Connect_Report.pdf](docs/report/Connect_Report.pdf) |

## Install and run

Needs Python 3.11 or newer and Node.js 20.19+ or 22.12+, on macOS or Linux (Windows: WSL).

```bash
git clone https://github.com/dereksodo/AmazingNetwork.git
cd AmazingNetwork
./run.sh
```

The first run installs everything, creates `.env` from `.env.example` and loads the demonstration data. Open http://localhost:5173 and sign in as `aisha@campus.example` with the password `demo-password`. Other handles: `omar`, `lina` (owner of Robotics Club), `karim` (officer), `yusuf`, `sam` and `maya` (moderators), `dean` (school admin). Each browser tab has its own sign-in.

| Command | Does |
|---|---|
| `./run.sh` | starts backend (8000) and frontend (5173) |
| `./run.sh seed` | replaces **all** data with the demonstration data (stop the product first) |
| `./run.sh test` | runs the backend tests |
| `./run.sh lint` | checks Ruff, Prettier and ESLint |

To start the two servers by hand after the first run:

```bash
cd backend && .venv/bin/uvicorn app.main:app --port 8000 --env-file ../.env
```

```bash
cd frontend && npm run dev
```

## Configuration

Every setting is in [.env.example](.env.example). `.env` is git-ignored.

**AI model.** The default is `gpt-6.1-terra` from OpenAI: put your key in `CONNECT_LLM_API_KEY` in `.env`. For a local model, load `qwen/qwen3-4b` in LM Studio, start its server and set `CONNECT_LLM_BASE_URL=http://localhost:1234/v1` and `CONNECT_LLM_MODEL=qwen/qwen3-4b`. Any OpenAI-compatible server works by changing settings only, for example DeepSeek:

```text
CONNECT_LLM_BASE_URL=https://api.deepseek.com
CONNECT_LLM_MODEL=deepseek-chat
CONNECT_LLM_API_KEY=<your key>
```

Without a model everything else works; reports are shown as "unscored".

Data is stored in `backend/connect.db` and survives restarts. All data is fictional.
