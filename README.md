# Talking Bot

Private Telegram assistant with `/start`, `/help`, `/whoami`, text echo, and
Google Calendar commands, YouTube search links, and optional voice-message input.

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

Spoken responses, natural-language typed requests, and always-on deployment.
Calendar setup below is optional for the basic echo bot.

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

## Voice-message requests (Phase 4)

Record a voice note in Telegram (the microphone button, not a video note or file
attachment). The bot transcribes it, displays **I heard: …**, and interprets one
calendar or YouTube request. Responses are text and links; spoken replies and live
calls are not implemented. Voice does not turn the bot into a general AI chatbot.

Voice is optional and requires an **OpenAI API key** with API billing/available
quota. A ChatGPT subscription does not include API credits. Each accepted recording
uses one Whisper transcription request and one `gpt-4o-mini` interpretation request.
The bot sends your audio and transcript to OpenAI; it does not send calendar contents
to OpenAI. Review the provider's data policies and pricing before enabling voice.
Existing typed commands remain available without this key.

### Windows setup

1. Stop the bot with Ctrl+C and update:

   ```powershell
   Set-Location C:\talking_bot\Talking-Bot
   git pull origin main
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Install FFmpeg for audio conversion if not already installed:

   ```powershell
   winget install --id Gyan.FFmpeg --exact
   ```

   Close and reopen PowerShell after installation. Check `ffmpeg -version`. If
   winget is unavailable, use an FFmpeg build linked from https://ffmpeg.org/download.html
   and add its `bin` folder to PATH. Alternatively put the full executable path in
   `.env` as `FFMPEG_PATH=C:\path\to\ffmpeg.exe`.

3. Create an API key at https://platform.openai.com/api-keys and ensure API billing
   is available. Open `.env` locally and append this line with your real key:

   ```text
   OPENAI_API_KEY=your_key_here
   ```

   Keep the existing Telegram and calendar settings. Never send the key in Telegram,
   chat, screenshots, or GitHub. Set a project budget/alert in your OpenAI account.

4. Reopen the project folder and start:

   ```powershell
   Set-Location C:\talking_bot\Talking-Bot
   .\.venv\Scripts\python.exe -m talking_bot
   ```

### Voice examples and limitations

- “What is on my calendar today?”
- “What is on my calendar tomorrow?”
- “Add a dentist appointment on December first, 2030, at three PM for one hour.”
- “Delete my dentist appointment.” (Searches the next 30 days; choose an event,
  then confirm. Recurring events and events with guests remain excluded.)
- “Play relaxing piano music.”

Use a future date you actually want, and include a title, date, unambiguous time,
and duration for creation. Relative dates are interpreted using BOT_TIMEZONE and
current local time. Missing or ambiguous details should produce a clarification;
resend the complete request with those details (no follow-up conversation memory).
Requests to move events, invite guests, manage recurrence, or perform multiple actions
are unsupported. A deletion containing date constraints should ask you to select the
exact event through `/delete`, rather than applying those constraints automatically.

Model interpretation can be wrong. Always inspect the transcript AND the calendar
preview's title, full date/time, and timezone before pressing Confirm. Cancel if any
part is wrong. The model does not call calendar APIs directly: the application validates
structured fields and routes through the same confirmation flow as typed commands.

Recordings must be at most 60 seconds and 10 MB. Temporary audio is deleted after
processing; no local transcript history is saved, but the transcript remains in your
Telegram chat and the providers apply their own retention policies. Delete Telegram
messages separately if desired. Do not run multiple instances with the same bot token.

First test “Play relaxing piano” without touching your calendar. Then try a schedule
request, followed by a clearly named test event and **Cancel**. Only confirm a real
change after verifying every detail. Cloud tests do not establish live OpenAI or
Telegram behavior; end-to-end verification needs your local credentials.

If voice fails, check `ffmpeg -version`, the local API key, network access to
`api.openai.com`, model availability, and OpenAI API billing/rate limits. Do not
replace a key by posting it to the bot. Normal text commands still work.
