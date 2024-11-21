import asyncio
import io
from functools import lru_cache
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image
from typing_extensions import Self


class DynamicCanvasRenderer:
    MAX_ATTEMPTS = 3
    RETRY_DELAY = 5
    CANVAS_SIZE = 1000
    DYNAMITE_COLOR = "#171F2A"
    DYNAMITE_SIZE = 5
    PUMPKIN_COLORS = [
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#fdbf13",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
        "#ff1600",
        "#ff8600",
    ]
    PUMPKIN_SIZE = 7

    _instance = None

    def __new__(cls, *args, **kwargs) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self._canvas: np.ndarray = np.zeros(
            self.CANVAS_SIZE * self.CANVAS_SIZE * 4, dtype=np.uint8
        )
        self._lock = asyncio.Lock()

    async def set_canvas(self, canvas_bytes: bytes) -> None:
        async with self._lock:
            canvas = Image.open(io.BytesIO(canvas_bytes)).convert("RGBA")
            canvas_array = np.array(canvas).flatten()
            self._canvas = canvas_array

    async def update_canvas(
        self,
        pixels_data: Dict[str, Any],
    ) -> None:
        """
        Updates the canvas with new data from the WebSocket connection only.

        Args:
            pixels_data (Dict[str, Any]): Data from the WebSocket connection.
        """
        async with self._lock:
            if pixels_data["channel"] == "event:message":
                await self._paint_squares(self._canvas, pixels_data["data"])
            elif pixels_data["channel"] == "pixel:message":
                await self._paint_pixels(self._canvas, pixels_data["data"])

    async def _paint_squares(
        self, canvas_array, pixels_data: List[Dict[str, Any]]
    ) -> None:
        """
        Paints squares on the canvas based on the given data.

        Args:
            canvas_array: The numpy array representing the canvas to be modified.
            pixels_data (List[Dict[str, Any]]): Data from the WebSocket connection.
        """
        for pixel_data in pixels_data:
            pixel_id: int = pixel_data["pixel"]

            x, y = self._pixel_id_to_xy(pixel_id)

            square_size = getattr(self, f"{pixel_data['type'].upper()}_SIZE")
            x = x - (square_size // 2)
            y = y - (square_size // 2)

            colors = (
                self.PUMPKIN_COLORS
                if pixel_data["type"] == "Pumpkin"
                else [self.DYNAMITE_COLOR] * (self.DYNAMITE_SIZE * self.DYNAMITE_SIZE)
            )

            for i, color in enumerate(colors):
                offset_x = i % square_size
                offset_y = i // square_size

                px = x + offset_x
                py = y + offset_y

                if px < 0 or py < 0 or px >= self.CANVAS_SIZE or py >= self.CANVAS_SIZE:
                    continue

                rgb_color = self._hex_to_rgb(color)

                pixel_index = (px + py * self.CANVAS_SIZE) * 4
                canvas_array[pixel_index] = rgb_color[0]
                canvas_array[pixel_index + 1] = rgb_color[1]
                canvas_array[pixel_index + 2] = rgb_color[2]
                canvas_array[pixel_index + 3] = 255

    async def _paint_pixels(self, canvas_array, pixels_data: Dict[str, Any]) -> None:
        """
        Paints individual pixels on the canvas based on the provided data.

        This function skips pixels with a hex color of "#171F2A" and pixels with an ID greater than the canvas size.
        It converts the hex color to RGB and updates the corresponding pixels in the canvas array.

        Args:
            canvas_array: The numpy array representing the canvas to be modified.
            pixels_data (Dict[str, Any]): A dictionary mapping hex color codes to lists of pixel IDs that should be painted with that color.
        """
        for hex_color, pixels_id in pixels_data.items():
            if hex_color == "#171F2A":
                continue

            rgb_color = self._hex_to_rgb(hex_color)

            for pixel_id in pixels_id:
                if pixel_id > self.CANVAS_SIZE * self.CANVAS_SIZE:
                    continue

                pixel_index = (pixel_id - 1) * 4
                canvas_array[pixel_index] = rgb_color[0]
                canvas_array[pixel_index + 1] = rgb_color[1]
                canvas_array[pixel_index + 2] = rgb_color[2]
                canvas_array[pixel_index + 3] = 255

    async def set_pixel(self, pixel_id: int, hex_color: str) -> None:
        """
        Sets a single pixel on the canvas to the specified color.
        Using only when YOU paint on the canvas, not from the WebSocket data

        Args:
            pixel_id (int): The ID of the pixel to be set.
            hex_color (str): The hex color to be set. Must be a valid hex color code.
        """
        if pixel_id > self.CANVAS_SIZE * self.CANVAS_SIZE:
            return

        async with self._lock:
            rgb_color = self._hex_to_rgb(hex_color)
            pixel_index = (pixel_id - 1) * 4
            self._canvas[pixel_index] = rgb_color[0]
            self._canvas[pixel_index + 1] = rgb_color[1]
            self._canvas[pixel_index + 2] = rgb_color[2]
            self._canvas[pixel_index + 3] = 255

    @property
    def get_canvas(self) -> np.ndarray:
        return self._canvas

    @lru_cache(maxsize=1024)
    def _pixel_id_to_xy(self, pixel_id: int) -> Tuple[int, int]:
        x = (pixel_id - 1) % self.CANVAS_SIZE
        y = (pixel_id - 1) // self.CANVAS_SIZE
        return x, y

    @lru_cache(maxsize=1024)
    def _xy_to_pixel_id(self, x: int, y: int) -> int:
        return y * self.CANVAS_SIZE + x + 1

    @lru_cache(maxsize=256)
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, ...]:
        color_int = int(hex_color.replace("#", ""), 16)

        red = (color_int >> 16) & 255
        green = (color_int >> 8) & 255
        blue = color_int & 255

        return red, green, blue

    @lru_cache(maxsize=256)
    def rgba_to_hex(self, rgba) -> str:
        r, g, b, a = rgba
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        return hex_color
