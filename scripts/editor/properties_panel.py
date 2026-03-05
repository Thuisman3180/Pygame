"""
Properties Panel — read-only display of the selected object's metadata.
"""

from __future__ import annotations

import json

import pygame

from .theme import COLORS, HEADER_HEIGHT, PANEL_PADDING, get_font
from .ui_panel import Panel

ROW_H = 22


class PropertiesPanel(Panel):
    """Shows metadata for the currently selected canvas object."""

    def __init__(self, rect: pygame.Rect) -> None:
        super().__init__(rect, title="Properties")
        self._fields: list[tuple[str, str]] = []

    def set_selection(
        self,
        tile_data: dict | None,
        layer_name: str = "",
    ) -> None:
        """Update displayed properties from *tile_data*."""
        self._fields.clear()
        if tile_data is None:
            return
        self._fields.append(("Layer", layer_name))
        self._fields.append(("Type", tile_data.get("type", "?")))
        self._fields.append(("Variant", str(tile_data.get("variant", "?"))))
        pos = tile_data.get("pos", [])
        self._fields.append(("Position", f"{pos[0]}, {pos[1]}" if len(pos) >= 2 else "?"))

    def clear_selection(self) -> None:
        self._fields.clear()

    # ── drawing ─────────────────────────────────────────────────────
    def draw_content(self, surface: pygame.Surface) -> None:
        cr = self.content_rect
        font_key = get_font(12, bold=True)
        font_val = get_font(12)
        y = cr.y + 4

        if not self._fields:
            hint = get_font(11).render("No selection", True, COLORS["text_dim"])
            surface.blit(hint, (cr.x + 4, y))
            return

        for key, val in self._fields:
            label_k = font_key.render(f"{key}:", True, COLORS["text"])
            label_v = font_val.render(val, True, COLORS["text_dim"])
            surface.blit(label_k, (cr.x + 4, y))
            surface.blit(label_v, (cr.x + 80, y))
            y += ROW_H
