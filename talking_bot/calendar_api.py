"""Google Calendar API adapter. OAuth runs on the user's computer, not in Telegram."""
import os
from pathlib import Path
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials

ROOT = Path(__file__).resolve().parents[1]
SCOPES = ['https://www.googleapis.com/auth/calendar.events']


class CalendarError(Exception):
    pass


def token_path():
    return ROOT / 'token.json'


def save_credentials(credentials):
    path = token_path()
    # Open with restrictive permissions on systems supporting POSIX modes.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(credentials.to_json())


class CalendarClient:
    def __init__(self):
        path = token_path()
        if not path.exists():
            raise CalendarError('Calendar is not connected. Run python -m talking_bot.google_auth on your computer first.')
        try:
            self.credentials = Credentials.from_authorized_user_file(str(path), SCOPES)
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                save_credentials(self.credentials)
            if not self.credentials.valid:
                raise ValueError('Invalid credentials')
        except Exception:
            raise CalendarError('Google authorization needs renewal. Run python -m talking_bot.google_auth again.') from None
        self.session = AuthorizedSession(self.credentials)
        calendar = os.environ.get('GOOGLE_CALENDAR_ID', 'primary').strip() or 'primary'
        self.base = 'https://www.googleapis.com/calendar/v3/calendars/' + quote(calendar, safe='') + '/events'

    def close(self):
        self.session.close()

    def request(self, method, suffix='', **kwargs):
        try:
            response = self.session.request(method, self.base + suffix, timeout=30, **kwargs)
        except Exception:
            raise CalendarError('Google Calendar could not be reached. Check your connection and retry.') from None
        if response.status_code == 412:
            raise CalendarError('This event changed since your preview. Search again before deleting.')
        if not response.ok:
            raise CalendarError(f'Google Calendar returned HTTP {response.status_code}. Check authorization and calendar access.')
        return response.json() if response.content else {}

    def events(self, start, end, query=None):
        params = {'timeMin': start.isoformat(), 'timeMax': end.isoformat(),
                  'singleEvents': 'true', 'orderBy': 'startTime', 'maxResults': 100}
        if query:
            params['q'] = query
        result = self.request('GET', params=params)
        return result.get('items', []), bool(result.get('nextPageToken'))

    def create(self, event):
        return self.request('POST', json=event, params={'sendUpdates': 'none'})

    def delete(self, event):
        # Never delete an entire recurring series through this first version.
        current = self.request('GET', '/' + quote(event['id'], safe=''))
        if current.get('recurrence') or current.get('recurringEventId'):
            raise CalendarError('Recurring events must be managed in Google Calendar for now.')
        if current.get('attendees'):
            raise CalendarError('Events with guests must be managed in Google Calendar for now.')
        if not event.get('etag') or current.get('etag') != event['etag']:
            raise CalendarError('This event changed since your preview. Search again before deleting.')
        self.request('DELETE', '/' + quote(event['id'], safe=''), headers={'If-Match': event['etag']})
