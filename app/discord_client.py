import httpx
from sqlmodel import Session, select

from app.db import engine
from app.models import CommandLog


def post_mirror(webhook_url: str, content: str) -> bool:
    try:
        response = httpx.post(webhook_url, json={"content": content}, timeout=5)
        response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def mirror_and_record_status(interaction_id: str, webhook_url: str, content: str):
    success = post_mirror(webhook_url, content)
    if not success:
        with Session(engine) as session:
            log = session.exec(
                select(CommandLog).where(CommandLog.interaction_id == interaction_id)
            ).first()
            if log:
                log.status = "mirror_failed"
                session.add(log)
                session.commit()
