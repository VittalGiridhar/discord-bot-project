# AI Notes

## Tools and models used

Built with Claude Code (Claude Sonnet 5), used as a pair-programmer for the entire project — planning, writing every file, running local tests, deploying, and debugging. No other AI coding tool was used. No `CLAUDE.md`, `AGENTS.md`, or `.cursorrules` file was used to drive the session — Claude Code worked directly from the assignment PDF and the conversation, with a plan written up front (in plan mode) and executed step by step with verification after each step.

Work split: Claude wrote 100% of the code, ran all local tests, and pushed to GitHub. I (the human) did everything that required my own accounts or browser — creating the Discord application, inviting the bot to a test server, creating the Neon project, setting up the Render web service, and copying API keys/connection strings/webhook URLs into the chat for Claude to wire up. I also did the final manual verification (running slash commands in Discord, checking replies).

## Key decisions

1. **Neon Postgres over SQLite.** Most free hosting tiers (including Render's) have an ephemeral filesystem — a SQLite file would be wiped on every redeploy or restart, losing the whole command log. Neon's free Postgres tier persists independently of the app host, which matters for a "dashboard shows a live log" requirement.

2. **Manual config form instead of a full Discord OAuth2 "add server" flow.** The assignment's flow ("admin connects it to a Discord server, picks a channel") could be built as a full OAuth2 flow where the admin logs in with Discord and picks from a list of their servers. That's meaningfully more code (token exchange, guild listing, permission checks) for a stretch-level UX improvement. Instead, the bot is invited once via a static Discord-generated URL, and the admin just pastes the Guild ID / Channel ID / webhook URL into a plain form. Same end state (the bot is connected and configured), far less to build and far less to debug.

3. **Mirror webhook posted as a FastAPI `BackgroundTask`, not awaited inline.** Discord requires a reply within ~3 seconds. The mirror notification is an external HTTP call to a second service that could be slow or down. Rather than building Discord's deferred-response/follow-up flow (a second interaction type to implement), the DB write and Discord reply happen synchronously (both fast, same-process), and the mirror call is scheduled to run *after* the response is already sent. If it fails, the already-saved log row is updated to `mirror_failed` instead of being lost or blocking the user-facing reply.

## The hardest bug

While building the admin dashboard, every page render failed with `TypeError: unhashable type: 'dict'` deep inside Jinja2's template cache lookup — a genuinely confusing error, since nothing in the code looked like it was hashing a dict. Claude's first instinct (and first written code) used the FastAPI/Starlette `TemplateResponse` call pattern from what is still the most common pattern online: `templates.TemplateResponse("login.html", {"request": request, "error": None})`. That pattern is from an older Starlette API. The installed Starlette version (1.7.0, pulled in fresh by `pip install` since no version was pinned) had moved to a newer signature: `TemplateResponse(request, name, context)`, with `request` as the first positional argument and no longer expected inside the context dict. Passing the dict where Starlette expected the request object meant it ended up being used as a cache key internally — hence "unhashable type: dict".

We noticed it because the local test suite we ran before deploying (hitting `/login` and `/dashboard` with curl) returned 500s, and the traceback pointed to `jinja2/utils.py`'s cache lookup rather than anywhere in our own code, which was the first clue the API itself had changed under us rather than our logic being wrong. The fix was switching every `TemplateResponse` call to the new three-positional-argument form. This is a good example of why pinning dependency versions (which this project currently doesn't do, to keep `requirements.txt` simple) is a tradeoff — unpinned installs can get a newer library than any tutorial or cached training knowledge assumed, and the fix is only obvious once you actually run the code rather than trust the first draft.

## What I'd improve with more time

- Pin dependency versions in `requirements.txt` (the bug above is exactly the failure mode unpinned dependencies invite)
- Add the stretch goals we scoped out for later: configurable command rules in the dashboard UI (currently the `/status` and `/report` behavior is hardcoded in `main.py`), an AI tagging step on `/report` text via Gemini/Groq, and buttons/modal interaction types
- Hash the admin password instead of comparing it in plaintext from an environment variable (acceptable for a throwaway single-admin assignment account, not acceptable for anything real)
- Add structured logging and a visible retry/failure history in the dashboard beyond the single `status` column on each row
- Automate the "replace the old auto-generated README" and local git push-credential issue (local `git push` couldn't authenticate in this environment; all pushes in this session went through the GitHub API directly instead) — a minor workflow friction, not a product issue
