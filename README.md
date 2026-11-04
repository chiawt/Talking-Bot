# Talking Bot

Private Telegram assistant with `/start`, `/help`, `/whoami`, text echo, and
Google Calendar commands and YouTube search links. Voice messages are a future phase.

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

Voice messages, natural-language calendar requests, and
always-on deployment. Calendar setup below is optional for the basic echo bot.

## Google Calendar (Phase 2)

This version uses explicit commands and dates, not natural language yet. Calendar
changes always require button confirmation, expire after five minutes, and are
forgotten when the bot restarts. Default calendar: your signed-in account's
`primary`; timezone: `Asia/Singapore`. You may set `GOOGLE_CALENDAR_ID` and
`BOT_TIMEZONE` in `.env` to change these defaults.

### Connect your Google account on Windows

1. Stop the bot with Ctrl+C. Update the checkout and dependencies:

   ```powershell
   Set-Location C:\talking_bot\Talking-Bot
   git pull origin main
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Open https://console.cloud.google.com/ and create/select a project.
3. Under **APIs & Services → Library**, enable **Google Calendar API**.
4. Configure the **Google Auth Platform / OAuth consent screen**: set an app name
   and contact email, choose External if using a personal Gmail account, keep it
   in Testing, and add your own Google email under Audience / Test users. Menu
   names may vary. Request the scope
   `https://www.googleapis.com/auth/calendar.events` under Data Access if prompted.
5. Create an **OAuth client ID** with application type **Desktop app**. Download
   its JSON file, rename it `credentials.json`, and place it in the project root
   beside `requirements.txt`. An API key or service account is not a substitute.
6. Run the local sign-in helper:

   ```powershell
   .\.venv\Scripts\python.exe -m talking_bot.google_auth
   ```

7. Sign in with your test-user Google account in the browser. Review the calendar
   permissions before granting access. Proceed past an unverified-app screen only
   for the OAuth project you created. A temporary localhost callback completes
   sign-in; no public webhook is needed. Complete this step on your computer,
   not a remote cloud machine.
8. The helper saves `token.json` locally. Both JSON credential files are ignored
   by Git. Treat them as private, and never send them to Telegram, GitHub, or chat.
9. Restart the bot:

   ```powershell
   .\.venv\Scripts\python.exe -m talking_bot
   ```

External apps in Testing can have refresh tokens expire after seven days. If
Google access expires or is revoked, rerun the sign-in helper. You can revoke
access through your Google account's third-party connections; stop the bot and
remove `token.json` locally to disconnect it. Anyone with access to that file may
be able to access your calendar. For shared computers, protect the project folder
with your operating system's account/file permissions.

### Try it in Telegram

- `/today`: events today, including all-day events.
- `/tomorrow`: tomorrow's events.
- `/week`: seven calendar days beginning today.
- `/add Dentist | 2030-12-01 15:00 | 60`: preview a future one-hour event in your
  configured timezone. Change the date to the one you actually want. Press
  **Confirm** to create it or **Cancel** to discard it. Overlaps show a warning.
- `/delete Dentist`: search the next 30 days, select the exact matching event,
  then confirm deletion. Only individual events without guests are supported;
  manage recurring events and invitations in Google Calendar itself.

A schedule shows at most 20 entries; deletion search shows at most five candidates.
Check Google Calendar for larger schedules. Bot-created events have no invitees.
A network failure during a write can leave its outcome uncertain: check Google
Calendar before retrying. Restarting clears all outstanding confirmations.

### Live acceptance check

First compare `/today` with Google Calendar. Create a clearly named test event,
verify its title and Singapore date/time in Google Calendar, and delete it through
`/delete`. Try **Cancel** and verify no event changes. These live checks require
your credentials and have not been performed by the automated tests. Tests use
mocked Google responses; they validate logic without touching a real calendar.

Local execution requires HTTPS access to `accounts.google.com`,
`oauth2.googleapis.com`, and `www.googleapis.com`, as well as Telegram. Cloud
execution needs the same allowed destinations and supported credential/proxy
configuration. A local OAuth token is not automatically available in the cloud.

## YouTube search links (Phase 3)

No additional API key, Google scope, or dependency is needed. In your private
Telegram chat, try:

```text
/play relaxing piano
/youtube chicken rice recipe
play songs by Adele
```

The bot returns a clickable YouTube search-results link and an **Open YouTube**
button. Tap it to choose the song or video. This version does not select a
specific video, download media, or automatically start/control playback. Only
explicit `play …` or `youtube …` text requests are routed to media; other text
still echoes. Searches are limited to 200 characters. Links open YouTube on your
device; the bot itself makes no YouTube requests. Your search is sent to YouTube
when you open the link.

To update, stop the bot with Ctrl+C, run `git pull origin main` in the project
folder, and restart with `.\.venv\Scripts\python.exe -m talking_bot`. Keep your
existing `.env`, `credentials.json`, and `token.json` files. To verify this feature,
send `/play relaxing piano`, tap the button, and check that YouTube shows the
requested search. This live Telegram/device check is separate from automated tests.
