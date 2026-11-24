"""Sign-up, sign-in, sign-out and the caller's own account (FR-ID)."""

from fastapi import APIRouter
from sqlalchemy import delete, exists, or_, select

from app import config
from app.auth.passwords import hash_password, verify_password
from app.auth.sessions import Credentials as BearerCredentials
from app.auth.sessions import CurrentUser, Db, create_session, end_session
from app.db import emit, now
from app.errors import ApiError, errors
from app.models import AuthSession, StudyProgramme, User
from app.people import profiles
from app.people.schemas import Credentials, Me, ProfileUpdate, Programme, Registration, SignedIn
from app.realtime.hub import LiveEvent

router = APIRouter(tags=["identity"])


@router.get("/programmes", response_model=list[Programme])
def list_programmes(db: Db):
    """List the study programmes offered on the sign-up form.

    **Role:** anyone.
    """
    return db.scalars(select(StudyProgramme).order_by(StudyProgramme.name)).all()


@router.post(
    "/auth/register",
    status_code=201,
    response_model=SignedIn,
    responses=errors("DOMAIN_NOT_ALLOWED", "EMAIL_TAKEN", public=True),
)
def register(body: Registration, db: Db):
    """Create an account with a university email address and sign in.

    **Role:** anyone. The password is stored as a salted scrypt hash.
    """
    email = body.email.lower()
    if not email.endswith(f"@{config.EMAIL_DOMAIN}"):
        raise ApiError("DOMAIN_NOT_ALLOWED")
    if db.scalar(select(exists().where(or_(User.email == email, User.handle == body.handle)))):
        raise ApiError("EMAIL_TAKEN")
    user = User(
        email=email,
        handle=body.handle,
        display_name=body.display_name,
        programme_id=body.programme_id,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()
    token = create_session(db, user)
    db.commit()
    return SignedIn(token=token, user=profiles.me(db, user))


@router.post("/auth/login", response_model=SignedIn, responses=errors("BAD_CREDENTIALS", public=True))
def login(body: Credentials, db: Db):
    """Sign in. Send the returned token as `Authorization: Bearer <token>`.

    **Role:** anyone.
    """
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.deleted_at.is_(None)))
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError("BAD_CREDENTIALS")
    token = create_session(db, user)
    db.commit()
    return SignedIn(token=token, user=profiles.me(db, user))


@router.post("/auth/logout", status_code=204, responses=errors())
def logout(user: CurrentUser, credentials: BearerCredentials, db: Db):
    """End this session; live connections opened with the token are closed (4401).

    **Role:** signed in.
    """
    end_session(db, credentials.credentials)
    emit(db, LiveEvent(f"user:{user.id}", "session.ended"))
    db.commit()


@router.get("/me", response_model=Me, responses=errors())
def get_me(user: CurrentUser, db: Db):
    """Return the caller's account, role, memberships and active mute.

    **Role:** signed in.
    """
    return profiles.me(db, user)


@router.patch("/me", response_model=Me, responses=errors())
def update_me(body: ProfileUpdate, user: CurrentUser, db: Db):
    """Change the caller's profile. Fields that are left out stay as they are.

    **Role:** signed in.
    """
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(user, name, value)
    db.commit()
    db.refresh(user)
    return profiles.me(db, user)


@router.delete("/me", status_code=204, responses=errors())
def delete_me(user: CurrentUser, db: Db):
    """Request account deletion: invisible at once, purged within 30 days (FR-ID-5).

    **Role:** signed in. All sessions end.
    """
    user.deleted_at = now()
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    emit(db, LiveEvent(f"user:{user.id}", "session.ended"))
    db.commit()
