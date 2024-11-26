import asyncio
import sys
from time import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import jwt
from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from aiohttp_socks import ProxyConnector
from attr import define, field
from pyrogram.client import Client
from typing_extensions import Self

from bot.config.config import settings
from bot.core.canvas_updater.centrifuge import decode_message, encode_commands
from bot.core.canvas_updater.dynamic_canvas_renderer import DynamicCanvasRenderer
from bot.core.canvas_updater.exceptions import (
    SessionErrors,
    TokenError,
    UpdateAuthHeaderError,
    WebSocketErrors,
)
from bot.core.tg_mini_app_auth import TelegramMiniAppAuth
from bot.utils.logger import dev_logger, logger


@define
class SessionData:
    """Represents a WebSocket session with its associated data."""

    name: str = field()
    notpx_headers: Dict[str, str] = field()
    websocket_headers: Dict[str, str] = field()
    image_notpx_headers: Dict[str, str] = field()
    telegram_client: Client = field()
    websocket_token: str = field()
    proxy: Optional[str] = field(default=None)
    active: bool = field(default=False)

    @classmethod
    def create(
        cls,
        notpx_headers: Dict[str, str],
        websocket_headers: Dict[str, str],
        image_notpx_headers: Dict[str, str],
        name: str,
        telegram_client: Client,
        proxy: Optional[str],
        websocket_token: str,
    ) -> Self:
        """Factory method to create a new session."""
        return cls(
            name=name,
            notpx_headers=notpx_headers,
            websocket_headers=websocket_headers,
            image_notpx_headers=image_notpx_headers,
            telegram_client=telegram_client,
            proxy=proxy,
            websocket_token=websocket_token,
        )


