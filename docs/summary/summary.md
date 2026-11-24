# Connect: Assignment 2 summary

AI1220 · November 2026 · <https://github.com/dereksodo/AmazingNetwork> · tag `assignment-2`

## Changes from Assignment 1

| Change | Reason | Record |
|---|---|---|
| Local accounts with hashed passwords and bearer tokens replace SSO and cookies | No SSO tenant; token works for REST and WebSocket; instant sign-out | ADR-005 |
| SQLite, one process, in-process event bus and background tasks replace PostgreSQL, Redis, worker and MinIO | Must start from a fresh clone; enough for the first release | ADR-006 |
| Live events carry ids only; views reload after a reconnect instead of replaying events | One access-checked door for content | ADR-007 |
| Yjs co-editing kept; merged state per draft instead of an update log; JSON frames | Simpler storage, one error format | ADR-002 |
| One SQL visibility rule for lists, single reads and live events; reshares follow their original | Paths cannot disagree | ADR-003 |
| AI: OpenAI-compatible client; one attempt with a deadline plus "ask again"; "pending" until the timeout instead of 5 s | Any model by settings; local models are slow | ADR-004 |
| Any other moderator may decide an appeal; unscored reports rank after high | Nobody waits for one person; unscored may be urgent | status file |
| Added after feedback: follow, block and mute endpoints; post versions, images, reshares, muted communities, study programmes; complete traceability | Feedback on Assignment 1 | status file |
| Dropped: rate limits, load test, hosting, usability test, AI evaluation set, email | Time; not needed by the six core areas | status file |

## Ownership

Planned ownership from Assignment 1. Each member confirms the row and adds links to their own pull requests before submission.

| Member | GitHub | System parts | Documentation file | Main pull requests |
|---|---|---|---|---|
| Jiadong Zhang | dereksodo | auth, people, communities, content, messaging, policy, models | docs/openapi.json, backend/README.md | to be added |
| Nura | NuraAlMheiri | realtime, collab, frontend/src/live, CI | docs/websocket.md | to be added |
| Fatima | fatimalmazrouei13 | frontend: pages, components, editor | frontend/README.md | to be added |
| Zayed | ZayedAlNahyan | moderation, AI, audit, tests | docs/requirements-status.md | to be added |

<div class="page"></div>

## Containers (C4 level 2)

![](../diagrams/c4-container.mmd)

## Components of the API application (C4 level 3)

![](../diagrams/c4-component-api.mmd)

<div class="page"></div>

## Entity relationships

Key columns only; the source files in `docs/diagrams/` list every column.

![](../diagrams/erd-people.mmd)

![](../diagrams/erd-content.mmd)

![](../diagrams/erd-collaboration.mmd)

![](../diagrams/erd-messaging.mmd)

![](../diagrams/erd-moderation.mmd)
