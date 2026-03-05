"""
Toolbar — horizontal button bar at the top of the editor window.
"""

from __future__ import annotations

from typing import Callable

import pygame

from .theme import (
    BUTTON_HEIGHT,
    BUTTON_PADDING,
    COLORS,
    TOOLBAR_HEIGHT,
    get_font,
)
from .ui_panel import Panel


class _Button:
    """Simple toolbar button with text label."""

    def __init__(
        self,
        text: str,
        callback: Callable[[], None],
        toggle: bool = False,
        shortcut: str = "",
    ) -> None:
        self.text = text
        self.callback = callback
        self.toggle = toggle
        self.active = False
        self.shortcut = shortcut
        self.rect = pygame.Rect(0, 0, 0, 0)
        self._hover = False

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        self.rect = rect
        if self.toggle and self.active:
            color = COLORS["button_active"]
        elif self._hover:
            color = COLORS["button_hover"]
        else:
            color = COLORS["button"]

        pygame.draw.rect(surface, color, rect, border_radius=3)
        pygame.draw.rect(surface, COLORS["panel_border"], rect, 1, border_radius=3)

        font = get_font(12)
        label = font.render(self.text, True, COLORS["text"])
        surface.blit(
            label,
            (rect.x + (rect.w - label.get_width()) // 2,
             rect.y + (rect.h - label.get_height()) // 2),
        )


class Toolbar(Panel):
    """Horizontal toolbar at the top of the editor."""

    def __init__(self, rect: pygame.Rect) -> None:
        super().__init__(rect, title="")
        self.buttons: list[_Button] = []
        self._separators: list[int] = []  # indices after which to draw a separator

    def add_button(
        self,
        text: str,
        callback: Callable[[], None],
        toggle: bool = False,
        shortcut: str = "",
    ) -> _Button:
        btn = _Button(text, callback, toggle, shortcut)
        self.buttons.append(btn)
        return btn

    def add_separator(self) -> None:
        if self.buttons:
            self._separators.append(len(self.buttons) - 1)

    # ── event handling ──────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if event.type == pygame.MOUSEMOTION:
            gx, gy = event.pos
            for btn in self.buttons:
                btn._hover = btn.rect.collidepoint(gx, gy)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.contains(event.pos):
                return False
            for btn in self.buttons:
                if btn.rect.collidepoint(event.pos):
                    if btn.toggle:
                        btn.active = not btn.active
                    btn.callback()
                    return True

        return False

    # ── drawing ─────────────────────────────────────────────────────
    def draw(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return
        # Background
        pygame.draw.rect(screen, COLORS["panel"], self.rect)
        pygame.draw.line(
            screen,
            COLORS["panel_border"],
            (self.rect.x, self.rect.bottom - 1),
            (self.rect.right, self.rect.bottom - 1),
        )

        # Lay out buttons
        x = self.rect.x + BUTTON_PADDING
        y = self.rect.y + (TOOLBAR_HEIGHT - BUTTON_HEIGHT) // 2

        font = get_font(12)
        for i, btn in enumerate(self.buttons):
            text_w = font.size(btn.text)[0]
            btn_w = text_w + 16
            btn_rect = pygame.Rect(x, y, btn_w, BUTTON_HEIGHT)
            btn.draw(screen, btn_rect)
            x += btn_w + BUTTON_PADDING

            # Separator
            if i in self._separators:
                sep_x = x + 2
                pygame.draw.line(
                    screen, COLORS["separator"],
                    (sep_x, y + 2), (sep_x, y + BUTTON_HEIGHT - 2)
                )
                x += 8