class WebSocketManager:
    """Manages WebSocket connections and sessions."""

    REFRESH_TOKEN_IF_NEEDED_INTERVAL = 60  # seconds
    MAX_RECONNECT_ATTEMPTS = 3  # after initial attempt
    RETRY_DELAY = 5  # seconds
    MAX_SWITCH_ATTEMPTS = 3  # including initial attempt
    SWITCH_TIMEOUT = 600 # 10 minutes

    _instance = None

    def __new__(cls, *args, **kwargs) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, token_endpoint: str, websocket_url: str) -> None:
        self.__token_endpoint: str = token_endpoint
        self.__websocket_url: str = websocket_url
        self.sessions: List[SessionData] = []
        self._active_session: Optional[SessionData] = None
        self._websocket: Optional[ClientWebSocketResponse] = None
        self._canvas_renderer = DynamicCanvasRenderer()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._running: bool = False
        self._websocket_task: Optional[asyncio.Task] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._token_refresh_event = asyncio.Event()
        self.__connection_attempts: int = 1
        self._switch_attempts: int = 1
        self._last_switch_time: float = 0
        self._is_canvas_set: bool = False

    async def add_session(
        self,
        notpx_headers: Dict[str, str],
        websocket_headers: Dict[str, str],
        image_notpx_headers: Dict[str, str],
        session_name: str,
        telegram_client: Client,
        proxy: str | None,
        websocket_token: str,
    ) -> None:
        """
        Add a new WebSocket session to the manager.

        This method creates a new session with the provided headers, client session,
        and other parameters, and adds it to the list of sessions managed by this
        WebSocketManager instance. If the session with the given name already exists,
        it will not be added again. If there is no active session, the newly added
        session will be activated.

        Args:
            notpx_headers (Dict[str, str]): Headers for the notpx API.
            websocket_headers (Dict[str, str]): Headers for the WebSocket connection.
            image_notpx_headers (Dict[str, str]): Headers for image-related notpx API.
            session_name (str): The name of the session.
            telegram_client (Client): The Telegram client associated with the session.
            proxy (Optional[str]): The proxy settings for the session, if any.
            websocket_token (str): The token used for WebSocket authentication.
        """
        async with self._lock:
            if session_name in [session.name for session in self.sessions]:
                return

            session = SessionData.create(
                name=session_name,
                notpx_headers=notpx_headers,
                websocket_headers=websocket_headers,
                image_notpx_headers=image_notpx_headers,
                telegram_client=telegram_client,
                proxy=proxy,
                websocket_token=websocket_token,
            )

            self.sessions.append(session)

            if not self._active_session:
                await self._activate_session(session)

    async def _activate_session(self, session: SessionData) -> None:
        """
        Activates the given session by setting it as the current active session.

        This method deactivates any currently active session before activating the
        specified session. It also initiates and manages tasks for token refresh
        and WebSocket connection if they are not already running.

        Args:
            session (SessionData): The session to be activated.
        """
        if self._active_session:
            self._active_session.active = False

        session.active = True
        self._active_session = session

        self._running = True

        if not self._refresh_task or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._token_refresh_loop())
            self._refresh_task.set_name("Token Refresh Loop")
            self._refresh_task.add_done_callback(handle_task_completion)

        if not self._websocket_task or self._websocket_task.done():
            self._websocket_task = asyncio.create_task(self._connect_websocket())
            self._websocket_task.set_name("WebSocket Connection")
            self._websocket_task.add_done_callback(handle_task_completion)

    async def _switch_to_next_session(self) -> None:
        """
        Switches to the next session in the list of sessions.

        This method switches from the current active session to the next session in
        the list of sessions. It cancels any running tasks for token refresh and
        WebSocket connection, and then activates the new session.

        Raises:
            SessionErrors.NoAvailableSessionsError: If there are no available sessions.
            SessionErrors.NoActiveSessionError: If there is no active session.
        """
        if not self.sessions:
            raise SessionErrors.NoAvailableSessionsError(
                "Can not switch to next session, no sessions available"
            )

        if not self._active_session:
            raise SessionErrors.NoActiveSessionError("No active session available")

        if time() - self._last_switch_time < self.SWITCH_TIMEOUT:
            if self._switch_attempts <= self.MAX_SWITCH_ATTEMPTS:
                self._switch_attempts += 1
                self._last_switch_time = time()
            else:
                logger.error("WebSocketManager | Max switch attempts reached")
                raise SessionErrors.MaxSwitchAttemptsError(
                    "Max switch attempts reached"
                )
        else:
            self._switch_attempts = 1
            self._last_switch_time = time()

        current_session_index = self.sessions.index(self._active_session)
        next_session_index = (current_session_index + 1) % len(self.sessions)

        next_session = self.sessions[next_session_index]

        logger.info(
            f"WebSocketManager | Switching from session {self._active_session.name} to session {next_session.name}"
        )

        self._running = False

        if self._websocket_task and not self._websocket_task.done():
            self._websocket_task.cancel()
            await self._websocket_task

        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            await self._refresh_task

        await self._activate_session(next_session)

    async def _connect_websocket(self) -> None:
        """
        Establishes and manages the WebSocket connection for the active session.

        This method continuously attempts to connect to the WebSocket server
        while the session is running. If there is no active session, it raises an
        error. It retrieves the latest image using the canvas renderer and then
        establishes a WebSocket connection using the active session's headers and
        centrifuge-protobuf protocols. Once connected, it logs the connection details and handles the
        WebSocket communication. If an error occurs, it handles reconnection attempts and switches
        to the next session if maximum attempts are exceeded. If task is cancelled, it returns.

        Raises:
            SessionErrors.NoActiveSessionError: If there is no active session.
        """
        while self._running:
            try:
                if not self._active_session:
                    raise SessionErrors.NoActiveSessionError(
                        "No active session available"
                    )

                proxy_connector = (
                    ProxyConnector().from_url(self._active_session.proxy)
                    if self._active_session.proxy
                    else None
                )
                async with ClientSession(connector=proxy_connector) as session:
                    async with session.ws_connect(
                        self.__websocket_url,
                        headers=self._active_session.websocket_headers,
                        protocols=["centrifuge-protobuf"],
                        ssl=settings.ENABLE_SSL,
                    ) as websocket:
                        self._websocket = websocket
                        logger.info(
                            "WebSocketManager | WebSocket connection established"
                        )
                        await self._handle_websocket_connection()
            except asyncio.CancelledError:
                return
            except Exception:
                if self.__connection_attempts > self.MAX_RECONNECT_ATTEMPTS:
                    logger.error(
                        "WebSocketManager | Maximum connection attempts exceeded, switching to next session"
                    )
                    await self._switch_to_next_session()
                    return

                logger.warning(
                    f"WebSocketManager | Connection attempt {self.__connection_attempts} failed, retrying in {self.RETRY_DELAY} seconds"
                )
                dev_logger.warning(f"{traceback.format_exc()}")

                self.__connection_attempts += 1

                await asyncio.sleep(self.RETRY_DELAY)

    async def _handle_websocket_connection(self) -> None:
        """
        Handles the WebSocket connection and sends the initial authentication command.

        This method is responsible for sending the initial authentication command to the
        WebSocket server, and then entering a loop where it receives and handles incoming
        messages. If the token refresh event is set, it clears the event and breaks the loop,
        which is used to restart the WebSocket connection when the token refresh event is
        triggered.

        Raises:
            SessionErrors.NoActiveSessionError: If there is no active session.
            WebSocketErrors.NoConnectionError: If the WebSocket connection is not established.
            WebSocketErrors.ServerClosedConnectionError: If the WebSocket server closed the connection.
            WebSocketErrors.ConnectionError: If the WebSocket connection failed.
            asyncio.CancelledError: If the task is cancelled.
        """
        if not self._active_session:
            raise SessionErrors.NoActiveSessionError("No active session available")

        if not self._websocket or self._websocket.closed:
            raise WebSocketErrors.NoConnectionError(
                "WebSocket connection not established"
            )

        await self._handle_websocket_auth()

        while self._running:
            # Check if the token refresh event is set
            # If it is, clear the event and break the loop
            # This is used to restart websocket connection when the token refresh event is triggered
            if self._token_refresh_event.is_set():
                logger.info(
                    "WebSocketManager | Token refresh event triggered, restarting WebSocket connection"
                )
                self._token_refresh_event.clear()
                return

            try:
                if not self._websocket or self._websocket.closed:
                    raise WebSocketErrors.NoConnectionError(
                        "WebSocket connection not established"
                    )

                message = await self._websocket.receive()

                if message.type == WSMsgType.CLOSE:
                    raise WebSocketErrors.ServerClosedConnectionError(
                        "WebSocket server closed connection"
                    )

                if not message.data:
                    continue

                elif message.data == b"\x00":
                    await self._websocket.send_bytes(b"\x00")
                    continue

                decoded_message = decode_message(message.data)

                await self._handle_websocket_message(decoded_message)
            except asyncio.CancelledError:
                raise
            except WebSocketErrors.ServerClosedConnectionError:
                logger.warning("WebSocketManager | WebSocket server closed connection")
                raise
            except Exception:
                logger.warning(
                    "WebSocketManager | Unknown WebSocket error occurred while handling message"
                )
                raise WebSocketErrors.ConnectionError("WebSocket connection failed")

    async def _handle_websocket_message(self, message) -> None:
        """
        Handles a WebSocket message from the server.

        This method is responsible for calling the DynamicCanvasRenderer
        to update the canvas with the given message.

        Raises:
            WebSocketErrors.NoConnectionError: If there is no WebSocket connection available.
        """
        if not self._websocket or self._websocket.closed:
            raise WebSocketErrors.NoConnectionError("No WebSocket connection available")

        if not message:
            return

        if self.__connection_attempts > 1:
            self.__connection_attempts = 1

        if isinstance(message, bytes):
            self._canvas_renderer.set_canvas(message)
            self._is_canvas_set = True
            return

        self._canvas_renderer.update_canvas(message)

    async def _handle_websocket_auth(self) -> None:
        if not self._websocket or self._websocket.closed:
            raise WebSocketErrors.NoConnectionError("No WebSocket connection available")

        if not self._active_session:
            raise SessionErrors.NoActiveSessionError("No active session available")

        auth_data = f'{{"token":"{self._active_session.websocket_token}"}}'

        auth_command = [
            {
                "connect": {
                    "data": auth_data.encode(),
                    "name": "js",
                },
                "id": 1,
            }
        ]

        await self._websocket.send_bytes(encode_commands(auth_command))

    async def _token_refresh_loop(self) -> None:
        """
        Refreshes the WebSocket token if it is about to expire.

        This method is responsible for periodically checking if the
        WebSocket token is about to expire, and if so, it refreshes
        the token and updates the authorization header for the
        active session.

        Raises:
            SessionErrors.NoActiveSessionError: If there is no active session.
        """
        if not self._active_session:
            raise SessionErrors.NoActiveSessionError("No active session available")

        while self._running:
            try:
                if self._is_token_expired():
                    await self._update_authorization_header()
                    self._active_session.websocket_token = await self._get_token()
                    self._token_refresh_event.set()
                await asyncio.sleep(self.REFRESH_TOKEN_IF_NEEDED_INTERVAL)
            except asyncio.CancelledError:
                return
            except Exception:
                logger.error(
                    "WebSocketManager | Token refresh failed, switching to next session"
                )
                await self._switch_to_next_session()
                break

    def _is_token_expired(self) -> bool:
        """
        Checks if the WebSocket token is expired or about to expire.

        This method decodes the current WebSocket token to extract its expiration
        time and determines whether the token is expired or will expire within the
        next 5 minutes. If the token is expired or invalid, it returns True.

        Returns:
            bool: True if the token is expired or invalid, False otherwise.

        Raises:
            SessionErrors.NoActiveSessionError: If there is no active session.
        """
        if not self._active_session:
            raise SessionErrors.NoActiveSessionError("No active session available")

        if not self._active_session.websocket_token:
            return True

        try:
            payload = jwt.decode(
                self._active_session.websocket_token,
                options={"verify_signature": False},
            )
            exp_time = datetime.fromtimestamp(payload["exp"])
            return datetime.now() + timedelta(minutes=5) >= exp_time
        except jwt.InvalidTokenError:
            return True

    async def _get_token(self, attempts: int = 1) -> str:
        """
        Retrieves a new WebSocket token for the active session.

        This asynchronous method attempts to fetch a new WebSocket token from the
        specified token endpoint using the active session's headers. If the request
        fails, it retries up to the maximum number of allowed attempts, with a delay
        between each retry. If all attempts fail, a TokenError is raised.

        Args:
            attempts (int): The current attempt number, defaults to 1.

        Returns:
            str: The retrieved WebSocket token.

        Raises:
            SessionErrors.NoActiveSessionError: If there is no active session.
            TokenError: If the token cannot be retrieved after maximum attempts.
        """
        if not self._active_session:
            raise SessionErrors.NoActiveSessionError("No active session available")

        try:
            proxy_connector = (
                ProxyConnector().from_url(self._active_session.proxy)
                if self._active_session.proxy
                else None
            )
            async with ClientSession(connector=proxy_connector) as session:
                async with session.get(
                    self.__token_endpoint,
                    headers=self._active_session.notpx_headers,
                    ssl=settings.ENABLE_SSL,
                ) as response:
                    response.raise_for_status()
                    response_json = await response.json()
                    return response_json.get("websocketToken")
        except Exception:
            if attempts <= self.MAX_RECONNECT_ATTEMPTS:
                logger.warning(
                    f"WebSocketManager | Token retrieval attempt {attempts} failed, retrying in {self.RETRY_DELAY}s"
                )
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._get_token(attempts + 1)
            raise TokenError("Failed to get token")

    async def _update_authorization_header(self) -> None:
        """
        Updates the authorization header for the active session.

        This asynchronous method attempts to fetch the latest authentication data
        from the Telegram Mini App using the active session's headers and
        associated Telegram client. It then updates the authorization header of
        the active session with the new authentication data. If the request fails,
        it logs a warning and raises a UpdateAuthHeaderError.

        Raises:
            SessionErrors.NoActiveSessionError: If there is no active session.
            UpdateAuthHeaderError: If the authorization header cannot be updated.
        """
        if not self._active_session:
            raise SessionErrors.NoActiveSessionError("No active session available")

        try:
            tg_mini_app_auth = TelegramMiniAppAuth(
                self._active_session.telegram_client,
                self._active_session.proxy,
            )
            tg_auth_app_data = await tg_mini_app_auth._get_telegram_web_data(
                "notpixel", "app", settings.REF_ID if settings.USE_REF else None
            )

            self._active_session.notpx_headers["Authorization"] = (
                f"initData {tg_auth_app_data['init_data']}"
            )
        except Exception:
            logger.error("WebSocketManager | Failed to update authorization header")
            raise UpdateAuthHeaderError("Failed to update authorization header")

    @property
    def is_canvas_set(self) -> bool:
        return self._is_canvas_set

    async def stop(self) -> None:
        """
        Stops the WebSocket manager and associated tasks.

        This asynchronous method stops the WebSocket manager and attempts to close
        the active WebSocket connection. It also cancels and waits for the
        completion of the WebSocket task and the token refresh task.
        """
        self._running = False

        if self._websocket_task:
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except Exception:
                pass

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except Exception:
                pass


def handle_task_completion(task: asyncio.Task) -> None:
    """
    Handles the completion of an asyncio task.

    This function checks if the task has raised any exception upon completion.
    If an exception is found, it raises the exception. The function ignores
    `asyncio.CancelledError` and `KeyboardInterrupt` exceptions. Other exceptions
    are logged using the `logger` and `dev_logger`, and the program exits with a
    status code of 1.

    Args:
        task (asyncio.Task): The asyncio task whose completion is being handled.
    """
    try:
        if task.exception():
            raise task.exception()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    except Exception as error:
        logger.error(
            f"{f'WebSocketManager | {error.__str__()}' if error else 'WebSocketManager | Something went wrong'}"
        )
        dev_logger.error(f"{traceback.format_exc()}")
        sys.exit(1)
