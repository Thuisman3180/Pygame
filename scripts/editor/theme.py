"""
Design token constants for the classic light-gray 'Software' theme.
"""

import pygame

# ── Colour Palette ──────────────────────────────────────────────────────────
COLORS = {
    "bg":            (224, 224, 224),   # Window background
    "panel":         (212, 212, 212),   # Panel fill
    "panel_header":  (192, 192, 192),   # Panel title-bar
    "panel_border":  (160, 160, 160),   # Panel outline
    "text":          (26, 26, 26),      # Primary text
    "text_dim":      (100, 100, 100),   # Secondary / muted text
    "accent":        (61, 126, 199),    # Primary accent
    "selection":     (90, 159, 212),    # Selected item highlight
    "selection_bg":  (61, 126, 199, 60),# Selection overlay (with alpha)
    "grid":          (60, 60, 60),      # Canvas grid lines
    "canvas_bg":     (42, 42, 42),      # Canvas dark background
    "button":        (200, 200, 200),   # Button normal
    "button_hover":  (180, 200, 225),   # Button hover
    "button_active": (140, 175, 210),   # Button pressed
    "scrollbar":     (170, 170, 170),   # Scrollbar track
    "scrollbar_thumb":(130, 130, 130),  # Scrollbar thumb
    "eye_on":        (61, 126, 199),    # Eye icon visible
    "eye_off":       (160, 160, 160),   # Eye icon hidden
    "tab_active":    (224, 224, 224),   # Active tab bg
    "tab_inactive":  (192, 192, 192),   # Inactive tab bg
    "separator":     (180, 180, 180),   # Toolbar separator
    "highlight":     (255, 200, 60),    # Selection rect on canvas
}

# ── Layout Constants ────────────────────────────────────────────────────────
TOOLBAR_HEIGHT   = 36
LEFT_SIDEBAR_W   = 240
RIGHT_SIDEBAR_W  = 280
PANEL_PADDING    = 6
SCROLLBAR_WIDTH  = 12
HEADER_HEIGHT    = 24
TAB_HEIGHT       = 26
BUTTON_HEIGHT    = 28
BUTTON_PADDING   = 4
TILE_THUMB_SIZE  = 32
TILE_THUMB_PAD   = 4

# ── Font Helper ─────────────────────────────────────────────────────────────
_font_cache: dict[tuple[int, bool], pygame.font.Font] = {}


def get_font(size: int = 14, bold: bool = False) -> pygame.font.Font:
    """Return a cached system font (Segoe UI with fallbacks)."""
    key = (size, bold)
    if key not in _font_cache:
        for name in ("segoeui", "arial", "helvetica", "sans"):
            font = pygame.font.SysFont(name, size, bold=bold)
            if font:
                _font_cache[key] = font
                break
        else:
            _font_cache[key] = pygame.font.SysFont(None, size, bold=bold)
    return _font_cache[key]
