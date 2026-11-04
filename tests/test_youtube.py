import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

from talking_bot.bot import build_application, echo
from talking_bot.config import Settings
from talking_bot.youtube import search_url, text_request, youtube_command


class SearchTests(unittest.TestCase):
    def test_query_is_encoded_and_host_is_fixed(self):
        query = '音乐 & cats? #mix https://example.com'
        title, url = search_url(query)
        self.assertEqual(title, query)
        parts = urlsplit(url)
        self.assertEqual(parts.scheme, 'https')
        self.assertEqual(parts.netloc, 'www.youtube.com')
        self.assertEqual(parse_qs(parts.query), {'search_query': [query]})
        self.assertEqual(parts.fragment, '')

    def test_empty_and_long_queries_rejected(self):
        for query in ['', '  ', 'a' * 201]:
            with self.subTest(query=query), self.assertRaises(ValueError):
                search_url(query)

    def test_normalize_whitespace(self):
        self.assertEqual(search_url('  relaxing\n piano  ')[0], 'relaxing piano')

    def test_narrow_text_routing(self):
        self.assertEqual(text_request('Play relaxing piano'), 'relaxing piano')
        self.assertEqual(text_request('youtube chicken rice'), 'chicken rice')
        for text in ['display schedule', '/today', 'hello', 'find my meeting']:
            self.assertIsNone(text_request(text))

    def test_command_registered(self):
        app = build_application(Settings('123456:offline-test-token', 42))
        matches = [h for h in app.handlers[0] if getattr(h, 'callback', None) == youtube_command]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].commands, frozenset({'play', 'youtube'}))


class YoutubeHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.reply = AsyncMock()
        self.update = SimpleNamespace(effective_chat=SimpleNamespace(type='private'),
            effective_user=SimpleNamespace(id=42),
            effective_message=SimpleNamespace(text='/play relaxing piano', reply_text=self.reply))
        self.context = SimpleNamespace(bot_data={'allowed_user_id': 42})

    async def test_command_returns_search_button_and_url(self):
        await youtube_command(self.update, self.context)
        self.assertIn('YouTube search: relaxing piano', self.reply.call_args.args[0])
        markup = self.reply.call_args.kwargs['reply_markup']
        self.assertEqual(markup.inline_keyboard[0][0].url, search_url('relaxing piano')[1])
        self.assertTrue(self.reply.call_args.kwargs['link_preview_options'].is_disabled)

    async def test_plain_play_request(self):
        self.update.effective_message.text = 'play relaxing piano'
        await echo(self.update, self.context)
        self.assertIn('YouTube search:', self.reply.call_args.args[0])

    async def test_command_without_query_shows_usage(self):
        self.update.effective_message.text = '/play'
        await youtube_command(self.update, self.context)
        self.assertIn('Try /play', self.reply.call_args.args[0])

    async def test_access_control(self):
        self.update.effective_user.id = 99
        await youtube_command(self.update, self.context)
        self.reply.assert_awaited_once_with('This is a private bot. Access denied.')

    async def test_group_is_ignored(self):
        self.update.effective_chat.type = 'group'
        await youtube_command(self.update, self.context)
        self.reply.assert_not_awaited()

    async def test_setup_mode_is_restricted(self):
        self.context.bot_data['allowed_user_id'] = None
        await youtube_command(self.update, self.context)
        self.assertIn('Setup mode:', self.reply.call_args.args[0])
