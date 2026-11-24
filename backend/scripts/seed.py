"""Replace all data with fictional demonstration data. Run from backend/: python -m scripts.seed"""

import base64
from datetime import timedelta

from pycrdt import Doc, XmlElement, XmlFragment, XmlText
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.collab.ydoc import FRAGMENT
from app.db import Base, SessionLocal, engine, now
from app.models import (
    Comment,
    Community,
    Conversation,
    Draft,
    DraftCollaborator,
    Event,
    Follow,
    Membership,
    Message,
    Post,
    PostImage,
    Reaction,
    Report,
    Rsvp,
    StudyProgramme,
    User,
)

PASSWORD = "demo-password"
# handle, display name, role, programme id
PEOPLE = [
    ("aisha", "Aisha Rahman", "user", 1),
    ("omar", "Omar Nasser", "user", 2),
    ("lina", "Lina Park", "user", 1),
    ("karim", "Karim Aziz", "user", 3),
    ("sam", "Sam Moderator", "moderator", None),
    ("maya", "Maya Moderator", "moderator", None),
    ("dean", "Dean of Students", "admin", None),
    ("yusuf", "Yusuf Khan", "user", 2),
]
PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def demo_document(text: str) -> bytes:
    """State of a Yjs document with one paragraph."""
    doc: Doc = Doc()
    paragraph = XmlElement("paragraph")
    doc.get(FRAGMENT, type=XmlFragment).children.append(paragraph)
    paragraph.children.append(XmlText(text))
    return doc.get_update()


def load_demo(db: Session) -> None:
    """Insert the demonstration data into empty tables."""
    for name in ("BSc Computer Science", "BSc Biology", "BA Architecture"):
        db.add(StudyProgramme(name=name))
        db.flush()
    password_hash = hash_password(PASSWORD)
    people: dict[str, User] = {}
    for handle, name, role, programme_id in PEOPLE:
        people[handle] = User(
            email=f"{handle}@campus.example",
            handle=handle,
            display_name=name,
            role=role,
            programme_id=programme_id,
            password_hash=password_hash,
            approve_followers=handle == "karim",
        )
        db.add(people[handle])
        db.flush()
    aisha, omar, lina, karim, sam, maya, dean, yusuf = people.values()

    robotics = Community(
        name="Robotics Club",
        description="We build robots every Tuesday.",
        status="approved",
        created_by_id=lina.id,
        decided_by_id=dean.id,
    )
    chess = Community(
        name="Chess Society",
        description="Casual and rated games.",
        join_policy="closed",
        status="approved",
        created_by_id=omar.id,
        decided_by_id=dean.id,
    )
    film = Community(name="Film Nights", description="One film a week.", created_by_id=yusuf.id)
    for community in (robotics, chess, film):
        db.add(community)
        db.flush()
    for user, community, role in (
        (lina, robotics, "owner"),
        (karim, robotics, "officer"),
        (aisha, robotics, "member"),
        (omar, chess, "owner"),
        (yusuf, film, "owner"),
    ):
        db.add(Membership(user_id=user.id, community_id=community.id, role=role))
    db.add(Membership(user_id=aisha.id, community_id=chess.id, status="pending"))
    db.add_all(
        [
            Follow(follower_id=omar.id, followed_id=aisha.id),
            Follow(follower_id=aisha.id, followed_id=lina.id),
            Follow(follower_id=omar.id, followed_id=karim.id, status="pending"),
        ]
    )

    posts = [
        Post(
            author_id=lina.id,
            community_id=robotics.id,
            visibility="community",
            pinned=True,
            body_html="<h2>Welcome!</h2><p>Members meet in <strong>Lab 3</strong>.</p>",
        ),
        Post(
            author_id=aisha.id,
            community_id=robotics.id,
            visibility="community",
            type="discussion",
            title="Robotics team needs a CAD helper",
            body_html="<p>Who can help?</p><ul><li>Fusion 360</li><li>Free pizza</li></ul>",
        ),
        Post(
            author_id=aisha.id, visibility="followers", body_html="<p>Moving to the new dorm next week.</p>"
        ),
        Post(
            author_id=omar.id,
            visibility="campus",
            body_html='<p>Library hours: <a href="https://library.example">see here</a>.</p>',
        ),
        Post(
            author_id=dean.id,
            visibility="campus",
            type="announcement",
            title="Exam timetable",
            pinned=True,
            body_html="<p>The timetable is online.</p>",
        ),
        Post(
            author_id=karim.id,
            community_id=robotics.id,
            visibility="campus",
            type="event",
            title="Robot open day",
            body_html="<p>Drive a robot yourself.</p>",
        ),
        Post(
            author_id=yusuf.id,
            visibility="campus",
            body_html="<p>Omar is an idiot and everyone should tell him so.</p>",
        ),
    ]
    for post in posts:
        db.add(post)
        db.flush()
    start = now() + timedelta(days=14)
    db.add(
        Event(
            post_id=posts[5].id,
            starts_at=start,
            ends_at=start + timedelta(hours=3),
            location="Lab 3",
            capacity=2,
            rsvp_deadline=start - timedelta(days=1),
        )
    )
    db.flush()
    db.add_all(
        [
            Rsvp(event_id=posts[5].id, user_id=aisha.id, status="going"),
            PostImage(post_id=posts[3].id, content_type="image/png", alt_text="A blue square", data=PIXEL),
            Comment(post_id=posts[1].id, author_id=karim.id, body="I know Fusion 360, see you Tuesday!"),
            Comment(post_id=posts[3].id, author_id=yusuf.id, body="Thanks, very useful."),
            Reaction(post_id=posts[3].id, user_id=aisha.id, kind="like"),
            Post(
                author_id=lina.id,
                visibility="campus",
                body_html="<p>Worth knowing!</p>",
                reshare_of_id=posts[3].id,
            ),
            Report(
                reporter_id=omar.id,
                target_type="post",
                target_id=posts[6].id,
                target_user_id=yusuf.id,
                reason="harassment",
                triage="unscored",
            ),
        ]
    )
    conversation = Conversation(user_a_id=aisha.id, user_b_id=omar.id)
    draft = Draft(
        community_id=robotics.id,
        creator_id=lina.id,
        kind="announcement",
        title="Spring competition",
        ydoc=demo_document("The spring competition is on 12 March."),
    )
    db.add_all([conversation, draft])
    db.flush()
    db.add_all(
        [
            Message(conversation_id=conversation.id, sender_id=omar.id, body="Are you coming on Thursday?"),
            Message(conversation_id=conversation.id, sender_id=aisha.id, body="Yes, see you there."),
            DraftCollaborator(draft_id=draft.id, user_id=lina.id),
            DraftCollaborator(draft_id=draft.id, user_id=karim.id),
        ]
    )
    db.commit()


def main() -> None:
    """Recreate all tables and load the data."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        load_demo(db)
    print("Demonstration data loaded. Sign in as <handle>@campus.example, password:", PASSWORD)
    print("Handles:", ", ".join(person[0] for person in PEOPLE))


if __name__ == "__main__":
    main()
