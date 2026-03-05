"""
Canvas — the central scrollable, zoomable, grid-based workspace.
Handles multi-layer rendering, tile placement, selection, and drag-to-move.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .theme import COLORS, TILE_THUMB_SIZE, get_font
from .ui_panel import Panel

if TYPE_CHECKING:
    from .level_data import LevelData
    from .history import History


class Canvas(Panel):
    """Central editing workspace for the level editor."""

    def __init__(
        self,
        rect: pygame.Rect,
        level_data: "LevelData",
        history: "History",
        assets: dict[str, list[pygame.Surface]],
    ) -> None:
        super().__init__(rect, title="")
        self.level_data = level_data
        self.history = history
        self.assets = assets

        # Camera / viewport
        self.scroll = [0.0, 0.0]
        self.zoom = 2.0  # render scale
        self.zoom_min = 0.5
        self.zoom_max = 6.0
        self.zoom_step = 0.25

        # Movement
        self.movement = [False, False, False, False]  # left, right, up, down
        self._mid_drag = False
        self._mid_drag_start = (0, 0)
        self._mid_scroll_start = [0.0, 0.0]

        # Grid
        self.grid_snap = True
        self.grid_size = 16  # tile_size from level_data

        # Active brush (set by editor from assets panel)
        self.brush_type: str = ""
        self.brush_variant: int = 0
        self.active_layer: str = "Terrain"

        # Clicking state
        self._clicking = False
        self._right_clicking = False

        # Selection
        self.selected_tile: dict | None = None
        self.selected_layer: str = ""
        self.selected_offgrid_idx: int | None = None
        self._dragging_tile = False
        self._drag_start_pos: tuple[int, int] | None = None

        # Callbacks (set by editor)
        self.on_select: object = None  # Callable or None
        self.on_log: object = None     # Callable or None

    # ── coordinate conversion ───────────────────────────────────────
    def _screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        """Convert screen (panel-local) coords to world pixel coords."""
        wx = sx / self.zoom + self.scroll[0]
        wy = sy / self.zoom + self.scroll[1]
        return (wx, wy)

    def _world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert world pixel coords to panel-local screen coords."""
        sx = (wx - self.scroll[0]) * self.zoom
        sy = (wy - self.scroll[1]) * self.zoom
        return (sx, sy)

    def _screen_to_tile(self, sx: int, sy: int) -> tuple[int, int]:
        """Convert screen coords to tile grid coords."""
        wx, wy = self._screen_to_world(sx, sy)
        ts = self.level_data.tile_size
        return (int(wx // ts), int(wy // ts))

    # ── update (called each frame) ──────────────────────────────────
    def update(self) -> None:
        speed = 3.0 / self.zoom * 2
        self.scroll[0] += (self.movement[1] - self.movement[0]) * speed
        self.scroll[1] += (self.movement[3] - self.movement[2]) * speed

    # ── event handling ──────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        # ── Mouse button down ──
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.contains(event.pos):
                return False
            lx, ly = self.local_mouse(event.pos)

            if event.button == 1:
                self._clicking = True
                tile_pos = self._screen_to_tile(lx, ly)
                world_pos = self._screen_to_world(lx, ly)

                # Try to select existing tile
                hit = self.level_data.get_tile_at(
                    tile_pos if self.grid_snap else world_pos,
                    on_grid=self.grid_snap,
                    assets=self.assets,
                )
                if hit:
                    layer_name, tile_data, offgrid_idx = hit
                    self.selected_tile = tile_data
                    self.selected_layer = layer_name
                    self.selected_offgrid_idx = offgrid_idx
                    self._dragging_tile = True
                    self._drag_start_pos = tile_pos if self.grid_snap else None
                    if callable(self.on_select):
                        self.on_select(tile_data, layer_name)
                else:
                    # Place tile
                    self._place_current_brush(tile_pos, world_pos)
                    self.selected_tile = None
                    self.selected_layer = ""
                    if callable(self.on_select):
                        self.on_select(None, "")

                return True

            if event.button == 3:
                self._right_clicking = True
                lx, ly = self.local_mouse(event.pos)
                tile_pos = self._screen_to_tile(lx, ly)
                self._remove_at(tile_pos)
                return True

            if event.button == 2:  # middle click → pan
                self._mid_drag = True
                self._mid_drag_start = event.pos
                self._mid_scroll_start = list(self.scroll)
                return True

            # Zoom
            if event.button == 4:
                self.zoom = min(self.zoom_max, self.zoom + self.zoom_step)
                return True
            if event.button == 5:
                self.zoom = max(self.zoom_min, self.zoom - self.zoom_step)
                return True

        # ── Mouse button up ──
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self._dragging_tile and self._drag_start_pos and self.selected_tile:
                    lx, ly = self.local_mouse(event.pos)
                    new_tile_pos = self._screen_to_tile(lx, ly)
                    if new_tile_pos != self._drag_start_pos:
                        action = self.level_data.move_tile(
                            self.selected_layer,
                            self._drag_start_pos,
                            new_tile_pos,
                            on_grid=True,
                        )
                        if action:
                            self.history.push(action)
                            if callable(self.on_log):
                                self.on_log(action.description)
                self._clicking = False
                self._dragging_tile = False
                self._drag_start_pos = None
            if event.button == 3:
                self._right_clicking = False
            if event.button == 2:
                self._mid_drag = False

        # ── Mouse motion ──
        if event.type == pygame.MOUSEMOTION:
            if self._mid_drag:
                dx = event.pos[0] - self._mid_drag_start[0]
                dy = event.pos[1] - self._mid_drag_start[1]
                self.scroll[0] = self._mid_scroll_start[0] - dx / self.zoom
                self.scroll[1] = self._mid_scroll_start[1] - dy / self.zoom
                return True

            # Continuous placement while dragging with left button
            if self._clicking and not self._dragging_tile and self.contains(event.pos):
                lx, ly = self.local_mouse(event.pos)
                tile_pos = self._screen_to_tile(lx, ly)
                world_pos = self._screen_to_world(lx, ly)
                if self.grid_snap:
                    self._place_current_brush(tile_pos, world_pos)

            # Continuous removal while dragging with right button
            if self._right_clicking and self.contains(event.pos):
                lx, ly = self.local_mouse(event.pos)
                tile_pos = self._screen_to_tile(lx, ly)
                self._remove_at(tile_pos)

        # ── Mouse wheel (for zoom when over canvas) ──
        if event.type == pygame.MOUSEWHEEL:
            if self.contains(pygame.mouse.get_pos()):
                if event.y > 0:
                    self.zoom = min(self.zoom_max, self.zoom + self.zoom_step)
                elif event.y < 0:
                    self.zoom = max(self.zoom_min, self.zoom - self.zoom_step)
                return True

        # ── Keyboard ──
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                self.movement[0] = True
            if event.key == pygame.K_d:
                self.movement[1] = True
            if event.key == pygame.K_w:
                self.movement[2] = True
            if event.key == pygame.K_s and not (event.mod & pygame.KMOD_CTRL):
                self.movement[3] = True

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                self.movement[0] = False
            if event.key == pygame.K_d:
                self.movement[1] = False
            if event.key == pygame.K_w:
                self.movement[2] = False
            if event.key == pygame.K_s:
                self.movement[3] = False

        return False

    # ── tile operations ─────────────────────────────────────────────
    def _place_current_brush(
        self, tile_pos: tuple[int, int], world_pos: tuple[float, float]
    ) -> None:
        if not self.brush_type:
            return
        if self.grid_snap:
            # Don't re-place if tile already there with same brush
            key = f"{tile_pos[0]};{tile_pos[1]}"
            existing = self.level_data.layers[self.active_layer]["tiles"].get(key)
            if existing and existing["type"] == self.brush_type and existing["variant"] == self.brush_variant:
                return
            action = self.level_data.place_tile(
                self.active_layer, self.brush_type, self.brush_variant,
                tile_pos, on_grid=True,
            )
        else:
            action = self.level_data.place_tile(
                self.active_layer, self.brush_type, self.brush_variant,
                (world_pos[0], world_pos[1]), on_grid=False,
            )
        self.history.push(action)

    def _remove_at(self, tile_pos: tuple[int, int]) -> None:
        # Try to remove from active layer first, then search all layers
        for layer_name in [self.active_layer] + [n for n in self.level_data.layers if n != self.active_layer]:
            action = self.level_data.remove_tile(layer_name, tile_pos, on_grid=True)
            if action:
                self.history.push(action)
                if callable(self.on_log):
                    self.on_log(action.description)
                return

    # ── drawing ─────────────────────────────────────────────────────
    def draw(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return

        # Clip to canvas rect
        screen.set_clip(self.rect)

        # Background
        pygame.draw.rect(screen, COLORS["canvas_bg"], self.rect)

        ts = self.level_data.tile_size
        z = self.zoom

        # ── Grid lines ──
        self._draw_grid(screen, ts, z)

        # ── Render layers bottom → top ──
        for layer_name, layer_data in self.level_data.layers.items():
            if not layer_data["visible"]:
                continue

            # On-grid tiles (only those visible in viewport)
            view_left = self.scroll[0]
            view_top = self.scroll[1]
            view_right = view_left + self.rect.w / z
            view_bottom = view_top + self.rect.h / z

            start_x = int(view_left // ts) - 1
            end_x = int(view_right // ts) + 2
            start_y = int(view_top // ts) - 1
            end_y = int(view_bottom // ts) + 2

            for x in range(start_x, end_x):
                for y in range(start_y, end_y):
                    key = f"{x};{y}"
                    if key in layer_data["tiles"]:
                        tile = layer_data["tiles"][key]
                        if tile["type"] in self.assets:
                            imgs = self.assets[tile["type"]]
                            variant = tile["variant"]
                            if 0 <= variant < len(imgs):
                                img = imgs[variant]
                                sx, sy = self._world_to_screen(
                                    x * ts, y * ts
                                )
                                sx += self.rect.x
                                sy += self.rect.y
                                scaled = pygame.transform.scale(
                                    img,
                                    (max(1, int(img.get_width() * z)),
                                     max(1, int(img.get_height() * z))),
                                )
                                screen.blit(scaled, (sx, sy))

            # Off-grid tiles
            for tile in layer_data["offgrid"]:
                if tile["type"] in self.assets:
                    imgs = self.assets[tile["type"]]
                    variant = tile["variant"]
                    if 0 <= variant < len(imgs):
                        img = imgs[variant]
                        sx, sy = self._world_to_screen(
                            tile["pos"][0], tile["pos"][1]
                        )
                        sx += self.rect.x
                        sy += self.rect.y
                        scaled = pygame.transform.scale(
                            img,
                            (max(1, int(img.get_width() * z)),
                             max(1, int(img.get_height() * z))),
                        )
                        screen.blit(scaled, (sx, sy))

        # ── Ghost preview ──
        self._draw_ghost(screen, ts, z)

        # ── Selection highlight ──
        if self.selected_tile:
            self._draw_selection(screen, ts, z)

        # ── Zoom indicator ──
        zoom_label = get_font(11).render(f"Zoom: {self.zoom:.2f}x", True, (180, 180, 180))
        screen.blit(zoom_label, (self.rect.right - zoom_label.get_width() - 8, self.rect.bottom - 20))

        screen.set_clip(None)

    def _draw_grid(self, screen: pygame.Surface, ts: int, z: float) -> None:
        """Draw grid lines on the canvas."""
        grid_color = COLORS["grid"]
        view_left = self.scroll[0]
        view_top = self.scroll[1]

        start_x = int(view_left // ts) * ts
        start_y = int(view_top // ts) * ts

        x = start_x
        while True:
            sx = (x - self.scroll[0]) * z + self.rect.x
            if sx > self.rect.right:
                break
            if sx >= self.rect.x:
                pygame.draw.line(screen, grid_color, (sx, self.rect.y), (sx, self.rect.bottom), 1)
            x += ts

        y = start_y
        while True:
            sy = (y - self.scroll[1]) * z + self.rect.y
            if sy > self.rect.bottom:
                break
            if sy >= self.rect.y:
                pygame.draw.line(screen, grid_color, (self.rect.x, sy), (self.rect.right, sy), 1)
            y += ts

    def _draw_ghost(self, screen: pygame.Surface, ts: int, z: float) -> None:
        """Draw translucent preview of the brush at cursor position."""
        if not self.brush_type or self.brush_type not in self.assets:
            return
        imgs = self.assets[self.brush_type]
        if self.brush_variant >= len(imgs):
            return
        img = imgs[self.brush_variant].copy()
        img.set_alpha(100)

        mpos = pygame.mouse.get_pos()
        if not self.rect.collidepoint(mpos):
            return

        lx, ly = self.local_mouse(mpos)

        if self.grid_snap:
            tx, ty = self._screen_to_tile(lx, ly)
            sx, sy = self._world_to_screen(tx * ts, ty * ts)
        else:
            wx, wy = self._screen_to_world(lx, ly)
            sx, sy = self._world_to_screen(wx, wy)

        scaled = pygame.transform.scale(
            img,
            (max(1, int(img.get_width() * z)), max(1, int(img.get_height() * z))),
        )
        screen.blit(scaled, (sx + self.rect.x, sy + self.rect.y))

    def _draw_selection(self, screen: pygame.Surface, ts: int, z: float) -> None:
        """Draw a highlight rect around the selected tile."""
        tile = self.selected_tile
        if not tile:
            return
        pos = tile.get("pos", [0, 0])

        if self.selected_offgrid_idx is not None:
            # Offgrid — use pixel position
            sx, sy = self._world_to_screen(pos[0], pos[1])
            if tile["type"] in self.assets:
                img = self.assets[tile["type"]][tile["variant"]]
                w = int(img.get_width() * z)
                h = int(img.get_height() * z)
            else:
                w = h = int(ts * z)
        else:
            sx, sy = self._world_to_screen(pos[0] * ts, pos[1] * ts)
            w = h = int(ts * z)

        sel_rect = pygame.Rect(sx + self.rect.x, sy + self.rect.y, w, h)
        pygame.draw.rect(screen, COLORS["highlight"], sel_rect, 2)
