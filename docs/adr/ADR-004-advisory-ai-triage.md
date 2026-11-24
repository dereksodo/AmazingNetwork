# ADR-004: AI report triage is advisory, asynchronous and behind a provider adapter

**Status:** Accepted · **Area:** AI feature and moderation · **Drivers:** D3, D4

**Context.** Moderators are few and report volume grows with participation (SN-5). An LLM can suggest a category and severity so urgent reports are seen first (FR-AI-*). But LLM output can be wrong, can be manipulated by text inside the reported content (prompt injection), and sending content to an external provider (DeepSeek) raises privacy questions (SN-6, Q3). Assignment 2 requires an LLM integration; paid calls are not required for Assignment 1.

**Options considered.**

1. *Automatic moderation:* the AI hides high-severity content immediately. Fast, but wrong decisions silence students without human review, and an attacker could game it.
2. *Synchronous call while filing the report.* Simple, but the reporter waits up to 10 s and an outage blocks reporting.
3. *Advisory, asynchronous triage:* the report is saved first, a worker job calls the LLM, the result is validated against a JSON schema and stored as a suggestion; moderators always decide.

**Decision.** Option 3, with the LLM behind an `LLMProvider` interface that has a `MockProvider` (default, used in tests and demos) and a `DeepSeekProvider` (JSON output mode, 10 s timeout, 2 retries with backoff). The prompt contains only the reported text, the report reason and the policy categories; no names, user IDs or conversation history. Reported text is wrapped in delimiters and treated as data. Output fields must be enum values or the report is marked *unscored*.

**Consequences.**

- No report is ever lost or delayed by the AI (report appears in the queue within 5 s either way).
- Obviously harmful content still waits for a human; we accept this to protect fairness and appeals.
- Moderator agree/disagree is recorded, giving an ongoing accuracy measure (NFR-12) and a basis to change prompts (`prompt_version` stored per suggestion).
- Switching to another provider or a local model touches one class only, which keeps the option open if the university rejects external processing (Q3).

**Amendment, Assignment 2.** Advisory, asynchronous and behind an interface, as decided. Changes: (1) the call runs as a FastAPI background task, not in a worker (ADR-006); (2) one provider class speaks the OpenAI-compatible chat API, so LM Studio, DeepSeek and others differ only in environment variables; (3) one attempt with one overall deadline (`CONNECT_LLM_TIMEOUT_SECONDS`) replaces two automatic retries, and moderators can ask again, because retries would keep a report without a result for half a minute; (4) there is no mock provider in the product: without a model, reports are simply unscored. Tests inject a fake provider.
