# Proof-of-concept demo script (≤ 3 minutes)

Before recording: start the backend and frontend as in the root README, and open http://localhost:5173 next to http://127.0.0.1:8000/docs.

| Time | Who speaks | Show | Say |
|---|---|---|---|
| 0:00–0:20 | Jiadong | README, repo tree | "Connect PoC: FastAPI backend and a plain browser client talking through contract C-POSTS in `shared/contracts/openapi.yaml`." |
| 0:20–1:00 | Fatima | Frontend: signed in as Aisha, community = Robotics Club, visibility = community, body with `<b>` and a `<script>` tag → Send | "The request and response panels show exactly the fields in the contract. 201 Created, Location header, and the script tag was stripped by the server." |
| 1:00–1:30 | Zayed | Switch user to Omar → fetch the same post id | "Omar isn't a Robotics member, so he gets 404 — the same answer as a post that doesn't exist, so hidden posts can't be discovered (FR-AUD-2)." Switch to Lina → 200. |
| 1:30–2:00 | Nura | Create a discussion with no title → 400 VALIDATION_ERROR; select "nobody" → 401 | "Errors follow the contract's error format." |
| 2:00–2:40 | Jiadong | Terminal: `pytest` | "29 tests, including a contract test that fails if the code drifts from the OpenAPI file, and table-driven tests of the audience policy." |
| 2:40–3:00 | Any | README "What the PoC simplifies" table | "Simplified: no React, mock SSO, in-memory store, no WebSockets or AI. Everything else follows the planned architecture." |
