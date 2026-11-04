"""Explicit calendar commands with short-lived, single-use confirmation buttons."""
import asyncio
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .calendar_api import CalendarClient, CalendarError


def zone():
    try:
        return ZoneInfo(os.environ.get('BOT_TIMEZONE', 'Asia/Singapore'))
    except ZoneInfoNotFoundError:
        raise CalendarError('Invalid BOT_TIMEZONE. Use a timezone such as Asia/Singapore.') from None


def parse_event(text, now=None):
    try:
        title, raw_date, raw_minutes = [part.strip() for part in text.split('|')]
        minutes = int(raw_minutes)
        naive = datetime.strptime(raw_date, '%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        raise CalendarError('Use /add Title | YYYY-MM-DD HH:MM | duration in minutes') from None
    if not title or len(title) > 200 or not 1 <= minutes <= 1440:
        raise CalendarError('Use a title of 1–200 characters and a duration of 1–1440 minutes.')
    tz = zone()
    start = naive.replace(tzinfo=tz)
    if start.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != naive:
        raise CalendarError('That local time does not exist due to a clock change. Choose another time.')
    if start.utcoffset() != naive.replace(tzinfo=tz, fold=1).utcoffset():
        raise CalendarError('That local time is ambiguous due to a clock change. Choose another time.')
    if start <= (now or datetime.now(tz)):
        raise CalendarError('Choose a future date and time.')
    end = (start.astimezone(timezone.utc) + timedelta(minutes=minutes)).astimezone(tz)
    return {'id': uuid.uuid4().hex, 'summary': title,
            'start': {'dateTime': start.isoformat(), 'timeZone': str(tz)},
            'end': {'dateTime': end.isoformat(), 'timeZone': str(tz)}}


def describe(event):
    def stamp(value):
        if 'dateTime' in value:
            return datetime.fromisoformat(value['dateTime'].replace('Z', '+00:00')).astimezone(zone()).strftime('%Y-%m-%d %H:%M')
        return value.get('date', '?') + ' (all day)'
    return f"{event.get('summary', '(Untitled)')[:200]}\n{stamp(event['start'])} → {stamp(event['end'])}"


def remember(context, kind, event):
    pending = context.user_data.setdefault('calendar_pending', {})
    now = time.monotonic()
    for key in list(pending):
        if pending[key]['expires'] < now:
            del pending[key]
    # Bound memory even if someone sends many requests.
    while len(pending) >= 20:
        del pending[next(iter(pending))]
    key = secrets.token_hex(8)
    pending[key] = {'kind': kind, 'event': event, 'expires': now + 300}
    return key


def buttons(key):
    return InlineKeyboardMarkup([[InlineKeyboardButton('Confirm', callback_data=f'cal:confirm:{key}'),
                                  InlineKeyboardButton('Cancel', callback_data=f'cal:cancel:{key}')]])


def call_api(operation, *args):
    client = CalendarClient()
    try:
        return getattr(client, operation)(*args)
    finally:
        client.close()


async def calendar_command(update, context, *, command_text=None):
    from .bot import authorized
    if not await authorized(update, context):
        return
    message = update.effective_message
    command_text = message.text if command_text is None else command_text
    command = command_text.split()[0].split('@')[0]
    text = command_text.partition(' ')[2].strip()
    try:
        tz = zone()
        now = datetime.now(tz)
        if command == '/add':
            event = parse_event(text)
            events, more = await asyncio.to_thread(call_api, 'events',
                datetime.fromisoformat(event['start']['dateTime']), datetime.fromisoformat(event['end']['dateTime']))
            key = remember(context, 'create', event)
            warning = '\nWarning: this time overlaps existing events.' if events else ''
            await message.reply_text('Create event?\n' + describe(event) + f'\nTimezone: {tz}' + warning,
                                     reply_markup=buttons(key))
            return
        if command == '/delete':
            if not text:
                raise CalendarError('Use /delete search words. Searches the next 30 days; select an event, then confirm.')
            events, more = await asyncio.to_thread(call_api, 'events', now, now + timedelta(days=30), text)
            events = [e for e in events if not e.get('recurringEventId') and not e.get('recurrence') and not e.get('attendees')]
            if not events:
                await message.reply_text('No matching individual events without guests in the next 30 days.')
                return
            await message.reply_text('Choose an event to preview deletion. Recurring events and events with guests are excluded.')
            for event in events[:5]:
                key = remember(context, 'select_delete', event)
                await message.reply_text(describe(event), reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Delete this event…', callback_data=f'cal:select:{key}')]]))
            if len(events) > 5 or more:
                await message.reply_text('Only the first five matches are shown. Narrow your search if needed.')
            return
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if command == '/tomorrow':
            start += timedelta(days=1)
        end = start + timedelta(days=7 if command == '/week' else 1)
        events, more = await asyncio.to_thread(call_api, 'events', start, end)
        await message.reply_text(f'Schedule ({tz})\n' + ('No events.' if not events else ''))
        for event in events[:20]:
            await message.reply_text(describe(event))
        if len(events) > 20 or more:
            await message.reply_text('Showing the first 20 events. See Google Calendar for the full schedule.')
    except CalendarError as exc:
        await message.reply_text(str(exc))


async def calendar_callback(update, context):
    from .bot import authorized
    query = update.callback_query
    await query.answer()
    if not await authorized(update, context):
        return
    _, action, key = query.data.split(':')
    pending = context.user_data.setdefault('calendar_pending', {})
    item = pending.get(key)
    if not item or item['expires'] < time.monotonic():
        pending.pop(key, None)
        await query.edit_message_text('This request expired or was already handled. Run the command again.')
        return
    if action == 'cancel':
        pending.pop(key)
        await query.edit_message_text('Cancelled. No calendar change was made.')
        return
    if action == 'select' and item['kind'] == 'select_delete':
        pending.pop(key)
        new_key = remember(context, 'delete', item['event'])
        await query.edit_message_text('Delete this event?\n' + describe(item['event']), reply_markup=buttons(new_key))
        return
    if action != 'confirm' or item['kind'] not in ('create', 'delete'):
        return
    # Consume before awaiting network IO: double clicks cannot repeat a write.
    pending.pop(key)
    await query.edit_message_text('Applying your confirmed change…')
    try:
        await asyncio.to_thread(call_api, item['kind'], item['event'])
        await query.edit_message_text('Event created.' if item['kind'] == 'create' else 'Event deleted.')
    except CalendarError as exc:
        await query.edit_message_text(str(exc) + '\nCheck Google Calendar before retrying: a network failure may leave the outcome uncertain.')
