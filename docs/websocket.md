# WebSocket channels

Two endpoints on the API server (`ws://127.0.0.1:8000`, forwarded by the frontend server on port 5173). All frames are JSON text.

## Connecting and authenticating

A browser cannot send an `Authorization` header here, and tokens in URLs end up in logs. So the **first frame** of every connection is:

```json
{"type": "auth", "token": "<token from POST /api/v1/auth/login>"}
```

If it is missing, malformed or the token is invalid, the server closes with **4401**. Both endpoints answer `{"type": "ping"}` with `{"type": "pong"}`; the browser pings every 25 seconds.

## Errors and close codes

REST errors are `{"error": {"code": "POST_NOT_FOUND", "message": "Post not found.", "details": ...}}`; all codes are in `openapi.json`. Errors on a socket are one frame and do not close it:

| Frame | Meaning |
|---|---|
| `{"type": "error", "code": "INVALID_FRAME"}` | Not JSON, unknown `type`, or missing field. The frame is ignored. |
| `{"type": "error", "code": "FORBIDDEN", "channel": "post:7"}` | Subscription refused (also for items that do not exist). |

| Close code | Meaning | Client |
|---|---|---|
| 4401 | Not signed in, signed out or session expired | shows the sign-in page |
| 4403 | Not, or no longer, allowed to edit this draft | editor read-only |
| 4409 | The draft is published | editor read-only |
| other | Network problem or restart | reconnects after 1, 2, 4 … 30 s |

## `/ws`: live events

Role: signed in. After `auth` the server sends `{"type": "ready", "user_id": 1}`. The connection listens to `feed` and the caller's `user:{id}` without asking.

| Channel | Who may listen | Events |
|---|---|---|
| `feed` | everyone; each event only to the post's audience | `post.created`, `post.updated`, `post.removed` |
| `user:{id}` | that user | `notification.created`, `notification.read`, `message.created`, `audience.changed`, `session.ended` |
| `community:{id}` | active members | `members.changed` |
| `post:{id}` | the post's audience | `post.created` (restored), `post.updated`, `post.removed`, `comment.created`, `comment.updated`, `comment.removed`, `reaction.changed`, `rsvp.changed` |
| `moderation` | moderators | `report.created`, `report.scored`, `report.decided`, `appeal.created`, `appeal.decided` |

**Client to server**

| Type | Example | Reply |
|---|---|---|
| `subscribe` | `{"type": "subscribe", "channel": "post:7"}` | `subscribed` or `error FORBIDDEN` |
| `unsubscribe` | `{"type": "unsubscribe", "channel": "post:7"}` | `unsubscribed` |
| `ping` | `{"type": "ping"}` | `pong` |

**Server to client**

| Type | Example |
|---|---|
| `ready` | `{"type": "ready", "user_id": 1}` |
| `subscribed` | `{"type": "subscribed", "channel": "post:7"}` |
| `unsubscribed` | `{"type": "unsubscribed", "channel": "post:7"}` |
| `event` | `{"type": "event", "channel": "feed", "event": "post.created", "data": {"post_id": 7, "community_id": null}}` |
| `revoked` | `{"type": "revoked", "channel": "community:1"}`: access was lost, nothing more will come |
| `error`, `pong` | see above |

`data` holds identifiers only: `post_id` and `community_id` for posts; `post_id` and `comment_id` for comments; `post_id` for reactions and RSVPs; `community_id` for members; `conversation_id` for messages; `report_id` for `report.scored` and `report.decided`; `appeal_id` for `appeal.decided`; otherwise empty. Content is fetched over REST (ADR-007).

## `/ws/drafts/{id}`: co-editing

Role: collaborator of the draft who is an officer of its community (admin for campus-wide drafts). `update` and `state_vector` are base64 of Yjs binary data.

**Client to server**

| Type | Example | Reply |
|---|---|---|
| `sync` | `{"type": "sync", "state_vector": "AA=="}` | `sync` |
| `update` | `{"type": "update", "update": "AQHq..."}` | `ack` to the sender, `update` to the others |
| `awareness` | `{"type": "awareness", "update": "AeT..."}` (cursor, at most 20,000 characters) | `awareness` to the others; not stored |
| `ping` | `{"type": "ping"}` | `pong` |

**Server to client**

| Type | Example |
|---|---|
| `presence` | `{"type": "presence", "users": [{"id": 3, "display_name": "Lina Park"}]}` |
| `sync` | `{"type": "sync", "update": "AQ...", "state_vector": "Ae...", "version": 16}` |
| `update` | `{"type": "update", "update": "AQ...", "version": 17}` |
| `ack` | `{"type": "ack", "version": 17}`: saved in the database |
| `awareness` | `{"type": "awareness", "update": "AeT..."}` |
| `published` | `{"type": "published", "post_id": 12}`, then close 4409 |
| `error`, `pong` | see above |

## The three situations

| Situation | Behaviour | Test in `test_realtime.py` |
|---|---|---|
| Users act at the same time: editing | Yjs merges both; a lock per room saves updates one after another | `test_concurrent_edits_merge` |
| … publishing | One conditional `UPDATE` wins; the other gets 409 `ALREADY_PUBLISHED` with the post id | `test_simultaneous_publishing_creates_one_post` |
| … publishing while another types | 409 `VERSION_CONFLICT`: the version on screen is old | `test_publishing_an_old_version_is_refused` |
| … editing a published post | `If-Match` with an old version gets 409 `VERSION_CONFLICT` | `test_content.py::test_edit_keeps_versions_and_refuses_stale_edits` |
| Connection drops: editor | Edits stay in the local document; after reconnecting both sides exchange what is missing | `test_offline_edits_are_merged_after_reconnecting` |
| … live events | Reconnect, subscribe again, every open view reloads over REST. Missed events are not replayed | demo step 4 |
| Not allowed to join | `error FORBIDDEN` on `/ws`, close 4403 on drafts | `test_forbidden_channels`, `test_outsiders_cannot_join_or_read_a_draft` |
| Loses access while connected | Checked for every frame and recipient: `revoked`, 4401 or 4403 before the next content | `test_lost_membership_revokes_the_channel`, `test_hidden_post_revokes_its_channel`, `test_demoted_officer_is_disconnected`, `test_logout_closes_the_connection` |
