import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth import ADMIN_PASSWORD, ADMIN_USERNAME, COOKIE_NAME, create_session_cookie, get_current_user
from app.db import get_session, init_db
from app.discord_client import mirror_and_record_status
from app.models import CommandLog, ServerConfig
from app.verify import verify_signature

load_dotenv()

PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
MIRROR_WEBHOOK_URL = os.environ["MIRROR_WEBHOOK_URL"]

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

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


@app.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie(
            COOKIE_NAME, create_session_cookie(username), httponly=True, max_age=86400
        )
        return response
    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid credentials"}, status_code=401
    )


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get("/dashboard")
def dashboard(request: Request, session: Session = Depends(get_session)):
    if not get_current_user(request):
        return RedirectResponse("/login", status_code=302)
    logs = session.exec(select(CommandLog).order_by(CommandLog.created_at.desc())).all()
    config = session.exec(select(ServerConfig)).first()
    return templates.TemplateResponse(
        request, "dashboard.html", {"logs": logs, "config": config}
    )


@app.post("/dashboard/settings")
def update_settings(
    request: Request,
    guild_id: str = Form(...),
    reply_channel_id: str = Form(...),
    mirror_webhook_url: str = Form(...),
    session: Session = Depends(get_session),
):
    if not get_current_user(request):
        return RedirectResponse("/login", status_code=302)
    config = session.exec(select(ServerConfig)).first()
    if config:
        config.guild_id = guild_id
        config.reply_channel_id = reply_channel_id
        config.mirror_webhook_url = mirror_webhook_url
    else:
        config = ServerConfig(
            guild_id=guild_id,
            reply_channel_id=reply_channel_id,
            mirror_webhook_url=mirror_webhook_url,
        )
    session.add(config)
    session.commit()
    return RedirectResponse("/dashboard", status_code=302)


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

        config = session.exec(select(ServerConfig)).first()
        mirror_url = config.mirror_webhook_url if config else MIRROR_WEBHOOK_URL

        mirror_message = f"**/{command_name}** by {discord_user}: {content}"
        background_tasks.add_task(
            mirror_and_record_status, interaction_id, mirror_url, mirror_message
        )

        return {
            "type": CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {"content": content},
        }

    raise HTTPException(status_code=400, detail="unhandled interaction type")
