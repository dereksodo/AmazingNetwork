"""Profiles, following and blocking (FR-INT-3, FR-AUD-3)."""

from fastapi import APIRouter
from sqlalchemy import and_, delete, or_, select

from app import policy
from app.auth.sessions import CurrentUser, Db
from app.db import emit
from app.errors import ApiError, errors
from app.models import Block, Follow, User
from app.notifications.service import notify
from app.people import profiles
from app.people.schemas import Decision, FollowState, Profile, UserRef
from app.realtime.hub import LiveEvent

router = APIRouter(tags=["people"])


@router.get("/users", response_model=list[UserRef], responses=errors())
def list_users(user: CurrentUser, db: Db, q: str = ""):
    """Find up to 30 users by name or handle. Blocked and deleted accounts are left out.

    **Role:** signed in.
    """
    return db.scalars(
        select(User)
        .where(
            policy.visible_users(user),
            User.id != user.id,
            or_(User.display_name.icontains(q, autoescape=True), User.handle.icontains(q, autoescape=True)),
        )
        .order_by(User.display_name)
        .limit(30)
    ).all()


@router.get("/users/{user_id}", response_model=Profile, responses=errors("USER_NOT_FOUND"))
def get_user(user_id: int, user: CurrentUser, db: Db):
    """Return a profile. A user in a block relationship looks like a missing user.

    **Role:** signed in, no block in either direction.
    """
    return profiles.profile(db, user, policy.get_visible_user(db, user, user_id))


@router.put(
    "/users/{user_id}/follow",
    response_model=FollowState,
    responses=errors("USER_NOT_FOUND", "NOT_YOURSELF"),
)
def follow_user(user_id: int, user: CurrentUser, db: Db):
    """Follow a user; pending until accepted if they approve followers. Idempotent.

    **Role:** signed in, no block in either direction.
    """
    if user_id == user.id:
        raise ApiError("NOT_YOURSELF")
    followed = policy.get_visible_user(db, user, user_id)
    follow = db.get(Follow, (user.id, user_id))
    if follow is None:
        follow = Follow(
            follower_id=user.id,
            followed_id=user_id,
            status="pending" if followed.approve_followers else "active",
        )
        db.add(follow)
        wording = "wants to follow you" if follow.status == "pending" else "follows you"
        notify(db, user_id, "follow", f"{user.display_name} {wording}.")
        db.commit()
    return FollowState(status=follow.status)


@router.delete("/users/{user_id}/follow", status_code=204, responses=errors())
def unfollow_user(user_id: int, user: CurrentUser, db: Db):
    """Stop following a user or withdraw a request. Idempotent.

    **Role:** signed in.
    """
    db.execute(delete(Follow).where(Follow.follower_id == user.id, Follow.followed_id == user_id))
    db.commit()


@router.get("/follow-requests", response_model=list[UserRef], responses=errors())
def list_follow_requests(user: CurrentUser, db: Db):
    """List users waiting for the caller's approval.

    **Role:** signed in.
    """
    return db.scalars(
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.followed_id == user.id, Follow.status == "pending", policy.visible_users(user))
    ).all()


@router.post("/follow-requests/{follower_id}", status_code=204, responses=errors("REQUEST_NOT_FOUND"))
def decide_follow_request(follower_id: int, body: Decision, user: CurrentUser, db: Db):
    """Accept or reject a pending follow request.

    **Role:** the followed user.
    """
    follow = db.get(Follow, (follower_id, user.id))
    if follow is None or follow.status != "pending":
        raise ApiError("REQUEST_NOT_FOUND")
    if body.accept:
        follow.status = "active"
        notify(db, follower_id, "follow", f"{user.display_name} accepted your follow request.")
    else:
        db.delete(follow)
    db.commit()


@router.delete("/followers/{follower_id}", status_code=204, responses=errors())
def remove_follower(follower_id: int, user: CurrentUser, db: Db):
    """Remove a follower, who loses access to followers-only posts. Idempotent.

    **Role:** the followed user.
    """
    db.execute(delete(Follow).where(Follow.follower_id == follower_id, Follow.followed_id == user.id))
    db.commit()


@router.get("/blocks", response_model=list[UserRef], responses=errors())
def list_blocks(user: CurrentUser, db: Db):
    """List the users the caller has blocked.

    **Role:** signed in.
    """
    return db.scalars(
        select(User).join(Block, Block.blocked_id == User.id).where(Block.blocker_id == user.id)
    ).all()


@router.put("/users/{user_id}/block", status_code=204, responses=errors("USER_NOT_FOUND", "NOT_YOURSELF"))
def block_user(user_id: int, user: CurrentUser, db: Db):
    """Block a user: mutual invisibility, and follows in both directions end. Idempotent.

    **Role:** signed in.
    """
    if user_id == user.id:
        raise ApiError("NOT_YOURSELF")
    if db.get(Block, (user.id, user_id)) is None:
        policy.get_visible_user(db, user, user_id)
        db.add(Block(blocker_id=user.id, blocked_id=user_id))
        db.execute(
            delete(Follow).where(
                or_(
                    and_(Follow.follower_id == user.id, Follow.followed_id == user_id),
                    and_(Follow.follower_id == user_id, Follow.followed_id == user.id),
                )
            )
        )
        emit(db, LiveEvent(f"user:{user_id}", "audience.changed"))
        emit(db, LiveEvent(f"user:{user.id}", "audience.changed"))
        db.commit()


@router.delete("/users/{user_id}/block", status_code=204, responses=errors())
def unblock_user(user_id: int, user: CurrentUser, db: Db):
    """Remove the caller's block. Idempotent; earlier follows do not come back.

    **Role:** signed in.
    """
    db.execute(delete(Block).where(Block.blocker_id == user.id, Block.blocked_id == user_id))
    db.commit()
