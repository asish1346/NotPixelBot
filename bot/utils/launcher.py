import argparse
import asyncio
import traceback
from random import randint
from typing import Dict, List

from better_proxy import Proxy

from bot.config.config import settings
from bot.core.notpxbot import run_notpxbot
from bot.core.registrator import get_telegram_client, register_sessions
from bot.utils.accounts_manager import AccountsManager
from bot.utils.banner_animation import print_banner_animation
from bot.utils.logger import dev_logger, logger

options = """
1. Register session
2. Start bot
3. Update user agent to telegram format
"""


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", type=int, help="Action to perform")

    if settings.PLAY_INTRO:
        print_banner_animation()

    action = parser.parse_args().action

    if not action:
        print(options)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
                print(options)
            elif action not in ["1", "2", "3"]:
                logger.warning("Action must be 1, 2 or 3")
                print(options)
            else:
                action = int(action)
                break

    if action == 1:
        while True:
            await register_sessions()

            answer = input("Do you want to register another session? [Y/n]: ")

            if not answer or answer.lower() == "y" or answer.lower() == "yes":
                continue

            break
    elif action == 2:
        accounts = await AccountsManager().get_accounts()
        await run_tasks(accounts=accounts)
    elif action == 3:
        await AccountsManager().update_ua_to_new_format()


async def run_tasks(accounts: List[Dict[str, str]]) -> None:
    tasks = []
    try:
        for account in accounts:
            session_name = account.get("session_name")
            user_agent = account.get("user_agent")
            raw_proxy = account.get("proxy")

            if not session_name or not user_agent:
                raise ValueError(
                    "Session name or user agent not found in accounts.json"
                )

            telegram_client = await get_telegram_client(
                session_name=session_name, user_agent=user_agent, raw_proxy=raw_proxy
            )
            proxy = Proxy.from_str(proxy=raw_proxy).as_url if raw_proxy else None

            start_delay = randint(
                settings.INITIAL_START_DELAY_SECONDS[0],
                settings.INITIAL_START_DELAY_SECONDS[1],
            )

            task = asyncio.create_task(
                run_notpxbot(
                    telegram_client=telegram_client,
                    user_agent=user_agent,
                    proxy=proxy,
                    start_delay=start_delay,
                )
            )
            task.set_name(session_name)

            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as error:
        logger.error(f"{error or 'Something went wrong'}")
        dev_logger.error(f"{traceback.format_exc()}")
