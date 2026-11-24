"""Building profile responses."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import now
from app.models import Follow, Membership, Sanction, User
from app.people.schemas import Me, MyMembership, Profile, UserRef


def me(db: Session, user: User) -> Me:
    """The caller's own account."""
    memberships = db.scalars(select(Membership).where(Membership.user_id == user.id))
    muted_until = db.scalar(
        select(func.max(Sanction.ends_at)).where(Sanction.user_id == user.id, Sanction.ends_at > now())
    )
    return Me(
        **UserRef.model_validate(user).model_dump(),
        email=user.email,
        bio=user.bio,
        role=user.role,
        programme=user.programme,
        approve_followers=user.approve_followers,
        memberships=[
            MyMembership(
                community_id=m.community_id,
                community_name=m.community.name,
                role=m.role,
                status=m.status,
            )
            for m in memberships
        ],
        muted_until=muted_until and muted_until.isoformat(),
    )


def profile(db: Session, viewer: User, user: User) -> Profile:
    """Another user's profile as the viewer sees it."""
    follow = db.get(Follow, (viewer.id, user.id))
    followers = db.scalar(
        select(func.count())
        .select_from(Follow)
        .where(Follow.followed_id == user.id, Follow.status == "active")
    )
    return Profile(
        **UserRef.model_validate(user).model_dump(),
        bio=user.bio,
        role=user.role,
        programme=user.programme,
        approve_followers=user.approve_followers,
        follow_status=follow.status if follow else "none",
        follower_count=followers,
    )
