# ADR-002: Yjs CRDT for real-time co-editing of drafts

**Status:** Accepted · **Area:** publishing and collaboration · **Drivers:** D2, D4

**Context.** Officers co-write announcements and events (FR-COL-1..5). Edits must reach other editors within 500 ms (NFR-2), simultaneous edits must not lose text (FR-COL-3), and a dropped connection must not lose work (FR-COL-4). Assignment 2 requires a React rich-text editor and WebSockets.

**Options considered.**

1. *Last-writer-wins with a version number.* Trivial, but the second save overwrites or is rejected, so real simultaneous editing is impossible.
2. *Paragraph locking* (one editor per paragraph). Simple to reason about, but blocks people, needs lock timeouts, and offline edits cannot be merged.
3. *Operational transformation (OT).* Proven (Google Docs) but the server must transform every operation; no maintained Python implementation fits our stack.
4. *CRDT with Yjs.* The TipTap editor has a Yjs collaboration extension; the Python `pycrdt` / `pycrdt-websocket` libraries speak the same protocol, so the FastAPI server can relay and persist updates.

**Decision.** Option 4. Each draft is a Yjs document in room `draft:{id}`. The server checks authorization on connect, relays updates through Redis to all API instances, appends each update to `draft_update` and writes a snapshot every 100 updates. Publishing converts the Yjs state to HTML, sanitizes it and uses a conditional `UPDATE ... WHERE version = expected_version` so only one publish succeeds.

**Consequences.**

- Concurrent edits converge automatically; offline edits merge on reconnect.
- Drafts are stored as binary state, so the server cannot validate content until publish; validation and sanitizing happen at publish time.
- Team must learn Yjs; risk R1 mitigated by a week-1 spike. Fallback: option 2 behind the same WebSocket endpoint.
- Only drafts use CRDTs; published posts use ordinary versioned rows with `If-Match` (409 on conflict).
