"""School administration: communities, moderators, audit log and AI statistics."""

import csv
import io
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import Field
from sqlalchemy import func, select, update

from app import policy
from app.audit import log
from app.auth.sessions import Admin, Db
from app.errors import ApiError, errors
from app.models import AiSuggestion, AuditLog, Community, User
from app.notifications.service import notify
from app.people.schemas import UserRef
from app.schemas import ApiInput, ApiModel

router = APIRouter(tags=["admin"], prefix="/admin")


class CommunityDecision(ApiInput):
    """Approve or reject a requested community."""

    accept: bool
    reason: str = Field(min_length=1, max_length=500, examples=["Meets the club policy."])


class RoleInput(ApiInput):
    """New global role."""

    role: Literal["user", "moderator"]
    reason: str = Field(min_length=1, max_length=500)


class UserWithRole(UserRef):
    """A user and their global role."""

    role: Literal["user", "moderator", "admin"]


class Agreement(ApiModel):
    """How often moderators agreed with the AI."""

    decided: int
    agreed: int


@router.post(
    "/communities/{community_id}/decision",
    status_code=204,
    responses=errors("NOT_ADMIN", "COMMUNITY_NOT_FOUND", "ALREADY_DECIDED"),
)
def decide_community(community_id: int, body: CommunityDecision, admin: Admin, db: Db):
    """Approve or reject a requested community and tell the requester.

    **Role:** admin. Audited.
    """
    community = policy.get_visible_community(db, admin, community_id)
    status = "approved" if body.accept else "rejected"
    won = db.execute(
        update(Community)
        .where(Community.id == community_id, Community.status == "pending")
        .values(status=status, decided_by_id=admin.id)
    )
    if won.rowcount == 0:
        raise ApiError("ALREADY_DECIDED")
    notify(db, community.created_by_id, "membership", f"{community.name} was {status}: {body.reason}")
    log.record(db, admin, f"community.{status}", f"community:{community_id}", body.reason)
    db.commit()


@router.put(
    "/users/{user_id}/role",
    response_model=UserWithRole,
    responses=errors("NOT_YOURSELF", "NOT_ADMIN", "USER_NOT_FOUND"),
)
def set_role(user_id: int, body: RoleInput, admin: Admin, db: Db):
    """Appoint or dismiss a moderator (FR-ID-3).

    **Role:** admin. Audited.
    """
    if user_id == admin.id:
        raise ApiError("NOT_YOURSELF")
    user = policy.get_visible_user(db, admin, user_id)
    user.role = body.role
    log.record(db, admin, f"role.{body.role}", f"user:{user_id}", body.reason)
    db.commit()
    return user


@router.get(
    "/audit-log",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}, **errors("NOT_ADMIN")},
)
def export_audit_log(start: date, end: date, admin: Admin, db: Db):
    """Export the audit log from `start` to `end` (both included, UTC) as CSV. The export is logged.

    **Role:** admin.
    """
    log.record(db, admin, "audit.export", f"{start}..{end}")
    db.commit()
    first = datetime.combine(start, time.min, UTC)
    after = datetime.combine(end, time.min, UTC) + timedelta(days=1)
    rows = db.execute(
        select(AuditLog, User.handle)
        .join(User, User.id == AuditLog.actor_id)
        .where(AuditLog.at >= first, AuditLog.at < after)
        .order_by(AuditLog.id)
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["at", "actor", "action", "target", "reason"])
    writer.writerows((e.at.isoformat(), handle, e.action, e.target, e.reason) for e, handle in rows)
    return Response(output.getvalue(), media_type="text/csv")


@router.get("/ai-agreement", response_model=Agreement, responses=errors("NOT_ADMIN"))
def get_ai_agreement(admin: Admin, db: Db):
    """How often moderators agreed with the AI suggestion (FR-AI-5).

    **Role:** admin.
    """
    decided = func.count(AiSuggestion.moderator_agreed)
    agreed = func.count().filter(AiSuggestion.moderator_agreed)
    row = db.execute(select(decided, agreed)).one()
    return Agreement(decided=row[0], agreed=row[1])
