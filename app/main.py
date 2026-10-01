import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

from app.verify import verify_signature

load_dotenv()

PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]

app = FastAPI()

PING = 1
APPLICATION_COMMAND = 2

PONG = 1
CHANNEL_MESSAGE_WITH_SOURCE = 4


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/interactions")
async def interactions(
    request: Request,
    x_signature_ed25519: str = Header(...),
    x_signature_timestamp: str = Header(...),
):
    body = await request.body()

    if not verify_signature(PUBLIC_KEY, x_signature_ed25519, x_signature_timestamp, body):
        raise HTTPException(status_code=401, detail="invalid request signature")

    payload = await request.json()
    interaction_type = payload["type"]

    if interaction_type == PING:
        return {"type": PONG}

    if interaction_type == APPLICATION_COMMAND:
        command_name = payload["data"]["name"]

        if command_name == "status":
            content = "Bot is up and running."
        elif command_name == "report":
            options = payload["data"].get("options", [])
            text = next((o["value"] for o in options if o["name"] == "text"), "")
            content = f"Report received: {text}"
        else:
            content = f"Unknown command: {command_name}"

        return {
            "type": CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {"content": content},
        }

    raise HTTPException(status_code=400, detail="unhandled interaction type")
