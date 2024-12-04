import io
import json
from functools import lru_cache
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image
from typing_extensions import Self

from bot.utils.logger import dev_logger, logger


class DynamicCanvasRenderer:
    MAX_ATTEMPTS = 3
    RETRY_DELAY = 5
    CANVAS_SIZE = 1024
    DYNAMITE_SIZE = 5
    DYNAMITE_COLORS = ["#171F2A"] * (DYNAMITE_SIZE * DYNAMITE_SIZE)
    PUMPKIN_SIZE = 7
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

    _instance = None

    def __new__(cls, *args, **kwargs) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self._canvas: np.ndarray

    def set_canvas(self, canvas_bytes: bytes) -> None:
        canvas = Image.open(io.BytesIO(canvas_bytes)).convert("RGBA")
        canvas_array = np.array(canvas).flatten()
        self._canvas = canvas_array

    def update_canvas(self, pixels_data: Dict[str, Any]) -> None:
        """
        Update the canvas with the given pixels data.

        Args:
            pixels_data (Dict[str, Any]): Data from the WebSocket connection.
        """
        channel = pixels_data["channel"]

        if channel == "event:message":
            self._process_event_message(pixels_data["data"])
        elif channel == "pixel:message":
            self.handle_pixel_message(pixels_data["data"])

    def _process_event_message(self, events: List[Dict[str, Any]]) -> None:
        for event in events:
            event_type = event["type"]
            if event_type in ["Dynamite", "Pumpkin"]:
                self._paint_square(event)
            elif event_type == "Pixanos":
                logger.info("DynamicCanvasRenderer | Pixanos event received")
                dev_logger.info(f"Received Pixanos event: {event}")
                self._process_pixanos_event(event["data"])
            else:
                logger.info(f"DynamicCanvasRenderer | Unknown event type: {event_type}")
                dev_logger.info(f"Unknown event type: {event_type} | Event: {event}")

    def _process_pixanos_event(self, pixanos_data_json: str) -> None:
        """
        Processes Pixanos event data.

        Args:
            pixanos_data (Dict[str, Any]): Data from the WebSocket connection.
        """
        pixanos_data = json.loads(pixanos_data_json)
        info = pixanos_data["info"]
        self._pixanos_repaint(info["seed"], info["percentage"], info["color"])

    def handle_pixel_message(self, pixel_data: Dict[str, List[int]]) -> None:
        """
        Handles pixel messages from the WebSocket connection.

        Args:
            pixel_data (Dict[str, Any]): Data from the WebSocket connection.
        """
        self._paint_pixels(pixel_data)

    def _paint_square(self, event_data: Dict[str, str]) -> None:
        """
        Paints square on the canvas based on the given data.

        Args:
            event_data (Dict[str, str]): Data from the WebSocket connection.
        """
        event_pixel_data_string = event_data.get("data")
        if not event_pixel_data_string:
            raise ValueError("Can't retrieve pixel data")

        event_pixel_data = json.loads(event_pixel_data_string)

        if "info" not in event_pixel_data or "pixelId" not in event_pixel_data["info"]:
            raise ValueError("Missing 'info' or 'pixelId' in event pixel data")

        pixel_id: int = event_pixel_data["info"]["pixelId"]

        x, y = self._pixel_id_to_xy(pixel_id)

        square_size = getattr(self, f"{event_data['type'].upper()}_SIZE")
        x = x - (square_size // 2)
        y = y - (square_size // 2)

        colors = (
            self.PUMPKIN_COLORS
            if event_data["type"] == "Pumpkin"
            else self.DYNAMITE_COLORS
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
            self._canvas[pixel_index] = rgb_color[0]
            self._canvas[pixel_index + 1] = rgb_color[1]
            self._canvas[pixel_index + 2] = rgb_color[2]
            self._canvas[pixel_index + 3] = 255

    def _paint_pixels(self, pixels_data: Dict[str, List[int]]) -> None:
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

            for pixel_id in pixels_id:
                self.paint_pixel(pixel_id, hex_color)

    def paint_pixel(self, pixel_id: int, hex_color: str) -> None:
        """
        Paints a single pixel on the canvas based on the provided pixel ID and hex color.

        Args:
            pixel_id (int): The ID of the pixel to be set.
            hex_color (str): The hex color to be set. Must be a valid hex color code.
        """
        if pixel_id > self.CANVAS_SIZE * self.CANVAS_SIZE:
            return

        rgb_color = self._hex_to_rgb(hex_color)
        pixel_index = (pixel_id - 1) * 4
        self._canvas[pixel_index] = rgb_color[0]
        self._canvas[pixel_index + 1] = rgb_color[1]
        self._canvas[pixel_index + 2] = rgb_color[2]
        self._canvas[pixel_index + 3] = 255

    def _pixanos_repaint(self, seed: int, percentage: float, hex_color: str):
        """
        Repaints a specified percentage of pixels on the canvas using a given color.

        This function selects a random subset of pixels on the canvas determined by
        the given percentage and repaints them with the specified color. The pixel
        selection is based on a seeded random generator to ensure reproducibility.

        Args:
            seed (int): The seed value for the random number generator, ensuring
                        consistent pixel selection across different runs.
            canvas_width (int): The width of the canvas, which is assumed to be square.
            percentage (int): The percentage of total pixels to be repainted.
            color (str): The hex color code to be used for repainting the selected pixels.
        """

        def create_random_generator(seed_value):
            multiplier = 1664525
            increment = 1013904223
            modulus = 4294967296
            state = seed_value & 0xFFFFFFFF

            def random():
                nonlocal state
                state = (multiplier * state + increment) % modulus
                return state / modulus

            return random

        total_pixels = self.CANVAS_SIZE * self.CANVAS_SIZE
        pixels_to_repaint = int(total_pixels * percentage)

        random_generator = create_random_generator(seed)
        selected_pixels = [i + 1 for i in range(pixels_to_repaint)]

        for current_pixel in range(pixels_to_repaint + 1, total_pixels + 1):
            random_index = int(random_generator() * current_pixel) + 1
            if random_index <= pixels_to_repaint:
                selected_pixels[random_index - 1] = current_pixel

        for pixel_id in selected_pixels:
            self.paint_pixel(pixel_id, hex_color)

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
    def rgba_to_hex(self, rgba: Tuple[int, int, int, int]) -> str:
        r, g, b, a = rgba
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        return hex_color
