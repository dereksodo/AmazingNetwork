# Requirements status and traceability

**Done** = implemented, **Partly** = see reason, **Dropped** = not in this release. Tests are in `backend/tests/`; `file::test` omits `test_` and `.py` from the file name. "Demo n" is a step of [demo-script.md](demo-script.md).

## Functional requirements

| ID | Status | Evidence or reason |
|---|---|---|
| FR-ID-1 | Partly | Local accounts instead of SSO (ADR-005); foreign domains refused: `identity::test_only_university_addresses`. Addresses are not verified by email. |
| FR-ID-2 | Done | `identity::test_register_creates_profile_with_programme`, `test_profile_update` |
| FR-ID-3 | Done | `identity::test_only_admin_appoints_moderators`, `communities::test_owner_manages_roles` |
| FR-ID-4 | Done | `identity::test_session_expires_after_seven_idle_days`, `test_logout_invalidates_the_token`, `realtime::test_logout_closes_the_connection` |
| FR-ID-5 | Partly | Invisible at once: `identity::test_deleted_account_is_invisible`. Purging is a script an operator runs, not a schedule; its account branch has no test. |
| FR-COM-1 | Done | `communities::test_community_needs_admin_approval` |
| FR-COM-2 | Done | `communities::test_join_open_and_closed` |
| FR-COM-3 | Done | `communities::test_owner_manages_roles`, `test_lost_membership_ends_access_at_once` |
| FR-COM-4 | Done | `communities::test_lost_membership_ends_access_at_once`, `realtime::test_lost_membership_revokes_the_channel`. Authors keep access to their own posts. |
| FR-PUB-1 | Done | `content::test_formatting_survives_saving`, `test_image_limits` |
| FR-PUB-2 | Done | `content::test_discussion_needs_title`, `test_officer_locks_and_pins` |
| FR-PUB-3 | Done | `realtime::test_publish_makes_editors_read_only`, `test_campus_drafts_belong_to_admins`, `content::test_officer_locks_and_pins` |
| FR-PUB-4 | Done | `content::test_waitlist_is_promoted_in_order`, `test_event_change_notifies_and_cancel_closes` |
| FR-PUB-5 | Done | `content::test_edit_keeps_versions_and_refuses_stale_edits`, `test_deleted_post_disappears_with_its_comments` |
| FR-PUB-6 | Done | `content::test_scripts_are_removed`, `test_allowed_links`, `realtime::test_yjs_document_becomes_safe_html` |
| FR-COL-1 | Done | `realtime::test_event_draft_needs_event_details`, `test_only_officers_can_be_invited` |
| FR-COL-2 | Done | `realtime::test_concurrent_edits_merge`, `test_presence_lists_editors`, `test_awareness_is_relayed` |
| FR-COL-3 | Done | `realtime::test_concurrent_edits_merge` |
| FR-COL-4 | Done | `realtime::test_offline_edits_are_merged_after_reconnecting`, demo 4. Offline edits are lost if the tab is closed. |
| FR-COL-5 | Done | `realtime::test_simultaneous_publishing_creates_one_post`, `test_publish_makes_editors_read_only` |
| FR-COL-6 | Done | `realtime::test_outsiders_cannot_join_or_read_a_draft` |
| FR-AUD-1 | Done | `audience::test_visibility_matrix`, `test_impossible_audiences` |
| FR-AUD-2 | Done | `audience::test_outsider_is_refused_on_every_path`, `test_hidden_item_looks_like_missing_item`, `test_image_follows_the_post`, `realtime::test_live_events_follow_the_audience`. Post search was not built. |
| FR-AUD-3 | Done | `audience::test_blocking_is_mutual_invisibility`, `test_block_ends_follows` |
| FR-AUD-4 | Done | `audience::test_changed_visibility_applies_to_post_and_comments` |
| FR-AUD-5 | Done | `audience::test_only_campus_posts_can_be_reshared`, `test_reshare_never_shows_an_original_that_became_private` |
| FR-AUD-6 | Done | `audience::test_mention_outside_the_audience_is_silent` |
| FR-INT-1 | Done | `content::test_comment_rules`, `test_comments_can_be_disabled` |
| FR-INT-2 | Done | `content::test_reactions_are_idempotent` |
| FR-INT-3 | Done | `audience::test_follow_gives_access_to_followers_posts`, `test_follow_request_needs_approval`, `communities::test_following_a_community_adds_campus_posts_only` |
| FR-INT-4 | Done | `content::test_feed_pages`, `realtime::test_new_post_arrives_live` |
| FR-INT-5 | Done | `communities::test_muted_community_sends_no_notifications`, `realtime::test_comment_and_message_arrive_live` |
| FR-INT-6 | Done | `content::test_direct_messages`, `realtime::test_comment_and_message_arrive_live` |
| FR-MOD-1 | Done | `moderation::test_report_rules` |
| FR-MOD-2 | Done | `moderation::test_queue_is_ordered_by_severity`. Unscored reports come after high, because they might be urgent. |
| FR-MOD-3 | Done | `moderation::test_hide_freezes_and_notifies`, `test_mute_blocks_every_write_and_can_be_lifted`, `test_action_needs_matching_fields`, `test_report_is_decided_once` |
| FR-MOD-4 | Done | `moderation::test_hide_freezes_and_notifies` |
| FR-MOD-5 | Done | `moderation::test_appeal_overturned_by_another_moderator`, `test_appeal_window`. Changed: any other moderator may take the appeal; it is not assigned to one person, so it cannot wait for someone absent. |
| FR-MOD-6 | Done | `moderation::test_audit_export`, `test_audit_log_is_insert_only` |
| FR-MOD-7 | Done | `moderation::test_officer_hides_comment_in_own_community` |
| FR-MOD-8 | Done | `moderation::test_dm_report_contains_only_selected_messages`, `content::test_direct_messages` |
| FR-MOD-9 | Done | Notices are notifications; no endpoint answers them. `moderation::test_hide_freezes_and_notifies` |
| FR-AI-1 | Done | `ai::test_suggestion_is_stored_and_never_acts` |
| FR-AI-2 | Done | `moderation::test_queue_is_ordered_by_severity`, demo 6 |
| FR-AI-3 | Done | `ai::test_suggestion_is_stored_and_never_acts` |
| FR-AI-4 | Partly | In the queue at once; unscored after failure: `ai::test_unreachable_model_leaves_report_unscored`, `test_unusable_output_is_refused`. Changed: shown as "pending" until the timeout (20 s by default) instead of 5 s, because local models are slow. |
| FR-AI-5 | Done | `ai::test_agreement_is_counted_for_admins` |
| FR-AI-6 | Done | `ai::test_prompt_contains_only_the_reported_text_without_names`. Removes registered names and handles, email addresses and number sequences; misspelled names remain. |

