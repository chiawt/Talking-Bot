# Talking Bot

Private Telegram assistant. Phase 1 supports `/start`, `/help`, `/whoami`, and
text echo. Google Calendar, YouTube links, and voice messages are future phases.

## Windows PowerShell

Requires Python 3.10+ and your BotFather token. From the project checkout:

```powershell
Set-Location C:\talking_bot\Talking-Bot
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Skip copying if `.env` already exists. Set `TELEGRAM_BOT_TOKEN` privately in that
file. Leave `TELEGRAM_ALLOWED_USER_ID` blank at first. Never share your token or
commit it; `.env` is ignored by Git.

```powershell
.\.venv\Scripts\python.exe -m talking_bot
```

Send `/whoami` to your bot in a private Telegram chat. Put the returned numeric
ID in `TELEGRAM_ALLOWED_USER_ID` in `.env`. Stop with Ctrl+C and restart using
the command above. Send `/start`, `/help`, and `hello`; expect `You said: hello`.

Without an owner ID, only `/whoami` is available and reveals only the caller's
own ID. Once configured, other users are denied. Group messages are ignored.
No message history is stored. Telegram still processes messages under its policies.

## Linux / cloud

Use the existing checkout; cloud tasks are isolated and need no extra worktree.

```bash
cd /workspace/Talking-Bot
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# Only if .env does not exist:
cp .env.example .env
# Edit .env privately, then run:
.venv/bin/python -m talking_bot
```

Existing process environment variables take precedence over `.env`. Only one
polling instance may use the same token at a time. No webhook or public server
is required. Internet access to `api.telegram.org` is required. Proxy-injected
credentials require HTTP client proxy configuration; local execution with a real
token is the simplest first live check.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Linux: `.venv/bin/python -m unittest discover -v`. Tests require no real token or
network. They cover access control, configuration, replies, and safe logging;
the private Telegram conversation above is still required for live verification.

## Troubleshooting

- Missing token: edit `.env` and restart.
- Invalid token: check BotFather; revoke and replace any exposed token.
- Conflict: stop the other polling instance.
- No reply: verify owner ID, private chat, and network access to Telegram.

## Next phases

Google Calendar authorization and confirmed event changes; YouTube search links;
voice messages; always-on deployment. No AI or calendar credentials are needed yet.
