import re
import traceback
from urllib.parse import urlparse

from pyrogram.client import Client

from bot.config.config import settings
from bot.utils.json_manager import JsonManager
from bot.utils.logger import dev_logger, logger
from bot.utils.ua_generator import generate_user_agent


async def register_sessions(session_name: str | None = None) -> None:
    try:
        API_ID = settings.API_ID
        API_HASH = settings.API_HASH

        if not API_ID or not API_HASH:
            raise ValueError("API_ID and API_HASH must be set in .env file")

        if not session_name:
            session_name = input("Enter session name (Enter to exit): ")

        if not session_name:
            return

        raw_proxy = input(
            "Enter proxy in format type://username:password@ip:port (Enter to skip): "
        )

        user_agent = generate_user_agent()

        session = await get_telegram_client(
            session_name=session_name, user_agent=user_agent, raw_proxy=raw_proxy
        )

        async with session:
            user_data = await session.get_me()

        json_manager = JsonManager()

        json_manager.save_to_json(
            "accounts.json",
            {
                "session_name": session_name,
                "user_agent": user_agent,
                "proxy": raw_proxy,
            },
        )

        logger.info(
            f"Session {session_name} registered | User: {user_data.username} | User ID: {user_data.id}"
        )
    except Exception as error:
        logger.error(f"{error or 'Something went wrong'}")
        dev_logger.error(f"Error while registering session: {traceback.format_exc()}")


async def get_telegram_client(
    session_name: str, user_agent: str, raw_proxy: str | None = None
) -> Client:
    try:
        if not session_name:
            raise ValueError("Session name cannot be empty")

        if not user_agent:
            raise ValueError("User agent cannot be empty")

        if not settings.API_ID or not settings.API_HASH:
            raise ValueError("API_ID and API_HASH must be set in .env file")

        device_model = re.search(r"Android ([\d.]+); ([\w\s-]+)", user_agent)

        if not device_model:
            raise ValueError("Invalid user agent")

        system_version = device_model.group(1)
        device_name = device_model.group(2)

        parsed_proxy = urlparse(raw_proxy) if raw_proxy else None

        proxy_dict = (
            {
                "scheme": parsed_proxy.scheme,
                "username": parsed_proxy.username,
                "password": parsed_proxy.password,
                "hostname": parsed_proxy.hostname,
                "port": parsed_proxy.port,
            }
            if parsed_proxy
            else None
        )

        telegram_client = Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            proxy=proxy_dict,  # type: ignore
            workdir="sessions",
            device_model=device_name,
            system_version=system_version,
            app_version="Telegram Android 11.4.2",
        )

        return telegram_client
    except Exception as error:
        raise Exception(
            f"Error while getting telegram client: {error or 'Unknown error'}"
        )
