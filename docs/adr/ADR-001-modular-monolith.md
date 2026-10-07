# ADR-001: Modular monolith plus one background worker

**Status:** Accepted · **Area:** overall structure / deployment · **Drivers:** D1, D5, D6

**Context.** Connect needs REST, WebSockets, background AI calls and scheduled purges. The team has four students, about six weeks for Assignment 2, and must use FastAPI. Audience rules (FR-AUD-*) must be enforced identically by every feature, and several operations (publishing a draft, taking a moderation action and writing the audit entry) must be atomic.

**Options considered.**

1. *Microservices* (separate posts, messaging, moderation, AI services). Independent scaling, but needs service-to-service authentication, distributed transactions and much more deployment work; audience rules would be duplicated or require network calls.
2. *Single FastAPI process doing everything*, including LLM calls inside the request. Simplest, but a slow or failing LLM would block request workers and scheduled jobs would have no home.
3. *Modular monolith (one FastAPI app with strict internal modules) plus one worker process* sharing PostgreSQL and Redis.

**Decision.** Option 3. Modules map to C4 components (K-POST, K-MOD, ...). Modules talk through Python interfaces, never through each other's tables. Slow or external work (LLM triage, email, purges) goes to the worker through a Redis queue.

**Consequences.**

- One deployable API, one database transaction per use case (e.g. moderation action + audit entry commit together).
- The API is stateless (sessions in DB, live events through Redis pub/sub), so it scales horizontally by running more instances (NFR-3).
- Module boundaries are enforced only by convention and review (CODEOWNERS, import rules checked in CI), not by the network.
- If one module later needs independent scaling (e.g. realtime), it can be split out along its existing interface.
