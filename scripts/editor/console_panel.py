"""
Console Panel — scrollable log / raw data text area.
"""

from __future__ import annotations

import time

import pygame

from .theme import COLORS, HEADER_HEIGHT, PANEL_PADDING, get_font
from .ui_panel import Panel

LINE_HEIGHT = 16
MAX_LINES = 200


class ConsolePanel(Panel):
    """Simple text console for log messages and raw data display."""

    def __init__(self, rect: pygame.Rect) -> None:
        super().__init__(rect, title="Console", scrollable=True)
        self._lines: list[str] = []

    def log(self, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        for line in text.split("\n"):
            self._lines.append(f"[{stamp}] {line}")
        # Trim
        if len(self._lines) > MAX_LINES:
            self._lines = self._lines[-MAX_LINES:]
        # Auto-scroll to bottom
        self._content_height = len(self._lines) * LINE_HEIGHT
        self._scroll_y = self._max_scroll()

    def clear(self) -> None:
        self._lines.clear()
        self._scroll_y = 0
        self._content_height = 0

    # ── drawing ─────────────────────────────────────────────────────
    def draw_content(self, surface: pygame.Surface) -> None:
        cr = self.content_rect
        clip = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
        surface.set_clip(clip)

        # Dark background for console area
        pygame.draw.rect(surface, (30, 30, 30), clip)

        font = get_font(11)
        y = cr.y - self._scroll_y

        for line in self._lines:
            if y + LINE_HEIGHT > cr.y and y < cr.y + cr.h:
                label = font.render(line, True, (200, 210, 200))
                surface.blit(label, (cr.x + 4, y))
            y += LINE_HEIGHT

        self._content_height = len(self._lines) * LINE_HEIGHT
        surface.set_clip(None)
