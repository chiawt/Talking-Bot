import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from talking_bot.bot import build_application, echo, help_command, on_error, start, unsupported, whoami
from talking_bot.config import Settings


class ConfigTests(unittest.TestCase):
    def test_missing_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                Settings.from_env()

    def test_setup_mode_and_hidden_token(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "secret"}, clear=True):
            settings = Settings.from_env()
            self.assertIsNone(settings.allowed_user_id)
            self.assertNotIn("secret", repr(settings))

    def test_owner_configuration(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "secret", "TELEGRAM_ALLOWED_USER_ID": "42"}, clear=True):
            self.assertEqual(Settings.from_env().allowed_user_id, 42)

    def test_invalid_ids(self):
        for value in ["abc", "0", "-42"]:
            with self.subTest(value=value), patch.dict(os.environ, {
                "TELEGRAM_BOT_TOKEN": "secret", "TELEGRAM_ALLOWED_USER_ID": value
            }, clear=True):
                with self.assertRaises(ValueError):
                    Settings.from_env()

    def test_application_builds(self):
        app = build_application(Settings("123456:offline-test-token", 42))
        self.assertEqual(app.bot_data["allowed_user_id"], 42)


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.reply = AsyncMock()
        self.update = SimpleNamespace(
            effective_chat=SimpleNamespace(type="private"),
            effective_user=SimpleNamespace(id=42),
            effective_message=SimpleNamespace(text="hello", reply_text=self.reply),
        )
        self.context = SimpleNamespace(bot_data={"allowed_user_id": 42})

    async def test_owner_commands(self):
        for handler in [start, help_command, whoami, echo, unsupported]:
            self.reply.reset_mock()
            await handler(self.update, self.context)
            self.reply.assert_awaited_once()

    async def test_echo(self):
        await echo(self.update, self.context)
        self.reply.assert_awaited_once_with("You said: hello")

    async def test_unauthorized_user(self):
        self.update.effective_user.id = 99
        for handler in [start, help_command, whoami, echo, unsupported]:
            self.reply.reset_mock()
            await handler(self.update, self.context)
            self.reply.assert_awaited_once_with("This is a private bot. Access denied.")

    async def test_groups_ignored(self):
        self.update.effective_chat.type = "group"
        for handler in [start, help_command, whoami, echo, unsupported]:
            await handler(self.update, self.context)
        self.reply.assert_not_awaited()

    async def test_setup_only_exposes_own_id(self):
        self.context.bot_data["allowed_user_id"] = None
        await whoami(self.update, self.context)
        self.assertIn("42", self.reply.call_args.args[0])
        for handler in [start, help_command, echo, unsupported]:
            self.reply.reset_mock()
            await handler(self.update, self.context)
            self.assertIn("Setup mode", self.reply.call_args.args[0])

    async def test_long_emoji_message(self):
        self.update.effective_message.text = "😀" * 4096
        await echo(self.update, self.context)
        self.assertLessEqual(len(self.reply.call_args.args[0].encode("utf-16-le")) // 2, 4096)

    async def test_safe_error_logs(self):
        self.context.error = RuntimeError("secret-token private message")
        with self.assertLogs("talking_bot.bot", level="ERROR") as logs:
            await on_error(self.update, self.context)
        self.assertNotIn("secret-token", str(logs.output))
