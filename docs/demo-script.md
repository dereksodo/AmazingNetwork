# Demonstration script

Start with `./run.sh seed`, then `./run.sh`. Open http://localhost:5173 in several tabs; each tab keeps its own sign-in. Every account is `<handle>@campus.example` with the password `demo-password`.

| Step | Tabs | Do | Expect |
|---|---|---|---|
| 1 Live post | aisha, omar | Aisha publishes a post with a heading and bold text | It appears for Omar without reloading; formatting survives a reload |
| 2 Refused access | omar | Open `/posts/2` (Robotics members only), then `/posts/99999` | The same "Post not found." Show the 404 in the developer tools |
| 3 Co-editing | lina, karim | Both open Drafts → Spring competition and type at once | Both texts merge; presence and cursors |
| 4 Reconnect | lina, karim | Stop the backend (Ctrl+C in its own terminal), type in both tabs, start it again | "Offline", then both edits appear in both tabs |
| 5 Publish race | lina, karim | Both press Publish | One post; the other sees "already published" with a link |
| 6 AI triage | lina, sam | Lina reports `/posts/7`; Sam has Moderation open | Report at once, suggestion a few seconds later; without a model "unscored" |
| 7 Appeal | sam, yusuf, maya | Sam hides the post; Yusuf appeals in Settings; Maya overturns | Sam never sees the appeal; the post is back |
| 8 Admin | dean | Approve Film Nights, export the audit log | CSV with every action |
| 9 Lost access | lina, aisha | Lina removes Aisha from Robotics; Aisha reloads `/posts/1` | "Post not found." |
| 10 Follow, block | omar | Follow Lina, then block Lina | Lina's posts disappear from Omar's lists |

For step 4 start the two servers separately, as described in the root README.
