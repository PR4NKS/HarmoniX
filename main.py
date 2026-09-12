"""HarmoniX Music Bot entrypoint and lifecycle orchestrator."""

import asyncio
import os
import signal
import sys
from pathlib import Path
from dotenv import load_dotenv

# Preload environment variables from .env file
load_dotenv()

from config.settings import get_settings
from bot.client import HarmoniXBot
from utils.logging import setup_logging, get_logger

logger = get_logger("HarmoniX.Main")


async def main() -> None:
    """Initialize configuration, setup logging, and start HarmoniX bot."""
    settings = get_settings()

    # Configure structured logging with rotation and security filters
    setup_logging(
        level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE,
    )

    logger.info("==================================================")
    logger.info("Starting %s - Advanced Discord Music Platform", settings.BOT_NAME)
    logger.info("==================================================")

    token = settings.DISCORD_TOKEN.strip()
    if not token or token == "your_bot_token_here":
        logger.critical(
            "DISCORD_TOKEN is not configured! Please configure your token in the .env file or environment variables."
        )
        print("\n[ERROR] DISCORD_TOKEN is missing!")
        print("1. Open the `.env` file in the project directory.")
        print("2. Set DISCORD_TOKEN=your_token_from_discord_developer_portal")
        print("3. Restart the bot.\n")
        sys.exit(1)

    # Initialize bot client
    bot = HarmoniXBot(settings=settings)

    # Signal handling for graceful shutdown
    loop = asyncio.get_running_loop()

    def handle_exit_signal():
        logger.info("Received termination signal. Closing HarmoniX...")
        asyncio.create_task(bot.close())

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_exit_signal)

    try:
        async with bot:
            await bot.start(token)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Shutting down gracefully...")
    except Exception as e:
        logger.critical("Fatal error during bot execution: %s", e, exc_info=True)
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
