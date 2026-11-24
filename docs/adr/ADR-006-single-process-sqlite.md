# ADR-006: One process with SQLite, an in-process event bus and background tasks

**Status:** Accepted · **Area:** deployment and data · **Changes:** ADR-001, NFR-3, containers C-WRK, C-REDIS, C-OBJ

**Context.** Assignment 1 planned PostgreSQL, Redis, MinIO and a worker. The first release must run on a teaching assistant's laptop by following the README alone. SQLite is sufficient for the assignment.

**Options considered.**

1. *Docker Compose with all planned containers.* Scales out, but needs Docker and four services for a demonstration with ten users.
2. *PostgreSQL only.* Still a server to install; does not remove the need for a broker.
3. *One FastAPI process with a SQLite file.* Nothing to install beyond Python and Node.

**Decision.** Option 3. SQLAlchemy keeps the database replaceable. Live events are queued on the database session and handed to the event bus after the commit, so nobody hears about a change that was rolled back. Triage runs as a background task. Images are stored in the database. `python -m scripts.purge` replaces the scheduled purge job. Mutes carry an end time, so nothing has to expire them.

**Consequences.**

- The API must run as exactly one process: the event bus and draft rooms are in memory. NFR-3 is dropped for this release.
- SQLite allows one writer at a time. Races are decided by conditional `UPDATE`s, or by writing before counting (waitlist, pins), which takes the write lock first.
- A model call running during a restart is lost; on start such reports become unscored and can be retried.
- To scale out: PostgreSQL through the connection URL (with `FOR UPDATE` where the write lock is relied on), and a Redis implementation of `Hub.dispatch` and the rooms.
