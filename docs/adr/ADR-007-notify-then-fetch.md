# ADR-007: Live events carry identifiers; content is fetched through REST

**Status:** Accepted · **Area:** live updates · **Changes:** §2.3 and §2.4 of the Assignment 1 report

**Context.** Assignment 1 sent whole posts in events and replayed missed events from a Redis stream after a reconnect. Both duplicate rules: the payload must be filtered per recipient (blocked commenters, reshares, RSVP state), and replayed events must be re-checked against current access.

**Options considered.**

1. *Full payload per recipient, replay buffer.* Fewest requests, two code paths that can leak.
2. *Identifiers only, replay buffer.* Safe payload, but the buffer adds event ids, gaps and a "too old" case.
3. *Identifiers only, reload after reconnect.*

**Decision.** Option 3. Every event names what changed; the browser reloads the view over REST, where the Audience Policy applies. Before each delivery the server checks with current data that the session is valid, the channel is allowed and the post is visible. A lost channel produces a `revoked` frame. After a reconnect every open view reloads.

**Consequences.**

- Content leaves the server through one door.
- More REST requests per event; acceptable at the demonstrated size.
- Events are not replayed, so a client must reload after a reconnect; ours does.
