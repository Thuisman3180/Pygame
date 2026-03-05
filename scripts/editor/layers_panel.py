"""
Layers Panel — shows the layer stack with visibility toggles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .theme import COLORS, HEADER_HEIGHT, PANEL_PADDING, get_font
from .ui_panel import Panel

if TYPE_CHECKING:
    from .level_data import LevelData

ROW_HEIGHT = 28
EYE_SIZE = 16


class LayersPanel(Panel):
    """Displays the layer stack and lets the user toggle visibility / select."""

    def __init__(self, rect: pygame.Rect, level_data: "LevelData") -> None:
        super().__init__(rect, title="Layers", scrollable=True)
        self.level_data = level_data
        self.active_layer: str = "Terrain"

    # ── event handling ──────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> bool:
        if super().handle_event(event):
            return True
        if not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.contains(event.pos):
                return False
            lx, ly = self.local_mouse(event.pos)
            cr = self.content_rect
            row_y = ly - cr.y + self._scroll_y
            if row_y < 0:
                return False
            idx = int(row_y // ROW_HEIGHT)
            layer_names = list(self.level_data.layers.keys())
            if 0 <= idx < len(layer_names):
                name = layer_names[idx]
                # Eye icon region (first 24px)
                if lx < cr.x + 24:
                    self.level_data.layers[name]["visible"] = not self.level_data.layers[name]["visible"]
                else:
                    self.active_layer = name
                return True
        return False

    # ── drawing ─────────────────────────────────────────────────────
    def draw_content(self, surface: pygame.Surface) -> None:
        cr = self.content_rect
        clip = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
        surface.set_clip(clip)

        font = get_font(13)
        y = cr.y - self._scroll_y

        for name, layer in self.level_data.layers.items():
            if y + ROW_HEIGHT > cr.y and y < cr.y + cr.h:
                row_rect = pygame.Rect(cr.x, y, cr.w, ROW_HEIGHT)

                # Highlight active layer
                if name == self.active_layer:
                    pygame.draw.rect(surface, COLORS["selection"], row_rect, border_radius=3)

                # Eye icon
                eye_x = cr.x + 4
                eye_y = y + (ROW_HEIGHT - EYE_SIZE) // 2
                eye_rect = pygame.Rect(eye_x, eye_y, EYE_SIZE, EYE_SIZE)
                color = COLORS["eye_on"] if layer["visible"] else COLORS["eye_off"]
                pygame.draw.circle(
                    surface,
                    color,
                    eye_rect.center,
                    EYE_SIZE // 2 - 1,
                )
                # Draw a small "pupil" for visible
                if layer["visible"]:
                    pygame.draw.circle(surface, COLORS["panel"], eye_rect.center, 3)

                # Layer name
                text_color = (255, 255, 255) if name == self.active_layer else COLORS["text"]
                label = font.render(name, True, text_color)
                surface.blit(label, (cr.x + 28, y + (ROW_HEIGHT - label.get_height()) // 2))

                # Tile count
                count = len(layer["tiles"]) + len(layer["offgrid"])
                count_label = get_font(11).render(str(count), True, COLORS["text_dim"])
                surface.blit(count_label, (cr.x + cr.w - count_label.get_width() - 4,
                                           y + (ROW_HEIGHT - count_label.get_height()) // 2))

                # Row separator
                pygame.draw.line(
                    surface, COLORS["panel_border"],
                    (cr.x, y + ROW_HEIGHT - 1), (cr.x + cr.w, y + ROW_HEIGHT - 1)
                )

            y += ROW_HEIGHT

        self._content_height = len(self.level_data.layers) * ROW_HEIGHT
        surface.set_clip(None)