## Technology constraints

| ID | Status | Evidence |
|---|---|---|
| TC-1 | Done | `backend/` |
| TC-2 | Done | `docs/websocket.md`, `test_realtime.py` |
| TC-3 | Done | `frontend/`, TipTap |
| TC-4 | Done | `backend/app/ai/`; any OpenAI-compatible model |
| TC-5 | Done | `backend/scripts/seed.py` |

## Non-functional requirements

| ID | Status | Evidence or reason |
|---|---|---|
| NFR-1 | Dropped | No load test; SQLite and one process are not meant for 500 users (ADR-006). |
| NFR-2 | Partly | Live delivery works (demo 1, 3); latency percentiles were not measured. |
| NFR-3 | Dropped | One process (ADR-006). |
| NFR-4 | Dropped | Not hosted. |
| NFR-5 | Partly | Every draft update is saved before it is acknowledged. No backup or restore drill. |
| NFR-6 | Partly | Authorization on every request and frame, sanitizing, hashed passwords (`test_audience.py`, `test_content.py`). No rate limits, TLS or ZAP scan. Cookies replaced by bearer tokens (ADR-005). |
| NFR-7 | Partly | `content::test_purge_erases_after_thirty_days`, `ai::test_prompt_contains_only_the_reported_text_without_names`. Purge is run by hand. Reported message copies are kept as evidence. |
| NFR-8 | Dropped | No usability test with users. |
| NFR-9 | Partly | axe-core found no serious or critical violation on 12 pages (run by hand on 24 November 2026, not in CI). No full screen-reader test. |
| NFR-10 | Done | `moderation::test_audit_export`, `test_audit_log_is_insert_only`. |
| NFR-11 | Partly | CI runs all tests on every PR; specification and diagrams are compared with the code (`test_openapi.py`). Line coverage is not measured. |
| NFR-12 | Dropped | No labelled evaluation set yet; agreement of moderators is recorded instead (FR-AI-5). |

## User stories

| ID | Status | Evidence or reason |
|---|---|---|
| US-1 | Done | Demo 3, 4; `test_realtime.py`. The 500 ms target was not measured. |
| US-2 | Done | Demo 1, 2; `test_audience.py` |
| US-3 | Partly | Demo 6; `test_ai.py`. "Pending" instead of "unscored within 5 s", see FR-AI-4. |
| US-4 | Done | Demo 7; `moderation::test_appeal_overturned_by_another_moderator`, `test_appeal_window` |
| US-5 | Done | `moderation::test_dm_report_contains_only_selected_messages`, `test_mute_blocks_every_write_and_can_be_lifted`, `audience::test_blocking_is_mutual_invisibility` |
| US-6 | Done | Demo 8; `moderation::test_audit_export`, `realtime::test_campus_drafts_belong_to_admins` |

## Feedback on Assignment 1

| Feedback | Where it is fixed |
|---|---|
| Traceability leaves out community, follow and accessibility requirements | This file; corrected matrix in `docs/report/report.md` §1.5 |
| No endpoint to block or follow | `PUT`/`DELETE /users/{id}/follow` and `/block`, `/follow-requests`, `/followers`, `/blocks`; `test_audience.py` |
| Post versions not stored | Table `post_version`, `GET /posts/{id}/versions` |
| Images not stored | Table `post_image`, `POST /posts/{id}/images`, `GET /images/{id}` |
| Reshares not stored | Column `post.reshare_of_id`, `POST /posts/{id}/reshare` |
| Muted communities not stored | Table `community_mute`, `PUT`/`DELETE /communities/{id}/mute` |
| Study programmes not stored | Table `study_programme`, `GET /programmes`, `PATCH /me` |

## Known defects and limitations

- Exactly one API process; room and channel state is in memory (ADR-006).
- Publishing a campus-wide announcement writes one notification per user in the request; this is slow for thousands of users.
- A report whose model call is interrupted by a restart becomes unscored and needs "Ask the AI again".
- Redaction cannot recognise misspelled names or a person described without a name.
- The model may be fooled by text in the report; it can only choose a listed category and severity, and a person decides.
- Pages with many posts run several queries per post.
- Images cannot be deleted one by one.
