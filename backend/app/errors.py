"""Uniform REST error format {"error": {"code", "message", "details"?}} and the error catalogue."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

CATALOGUE: dict[str, tuple[int, str]] = {
    "VALIDATION_ERROR": (400, "The request is invalid."),
    "EMPTY_CONTENT": (400, "There is no text left after removing unsupported content."),
    "CONTENT_TOO_LONG": (400, "The text may have at most 5,000 characters."),
    "INVALID_AUDIENCE": (400, "This visibility cannot be combined with this place."),
    "ACTION_NOT_ALLOWED": (400, "This action cannot be applied to this kind of target."),
    "NOT_YOURSELF": (400, "You cannot do this to your own account or content."),
    "UNAUTHENTICATED": (401, "Sign in first."),
    "BAD_CREDENTIALS": (401, "Wrong email or password."),
    "DOMAIN_NOT_ALLOWED": (403, "Connect is only for university members."),
    "NOT_ADMIN": (403, "Only a school admin can do this."),
    "NOT_MODERATOR": (403, "Only a moderator can do this."),
    "NOT_A_MEMBER": (403, "Only members of the community can do this."),
    "NOT_AN_OFFICER": (403, "Only officers of the community can do this."),
    "NOT_OWNER": (403, "Only the owner of the community can do this."),
    "NOT_AUTHOR": (403, "Only the author can do this."),
    "ROLE_NOT_ALLOWED": (403, "Your role cannot do this."),
    "MUTED": (403, "You are muted by a moderator and can only read."),
    "COMMENTS_DISABLED": (403, "Comments are disabled."),
    "BLOCKED": (403, "You cannot message this person."),
    "SAME_MODERATOR": (403, "An appeal is decided by a different moderator."),
    "USER_NOT_FOUND": (404, "User not found."),
    "COMMUNITY_NOT_FOUND": (404, "Community not found."),
    "REQUEST_NOT_FOUND": (404, "There is no such pending request."),
    "POST_NOT_FOUND": (404, "Post not found."),
    "COMMENT_NOT_FOUND": (404, "Comment not found."),
    "IMAGE_NOT_FOUND": (404, "Image not found."),
    "DRAFT_NOT_FOUND": (404, "Draft not found."),
    "CONVERSATION_NOT_FOUND": (404, "Conversation not found."),
    "TARGET_NOT_FOUND": (404, "The reported item was not found."),
    "REPORT_NOT_FOUND": (404, "Report not found."),
    "ACTION_NOT_FOUND": (404, "Moderation action not found."),
    "APPEAL_NOT_FOUND": (404, "Appeal not found."),
    "EMAIL_TAKEN": (409, "An account with this email or handle exists already."),
    "NAME_TAKEN": (409, "A community with this name exists already."),
    "ALREADY_MEMBER": (409, "You are a member or have asked to join already."),
    "ALREADY_DECIDED": (409, "Someone else has decided this already."),
    "OWNER_CANNOT_LEAVE": (409, "The owner cannot leave or be removed."),
    "VERSION_CONFLICT": (409, "Someone changed this in the meantime. Reload and try again."),
    "ALREADY_PUBLISHED": (409, "This draft was already published."),
    "CONTENT_FROZEN": (409, "Hidden content accepts no changes or interactions."),
    "NOT_RESHAREABLE": (409, "Only campus-visible posts can be reshared."),
    "TOO_MANY_IMAGES": (409, "A post can have at most 4 images."),
    "TOO_MANY_PINS": (409, "A community can have at most 3 pinned posts."),
    "DUPLICATE_REPORT": (409, "You have already reported this."),
    "ALREADY_APPEALED": (409, "You have already appealed this decision."),
    "EDIT_WINDOW_CLOSED": (410, "Comments can be edited for 15 minutes."),
    "RSVP_CLOSED": (410, "RSVPs for this event are closed."),
    "APPEAL_WINDOW_CLOSED": (410, "The appeal window of 7 days is closed."),
    "IMAGE_TOO_LARGE": (413, "An image may have at most 5 MB."),
    "IMAGE_TYPE": (415, "Only PNG, JPEG, GIF and WebP images are accepted."),
    "LOCKED": (423, "This discussion is locked."),
}


class ErrorDetail(BaseModel):
    """One invalid field."""

    field: str = Field(examples=["title"])
    message: str = Field(examples=["String should have at most 120 characters"])


class ErrorBody(BaseModel):
    """Machine-readable code, human-readable message and optional field details."""

    code: str = Field(examples=["POST_NOT_FOUND"])
    message: str = Field(examples=["Post not found."])
    details: list[ErrorDetail] | dict | None = None


class ErrorResponse(BaseModel):
    """Every error response of the REST API has this shape."""

    error: ErrorBody


class ApiError(Exception):
    """An expected refusal; the status and message come from the catalogue."""

    def __init__(self, code: str, details: dict | None = None) -> None:
        self.code = code
        self.details = details
        self.status_code, self.message = CATALOGUE[code]


def errors(*codes: str, public: bool = False) -> dict[int | str, dict]:
    """Build the OpenAPI `responses` argument; 401 is included unless the endpoint is public."""
    grouped: dict[int | str, dict] = {}
    for code in codes if public else ("UNAUTHENTICATED", *codes):
        status, message = CATALOGUE[code]
        entry = grouped.setdefault(
            status,
            {"model": ErrorResponse, "description": "", "content": {"application/json": {"examples": {}}}},
        )
        entry["description"] = (entry["description"] + f" `{code}`: {message}").strip()
        entry["content"]["application/json"]["examples"][code] = {
            "value": {"error": {"code": code, "message": message}}
        }
    return grouped


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    """Render an ApiError."""
    body: dict = {"code": exc.code, "message": exc.message}
    if exc.details:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content={"error": body})


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Render Pydantic validation errors as 400 VALIDATION_ERROR."""
    details = [
        {"field": ".".join(str(part) for part in err["loc"][1:]) or "body", "message": err["msg"]}
        for err in exc.errors()
    ]
    body = {"code": "VALIDATION_ERROR", "message": "The request is invalid.", "details": details}
    return JSONResponse(status_code=400, content={"error": body})
