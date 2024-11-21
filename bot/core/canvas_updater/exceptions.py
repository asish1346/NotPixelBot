class WebSocketErrors(Exception):
    """Base exception for WebSocket-related errors."""

    def __init__(self, message: str = "Unknown WebSocket error") -> None:
        super().__init__(message)

    class ServerClosedConnectionError(Exception):
        """Raised when the WebSocket server connection is closed."""

        def __init__(self, message: str = "WebSocket server closed connection") -> None:
            super().__init__(message)

    class AuthenticationError(Exception):
        """Raised when the WebSocket authentication fails."""

        def __init__(self, message: str = "WebSocket authentication failed") -> None:
            super().__init__(message)

    class ConnectionError(Exception):
        """Raised when the WebSocket connection fails."""

        def __init__(self, message: str = "WebSocket connection failed") -> None:
            super().__init__(message)

    class NoConnectionError(Exception):
        """Raised when there is no WebSocket connection available."""

        def __init__(self, message: str = "No WebSocket connection available") -> None:
            super().__init__(message)


class SessionErrors(Exception):
    """Base exception for Session-related errors."""

    def __init__(self, message: str = "Unknown Session error") -> None:
        super().__init__(message)

    class NoAvailableSessionsError(Exception):
        """Raised when there are no available sessions."""

        def __init__(self, message: str = "No available sessions") -> None:
            super().__init__(message)

    class NoActiveSessionError(Exception):
        """Raised when there is no active session."""

        def __init__(self, message: str = "No active session") -> None:
            super().__init__(message)


class TokenError(Exception):
    """Base exception for token-related errors."""

    def __init__(self, message: str = "Unknown token error") -> None:
        super().__init__(message)
    

class UpdateAuthHeaderError(Exception):
    """Base exception for updating auth header errors."""

    def __init__(self, message: str = "Unknown update auth header error") -> None:
        super().__init__(message)
