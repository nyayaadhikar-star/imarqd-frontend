# apps/api/src/app/db/crud_user_media.py
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UserMedia

async def upsert_user_media(
    db: AsyncSession,
    user_uuid: str,
    email_sha: str,
    media_id: str,
    file_sha256: str | None = None,
    ipfs_cid: str | None = None,
) -> None:
    media_id = media_id.lower()
    email_sha = email_sha.lower()
    file_sha256 = (file_sha256 or "").lower() or None

    # Try insert; on conflict (user_uuid, media_id) do nothing, but refresh last_seen_at
    # SQLAlchemy 2.x portable way:
    stmt = insert(UserMedia).values(
        user_uuid=user_uuid, email_sha=email_sha, media_id=media_id,
        file_sha256=file_sha256, ipfs_cid=ipfs_cid
    ).on_conflict_do_nothing(
        index_elements=["user_uuid", "media_id"]
    )
    await db.execute(stmt)

    # Touch last_seen_at even if already present
    await db.execute(
        select(UserMedia).where(
            UserMedia.user_uuid == user_uuid,
            UserMedia.media_id == media_id
        ).with_for_update()
    )
    await db.commit()

async def get_user_media_ids(db: AsyncSession, user_uuid: str) -> list[str]:
    q = await db.execute(
        select(UserMedia.media_id).where(UserMedia.user_uuid == user_uuid)
    )
    return [row[0] for row in q.all()]
