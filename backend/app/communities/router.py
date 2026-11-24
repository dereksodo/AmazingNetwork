"""Communities, membership, following and muting (FR-COM, FR-INT-3, FR-INT-5)."""

from typing import Literal

from fastapi import APIRouter, Response
from pydantic import Field
from sqlalchemy import delete, exists, func, select
from sqlalchemy.orm import Session

from app import policy
from app.auth.sessions import CurrentUser, Db
from app.db import emit
from app.errors import ApiError, errors
from app.models import Community, CommunityFollow, CommunityMute, Membership, User
from app.notifications.service import notify
from app.people.schemas import Decision
from app.realtime.hub import LiveEvent
from app.schemas import ApiInput, ApiModel, UserRef

router = APIRouter(tags=["communities"], prefix="/communities")


class CommunityInput(ApiInput):
    """Request for a new community."""

    name: str = Field(min_length=3, max_length=80, examples=["Robotics Club"])
    description: str = Field(max_length=500, examples=["We build robots every Tuesday."])
    join_policy: Literal["open", "closed"]


class CommunityOut(ApiModel):
    """A community and the caller's relationship to it."""

    id: int
    name: str
    description: str
    join_policy: Literal["open", "closed"]
    status: Literal["pending", "approved", "rejected"]
    member_count: int
    my_role: Literal["member", "officer", "owner"] | None
    my_status: Literal["pending", "active"] | None
    following: bool
    muted: bool


class MemberOut(ApiModel):
    """A member or a pending request."""

    user: UserRef
    role: Literal["member", "officer", "owner"]
    status: Literal["pending", "active"]


class JoinState(ApiModel):
    """The caller's membership after joining."""

    status: Literal["pending", "active"]


class RoleChange(ApiInput):
    """New role of a member."""

    role: Literal["member", "officer"]


def community_out(db: Session, user: User, community: Community) -> CommunityOut:
    """Describe a community to the caller."""
    mine = db.get(Membership, (user.id, community.id))
    return CommunityOut(
        id=community.id,
        name=community.name,
        description=community.description,
        join_policy=community.join_policy,
        status=community.status,
        member_count=db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.community_id == community.id, Membership.status == "active")
        ),
        my_role=mine and mine.role,
        my_status=mine and mine.status,
        following=db.get(CommunityFollow, (user.id, community.id)) is not None,
        muted=db.get(CommunityMute, (user.id, community.id)) is not None,
    )


def _changed(db: Session, community_id: int) -> None:
    emit(db, LiveEvent(f"community:{community_id}", "members.changed", {"community_id": community_id}))


@router.get("", response_model=list[CommunityOut], responses=errors())
def list_communities(user: CurrentUser, db: Db):
    """List approved communities and the caller's own requests.

    **Role:** signed in. Admins also see pending and rejected requests.
    """
    found = db.scalars(select(Community).where(policy.visible_communities(user)).order_by(Community.name))
    return [community_out(db, user, community) for community in found.all()]


@router.post("", status_code=202, response_model=CommunityOut, responses=errors("NAME_TAKEN"))
def request_community(body: CommunityInput, user: CurrentUser, db: Db):
    """Request a community. It is pending until an admin approves it; the requester becomes owner.

    **Role:** signed in.
    """
    if db.scalar(select(exists().where(Community.name == body.name))):
        raise ApiError("NAME_TAKEN")
    community = Community(**body.model_dump(), created_by_id=user.id)
    db.add(community)
    db.flush()
    db.add(Membership(user_id=user.id, community_id=community.id, role="owner"))
    db.commit()
    return community_out(db, user, community)


@router.get("/{community_id}", response_model=CommunityOut, responses=errors("COMMUNITY_NOT_FOUND"))
def get_community(community_id: int, user: CurrentUser, db: Db):
    """Return one community.

    **Role:** signed in; pending communities only for their requester and admins.
    """
    return community_out(db, user, policy.get_visible_community(db, user, community_id))


@router.post(
    "/{community_id}/join",
    response_model=JoinState,
    responses={
        202: {"model": JoinState, "description": "Closed community: an officer must accept."},
        **errors("COMMUNITY_NOT_FOUND", "ALREADY_MEMBER"),
    },
)
def join(community_id: int, response: Response, user: CurrentUser, db: Db):
    """Join an open community at once (200) or ask to join a closed one (202).

    **Role:** signed in.
    """
    community = policy.get_open_community(db, user, community_id)
    if db.get(Membership, (user.id, community_id)) is not None:
        raise ApiError("ALREADY_MEMBER")
    status = "active" if community.join_policy == "open" else "pending"
    db.add(Membership(user_id=user.id, community_id=community_id, status=status))
    _changed(db, community_id)
    db.commit()
    response.status_code = 200 if status == "active" else 202
    return JoinState(status=status)


@router.get(
    "/{community_id}/members",
    response_model=list[MemberOut],
    responses=errors("COMMUNITY_NOT_FOUND", "NOT_A_MEMBER"),
)
def list_members(community_id: int, user: CurrentUser, db: Db):
    """List the members; officers also see pending requests.

    **Role:** member.
    """
    policy.get_open_community(db, user, community_id)
    if policy.membership(db, user, community_id) is None:
        raise ApiError("NOT_A_MEMBER")
    query = (
        select(Membership)
        .join(User)
        .where(Membership.community_id == community_id, policy.visible_users(user))
        .order_by(User.display_name)
    )
    if not policy.is_officer(db, user, community_id):
        query = query.where(Membership.status == "active")
    return db.scalars(query).all()


