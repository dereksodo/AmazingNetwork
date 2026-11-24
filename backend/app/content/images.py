"""Post images (FR-PUB-1). The bytes are stored in the database."""

from typing import Annotated

from fastapi import APIRouter, Form, Response, UploadFile

from app import policy
from app.auth.sessions import CurrentUser, Db
from app.content.posts import emit_post
from app.content.schemas import ImageOut
from app.errors import ApiError, errors
from app.models import PostImage

router = APIRouter(tags=["images"])
MAX_IMAGES = 4
MAX_BYTES = 5 * 1024 * 1024


def detect_type(data: bytes) -> str:
    """Image type from the file signature; the name and type sent by the client are not trusted."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise ApiError("IMAGE_TYPE")


@router.post(
    "/posts/{post_id}/images",
    status_code=201,
    response_model=ImageOut,
    responses=errors(
        "MUTED", "NOT_AUTHOR", "POST_NOT_FOUND", "CONTENT_FROZEN", "TOO_MANY_IMAGES", "IMAGE_TOO_LARGE",
        "IMAGE_TYPE",
    ),
)  # fmt: skip
def upload_image(
    post_id: int, file: UploadFile, alt_text: Annotated[str, Form(max_length=200)], user: CurrentUser, db: Db
):
    """Add an image of at most 5 MB to a post (at most 4 per post).

    **Role:** author, not muted.
    """
    post = policy.get_own_post(db, user, post_id)
    if len(post.images) >= MAX_IMAGES:
        raise ApiError("TOO_MANY_IMAGES")
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ApiError("IMAGE_TOO_LARGE")
    image = PostImage(post_id=post_id, content_type=detect_type(data), alt_text=alt_text, data=data)
    db.add(image)
    emit_post(db, post, "post.updated")
    db.commit()
    return image


@router.get(
    "/images/{image_id}",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}, "image/jpeg": {}, "image/gif": {}, "image/webp": {}}},
        **errors("IMAGE_NOT_FOUND"),
    },
)
def get_image(image_id: int, user: CurrentUser, db: Db):
    """Return the bytes of an image.

    **Role:** in the audience of the post.
    """
    image = db.get(PostImage, image_id)
    if image is None or not policy.can_view_post(db, user, image.post_id):
        raise ApiError("IMAGE_NOT_FOUND")
    return Response(image.data, media_type=image.content_type, headers={"X-Content-Type-Options": "nosniff"})
