# ADR-003: One server-side Audience Policy component for every read path

**Status:** Accepted · **Area:** audience control and authorization · **Drivers:** D1

**Context.** A post must never reach someone outside its audience through *any* path: single fetch, feed, search, comments, notifications, mentions or WebSocket events (FR-AUD-2). Rules combine visibility, membership, follows, blocks, roles, moderation status and the DM exception for moderators. Leaks are the highest-impact failure for students (SN-2) and the university (SN-6).

**Options considered.**

1. *Checks written inside each endpoint.* Fast to start, but rules drift between endpoints and WebSocket fan-out is easy to forget.
2. *Filter in the frontend.* Unacceptable: data has already left the server.
3. *Central policy component (K-POLICY)* offering `can_view(user, item)`, `can_act(user, action, item)` and a SQL filter builder used by list queries; the Realtime Gateway calls it again for each recipient before sending an event.
4. *Database row-level security.* Strong guarantee, but harder to test and debug for the team and awkward for the WebSocket path.

**Decision.** Option 3. All endpoints and the WebSocket gateway depend on K-POLICY. Content outside the caller's audience returns **404 POST_NOT_FOUND** (identical to a missing post) so its existence is not revealed. The proof of concept already implements this (`backend/app/policy.py`).

**Consequences.**

- One place to review and test: table-driven unit tests cover every role × visibility × relationship combination (NFR-11).
- Small extra cost per event (a policy check per recipient); acceptable at campus scale, and cached membership sets keep it cheap.
- New endpoints must use the policy; a CI test lists all routes and fails if a content route lacks the policy dependency.
- Visibility changes take effect immediately because nothing caches permission decisions beyond one request.
