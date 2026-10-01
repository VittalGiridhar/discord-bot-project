import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from sqlmodel import Session, select

from app.db import get_session, init_db
from app.discord_client import mirror_and_record_status
from app.models import CommandLog
from app.verify import verify_signature

load_dotenv()

PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
MIRROR_WEBHOOK_URL = os.environ["MIRROR_WEBHOOK_URL"]

app = FastAPI()

PING = 1
APPLICATION_COMMAND = 2

PONG = 1
CHANNEL_MESSAGE_WITH_SOURCE = 4


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/interactions")
async def interactions(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signature_ed25519: str = Header(...),
    x_signature_timestamp: str = Header(...),
    session: Session = Depends(get_session),
):
    body = await request.body()

    if not verify_signature(PUBLIC_KEY, x_signature_ed25519, x_signature_timestamp, body):
        raise HTTPException(status_code=401, detail="invalid request signature")

    payload = await request.json()
    interaction_type = payload["type"]

    if interaction_type == PING:
        return {"type": PONG}

    if interaction_type == APPLICATION_COMMAND:
        interaction_id = payload["id"]

        existing = session.exec(
            select(CommandLog).where(CommandLog.interaction_id == interaction_id)
        ).first()
        if existing:
            return {
                "type": CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {"content": existing.action_taken},
            }

        command_name = payload["data"]["name"]
        member = payload.get("member", {})
        discord_user = member.get("user", {}).get("username", "unknown")

        input_text = ""
        if command_name == "status":
            content = "Bot is up and running."
        elif command_name == "report":
            options = payload["data"].get("options", [])
            input_text = next((o["value"] for o in options if o["name"] == "text"), "")
            content = f"Report received: {input_text}"
        else:
            content = f"Unknown command: {command_name}"

        log = CommandLog(
            interaction_id=interaction_id,
            command_name=command_name,
            discord_user=discord_user,
            input_text=input_text,
            action_taken=content,
        )
        session.add(log)
        session.commit()

        mirror_message = f"**/{command_name}** by {discord_user}: {content}"
        background_tasks.add_task(
            mirror_and_record_status, interaction_id, MIRROR_WEBHOOK_URL, mirror_message
        )

        return {
            "type": CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {"content": content},
        }

    raise HTTPException(status_code=400, detail="unhandled interaction type")
