"""
Assets Panel — scrollable grid of tiles with category tabs.
"""

from __future__ import annotations

import pygame

from .theme import (
    COLORS,
    HEADER_HEIGHT,
    PANEL_PADDING,
    TAB_HEIGHT,
    TILE_THUMB_PAD,
    TILE_THUMB_SIZE,
    get_font,
)
from .ui_panel import Panel


class AssetsPanel(Panel):
    """Tile/sprite picker with category tabs and a scrollable thumbnail grid."""

    def __init__(self, rect: pygame.Rect, assets: dict[str, list[pygame.Surface]]) -> None:
        super().__init__(rect, title="Assets / Tileset", scrollable=True)
        self.assets = assets
        self.categories: list[str] = list(assets.keys())
        self.active_category: int = 0
        self.selected_variant: int = 0

    @property
    def current_type(self) -> str:
        return self.categories[self.active_category]

    # ── helpers ─────────────────────────────────────────────────────
    def _tab_rects(self) -> list[pygame.Rect]:
        """Return rects for each category tab."""
        cr = self.content_rect
        tab_w = max(40, cr.w // max(1, len(self.categories)))
        rects = []
        for i in range(len(self.categories)):
            rects.append(pygame.Rect(cr.x + i * tab_w, cr.y, tab_w, TAB_HEIGHT))
        return rects

    def _grid_origin(self) -> tuple[int, int]:
        cr = self.content_rect
        return (cr.x, cr.y + TAB_HEIGHT + 4)

    def _cols(self) -> int:
        cr = self.content_rect
        return max(1, cr.w // (TILE_THUMB_SIZE + TILE_THUMB_PAD))

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

            # Check tabs
            for i, tr in enumerate(self._tab_rects()):
                if tr.collidepoint(lx, ly):
                    self.active_category = i
                    self.selected_variant = 0
                    self._scroll_y = 0
                    return True

            # Check grid cells
            gx, gy = self._grid_origin()
            cols = self._cols()
            variants = self.assets[self.current_type]
            grid_y = ly - gy + self._scroll_y

            if grid_y >= 0:
                col = (lx - gx) // (TILE_THUMB_SIZE + TILE_THUMB_PAD)
                row = grid_y // (TILE_THUMB_SIZE + TILE_THUMB_PAD)
                idx = int(row * cols + col)
                if 0 <= idx < len(variants):
                    self.selected_variant = idx
                    return True

        return False

    # ── drawing ─────────────────────────────────────────────────────
    def draw_content(self, surface: pygame.Surface) -> None:
        cr = self.content_rect

        # ── Tabs ──
        font = get_font(11)
        for i, tr in enumerate(self._tab_rects()):
            color = COLORS["tab_active"] if i == self.active_category else COLORS["tab_inactive"]
            pygame.draw.rect(surface, color, tr)
            pygame.draw.rect(surface, COLORS["panel_border"], tr, 1)
            # Truncate label to fit
            name = self.categories[i]
            label = font.render(name[:6], True, COLORS["text"])
            surface.blit(
                label,
                (tr.x + (tr.w - label.get_width()) // 2,
                 tr.y + (tr.h - label.get_height()) // 2),
            )

        # ── Thumbnail grid ──
        gx, gy = self._grid_origin()
        cols = self._cols()
        variants = self.assets[self.current_type]

        # Clip to content area below tabs
        clip = pygame.Rect(cr.x, gy, cr.w, cr.y + cr.h - gy)
        surface.set_clip(clip)

        cell = TILE_THUMB_SIZE + TILE_THUMB_PAD
        for idx, img in enumerate(variants):
            col = idx % cols
            row = idx // cols
            x = gx + col * cell
            y = gy + row * cell - self._scroll_y
            if y + TILE_THUMB_SIZE < gy or y > gy + clip.h:
                continue

            # Background cell
            cell_rect = pygame.Rect(x, y, TILE_THUMB_SIZE, TILE_THUMB_SIZE)
            pygame.draw.rect(surface, COLORS["canvas_bg"], cell_rect)

            # Scale tile image to fit thumbnail
            scaled = pygame.transform.scale(img, (TILE_THUMB_SIZE, TILE_THUMB_SIZE))
            surface.blit(scaled, (x, y))

            # Selection highlight
            if idx == self.selected_variant:
                pygame.draw.rect(surface, COLORS["accent"], cell_rect, 2)

        rows = (len(variants) + cols - 1) // cols if cols > 0 else 0
        self._content_height = TAB_HEIGHT + 4 + rows * cell

        surface.set_clip(None)
