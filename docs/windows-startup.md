# Run the bot on your Windows computer

This setup keeps the existing local project and credentials. No server, paid
hosting account, or inbound port is needed. Your computer must remain on, awake,
connected to the Internet, and signed in. Sleep, hibernation, shutdown, or sign-out
stops availability. Locking the screen keeps the signed-in session running.

## Register automatic startup

First verify that the bot works when launched manually. Stop that copy with Ctrl+C
before starting the scheduled one. Run in normal PowerShell under your own Windows
account, not a different administrator account:

```powershell
Set-Location C:\talking_bot\Talking-Bot
git pull origin main
.\scripts\register-windows-task.ps1
Start-ScheduledTask -TaskName TalkingBot
```

The script creates a Task Scheduler task named TalkingBot that runs Python from
this checkout when you sign in. It uses your existing `.env` and Google token;
it does not copy secrets or store them in task arguments. It retries a failed
process up to three times, one minute apart, and does not start overlapping task
instances. This restriction cannot detect copies you start manually, so always
stop the scheduled task before launching a manual bot. The task may display a
Python console window. Do not close it if you want that instance to keep running.

Windows policy or organization restrictions may block script execution/task
registration. Do not disable organizational controls. If the script is blocked,
use Task Scheduler's Create Task interface with the settings below, or ask your
Windows administrator. The Linux development machine cannot verify Windows task
registration; check it on your computer before relying on automatic startup.

Manual Task Scheduler configuration (run only while you are logged on):

- Name: TalkingBot; run as your own account without highest privileges.
- Trigger: at log on, for your account.
- Program: `C:\talking_bot\Talking-Bot\.venv\Scripts\python.exe`.
- Arguments: `-u -m talking_bot`.
- Start in: `C:\talking_bot\Talking-Bot`.
- Settings: restart on failure every one minute, up to three times; do not start
  a new instance if already running; remove the default run-duration limit.
- If wanted, allow running on battery. This consumes battery; it does not change
  Windows sleep settings.

## Check readiness

```powershell
Get-ScheduledTask -TaskName TalkingBot | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName TalkingBot
```

Task state alone does not prove Telegram works. Send `/help`, `/today` (if Google
is connected), and `/play relaxing piano` in Telegram. If voice is configured,
test a voice note separately. Sign out/in at a convenient time and repeat these
checks to verify the logon trigger. A running task has not necessarily completed
successfully; do not interpret its LastTaskResult as a bot health check.

In Windows Settings, review **System → Power & battery → Screen and sleep**
(names vary). If you want continuous availability while plugged in, prevent the
computer from sleeping while plugged in; turning the display off is fine. Laptop
lid settings may still put it to sleep. Keep security updates enabled.

## Stop, update, or remove

```powershell
Stop-ScheduledTask -TaskName TalkingBot
Set-Location C:\talking_bot\Talking-Bot
git pull origin main
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Start-ScheduledTask -TaskName TalkingBot
```

Stopping a task can terminate the process abruptly. Check Google Calendar before
retrying a change that was in flight. Pending confirmations disappear after a
restart. Stopping it does not disable its next logon trigger. To disable automatic
startup use `Disable-ScheduledTask -TaskName TalkingBot`; to remove it use
`Unregister-ScheduledTask -TaskName TalkingBot` and confirm the removal prompt.
The registration script intentionally refuses to overwrite an existing task.

For troubleshooting, stop the task and run Python manually so you can see its
startup messages. Never share `.env`, token.json, credentials.json, or screenshots
containing keys. Keep only one bot copy running. Google OAuth Testing tokens may
need renewal after seven days; rerun the local Google sign-in helper when required.
This setup adds process restart, not health alerts or a guarantee of uptime.
