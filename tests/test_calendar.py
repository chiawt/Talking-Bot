import os
import time
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo

from talking_bot.calendar_api import CalendarClient, CalendarError
from talking_bot.calendar_handlers import calendar_callback, calendar_command, parse_event, remember


def event():
    return {'id': 'abc123', 'etag': 'revision1', 'summary': 'Dentist',
            'start': {'dateTime': '2030-12-01T15:00:00+08:00'},
            'end': {'dateTime': '2030-12-01T16:00:00+08:00'}}


class ParsingTests(unittest.TestCase):
    def test_explicit_time_and_duration(self):
        with patch.dict(os.environ, {'BOT_TIMEZONE': 'Asia/Singapore'}):
            result = parse_event('Dentist | 2030-12-01 15:00 | 60')
        self.assertEqual(result['start']['dateTime'], '2030-12-01T15:00:00+08:00')
        self.assertEqual(result['end']['dateTime'], '2030-12-01T16:00:00+08:00')
        self.assertEqual(len(result['id']), 32)

    def test_reject_invalid_and_past(self):
        for text in ['Dentist tomorrow', 'Dentist | 2030-02-30 15:00 | 60',
                     'Dentist | 2030-12-01 15:00 | 0', 'Dentist | 2000-12-01 15:00 | 60']:
            with self.subTest(text=text), self.assertRaises(CalendarError):
                parse_event(text)

    def test_invalid_zone(self):
        with patch.dict(os.environ, {'BOT_TIMEZONE': 'invalid'}), self.assertRaises(CalendarError):
            parse_event('Dentist | 2030-12-01 15:00 | 60')

    def test_dst_nonexistent_and_ambiguous(self):
        with patch.dict(os.environ, {'BOT_TIMEZONE': 'America/New_York'}):
            for date in ['2030-03-10 02:30', '2030-11-03 01:30']:
                with self.subTest(date=date), self.assertRaises(CalendarError):
                    parse_event(f'Dentist | {date} | 60')


class ApiTests(unittest.TestCase):
    def client(self):
        client = CalendarClient.__new__(CalendarClient)
        client.request = Mock()
        return client

    def test_delete_uses_precondition(self):
        client = self.client()
        client.request.side_effect = [event(), {}]
        client.delete(event())
        self.assertEqual(client.request.call_args.args, ('DELETE', '/abc123'))
        self.assertEqual(client.request.call_args.kwargs['headers'], {'If-Match': 'revision1'})

    def test_refuse_changed_guest_and_recurring_events(self):
        for extra in [{'etag': 'changed'}, {'attendees': [{'email': 'guest@example.com'}]},
                      {'recurringEventId': 'series'}, {'recurrence': ['RRULE:FREQ=DAILY']}]:
            client = self.client()
            client.request.return_value = event() | extra
            with self.subTest(extra=extra), self.assertRaises(CalendarError):
                client.delete(event())
            self.assertEqual(client.request.call_count, 1)

    def test_list_queries_are_bounded(self):
        client = self.client()
        client.request.return_value = {'items': [event()], 'nextPageToken': 'next'}
        now = datetime.now(ZoneInfo('Asia/Singapore'))
        items, more = client.events(now, now, 'Dentist')
        self.assertTrue(more)
        self.assertEqual(items, [event()])
        self.assertEqual(client.request.call_args.kwargs['params']['q'], 'Dentist')


class CalendarFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.message = SimpleNamespace(text='/today', reply_text=AsyncMock())
        self.query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock(), data='')
        self.update = SimpleNamespace(effective_chat=SimpleNamespace(type='private'),
            effective_user=SimpleNamespace(id=42), effective_message=self.message, callback_query=self.query)
        self.context = SimpleNamespace(bot_data={'allowed_user_id': 42}, user_data={})

    def confirm(self, kind='create'):
        key = remember(self.context, kind, event())
        self.query.data = 'cal:confirm:' + key
        return key

    async def test_create_preview_does_not_write(self):
        self.message.text = '/add Dentist | 2030-12-01 15:00 | 60'
        with patch('talking_bot.calendar_handlers.call_api', return_value=([event()], False)) as api:
            await calendar_command(self.update, self.context)
        self.assertEqual(api.call_args.args[0], 'events')
        self.assertIn('overlaps', self.message.reply_text.call_args.args[0])
        self.assertIsNotNone(self.message.reply_text.call_args.kwargs['reply_markup'])

    async def test_confirm_once_only(self):
        self.confirm()
        with patch('talking_bot.calendar_handlers.call_api', return_value={}) as api:
            await calendar_callback(self.update, self.context)
            await calendar_callback(self.update, self.context)
        api.assert_called_once_with('create', event())
        self.assertIn('already handled', self.query.edit_message_text.call_args.args[0])

    async def test_cancel_does_not_write(self):
        key = self.confirm()
        self.query.data = 'cal:cancel:' + key
        with patch('talking_bot.calendar_handlers.call_api') as api:
            await calendar_callback(self.update, self.context)
        api.assert_not_called()
        self.assertNotIn(key, self.context.user_data['calendar_pending'])

    async def test_expired_does_not_write(self):
        key = self.confirm()
        self.context.user_data['calendar_pending'][key]['expires'] = time.monotonic() - 1
        with patch('talking_bot.calendar_handlers.call_api') as api:
            await calendar_callback(self.update, self.context)
        api.assert_not_called()

    async def test_nonowner_cannot_confirm(self):
        self.confirm()
        self.update.effective_user.id = 99
        with patch('talking_bot.calendar_handlers.call_api') as api:
            await calendar_callback(self.update, self.context)
        api.assert_not_called()
        self.message.reply_text.assert_awaited_once_with('This is a private bot. Access denied.')

    async def test_delete_selection_requires_another_confirmation(self):
        key = remember(self.context, 'select_delete', event())
        self.query.data = 'cal:select:' + key
        with patch('talking_bot.calendar_handlers.call_api') as api:
            await calendar_callback(self.update, self.context)
        api.assert_not_called()
        self.assertIn('Delete this event?', self.query.edit_message_text.call_args.args[0])
        key2, = self.context.user_data['calendar_pending']
        self.query.data = 'cal:confirm:' + key2
        with patch('talking_bot.calendar_handlers.call_api', return_value={}) as api:
            await calendar_callback(self.update, self.context)
        api.assert_called_once_with('delete', event())

    async def test_calendar_error_is_actionable(self):
        with patch('talking_bot.calendar_handlers.call_api', side_effect=CalendarError('Connect Google first.')):
            await calendar_command(self.update, self.context)
        self.message.reply_text.assert_awaited_once_with('Connect Google first.')

    async def test_uncertain_write_error_is_reported(self):
        self.confirm()
        with patch('talking_bot.calendar_handlers.call_api', side_effect=CalendarError('Network error.')):
            await calendar_callback(self.update, self.context)
        self.assertIn('outcome uncertain', self.query.edit_message_text.call_args.args[0])
