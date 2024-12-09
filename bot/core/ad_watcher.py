import asyncio
import random
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import aiohttp

from bot.config.config import settings
from bot.utils.logger import logger


class AdWatcher:
    BASE_ADSGRAM_URL = "https://api.adsgram.ai/"

    def __init__(self, user_data, session_name, headers, chat_instance, balance):
        self.user_data = user_data
        self.session_name = session_name
        self._headers = headers
        self.chat_instance = chat_instance
        self.balance = balance

    def _get_video_duration_regex(self, xml_text: str) -> int | None:
        """
        Extracts video duration from xml_text.

        Args:
            xml_text (str): XML text containing video duration.

        Returns:
            int | None: Video duration in seconds, or None if not found.
        """
        match = re.search(r"<Duration>(\d{2}:\d{2}:\d{2})</Duration>", xml_text)
        if not match:
            return None

        hours, minutes, seconds = map(int, match.group(1).split(":"))
        return hours * 3600 + minutes * 60 + seconds

    async def _handle_fullscreen_media(
        self, session: aiohttp.ClientSession, trackings_data: list
    ) -> None:
        """
        Handles fullscreen media.

        Args:
            session (aiohttp.ClientSession): HTTP session.
            trackings_data (list): List of trackings data.
        """
        logger.info(f"{self.session_name} | Watching ads")

        render_url = trackings_data[0].get("value")
        response_render = await session.get(
            render_url, headers=self._headers["adsgram"], ssl=settings.ENABLE_SSL
        )
        response_render.raise_for_status()

        await asyncio.sleep(2)

        show_url = trackings_data[1].get("value")
        response_show = await session.get(
            show_url, headers=self._headers["adsgram"], ssl=settings.ENABLE_SSL
        )
        response_show.raise_for_status()

        await asyncio.sleep(13)

        reward_url = trackings_data[4].get("value")
        response_reward = await session.get(
            reward_url, headers=self._headers["adsgram"], ssl=settings.ENABLE_SSL
        )
        response_reward.raise_for_status()

        self.balance += 16
        logger.info(f"{self.session_name} | Watched ads | Reward: +16 PX")

    async def _handle_rewarded_video(
        self, session: aiohttp.ClientSession, adsgram_response_json: dict
    ) -> None:
        """
        Handles rewarded video.

        Args:
            session (aiohttp.ClientSession): HTTP session.
            adsgram_response_json (dict): Adsgram response JSON.
        """
        logger.info(f"{self.session_name} | Watching ads")

        trackings_data = adsgram_response_json.get("banner", {}).get("trackings", {})
        xml_text = (
            adsgram_response_json.get("banner", {})
            .get("bannerAssets", [{}])[0]
            .get("value")
        )

        if not xml_text or not trackings_data:
            raise Exception(f"{self.session_name} | Failed to get ad data")

        parsed_url = urlparse(trackings_data[0].get("value"))
        query_params = parse_qs(parsed_url.query)
        record = query_params.get("record", [None])[0]

        if not record:
            raise Exception(f"{self.session_name} | Failed to get record")

        events = [
            ("start", 2, "00:00:00"),
            ("render", 0, "00:00:00"),
            ("show", 1, "00:00:02"),
            ("complete", 6, "00:00:full"),
            ("reward", 4, None),
        ]

        for event_name, tracking_type_id, base_mediaplayhead in events:
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            if event_name == "complete":
                ad_duration = self._get_video_duration_regex(xml_text)
                if not ad_duration:
                    raise Exception(f"{self.session_name} | Failed to get ad duration")

                milliseconds = random.randint(25, 233)
                mediaplayhead = f"00:00:{ad_duration:02d}.{milliseconds:03d}"

                await asyncio.sleep(ad_duration - 2)
            else:
                milliseconds = random.randint(6, 120)
                mediaplayhead = f"{base_mediaplayhead}.{milliseconds:03d}"

            if event_name in ["start", "complete"]:
                event_url = f"{self.BASE_ADSGRAM_URL}event?record={record}&trackingtypeid={tracking_type_id}&user_timestamp={timestamp}&mediaplayhead={mediaplayhead}&type={event_name}"
                event_response = await session.get(
                    event_url, headers=self._headers["adsgram"], ssl=settings.ENABLE_SSL
                )
                event_response.raise_for_status()

            elif event_name in ["render", "show"]:
                event_url = trackings_data[tracking_type_id].get("value")
                parsed_url = urlparse(event_url)
                query_params = parse_qs(parsed_url.query)
                query_params["user_timestamp"] = [timestamp]
                query_params["mediaplayhead"] = [mediaplayhead]

                encoded_query = urlencode(query_params, doseq=True)
                event_url = urlunparse(
                    (
                        parsed_url.scheme,
                        parsed_url.netloc,
                        parsed_url.path,
                        None,
                        encoded_query,
                        None,
                    )
                )

                event_response = await session.get(
                    event_url, headers=self._headers["adsgram"], ssl=settings.ENABLE_SSL
                )
                event_response.raise_for_status()

                if event_name == "show":
                    await asyncio.sleep(2)

            elif event_name == "reward":
                event_url = trackings_data[tracking_type_id].get("value")
                reward_response = await session.get(
                    event_url, headers=self._headers["adsgram"], ssl=settings.ENABLE_SSL
                )
                reward_response.raise_for_status()

        self.balance += 16
        logger.info(f"{self.session_name} | Successfully watched ads | Reward: +16 PX")

    async def watch_ads(self, session: aiohttp.ClientSession) -> int:
        """
        Watch ads and earn rewards.

        Args:
            session (aiohttp.ClientSession): The aiohttp session to use for the request.

        Returns:
            int: The balance after watching ads.
        """
        try:
            params = {
                "blockId": 4853,
                "tg_id": self.user_data["user_id"],
                "tg_platform": "android",
                "platform": "Linux aarch64",
                "language": self.user_data["language_code"],
                "chat_type": "sender",
                "chat_instance": int(self.chat_instance),
                "top_domain": "app.notpx.app",
            }

            while True:
                adsgram_watch_ad_url = f"{self.BASE_ADSGRAM_URL}adv?{urlencode(params)}"

                adsgram_response = await session.get(
                    adsgram_watch_ad_url,
                    headers=self._headers["adsgram"],
                    ssl=settings.ENABLE_SSL,
                )

                if adsgram_response.status == 403:
                    logger.info(f"{self.session_name} | No ads to watch")
                    break
                adsgram_response.raise_for_status()
                adsgram_response_json = await adsgram_response.json()

                if not adsgram_response_json:
                    logger.info(f"{self.session_name} | No ads to watch")
                    break

                adsgram_response_json = await adsgram_response.json()

                if adsgram_response_json["bannerType"] == "FullscreenMedia":
                    await self._handle_fullscreen_media(
                        session,
                        adsgram_response_json.get("banner", {}).get("trackings", {}),
                    )
                elif adsgram_response_json["bannerType"] == "RewardedVideo":
                    await self._handle_rewarded_video(session, adsgram_response_json)
                else:
                    ad_type = adsgram_response_json["bannerType"]
                    logger.info(
                        f"{self.session_name} | Unknown ad type | Ad type: {ad_type}"
                    )
                    break

                await asyncio.sleep(random.randint(34, 36))
            return self.balance
        except Exception:
            raise Exception(f"{self.session_name} | Failed to watch ads")
