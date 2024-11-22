import asyncio
import io
import random
import sys
import traceback
from datetime import datetime
from random import choice, randint
from time import time
from typing import Dict, List, NoReturn
from uuid import uuid4

import aiohttp
import cv2
import numpy as np
from aiohttp_socks import ProxyConnector
from PIL import Image
from pyrogram.client import Client

from bot.config.config import settings
from bot.core.canvas_updater.dynamic_canvas_renderer import DynamicCanvasRenderer
from bot.core.canvas_updater.websocket_manager import WebSocketManager
from bot.core.notpx_api_checker import NotPXAPIChecker
from bot.core.tg_mini_app_auth import TelegramMiniAppAuth
from bot.utils.logger import dev_logger, logger
from bot.utils.json_manager import JsonManager

class NotPXBot:
    RETRY_ITERATION_DELAY = 10 * 60  # 10 minutes
    RETRY_DELAY = 5  # 5 seconds

    def __init__(
        self, telegram_client: Client, websocket_manager: WebSocketManager
    ) -> None:
        self.telegram_client: Client = telegram_client
        self.session_name: str = telegram_client.name
        self.websocket_manager: WebSocketManager = websocket_manager
        self._headers = self._create_headers()
        self.template_id: int = 0  # defiend in _set_template
        self.template_url: str = ""  # defiend in _set_template
        self.template_x: int = 0  # defiend in _set_template
        self.template_y: int = 0  # defiend in _set_template
        self.template_size: int = 0  # defiend in _set_template
        self.max_boosts: Dict[str, int] = {
            "paintReward": 7,
            "reChargeSpeed": 11,
            "energyLimit": 7,
        }
        self.boost_prices: Dict[str, Dict[int, int]] = {
            "paintReward": {2: 5, 3: 100, 4: 200, 5: 300, 6: 500, 7: 600},
            "reChargeSpeed": {
                2: 5,
                3: 100,
                4: 200,
                5: 300,
                6: 400,
                7: 500,
                8: 600,
                9: 700,
                10: 800,
                11: 900,
            },
            "energyLimit": {2: 5, 3: 100, 4: 200, 5: 300, 6: 400, 7: 10},
        }
        self._canvas_renderer: DynamicCanvasRenderer = DynamicCanvasRenderer()
        self._tasks_list: Dict[str, str] = {
            "x:notpixel": "notpixel",
            "x:notcoin": "notcoin",
            "channel:notpixel_channel": "notpixel_channel",
            "channel:notcoin": "notcoin",
            "leagueBonusGold": "leagueBonusGold",
            "leagueBonusSilver": "leagueBonusSilver",
            "leagueBonusPlatinum": "leagueBonusPlatinum",
            "pixelInNickname": "pixelInNickname",
        }
        self._tasks_to_complete = {}
        self._notpx_api_checker: NotPXAPIChecker = NotPXAPIChecker()

    def _create_headers(self) -> Dict[str, Dict[str, str]]:
        base_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://app.notpx.app",
            "Referer": "https://app.notpx.app/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "",
        }

        websocket_headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "websocket",
            "Sec-Fetch-Mode": "websocket",
            "Sec-Fetch-Site": "same-site",
        }

        def create_headers(additional_headers=None):
            headers = base_headers.copy()
            if additional_headers:
                headers.update(additional_headers)
            return headers

        return {
            "notpx": create_headers({"Authorization": ""}),
            "tganalytics": create_headers(),
            "plausible": create_headers({"Sec-Fetch-Site": "cross-site"}),
            "websocket": create_headers(websocket_headers),
            "image_notpx": create_headers(),
        }

    async def run(self, user_agent: str, proxy: str | None) -> NoReturn:
        for header in self._headers.values():
            header["User-Agent"] = user_agent

        self.proxy = proxy

        while True:
            try:
                proxy_connector = ProxyConnector().from_url(proxy) if proxy else None
                async with aiohttp.ClientSession(connector=proxy_connector) as session:
                    if proxy:
                        await self._proxy_checker(session, proxy)

                    await self._perform_notpx_actions(session, self.telegram_client)

                minutes_to_sleep = random.randint(
                    settings.ITERATION_SLEEP_MINUTES[0],
                    settings.ITERATION_SLEEP_MINUTES[1],
                )
                sleep_time = minutes_to_sleep * 60
                logger.info(
                    f"{self.session_name} | Sleeping for: {minutes_to_sleep // 60} hours and {minutes_to_sleep % 60} minutes"
                )
                await asyncio.sleep(sleep_time)
            except Exception as error:
                handle_error(self.session_name, error)
                logger.info(
                    f"{self.session_name} | Retrying in {self.RETRY_ITERATION_DELAY} seconds"
                )
                await asyncio.sleep(self.RETRY_ITERATION_DELAY)

    async def _proxy_checker(self, session: aiohttp.ClientSession, proxy: str):
        try:
            response = await session.get(
                "https://ipinfo.io/json",
                timeout=aiohttp.ClientTimeout(10),
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()
            response_json = await response.json()
            ip = response_json.get("ip", "Not Found")
            country = response_json.get("country", "Not Found")

            logger.info(
                f"{self.session_name} | Proxy connected | IP: {ip} | Country: {country}"
            )
        except Exception:
            raise Exception(f"{self.session_name} | Proxy error | {proxy}")

    async def _perform_notpx_actions(
        self, session: aiohttp.ClientSession, telegram_client
    ):
        if settings.SLEEP_AT_NIGHT:
            await self._handle_night_sleep()

        if not await self._notpx_api_checker.check_api(session, self._headers["notpx"]):
            logger.critical("NotPX API has been changed!Try Ater Sometime!")
            sys.exit(1)

        tg_mini_app_auth = TelegramMiniAppAuth(self.telegram_client, proxy=self.proxy)
        tg_auth_app_data = await tg_mini_app_auth._get_telegram_web_data(
            "notpixel", "app", settings.REF_ID if settings.USE_REF else None
        )

        auth_url = tg_auth_app_data["auth_url"]
        self.user_data = tg_auth_app_data["user_data"]

        self._headers["notpx"]["Authorization"] = (
            f"initData {tg_auth_app_data['init_data']}"
        )

        await self._send_tganalytics_event(session)

        plausible_payload = await self._create_plausible_payload(auth_url)
        await self._send_plausible_event(session, plausible_payload)
        if settings.PARTICIPATE_IN_TOURNAMENT:
            json_manager = JsonManager()
            session_data = json_manager.get_account_by_session_name(self.session_name)
            if not session_data:
                raise ValueError(
                    f"Session name '{self.session_name}' not found in accounts.json"
                )
            if not session_data.get("tournament_first_round_template_id"):
                await self._set_tournament_template(session)
                json_manager.update_account(
                    self.session_name,
                    tournament_first_round_template_id=settings.TOURNAMENT_TEMPLATE_ID,
                )
        about_me_data = await self._get_me(session)

        websocket_token = about_me_data.get("websocketToken")

        if not websocket_token:
            raise ValueError(f"{self.session_name} | Couldn't retrieve websocket token")

        await self._get_status(session)

        if not await self._check_my(session):
            await self._set_template(session)

        await self.websocket_manager.add_session(
            notpx_headers=self._headers["notpx"],
            websocket_headers=self._headers["websocket"],
            image_notpx_headers=self._headers["notpx"],
            session_name=self.session_name,
            telegram_client=self.telegram_client,
            proxy=self.proxy,
            websocket_token=websocket_token,
        )

        if settings.UPGRADE_BOOSTS:
            if (
                self.boost_energyLimit != self.max_boosts["energyLimit"]
                or self.boost_paintReward != self.max_boosts["paintReward"]
                or self.boost_reChargeSpeed != self.max_boosts["reChargeSpeed"]
            ):
                await self._upgrade_boosts(session)
            else:
                logger.info(f"{self.session_name} | All boosts are maxed")

        while not self.websocket_manager.is_websocket_connected:
            await asyncio.sleep(2)

        if settings.PAINT_PIXELS:
            await self._paint_pixels(session)

        if settings.CLAIM_PX:
            await self._claim_px(session)

        if settings.COMPLETE_TASKS and self._tasks_to_complete:
            await self._task_completion(
                session, telegram_client, self._tasks_to_complete
            )

    async def _handle_night_sleep(self) -> None:
        current_hour = datetime.now().hour
        start_night_time = randint(
            settings.NIGHT_START_HOURS[0], settings.NIGHT_START_HOURS[1]
        )
        end_night_time = randint(
            settings.NIGHT_END_HOURS[0], settings.NIGHT_END_HOURS[1]
        )
        if start_night_time <= current_hour <= end_night_time:
            random_minutes_to_sleep_time = randint(
                settings.ADDITIONAL_NIGHT_SLEEP_MINUTES[0],
                settings.ADDITIONAL_NIGHT_SLEEP_MINUTES[1],
            )
            sleep_time_in_hours = end_night_time - current_hour
            logger.info(
                f"{self.session_name} | It's night time. Sleeping for: {int(sleep_time_in_hours)} hours and {random_minutes_to_sleep_time} minutes"
            )

            await asyncio.sleep(
                (sleep_time_in_hours * 60 * 60) + (random_minutes_to_sleep_time * 60)
            )

    async def _get_me(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> Dict[str, str]:
        try:
            response = await session.get(
                "https://notpx.app/api/v1/users/me",
                headers=self._headers["notpx"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} | Failed to get info, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._get_me(session=session, attempts=attempts + 1)
            raise Exception(f"{self.session_name} | Error while getting info")

    async def _send_tganalytics_event(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> None:
        try:
            response = await session.get(
                "https://tganalytics.xyz/aee7c93a9ae7930fb19732325d2c560c53849aa7",
                headers=self._headers["tganalytics"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()

            task = await response.text()
            solution = await self._solve_task(task)

            headers = self._headers["tganalytics"]
            headers["Content"] = solution
            headers["TGA-Auth-Token"] = (
                "eyJhcHBfbmFtZSI6Ik5vdFBpeGVsIiwiYXBwX3VybCI6Imh0dHBzOi8vdC5tZS9ub3RwaXhlbC9hcHAiLCJhcHBfZG9tYWluIjoiaHR0cHM6Ly9hcHAubm90cHguYXBwIn0=!qE41yKlb/OkRyaVhhgdePSZm5Nk7nqsUnsOXDWqNAYE="
            )

            random_event_delay = randint(2500, 2800)

            payload = self._create_tganalytics_payload(random_event_delay)

            await asyncio.sleep(random_event_delay / 1000)

            response = await session.post(
                "https://tganalytics.xyz/events",
                headers=headers,
                json=payload,
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()

            logger.info( f"{self.session_name} |\033[92m Sent TgAnalytics Data To Ashu's Server\033[0m")
        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} |\033[93m Failed To Send Tganalytics Data To Server, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}\033[0m"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._send_tganalytics_event(
                    session=session, attempts=attempts + 1
                )
            raise Exception(
                f"{self.session_name} |\033[91m Error While Sending Tganalytics Data To Server\033[0m"
            )

    def _create_tganalytics_payload(self, random_event_delay) -> List[Dict[str, str]]:
        base_event = {
            "session_id": str(uuid4()),
            "user_id": int(self.user_data["user_id"]),
            "app_name": "NotPixel",
            "is_premium": self.user_data["is_premium_user"],
            "platform": "android",
            "locale": self.user_data["language_code"],
        }
        return [
            {
                **base_event,
                "event_name": "app-hide",
                "client_timestamp": str(int(time() * 1000)),
            },
            {
                **base_event,
                "event_name": "app-init",
                "client_timestamp": str(int(time() * 1000) + random_event_delay),
            },
        ]

    async def _send_plausible_event(
        self,
        session: aiohttp.ClientSession,
        payload: Dict[str, str | None],
        attempts: int = 1,
    ) -> None:
        try:
            response = await session.post(
                "https://plausible.joincommunity.xyz/api/event",
                headers=self._headers["plausible"],
                data=payload,
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()
            logger.info(f"{self.session_name} |\033[92m Payload Sent To Ashu's Server\033[0m")
        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} |\033[93m Failed to send payload to server, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}\033[0m"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._send_plausible_event(
                    session=session, payload=payload, attempts=attempts + 1
                )
            raise Exception(
                f"{self.session_name} |\033[91m Error while sending payload server\033[0m"
            )

    async def _create_plausible_payload(self, url: str) -> Dict[str, str | None]:
        return {"n": "pageview", "u": url, "d": "notpx.app", "r": None}

    async def _solve_task(self, task: str) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                "node",
                "bot/core/poh_solver/main.js",
                task,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if stderr:
                raise Exception(
                    f"{self.session_name} |\033[91m Error while solving task | {stderr.decode('utf-8').strip()}\033[0m"
                )
            return stdout.decode("utf-8").strip()
        except Exception:
            raise Exception(f"{self.session_name} |\033[93m Unknown error while solving task\033[0m")

    async def _claim_px(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> None:
        try:
            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/claiming"
            )
            await self._send_plausible_event(session, plausible_payload)

            response = await session.get(
                "https://notpx.app/api/v1/mining/claim",
                headers=self._headers["notpx"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()
            response_json = await response.json()

            claimed_px = response_json.get("claimed")

            logger.info(
                f"{self.session_name} | Successfully claimed \033[95m{round(claimed_px, 2)}\033[0m px"
            )

            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/"
            )
            await self._send_plausible_event(session, plausible_payload)
        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} |\033[93mFailed to claim px, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}\033[0m"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._claim_px(session=session, attempts=attempts + 1)
            raise Exception(f"{self.session_name} |\033[91m Error while claiming px\033[0m")

    async def _set_template(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> None:
        try:
            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/template"
            )
            await self._send_plausible_event(session, plausible_payload)

            response = await session.get(
                "https://notpx.app/api/v1/image/template/list?limit=12&offset=0",
                headers=self._headers["notpx"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()
            response_json = await response.json()

            random_template = choice(response_json)

            response = await session.get(
                f"https://notpx.app/api/v1/image/template/{random_template['templateId']}",
                headers=self._headers["notpx"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()
            response_json = await response.json()

            self.template_id = response_json.get("id")
            self.template_url = response_json.get("url")
            self.template_x = response_json.get("x")
            self.template_y = response_json.get("y")
            self.template_size = response_json.get("imageSize")

            response = await session.put(
                f"https://notpx.app/api/v1/image/template/subscribe/{self.template_id}",
                headers=self._headers["notpx"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()

            logger.info(f"{self.session_name} |\033[95m Successfully set template\033[0m")

            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/"
            )
            await self._send_plausible_event(session, plausible_payload)
        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} |\033[93m Failed to set template, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}\033[0m"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._set_template(session=session, attempts=attempts + 1)
            raise Exception(f"{self.session_name} |\033[93m Error while setting template\033[0m")

    async def _check_my(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> bool | None:
        try:
            response = await session.get(
                "https://notpx.app/api/v1/image/template/my",
                headers=self._headers["notpx"],
                ssl=settings.ENABLE_SSL,
            )
            if response.status == 404:
                return False
            elif response.status == 200:
                response_json = await response.json()

                self.template_id = response_json.get("templateId")
                self.template_url = response_json.get("url")
                self.template_x = response_json.get("x")
                self.template_y = response_json.get("y")
                self.template_size = response_json.get("imageSize")

                return True
            else:
                response.raise_for_status()
        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} | Failed to check info, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._check_my(session=session, attempts=attempts + 1)
            raise Exception(f"{self.session_name} | Error while checking my")

    async def _get_status(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> None:
        try:
            response = await session.get(
                "https://notpx.app/api/v1/mining/status",
                headers=self._headers["notpx"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()

            response_json = await response.json()
            self.boost_energyLimit = response_json.get("boosts", {}).get("energyLimit")
            self.boost_paintReward = response_json.get("boosts", {}).get("paintReward")
            self.boost_reChargeSpeed = response_json.get("boosts", {}).get(
                "reChargeSpeed"
            )
            self.balance = response_json.get("userBalance")
            self.league = response_json.get("league")
            self._charges = response_json.get("charges")

            self._completed_tasks = response_json.get("tasks")
            for task in self._tasks_list:
                if task not in self._completed_tasks:
                    self._tasks_to_complete[task] = self._tasks_list[task]

            logger.info(
                f"{self.session_name} |\033[32m Successfully logged in \033[0m | Balance:\033[34m{round(self.balance, 2)}\033[0m| League:\033[93m{self.league.capitalize()}\033[0m"
            )

        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} | Failed to get status, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._get_status(session=session, attempts=attempts + 1)
            raise Exception(f"{self.session_name} | Error while getting status")

    async def _upgrade_boosts(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> None:
        boost_order = ["energyLimit", "paintReward", "reChargeSpeed"]

        try:
            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/claiming"
            )
            await self._send_plausible_event(session, plausible_payload)

            while True:
                for boost_type in boost_order:
                    current_boost = getattr(self, f"boost_{boost_type}")
                    if current_boost < self.max_boosts[boost_type]:
                        if await self._upgrade_boost(session, boost_type):
                            await asyncio.sleep(random.uniform(1, 2))
                            break
                        plausible_payload = await self._create_plausible_payload(
                            "https://app.notpx.app/"
                        )
                        await self._send_plausible_event(session, plausible_payload)
                        return
                else:
                    plausible_payload = await self._create_plausible_payload(
                        "https://app.notpx.app/"
                    )
                    await self._send_plausible_event(session, plausible_payload)
                    return

        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} | Failed to upgrade boosts, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                await self._upgrade_boosts(session=session, attempts=attempts + 1)
            else:
                raise Exception(f"{self.session_name} | Error while upgrading boosts")

    async def _upgrade_boost(self, session, boost_type) -> bool:
        url = f"https://notpx.app/api/v1/mining/boost/check/{boost_type}"

        if (
            self.balance
            < self.boost_prices[boost_type][getattr(self, f"boost_{boost_type}") + 1]
        ):
            logger.info(
                f"{self.session_name} | Not enough balance to upgrade {boost_type}"
            )
            return False

        response = await session.get(
            url, headers=self._headers["notpx"], ssl=settings.ENABLE_SSL
        )
        response.raise_for_status()
        response_json = await response.json()

        if not response_json.get(boost_type):
            raise Exception(
                f"{self.session_name} | Couldn't retrieve {boost_type} from response json while upgrading boost"
            )

        old_boost = getattr(self, f"boost_{boost_type}")
        setattr(self, f"boost_{boost_type}", old_boost + 1)
        self.balance -= self.boost_prices[boost_type][
            getattr(self, f"boost_{boost_type}")
        ]
        logger.info(
            f"{self.session_name} | Successfully leveled up {boost_type}! | LVL.{old_boost} -> LVL.{old_boost + 1}"
        )
        return True

    async def _paint_pixel(
        self,
        session: aiohttp.ClientSession,
        canvas_x: int,
        canvas_y: int,
        template_pixel: np.ndarray,
    ) -> None:
        """Paint a single pixel and handle the response."""

        template_pixel_hex = self._canvas_renderer.rgba_to_hex(
            tuple(template_pixel.flatten().tolist())
        )
        canvas_pixel_id = self._canvas_renderer._xy_to_pixel_id(canvas_x, canvas_y)

        payload = {
            "pixelId": canvas_pixel_id,
            "newColor": template_pixel_hex,
        }

        async with session.post(
            "https://notpx.app/api/v1/repaint/start",
            headers=self._headers["notpx"],
            json=payload,
            ssl=settings.ENABLE_SSL,
        ) as response:
            response.raise_for_status()

            self._charges -= 1
            await self._canvas_renderer.set_pixel(canvas_pixel_id, template_pixel_hex)

            response_json = await response.json()
            new_balance = response_json.get("balance")

            if round(new_balance, 2) > round(self.balance, 2):
                balance_increase = new_balance - self.balance
                logger.info(
                    f"{self.session_name} | Successfully painted pixel |\033[92m +{round(balance_increase, 2)}\033[0m PX | Balance:\033[34m{round(self.balance, 2)}\033[0m PX"
                )
                self.balance = new_balance
                return

            logger.warning(
                f"{self.session_name} | Successfully painted pixel |\033[38;2;255;165;0m +{round(balance_increase, 2)}\033[0m PX | Balance:\033[34m{round(self.balance, 2)}\033[0m PX"
            )

    async def _paint_pixels(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> None:
        MAX_CONSECUTIVE_ZERO = 5
        consecutive_zero_rewards = 0

        try:
            response = await session.get(
                self.template_url,
                headers=self._headers["image_notpx"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()

            template_from_response = Image.open(io.BytesIO(await response.read()))

            if template_from_response.size != (self.template_size, self.template_size):
                template_cv2 = cv2.cvtColor(
                    np.array(template_from_response), cv2.COLOR_RGBA2BGRA
                )
                template_cv2 = cv2.resize(
                    template_cv2, (self.template_size, self.template_size)
                )
                template_cv2 = cv2.cvtColor(template_cv2, cv2.COLOR_BGR2RGBA)
                template_from_response = Image.fromarray(template_cv2)

            template_from_response = template_from_response.convert("RGBA")
            template_array = np.array(template_from_response)
            template_2d = template_array.reshape(
                (self.template_size, self.template_size, 4)
            )

            for ty in range(self.template_size):
                if self._charges <= 0:
                    break

                for tx in range(self.template_size):
                    if self._charges <= 0:
                        break

                    if consecutive_zero_rewards >= MAX_CONSECUTIVE_ZERO:
                        logger.warning(
                            f"{self.session_name} | No reward for {MAX_CONSECUTIVE_ZERO} consecutive times. Resetting template."
                        )
                        await self._set_template(session)  # Reset template
                        return await self._paint_pixels(session, attempts=attempts)

                    canvas_array = self._canvas_renderer.get_canvas
                    canvas_2d = canvas_array.reshape(
                        (
                            self._canvas_renderer.CANVAS_SIZE,
                            self._canvas_renderer.CANVAS_SIZE,
                            4,
                        )
                    )

                    canvas_x = self.template_x + tx
                    canvas_y = self.template_y + ty

                    template_pixel = template_2d[ty, tx]
                    canvas_pixel = canvas_2d[canvas_y, canvas_x]

                    if template_pixel[3] == 0:
                        continue

                    if not np.array_equal(template_pixel[:3], canvas_pixel[:3]):
                        initial_balance = self.balance

                        await self._paint_pixel(
                            session=session,
                            canvas_x=canvas_x,
                            canvas_y=canvas_y,
                            template_pixel=template_pixel,
                        )

                        if round(self.balance, 2) <= round(initial_balance, 2):
                            consecutive_zero_rewards += 1
                        else:
                            consecutive_zero_rewards = 0

                        await asyncio.sleep(random.uniform(0.95, 2.3))

        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} | Failed to paint pixels, changing template and retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}"
                )
                await self._set_template(session)
                await asyncio.sleep(self.RETRY_DELAY)
                await self._paint_pixels(session=session, attempts=attempts + 1)
            else:
                raise Exception(
                    f"{self.session_name} | Max retry attempts reached while painting pixels"
                )

    async def _task_completion(
        self,
        session: aiohttp.ClientSession,
        telegram_client: Client,
        tasks_to_complete: Dict,
        attempts: int = 1,
    ) -> None:
        try:
            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/claiming"
            )
            await self._send_plausible_event(session, plausible_payload)

            twitter_keys = [key for key in tasks_to_complete if key.startswith("x:")]
            channel_keys = [
                key for key in tasks_to_complete if key.startswith("channel:")
            ]

            if twitter_keys:
                for key in twitter_keys:
                    twitter_account = tasks_to_complete[key]
                    response = await session.get(
                        f"https://notpx.app/api/v1/mining/task/check/x?name={twitter_account}",
                        headers=self._headers["notpx"],
                        ssl=settings.ENABLE_SSL,
                    )
                    response.raise_for_status()
                    response_json = await response.json()
                    if response_json.get("x:" + twitter_account):
                        logger.info(
                            f"{self.session_name} | Completed task: {twitter_account} on X.com"
                        )
                    else:
                        logger.warning(
                            f"{self.session_name} | Failed to complete task: {twitter_account} on X.com"
                        )
                    await asyncio.sleep(random.uniform(4.95, 6.35))

            if channel_keys:
                for key in channel_keys:
                    channel = tasks_to_complete[key]
                    async with telegram_client:
                        await telegram_client.join_chat(channel)

                    await asyncio.sleep(random.uniform(1.95, 2.35))

                    response = await session.get(
                        f"https://notpx.app/api/v1/mining/task/check/channel?name={channel}",
                        headers=self._headers["notpx"],
                        ssl=settings.ENABLE_SSL,
                    )
                    response.raise_for_status()
                    logger.info(f"{self.session_name} | Completed task: Join {channel}")
                    await asyncio.sleep(random.uniform(4.95, 6.35))

            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/"
            )
            await self._send_plausible_event(session, plausible_payload)

        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} | Failed to complete tasks, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                await self._task_completion(
                    session=session,
                    telegram_client=telegram_client,
                    tasks_to_complete=tasks_to_complete,
                    attempts=attempts + 1,
                )
            else:
                raise Exception(
                    f"{self.session_name} | Max retry attempts reached while completing tasks"
                )
    async def _set_tournament_template(
        self, session: aiohttp.ClientSession, attempts: int = 1
    ) -> None:
        try:
            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/tournament"
            )
            await self._send_plausible_event(session, plausible_payload)            
            response = await session.put(
                f"https://notpx.app/api/v1/tournament/template/subscribe/{settings.TOURNAMENT_TEMPLATE_ID}",
                headers=self._headers["notpx"],
                ssl=settings.ENABLE_SSL,
            )
            response.raise_for_status()
            logger.info(
                f"{self.session_name} | Set tournament template | Template ID: {settings.TOURNAMENT_TEMPLATE_ID}"
            )

            plausible_payload = await self._create_plausible_payload(
                "https://app.notpx.app/"
            )
            await self._send_plausible_event(session, plausible_payload)        
        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"{self.session_name} | Failed to set tournament template, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}"
                )
                dev_logger.warning(f"{self.session_name} | {traceback.format_exc()}")
                await asyncio.sleep(self.RETRY_DELAY)
                await self._set_tournament_template(
                    session=session, attempts=attempts + 1
                )
            else:
                raise Exception(
                    f"{self.session_name} | Max retry attempts reached while setting tournament template"
                )

def handle_error(session_name, error: Exception) -> None:
    logger.error(f"{error.__str__() if error else 'NotPXBot | Something went wrong'}")
    dev_logger.error(f"{session_name} | {traceback.format_exc()}")


async def run_notpxbot(
    telegram_client: Client,
    user_agent: str,
    proxy: str | None,
    start_delay: int,
) -> None:
    websocket_manager = None
    try:
        websocket_manager = WebSocketManager(
            token_endpoint="https://notpx.app/api/v1/users/me",
            websocket_url="wss://notpx.app/connection/websocket",
        )
        logger.info(f"{telegram_client.name} | Starting in {start_delay} seconds")
        await asyncio.sleep(start_delay)

        await NotPXBot(
            telegram_client=telegram_client, websocket_manager=websocket_manager
        ).run(user_agent=user_agent, proxy=proxy)
    except Exception as error:
        handle_error(telegram_client.name, error)
    finally:
        if telegram_client.is_connected:
            await telegram_client.disconnect()

        if websocket_manager and websocket_manager._running:
            await websocket_manager.stop()

        logger.info(f"{telegram_client.name} | Stopped")
