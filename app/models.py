from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ServerConfig(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    guild_id: str = Field(unique=True)
    reply_channel_id: str
    mirror_webhook_url: str
    created_at: datetime = Field(default_factory=utcnow)


class CommandLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    interaction_id: str = Field(unique=True)
    command_name: str
    discord_user: str
    input_text: str = ""
    action_taken: str = ""
    status: str = "ok"
    created_at: datetime = Field(default_factory=utcnow)
