import logging
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update

from .bot import build_application
from .config import Settings


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    for name in ("httpx", "httpcore", "telegram"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(str(exc))
        return 1
    print("Starting Talking Bot. Press Ctrl+C to stop.")
    if settings.allowed_user_id is None:
        print("Setup mode: send /whoami privately, set your user ID, then restart.")
    try:
        build_application(settings).run_polling(allowed_updates=[Update.MESSAGE])
    except Exception as exc:
        print(f"Bot stopped ({type(exc).__name__}). Check your token, network, and other running instances.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
