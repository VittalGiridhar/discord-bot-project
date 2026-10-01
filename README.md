# Discord Slash-Command Bot

A FastAPI web app + Discord bot. Users run slash commands in Discord; the app verifies, records, and replies to them, mirrors a notification to a second Discord channel, and shows everything on an admin dashboard.

## What it does

- `/status` — returns a simple status reply
- `/report <text>` — records the report text and confirms receipt
- Every command is verified (Discord's Ed25519 signature), recorded in Postgres, replied to in Discord, and mirrored as a notification to a second Discord channel (configurable from the dashboard)
- Duplicate interactions (same interaction ID delivered twice by Discord) are not reprocessed
- If the mirror notification fails, the bot still replies successfully and the failure is recorded (not silently dropped)
- An admin dashboard (behind login) shows the full command log and lets the admin set which Discord server/channel/mirror-webhook the bot is connected to

## Tech stack

- **Backend:** FastAPI (Python)
- **Database:** Postgres (hosted on [Neon](https://neon.tech), free tier)
- **Frontend:** Server-rendered Jinja2 templates (no separate frontend framework)
- **Hosting:** [Render](https://render.com), free tier
- **Discord:** Bot + 2 slash commands registered via Discord's REST API, interactions delivered via HTTP (no gateway/websocket)

## Running locally

1. Clone the repo and create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in the values (see **Environment variables** below)
3. Run the app:
   ```
   uvicorn app.main:app --reload
   ```
4. Visit `http://127.0.0.1:8000/health` to confirm it's running

Note: Discord's interactions endpoint cannot point at `localhost` — to receive real Discord traffic you need a public URL (see **Deployment**). Local running is useful for the dashboard and for testing logic directly.

## Environment variables

See `.env.example` for the full list. Summary:

| Variable | Where to get it |
|---|---|
| `DISCORD_PUBLIC_KEY` | Discord Developer Portal → your app → General Information |
| `DISCORD_BOT_TOKEN` | Discord Developer Portal → your app → Bot → Reset Token |
| `DISCORD_APPLICATION_ID` | Discord Developer Portal → your app → General Information |
| `DATABASE_URL` | Neon project → Connect → connection string |
| `MIRROR_WEBHOOK_URL` | A Discord channel → Edit Channel → Integrations → Webhooks (used as a fallback before the dashboard config is set) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Pick your own — this is the dashboard login |
| `SESSION_SECRET` | Any long random string, used to sign the login session cookie |

## Registering slash commands

One-time setup, run after setting `DISCORD_APPLICATION_ID` and `DISCORD_BOT_TOKEN` in `.env`:
```
python register_commands.py
```
This registers `/status` and `/report` with Discord.

## Deployment

Deployed on **Render** as a Python web service:
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- All variables from `.env.example` are set as Render environment variables (never committed to the repo)

After deploying, the Render URL + `/interactions` is set as the **Interactions Endpoint URL** in the Discord Developer Portal (General Information tab). Discord verifies this URL by sending a signed PING, which the app must answer correctly before Discord will accept it.

Database: a free [Neon](https://neon.tech) Postgres project. Tables are created automatically on app startup.

## Using the dashboard

1. Go to `/login` and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`
2. On `/dashboard`, fill in the Guild ID, Reply Channel ID, and Mirror Webhook URL for your Discord server, click Save
3. The command log table below shows every interaction received, with status (`ok` or `mirror_failed`)

## Testing this submission

- **Live app:** https://discord-bot-project-xa1w.onrender.com
- **Test Discord server invite:** https://discord.gg/cKHGcS2ew — join this server to see the bot and the mirror notification channel (`#mirror-log`) directly
- **Admin dashboard login:** https://discord-bot-project-xa1w.onrender.com/login
  - Username: `admin`
  - Password: `a0gZ0iiXoX5DmwpI`
  - (Throwaway credentials, created for grading this submission.)

To test the bot: join the server above, then run `/status` or `/report <some text>` in any text channel. You should see: a reply from the bot, a mirrored message in `#mirror-log`, and a new row on the admin dashboard's command log.
