# Assignment 1 — Decisions Needed

Tick one box per question (`[x]`) unless it says "pick any". ⭐ = my recommendation, which is what the draft so far assumes.
Add notes under any question. When you're done, tell me and I'll build the report, diagrams and PoC from your answers.

---

## ✅ Decided so far

**Product name:** Connect.

**Users:** student, group officer, moderator, school admin. "Non-member" means a student outside a given community. The **dev team is a stakeholder only**, with no in-app role.

**Content types (first release):** post, discussion, draft, announcement, event, comment, reaction, direct message.
**Later:** shorts (short videos).

**Who can create what:**

| | Student | Officer | School admin | Non-member | Moderator |
|---|---|---|---|---|---|
| Post / discussion | ✅ | ✅ | ❌ | ❌ | ✅ |
| Announcement / event | ❌ | ✅ | ✅ (campus-wide) | ❌ | ❌ |
| Comment / reaction | ✅ | ✅ | ✅ | ❌ | ✅ |
| Direct message | ✅ | ✅ | ❌ | ✅ (unless blocked) | ❌ (system notices instead) |
| Draft | own | own + shared community drafts | own | – | – |

**Who can see what:**
- Content is visible to its audience; moderators can see everything except direct messages.
- A direct message is visible only to its sender and recipient.
- A draft is visible only to its collaborators.

**Moderation policies:**
1. **Hide or remove content.** Hiding can be undone during an appeal; removed content is permanently deleted after 30 days. Every action needs a reason, and the author is notified.
2. **System notices.** Moderators message students through a "Connect Moderation" account, which can't be replied to.
3. **Direct messages stay private.** When a user reports a direct message, only the messages they select are attached to the report; moderators never see the whole conversation.
4. **Timed mute (24 h / 7 d / 30 d).** A muted user can't post, comment or send direct messages but can still read. Mutes can be appealed.
5. **Appeals.** One appeal per action, within 7 days, reviewed by a different moderator.
6. **Audit log.** Every moderator action is logged.
7. **Officers** can hide comments inside their own community.

---

## A. Product

**A1. Product name**
- [ ] ⭐ Quad
- [ ] CampusLoop
- [ ] UniHub
- [ ] Other: _Connect_____

**A2. Who can sign up?**
- [1] ⭐ Students and staff with a university email
- [ ] Students only
- [ ] Students, staff and alumni
- [ ] Other: ______

**A3. Platform for the first release**
- [1] ⭐ Web app only (responsive on mobile browsers)
- [ ] Web app plus a basic mobile app

**A4. Anonymous posting**
- [1] ⭐ Not allowed (keeps people accountable to moderators)
- [ ] Allowed in specific communities, but moderators can see who posted

---

## B. AI feature

**B1. Which AI feature?**
- [1] ⭐ Report Triage Assistant: suggests a category and severity for reported content, to help moderators
- [ ] Announcement Co-writer: helps officers draft and polish event posts
- [ ] "Catch me up" summarizer: summarizes long discussion threads for students
- [ ] Other: ______

**B2. LLM provider for Assignment 2**
- [1] ⭐ Provider-agnostic adapter with a mock by default; plug in a real API later; we choose DeepSeek
- [ ] Claude API
- [ ] OpenAI API
- [ ] Local model (e.g. Ollama)

**B3. Can the AI act on content by itself?**
- [1] ⭐ No, it only suggests; a human always decides
- [ ] Yes, it can auto-hide high-severity content until a moderator reviews it

---

## C. Content and interaction rules

**C1. Content types:** ✅ decided (see top).

**C2. Visibility levels** (pick any)
- [1] ⭐ Campus (all verified users)
- [1] ⭐ Community members only
- [1] ⭐ Followers only
- [ ] Specific list of people

**C3. Who can create a community?**
- [1] ⭐ Any user; an admin approves it
- [ ] Any user, no approval
- [ ] Only admins

**C4. Appeal window after a moderation action**
- [ ] ⭐ 14 days, one appeal, reviewed by a different moderator
- [1] 7 days
- [ ] 30 days

---

## D. Architecture

**D1. Real-time co-editing approach**
- [1] ⭐ Yjs CRDT with the TipTap editor (true simultaneous editing)
- [ ] Section locking: one editor per paragraph at a time (simpler)
- [ ] Last-writer-wins with version check (simplest, weakest experience)

**D2. Database**
- [1] ⭐ PostgreSQL (SQLite allowed in the PoC)
- [ ] SQLite everywhere
- [ ] MongoDB

**D3. Backend structure**
- [1] ⭐ Modular monolith (FastAPI) plus one background worker
- [ ] Single FastAPI app, no worker
- [ ] Microservices

**D4. Which container gets the C4 component diagram?**
- [1] ⭐ API application (FastAPI)
- [ ] Web app (React)

**D5. Which interaction gets the UML sequence diagram?**
- [1] ⭐ Two officers co-editing a draft, then publishing (with concurrent-publish conflict)
- [ ] Reporting content → AI triage → moderator action
- [ ] Other: ______

---

## E. Team and process

**E1. Team member names and roles**

| Role | Name |
|---|---|
| A: Backend core (auth, communities, posts, authorization, DB) | _JIADONG ZHANG_____ |
| B: Real-time (WebSockets, collaboration, Redis) and CI | __NURA____ |
| C: Frontend (React, editor, accessibility) | __FATIMA____ |
| D: Moderation, AI feature, testing, docs | __ZAYED____ |

- [1] ⭐ Use the role split above
- [ ] Different split (describe): ______

**E2. Methodology**
- [1] ⭐ Light Scrum, 1-week sprints
- [ ] Kanban
- [ ] 2-week sprints

**E3. Assignment 2 timeline**
- Start date: ______  Deadline: ______
- [1] ⭐ I don't know yet; assume 6 weeks; finish only assignment 1 now

**E4. GitHub repository**
- Repo URL (or "not created yet"): _https://github.com/dereksodo/AmazingNetwork_____
- [1] ⭐ GitHub Flow (protected `main`, feature branches, PR + 1 review)
- [ ] Other: ______

---

## F. Deliverables

**F1. Diagram tool** (source files must be submitted)
- [1] ⭐ PlantUML / Mermaid (text files, easy to keep in Git)
- [ ] draw.io (.drawio files)
- [ ] Other: ______

**F2. Report format** (must end up as one PDF)
- [1] ⭐ Markdown → PDF
- [ ] LaTeX
- [ ] Word / Google Docs

**F3. Proof-of-concept interaction**
- [1] ⭐ Create a post and fetch it back (`POST /api/v1/posts`, `GET /api/v1/posts/{id}`)
- [ ] Join a community
- [ ] Report a post

**F4. PoC frontend**
- [1] ⭐ Plain HTML + JavaScript page (allowed, simplest)
- [ ] Minimal React app

**F5. What should I produce next?** (pick any)
- [1] Full report draft
- [1] All diagrams (C4 ×3, sequence, ERD) as source files
- [1] PoC code + README
- [1] Repo skeleton (folders, CI, CODEOWNERS, PR template)

---

**Notes / anything else:**
please do not push and commit anything. only keep track of files locally
