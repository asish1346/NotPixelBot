import os
from typing import Dict, List

from bot.config.config import settings
from bot.core.registrator import register_sessions
from bot.utils.json_manager import JsonManager
from bot.utils.logger import logger


class AccountsManager:
    def __init__(self):
        self.workdir = "sessions/"
        self.api_id = settings.API_ID
        self.api_hash = settings.API_HASH

    async def get_accounts(self):
        session_names = self.parse_sessions()
        available_accounts = await self.get_available_accounts(session_names)

        if not available_accounts:
            raise ValueError("No available accounts found, please register first")
        else:
            logger.info(f"Found {len(available_accounts)} available accounts")

        return available_accounts

    def parse_sessions(self):
        sessions = []
        for file in os.listdir(self.workdir):
            if file.endswith(".session"):
                sessions.append(file.replace(".session", ""))

        return sessions

    @staticmethod
    async def get_available_accounts(session_names: list) -> List[Dict[str, str]]:
        json_manager = JsonManager()

        accounts = json_manager.get_all_accounts()

        available_accounts = []

        for session_name in session_names:
            account = next(
                (
                    account
                    for account in accounts
                    if account.get("session_name") == session_name
                ),
                None,
            )

            if account:
                available_accounts.append(account)
            else:
                logger.warning(f"Session {session_name} not found in accounts.json")
                user_response = input(
                    f"Do you want to add session {session_name} to accounts.json? [Y/n]: "
                )

                if (
                    not user_response
                    or user_response.lower() == "y"
                    or user_response.lower() == "yes"
                ):
                    await register_sessions(session_name=session_name)
                    available_accounts.append(
                        json_manager.get_account_by_session_name(session_name)
                    )

        return available_accounts
