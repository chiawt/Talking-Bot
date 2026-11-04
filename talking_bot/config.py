import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    token: str = field(repr=False)
    allowed_user_id: int | None = None

    @classmethod
    def from_env(cls):
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("Set TELEGRAM_BOT_TOKEN in your local .env file.")
        raw_id = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()
        if not raw_id:
            return cls(token)
        try:
            user_id = int(raw_id)
        except ValueError:
            raise ValueError("TELEGRAM_ALLOWED_USER_ID must be a positive numeric ID.") from None
        if user_id <= 0:
            raise ValueError("TELEGRAM_ALLOWED_USER_ID must be a positive numeric ID.")
        return cls(token, user_id)
