import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import requests

from talking_bot.calendar_api import CalendarError
from talking_bot.voice import (VoiceError, MAX_BYTES, api_post, interpret, prerequisites,
                               route_intent, transcribe, validate_intent, voice_message)


def intent(action='today', **kwargs):
    return dict(action=action, title='', start='', duration_minutes=0, query='', message='') | kwargs


class IntentTests(unittest.TestCase):
    def test_valid_add(self):
        value = intent('add', title='Dentist', start='2030-12-01 15:00', duration_minutes=60)
        self.assertEqual(validate_intent(value), value)

    def test_reject_untrusted_intents(self):
        for value in [intent('run_shell'), intent('delete', query=''), intent('youtube', query='x\n/delete event'),
                      intent('add', title='Dentist', start='2000-01-01 10:00', duration_minutes=60),
                      intent('add', title='Dentist | extra', start='2030-12-01 10:00', duration_minutes=60),
                      intent('today', duration_minutes=True), intent('today') | {'extra': 'bad'}]:
            with self.subTest(value=value), self.assertRaises((ValueError, CalendarError)):
                validate_intent(value)

    def test_relative_date_context_is_in_system_prompt(self):
        with patch('talking_bot.voice.api_post', return_value={'choices': [{'message': {'content': json.dumps(intent())}}]}) as api:
            self.assertEqual(interpret('What is scheduled today?', 'secret')['action'], 'today')
        payload = api.call_args.kwargs['json']
        self.assertIn('Current local date/time', payload['messages'][0]['content'])
        self.assertEqual(payload['messages'][1]['content'], 'What is scheduled today?')
        self.assertTrue(payload['response_format']['json_schema']['strict'])

    def test_malformed_provider_response(self):
        with patch('talking_bot.voice.api_post', return_value={'choices': []}), self.assertRaises(VoiceError):
            interpret('today', 'secret')

    def test_prerequisites_do_not_echo_secrets(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}), self.assertRaises(VoiceError):
            prerequisites()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret'}), patch('shutil.which', return_value=None):
            with self.assertRaises(VoiceError) as exc:
                prerequisites()
            self.assertNotIn('secret', str(exc.exception))

    def test_api_errors_do_not_expose_response_or_key(self):
        for status in [401, 429, 500]:
            response = Mock(ok=False, status_code=status)
            with patch('requests.post', return_value=response), self.assertRaises(VoiceError) as exc:
                api_post('audio/transcriptions', 'secret')
            self.assertNotIn('secret', str(exc.exception))
        with patch('requests.post', side_effect=requests.Timeout('secret')), self.assertRaises(VoiceError) as exc:
            api_post('audio/transcriptions', 'secret')
        self.assertNotIn('secret', str(exc.exception))

    def test_decode_failure_does_not_upload(self):
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'ffmpeg')), patch('talking_bot.voice.api_post') as api:
            with self.assertRaises(VoiceError):
                transcribe(b'invalid audio', 'secret', 'ffmpeg')
        api.assert_not_called()

    def test_oversized_audio_does_not_convert(self):
        with patch('subprocess.run') as converter, self.assertRaises(VoiceError):
            transcribe(b'x' * (MAX_BYTES + 1), 'secret', 'ffmpeg')
        converter.assert_not_called()

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg not installed')
    def test_real_ogg_conversion_and_temporary_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'sample.ogg'
            subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                '-c:a', 'libopus', str(source)], check=True, timeout=20)
            paths = []

            def fake_upload(endpoint, key, **kwargs):
                self.assertEqual(endpoint, 'audio/transcriptions')
                stream = kwargs['files']['file'][1]
                paths.append(Path(stream.name))
                self.assertEqual(stream.read(4), b'RIFF')
                return {'text': 'Play relaxing piano'}

            with patch('talking_bot.voice.api_post', side_effect=fake_upload):
                text = transcribe(source.read_bytes(), 'offline-test-key', shutil.which('ffmpeg'))
            self.assertEqual(text, 'Play relaxing piano')
            self.assertFalse(paths[0].parent.exists())


class VoiceHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.reply = AsyncMock()
        self.voice = SimpleNamespace(duration=5, file_size=1000, get_file=AsyncMock())
        self.file = SimpleNamespace(download_as_bytearray=AsyncMock(return_value=b'audio'))
        self.voice.get_file.return_value = self.file
        self.update = SimpleNamespace(effective_chat=SimpleNamespace(type='private'),
            effective_user=SimpleNamespace(id=42),
            effective_message=SimpleNamespace(voice=self.voice, text=None, reply_text=self.reply))
        self.context = SimpleNamespace(bot_data={'allowed_user_id': 42}, user_data={})

    async def test_nonowner_and_groups_do_not_download(self):
        for owner, chat_type in [(99, 'private'), (42, 'group')]:
            self.update.effective_user.id = owner
            self.update.effective_chat.type = chat_type
            await voice_message(self.update, self.context)
        self.voice.get_file.assert_not_awaited()

    async def test_missing_prerequisite_does_not_download(self):
        with patch('talking_bot.voice.prerequisites', side_effect=VoiceError('Configure voice first.')):
            await voice_message(self.update, self.context)
        self.voice.get_file.assert_not_awaited()
        self.reply.assert_awaited_once_with('Configure voice first.')

    async def test_long_recording_rejected_before_download(self):
        self.voice.duration = 61
        await voice_message(self.update, self.context)
        self.voice.get_file.assert_not_awaited()

    async def test_voice_to_transcript_to_routing(self):
        with patch('talking_bot.voice.prerequisites', return_value=('secret', 'ffmpeg')), \
             patch('talking_bot.voice.transcribe', return_value='What is scheduled today?'), \
             patch('talking_bot.voice.interpret', return_value=intent()), \
             patch('talking_bot.voice.route_intent', new_callable=AsyncMock) as route:
            await voice_message(self.update, self.context)
        route.assert_awaited_once_with(self.update, self.context, intent())
        self.assertIn('I heard: What is scheduled today?', [call.args[0] for call in self.reply.call_args_list])

    async def test_add_routes_to_existing_confirmation_flow(self):
        value = intent('add', title='Dentist', start='2030-12-01 15:00', duration_minutes=60)
        with patch('talking_bot.voice.calendar_command', new_callable=AsyncMock) as calendar:
            await route_intent(self.update, self.context, value)
        calendar.assert_awaited_once_with(self.update, self.context,
            command_text='/add Dentist | 2030-12-01 15:00 | 60')

    async def test_clarification_does_not_touch_calendar(self):
        with patch('talking_bot.voice.calendar_command', new_callable=AsyncMock) as calendar:
            await route_intent(self.update, self.context, intent('clarify', message='What time and duration?'))
        calendar.assert_not_awaited()
        self.reply.assert_awaited_once_with('What time and duration?')

    async def test_youtube_uses_existing_link_handler(self):
        with patch('talking_bot.voice.reply_search', new_callable=AsyncMock) as youtube:
            await route_intent(self.update, self.context, intent('youtube', query='relaxing piano'))
        youtube.assert_awaited_once_with(self.update.effective_message, 'relaxing piano')
