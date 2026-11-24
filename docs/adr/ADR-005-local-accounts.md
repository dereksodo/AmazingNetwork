# ADR-005: Local accounts with hashed passwords instead of university SSO

**Status:** Accepted · **Area:** identity · **Changes:** FR-ID-1, A-1

**Context.** Assignment 1 planned sign-in through the university's OpenID Connect service with a session cookie. We have no test tenant, the product must start from a fresh clone, and Assignment 2 asks for password hashes. A browser cannot send an `Authorization` header when it opens a WebSocket.

**Options considered.**

1. *Mock OpenID Connect server.* Realistic flow, but a fake identity server proves nothing about membership and is one more process to start.
2. *Local accounts, signed JWT.* Stateless, but signing out cannot invalidate a token without a deny list (FR-ID-4).
3. *Local accounts, opaque token with a session row.* One lookup per request, instant sign-out.

**Decision.** Option 3. Addresses must be on `CONNECT_EMAIL_DOMAIN`. Passwords are salted scrypt hashes; the database stores only the SHA-256 of a token. REST uses `Authorization: Bearer`; WebSockets send the token in the first message, not in the URL, so it is not written to access logs. The browser keeps the token in `sessionStorage`.

**Consequences.**

- Membership rests on the address; addresses are not verified by email. This is the largest gap to production and is listed in `docs/requirements-status.md`.
- No CSRF risk, because the browser never attaches the token by itself. A script injection could read it, so sanitizing (FR-PUB-6) matters more.
- Two tabs can be signed in as two people, which makes the live demonstration easy.
- `auth/router.py` is the only file to replace when SSO becomes available.
