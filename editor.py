
import sys
import os

import pygame

from scripts.utils import load_images
from scripts.editor.theme import (
    COLORS,
    LEFT_SIDEBAR_W,
    RIGHT_SIDEBAR_W,
    TOOLBAR_HEIGHT,
    get_font,
)
from scripts.editor.level_data import LevelData
from scripts.editor.history import History
from scripts.editor.canvas import Canvas
from scripts.editor.toolbar import Toolbar
from scripts.editor.layers_panel import LayersPanel
from scripts.editor.assets_panel import AssetsPanel
from scripts.editor.properties_panel import PropertiesPanel
from scripts.editor.console_panel import ConsolePanel


DEFAULT_MAP = "data/maps/editor_save.json"
LEGACY_MAP = "map.json"
WINDOW_W, WINDOW_H = 1280, 720


class Editor:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Level Editor")
        self.screen = pygame.display.set_mode(
            (WINDOW_W, WINDOW_H), pygame.RESIZABLE
        )
        self.clock = pygame.time.Clock()

        self.assets: dict[str, list[pygame.Surface]] = {
            "decor": load_images("tiles/decor"),
            "grass": load_images("tiles/grass"),
            "large_decor": load_images("tiles/large_decor"),
            "stone": load_images("tiles/stone"),
            "spawners": load_images("tiles/spawners"),
        }

        self.level_data = LevelData(tile_size=16)
        self.history = History()


        self._try_load_map()

        dummy = pygame.Rect(0, 0, 1, 1)

        self.toolbar = Toolbar(dummy)
        self._setup_toolbar()

        self.layers_panel = LayersPanel(dummy, self.level_data)
        self.assets_panel = AssetsPanel(dummy, self.assets)
        self.properties_panel = PropertiesPanel(dummy)
        self.console_panel = ConsolePanel(dummy)
        self.canvas = Canvas(dummy, self.level_data, self.history, self.assets)


        self.canvas.on_select = self._on_canvas_select
        self.canvas.on_log = self._on_log


        self._layout()

        self._on_log("Editor ready. WASD=scroll, Wheel=zoom, G=grid snap, T=autotile")

    def _layout(self) -> None:
        w, h = self.screen.get_size()


        self.toolbar.resize(pygame.Rect(0, 0, w, TOOLBAR_HEIGHT))


        left_top = TOOLBAR_HEIGHT
        left_h = h - left_top
        layers_h = int(left_h * 0.35)
        assets_h = left_h - layers_h

        self.layers_panel.resize(
            pygame.Rect(0, left_top, LEFT_SIDEBAR_W, layers_h)
        )
        self.assets_panel.resize(
            pygame.Rect(0, left_top + layers_h, LEFT_SIDEBAR_W, assets_h)
        )


        right_x = w - RIGHT_SIDEBAR_W
        right_h = h - TOOLBAR_HEIGHT
        props_h = int(right_h * 0.40)
        console_h = right_h - props_h

        self.properties_panel.resize(
            pygame.Rect(right_x, left_top, RIGHT_SIDEBAR_W, props_h)
        )
        self.console_panel.resize(
            pygame.Rect(right_x, left_top + props_h, RIGHT_SIDEBAR_W, console_h)
        )

        canvas_x = LEFT_SIDEBAR_W
        canvas_w = w - LEFT_SIDEBAR_W - RIGHT_SIDEBAR_W
        canvas_h = h - TOOLBAR_HEIGHT
        self.canvas.resize(pygame.Rect(canvas_x, left_top, max(1, canvas_w), canvas_h))

    def _setup_toolbar(self) -> None:
        self.toolbar.add_button("Save", self._save, shortcut="Ctrl+S")
        self.toolbar.add_button("Load", self._load, shortcut="Ctrl+O")
        self.toolbar.add_separator()
        self.toolbar.add_button("Undo", self._undo, shortcut="Ctrl+Z")
        self.toolbar.add_button("Redo", self._redo, shortcut="Ctrl+Y")
        self.toolbar.add_separator()
        self._grid_btn = self.toolbar.add_button("Grid: ON", self._toggle_grid, toggle=True)
        self._grid_btn.active = True
        self._gridsize_btn = self.toolbar.add_button("16px", self._cycle_grid_size)
        self.toolbar.add_separator()
        self.toolbar.add_button("Autotile", self._autotile, shortcut="T")
        self.toolbar.add_separator()
        self.toolbar.add_button("Export v1", self._export_v1)

    def _save(self) -> None:
        self.level_data.save(DEFAULT_MAP)
        self._on_log(f"Saved → {DEFAULT_MAP}")

    def _load(self) -> None:
        if os.path.exists(DEFAULT_MAP):
            self.level_data.load(DEFAULT_MAP)
            self._on_log(f"Loaded ← {DEFAULT_MAP}")
        elif os.path.exists(LEGACY_MAP):
            self.level_data.load(LEGACY_MAP)
            self._on_log(f"Loaded (legacy) ← {LEGACY_MAP}")
        else:
            self._on_log("No map file found to load.")
        self.history.clear()

    def _undo(self) -> None:
        desc = self.history.undo()
        if desc:
            self._on_log(f"Undo: {desc}")
        else:
            self._on_log("Nothing to undo.")

    def _redo(self) -> None:
        desc = self.history.redo()
        if desc:
            self._on_log(f"Redo: {desc}")
        else:
            self._on_log("Nothing to redo.")

    def _toggle_grid(self) -> None:
        self.canvas.grid_snap = self._grid_btn.active
        label = "Grid: ON" if self._grid_btn.active else "Grid: OFF"
        self._grid_btn.text = label
        self._on_log(f"Grid snap: {'ON' if self.canvas.grid_snap else 'OFF'}")

    def _cycle_grid_size(self) -> None:
        sizes = [16, 32]
        current = self.canvas.grid_size
        idx = (sizes.index(current) + 1) % len(sizes) if current in sizes else 0
        self.canvas.grid_size = sizes[idx]
        self.level_data.tile_size = sizes[idx]
        self._gridsize_btn.text = f"{sizes[idx]}px"
        self._on_log(f"Grid size: {sizes[idx]}px")

    def _autotile(self) -> None:
        from scripts.tilemap import AUTOTILE_MAP, AUTOTILE_TYPES
        terrain = self.level_data.layers.get("Terrain")
        if not terrain:
            return
        tilemap = terrain["tiles"]
        for loc in tilemap:
            tile = tilemap[loc]
            neighbors = set()
            for shift in [(1, 0), (-1, 0), (0, -1), (0, 1)]:
                check_loc = f"{tile['pos'][0] + shift[0]};{tile['pos'][1] + shift[1]}"
                if check_loc in tilemap:
                    if tilemap[check_loc]["type"] == tile["type"]:
                        neighbors.add(shift)
            neighbors = tuple(sorted(neighbors))
            if (tile["type"] in AUTOTILE_TYPES) and (neighbors in AUTOTILE_MAP):
                tile["variant"] = AUTOTILE_MAP[neighbors]
        self._on_log("Autotile applied to Terrain layer.")

    def _export_v1(self) -> None:
        import json
        data = self.level_data.export_for_game()
        path = "map.json"
        with open(path, "w") as f:
            json.dump(data, f)
        self._on_log(f"Exported v1 format → {path}")

    def _on_canvas_select(self, tile_data: dict | None, layer_name: str) -> None:
        if tile_data:
            self.properties_panel.set_selection(tile_data, layer_name)
            self._on_log(f"Selected {tile_data.get('type','')} on [{layer_name}]")
        else:
            self.properties_panel.clear_selection()

    def _on_log(self, text: str) -> None:
        self.console_panel.log(text)


    def _try_load_map(self) -> None:
        for path in [DEFAULT_MAP, LEGACY_MAP, "data/maps/0.json", "data/maps/1.json", "data/maps/2.json"]:
            if os.path.exists(path):
                try:
                    self.level_data.load(path)
                    return
                except Exception:
                    pass


    def run(self) -> None:
        while True:

            self.canvas.brush_type = self.assets_panel.current_type
            self.canvas.brush_variant = self.assets_panel.selected_variant
            self.canvas.active_layer = self.layers_panel.active_layer
            self.canvas.grid_size = self.level_data.tile_size


            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE
                    )
                    self._layout()
                    continue


                if event.type == pygame.KEYDOWN:
                    ctrl = event.mod & pygame.KMOD_CTRL
                    if ctrl and event.key == pygame.K_s:
                        self._save()
                        continue
                    if ctrl and event.key == pygame.K_o:
                        self._load()
                        continue
                    if ctrl and event.key == pygame.K_z:
                        self._undo()
                        continue
                    if ctrl and event.key == pygame.K_y:
                        self._redo()
                        continue
                    if event.key == pygame.K_g:
                        self._grid_btn.active = not self._grid_btn.active
                        self._toggle_grid()
                        continue
                    if event.key == pygame.K_t:
                        self._autotile()
                        continue


                consumed = False
                for panel in [
                    self.toolbar,
                    self.layers_panel,
                    self.assets_panel,
                    self.properties_panel,
                    self.console_panel,
                    self.canvas,
                ]:
                    if panel.handle_event(event):
                        consumed = True
                        break


            self.canvas.update()


            self.screen.fill(COLORS["bg"])
            self.canvas.draw(self.screen)
            self.layers_panel.draw(self.screen)
            self.assets_panel.draw(self.screen)
            self.properties_panel.draw(self.screen)
            self.console_panel.draw(self.screen)
            self.toolbar.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)


if __name__ == "__main__":
    Editor().run()