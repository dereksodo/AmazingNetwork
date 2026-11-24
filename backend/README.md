# Backend

FastAPI application (container C-API). Packages follow the components in [c4-component-api.mmd](../docs/diagrams/c4-component-api.mmd).

| Feature | Where |
|---|---|
| Who may see and do what (K-POLICY) | `app/policy.py` |
| Sign-in, tokens, role dependencies | `app/auth/` |
| Profiles, follow, block | `app/people/` |
| Communities, membership, community follow and mute | `app/communities/` |
| Posts, versions, reshares, reactions, pins | `app/content/posts.py` |
| Comments; events and waitlist; images; HTML allow-list | `app/content/comments.py`, `events.py`, `images.py`, `sanitize.py` |
| Direct messages | `app/messaging/` |
| Drafts: REST and publishing; WebSocket; rooms; Yjs to HTML | `app/collab/router.py`, `socket.py`, `rooms.py`, `ydoc.py` |
| Live events: `/ws`; bus; per-recipient check | `app/realtime/router.py`, `hub.py`, `access.py` |
| Reports, decisions, appeals, administration | `app/moderation/` |
| AI triage: model client; redaction, prompt, validation | `app/ai/provider.py`, `triage.py` |
| Notifications, audit log | `app/notifications/`, `app/audit/` |
| Tables | `app/models/` |
| Error codes and format | `app/errors.py` |

A request goes router → policy → models; `emit` queues a live event that `db.py` sends after the commit. Races are decided by conditional `UPDATE`s.

Run from this folder, with the virtual environment created by `../run.sh`:

```bash
.venv/bin/pytest
```

```bash
.venv/bin/ruff format . && .venv/bin/ruff check .
```

After changing endpoints or tables, refresh the committed specification and diagrams (tests fail otherwise):

```bash
.venv/bin/python -m scripts.export_openapi && .venv/bin/python -m scripts.export_erd
```

`scripts.seed` loads the demonstration data; `scripts.purge` erases removed content and deleted accounts after 30 days.
