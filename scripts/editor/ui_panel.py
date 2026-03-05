"""
Base Panel class — provides a positioned, titled, bordered rectangle
with optional vertical scrollbar for content overflow.
"""

from __future__ import annotations

import pygame

from .theme import (
    COLORS,
    HEADER_HEIGHT,
    PANEL_PADDING,
    SCROLLBAR_WIDTH,
    get_font,
)


class Panel:
    """Base class for all editor panels."""

    def __init__(
        self,
        rect: pygame.Rect,
        title: str = "",
        scrollable: bool = False,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.title = title
        self.visible = True
        self.scrollable = scrollable
        self._scroll_y = 0
        self._content_height = 0
        self._dragging_scroll = False
        self.surface = pygame.Surface((max(1, self.rect.w), max(1, self.rect.h)), pygame.SRCALPHA)

    # ── geometry helpers ────────────────────────────────────────────────
    @property
    def content_rect(self) -> pygame.Rect:
        """Area below the title bar, inside padding, minus scrollbar."""
        y = HEADER_HEIGHT if self.title else 0
        w = self.rect.w - PANEL_PADDING * 2
        if self.scrollable:
            w -= SCROLLBAR_WIDTH
        h = self.rect.h - y - PANEL_PADDING
        return pygame.Rect(PANEL_PADDING, y, max(1, w), max(1, h))

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)
        self.surface = pygame.Surface((max(1, self.rect.w), max(1, self.rect.h)), pygame.SRCALPHA)

    def local_mouse(self, global_pos: tuple[int, int]) -> tuple[int, int]:
        """Convert global mouse pos to coordinates relative to the panel."""
        return (global_pos[0] - self.rect.x, global_pos[1] - self.rect.y)

    def contains(self, global_pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(global_pos)

    # ── scrollbar ───────────────────────────────────────────────────────
    def _max_scroll(self) -> int:
        overflow = self._content_height - self.content_rect.h
        return max(0, overflow)

    def _scrollbar_rect(self) -> pygame.Rect:
        cr = self.content_rect
        return pygame.Rect(
            self.rect.w - SCROLLBAR_WIDTH - 2,
            cr.y,
            SCROLLBAR_WIDTH,
            cr.h,
        )

    def _thumb_rect(self) -> pygame.Rect | None:
        if self._content_height <= self.content_rect.h:
            return None
        sb = self._scrollbar_rect()
        ratio = self.content_rect.h / self._content_height
        thumb_h = max(20, int(sb.h * ratio))
        max_s = self._max_scroll()
        if max_s == 0:
            thumb_y = sb.y
        else:
            thumb_y = sb.y + int((sb.h - thumb_h) * (self._scroll_y / max_s))
        return pygame.Rect(sb.x, thumb_y, sb.w, thumb_h)

    # ── event handling ──────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Process an event. Returns True if the event was consumed.
        Override in subclasses — call super first for scrollbar logic.
        """
        if not self.visible:
            return False

        if self.scrollable:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.contains(event.pos):
                    lx, ly = self.local_mouse(event.pos)
                    thumb = self._thumb_rect()
                    if thumb and thumb.collidepoint(lx, ly):
                        self._dragging_scroll = True
                        return True

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging_scroll = False

            if event.type == pygame.MOUSEMOTION and self._dragging_scroll:
                sb = self._scrollbar_rect()
                _, rely = self.local_mouse(event.pos)
                ratio = max(0, min(1, (rely - sb.y) / max(1, sb.h)))
                self._scroll_y = int(ratio * self._max_scroll())
                return True

            if event.type == pygame.MOUSEWHEEL and self.contains(pygame.mouse.get_pos()):
                self._scroll_y -= event.y * 24
                self._scroll_y = max(0, min(self._scroll_y, self._max_scroll()))
                return True

        return False

    # ── drawing ─────────────────────────────────────────────────────────
    def draw(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return

        self.surface.fill(COLORS["panel"])

        # Title bar
        if self.title:
            header = pygame.Rect(0, 0, self.rect.w, HEADER_HEIGHT)
            pygame.draw.rect(self.surface, COLORS["panel_header"], header)
            pygame.draw.line(
                self.surface,
                COLORS["panel_border"],
                (0, HEADER_HEIGHT - 1),
                (self.rect.w, HEADER_HEIGHT - 1),
            )
            label = get_font(12, bold=True).render(self.title, True, COLORS["text"])
            self.surface.blit(label, (PANEL_PADDING, (HEADER_HEIGHT - label.get_height()) // 2))

        # Subclass content
        self.draw_content(self.surface)

        # Scrollbar
        if self.scrollable:
            sb = self._scrollbar_rect()
            pygame.draw.rect(self.surface, COLORS["scrollbar"], sb, border_radius=3)
            thumb = self._thumb_rect()
            if thumb:
                pygame.draw.rect(self.surface, COLORS["scrollbar_thumb"], thumb, border_radius=3)

        # Border
        pygame.draw.rect(self.surface, COLORS["panel_border"], (0, 0, self.rect.w, self.rect.h), 1)

        screen.blit(self.surface, self.rect.topleft)

    def draw_content(self, surface: pygame.Surface) -> None:
        """Override in subclasses to draw panel body."""
        pass
