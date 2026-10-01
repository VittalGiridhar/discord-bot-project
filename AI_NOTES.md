# AI Notes

## Tools and models used

Built with Claude Code (Claude Sonnet 5), used as a pair-programmer for the entire project — planning, writing every file, running local tests, deploying, and debugging. No other AI coding tool was used. No `CLAUDE.md`, `AGENTS.md`, or `.cursorrules` file was used to drive the session — Claude Code worked directly from the assignment PDF and the conversation, with a plan written up front (in plan mode) and executed step by step with verification after each step.

Work split: Claude Code wrote the implementation (every file, local tests, deployment commands), but the architecture was a back-and-forth — Claude proposed options with tradeoffs at each decision point and I picked between them before any code was written, using plan mode so the full approach was reviewable before execution. I also did everything requiring my own accounts or browser: creating the Discord application, inviting the bot to a test server, creating the Neon project, setting up the Render web service, and supplying API keys/connection strings/webhook URLs. Critically, I did the live verification at every step — running real slash commands in Discord, reading actual replies, and catching things Claude couldn't see from its side (a webhook URL I'd mistyped, confusion over what the dashboard's "Save" button was actually doing). The debugging in the next section was driven by me asking "why didn't that work" until the real mechanism was clear, not by accepting the first explanation.

## Key decisions

1. **Neon Postgres over SQLite — my call, prompted by a tradeoff Claude raised.** Most free hosting tiers (including Render's) have an ephemeral filesystem — a SQLite file would be wiped on every redeploy or restart, losing the whole command log. I chose Neon's free Postgres tier specifically because the assignment requires the dashboard to show a *persistent* log, and I wasn't willing to risk that getting wiped on a redeploy.

2. **A second Discord channel webhook instead of Slack — I overrode the original plan.** Claude's first plan defaulted to "Slack webhook or second Discord channel," listing Slack first. I rejected that during plan review and required a Discord-only mirror channel, since it meant no separate Slack app/workspace to set up for a mirror that's functionally identical for this assignment's purposes.

3. **Manual config form instead of a full Discord OAuth2 "add server" flow — a tradeoff I accepted after Claude explained the cost.** A full OAuth2 flow (admin logs in with Discord, picks from their actual servers) is closer to what a "real" product would do, but it's meaningfully more code — token exchange, guild listing, permission checks — for a stretch-level UX improvement over just pasting a Guild ID/Channel ID/webhook URL into a form. I chose the simpler path to keep the core requirements solid rather than spend the time budget on OAuth plumbing.

## The hardest bug

While building the admin dashboard, every page render failed with `TypeError: unhashable type: 'dict'` deep inside Jinja2's template cache lookup — a genuinely confusing error, since nothing in the code looked like it was hashing a dict. Claude's first instinct (and first written code) used the FastAPI/Starlette `TemplateResponse` call pattern from what is still the most common pattern online: `templates.TemplateResponse("login.html", {"request": request, "error": None})`. That pattern is from an older Starlette API. The installed Starlette version (1.7.0, pulled in fresh by `pip install` since no version was pinned) had moved to a newer signature: `TemplateResponse(request, name, context)`, with `request` as the first positional argument and no longer expected inside the context dict. Passing the dict where Starlette expected the request object meant it ended up being used as a cache key internally — hence "unhashable type: dict".

We noticed it because the local test suite we ran before deploying (hitting `/login` and `/dashboard` with curl) returned 500s, and the traceback pointed to `jinja2/utils.py`'s cache lookup rather than anywhere in our own code, which was the first clue the API itself had changed under us rather than our logic being wrong. The fix was switching every `TemplateResponse` call to the new three-positional-argument form. This is a good example of why pinning dependency versions (which this project currently doesn't do, to keep `requirements.txt` simple) is a tradeoff — unpinned installs can get a newer library than any tutorial or cached training knowledge assumed, and the fix is only obvious once you actually run the code rather than trust the first draft.

## What I'd improve with more time

- Pin dependency versions in `requirements.txt` (the bug above is exactly the failure mode unpinned dependencies invite)
- Add the stretch goals we scoped out for later: configurable command rules in the dashboard UI (currently the `/status` and `/report` behavior is hardcoded in `main.py`), an AI tagging step on `/report` text via Gemini/Groq, and buttons/modal interaction types
- Hash the admin password instead of comparing it in plaintext from an environment variable (acceptable for a throwaway single-admin assignment account, not acceptable for anything real)
- Add structured logging and a visible retry/failure history in the dashboard beyond the single `status` column on each row
- Automate the "replace the old auto-generated README" and local git push-credential issue (local `git push` couldn't authenticate in this environment; all pushes in this session went through the GitHub API directly instead) — a minor workflow friction, not a product issue