@router.post(
    "/{community_id}/requests/{user_id}",
    status_code=204,
    responses=errors("COMMUNITY_NOT_FOUND", "NOT_AN_OFFICER", "REQUEST_NOT_FOUND"),
)
def decide_join_request(community_id: int, user_id: int, body: Decision, user: CurrentUser, db: Db):
    """Accept or reject a request to join a closed community.

    **Role:** officer.
    """
    community = policy.get_open_community(db, user, community_id)
    policy.require_officer(db, user, community_id)
    request = db.get(Membership, (user_id, community_id))
    if request is None or request.status != "pending":
        raise ApiError("REQUEST_NOT_FOUND")
    if body.accept:
        request.status = "active"
    else:
        db.delete(request)
    outcome = "accepted" if body.accept else "declined"
    notify(db, user_id, "membership", f"Your request to join {community.name} was {outcome}.")
    _changed(db, community_id)
    db.commit()


@router.patch(
    "/{community_id}/members/{user_id}",
    status_code=204,
    responses=errors("COMMUNITY_NOT_FOUND", "NOT_OWNER", "USER_NOT_FOUND", "OWNER_CANNOT_LEAVE"),
)
def change_member_role(community_id: int, user_id: int, body: RoleChange, user: CurrentUser, db: Db):
    """Promote a member to officer or demote an officer.

    **Role:** owner.
    """
    _managed_member(db, user, community_id, user_id).role = body.role
    _changed(db, community_id)
    db.commit()


@router.delete(
    "/{community_id}/members/me",
    status_code=204,
    responses=errors("NOT_A_MEMBER", "OWNER_CANNOT_LEAVE"),
)
def leave(community_id: int, user: CurrentUser, db: Db):
    """Leave a community or withdraw a join request. Community-only content disappears at once.

    **Role:** member, except the owner.
    """
    mine = db.get(Membership, (user.id, community_id))
    if mine is None:
        raise ApiError("NOT_A_MEMBER")
    if mine.role == "owner":
        raise ApiError("OWNER_CANNOT_LEAVE")
    db.delete(mine)
    _changed(db, community_id)
    db.commit()


@router.delete(
    "/{community_id}/members/{user_id}",
    status_code=204,
    responses=errors("COMMUNITY_NOT_FOUND", "NOT_OWNER", "USER_NOT_FOUND", "OWNER_CANNOT_LEAVE"),
)
def remove_member(community_id: int, user_id: int, user: CurrentUser, db: Db):
    """Remove a member, who loses community-only content and its live events at once.

    **Role:** owner.
    """
    db.delete(_managed_member(db, user, community_id, user_id))
    _changed(db, community_id)
    db.commit()


def _managed_member(db: Session, user: User, community_id: int, user_id: int) -> Membership:
    """Load a membership the owner may change."""
    policy.get_open_community(db, user, community_id)
    mine = policy.membership(db, user, community_id)
    if mine is None or mine.role != "owner":
        raise ApiError("NOT_OWNER")
    if user_id == user.id:
        raise ApiError("OWNER_CANNOT_LEAVE")
    member = db.get(Membership, (user_id, community_id))
    if member is None or member.status != "active":
        raise ApiError("USER_NOT_FOUND")
    return member


@router.put("/{community_id}/follow", status_code=204, responses=errors("COMMUNITY_NOT_FOUND"))
def follow_community(community_id: int, user: CurrentUser, db: Db):
    """Add the community's campus posts to the caller's feed. Grants no access. Idempotent.

    **Role:** signed in.
    """
    policy.get_open_community(db, user, community_id)
    db.merge(CommunityFollow(user_id=user.id, community_id=community_id))
    db.commit()


@router.delete("/{community_id}/follow", status_code=204, responses=errors())
def unfollow_community(community_id: int, user: CurrentUser, db: Db):
    """Stop following a community. Idempotent.

    **Role:** signed in.
    """
    db.execute(
        delete(CommunityFollow).where(
            CommunityFollow.user_id == user.id, CommunityFollow.community_id == community_id
        )
    )
    db.commit()


@router.put("/{community_id}/mute", status_code=204, responses=errors("COMMUNITY_NOT_FOUND"))
def mute_community(community_id: int, user: CurrentUser, db: Db):
    """Stop notifications from a community; its posts stay in the feed. Idempotent.

    **Role:** signed in.
    """
    policy.get_open_community(db, user, community_id)
    db.merge(CommunityMute(user_id=user.id, community_id=community_id))
    db.commit()


@router.delete("/{community_id}/mute", status_code=204, responses=errors())
def unmute_community(community_id: int, user: CurrentUser, db: Db):
    """Receive notifications from a community again. Idempotent.

    **Role:** signed in.
    """
    db.execute(
        delete(CommunityMute).where(
            CommunityMute.user_id == user.id, CommunityMute.community_id == community_id
        )
    )
    db.commit()
