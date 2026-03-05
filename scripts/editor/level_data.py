"""
Multi-layer level data model — decoupled from rendering.
Handles save/load with backward compatibility for old single-layer maps.
"""

from __future__ import annotations

import copy
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from .history import Action

# Default ordered layer names (bottom → top)
DEFAULT_LAYERS = ["Background", "Terrain", "Props", "Player", "Foreground"]

CURRENT_VERSION = 2


def _empty_layer(visible: bool = True) -> dict:
    return {"visible": visible, "tiles": {}, "offgrid": []}


class LevelData:
    """
    The canonical data model for a level.

    ``layers`` is an OrderedDict mapping layer names to dicts of:
        {"visible": bool, "tiles": {"x;y": tile_dict, …}, "offgrid": [tile_dict, …]}
    """

    def __init__(self, tile_size: int = 16) -> None:
        self.tile_size: int = tile_size
        self.layers: OrderedDict[str, dict] = OrderedDict()
        for name in DEFAULT_LAYERS:
            self.layers[name] = _empty_layer()

    # ── tile manipulation ───────────────────────────────────────────────
    def place_tile(
        self,
        layer: str,
        tile_type: str,
        variant: int,
        pos: tuple[int, int] | list,
        on_grid: bool,
    ) -> Action:
        """Return an Action that places a tile (does NOT execute it)."""
        layer_data = self.layers[layer]

        if on_grid:
            key = f"{int(pos[0])};{int(pos[1])}"
            new_tile = {"type": tile_type, "variant": variant, "pos": list(pos)}
            old_tile = layer_data["tiles"].get(key)

            def do():
                layer_data["tiles"][key] = copy.deepcopy(new_tile)

            def undo():
                if old_tile is not None:
                    layer_data["tiles"][key] = copy.deepcopy(old_tile)
                else:
                    layer_data["tiles"].pop(key, None)

            return Action(do, undo, f"Place {tile_type} at {key}")

        else:
            new_tile = {"type": tile_type, "variant": variant, "pos": list(pos)}

            def do():
                layer_data["offgrid"].append(copy.deepcopy(new_tile))

            def undo():
                # Remove last matching tile
                for i in range(len(layer_data["offgrid"]) - 1, -1, -1):
                    t = layer_data["offgrid"][i]
                    if t["type"] == tile_type and t["variant"] == variant and t["pos"] == list(pos):
                        layer_data["offgrid"].pop(i)
                        break

            return Action(do, undo, f"Place offgrid {tile_type}")

    def remove_tile(
        self, layer: str, pos: tuple[int, int], on_grid: bool
    ) -> Action | None:
        """Return an Action that removes a tile, or None if nothing there."""
        layer_data = self.layers[layer]

        if on_grid:
            key = f"{int(pos[0])};{int(pos[1])}"
            old_tile = layer_data["tiles"].get(key)
            if old_tile is None:
                return None
            old_copy = copy.deepcopy(old_tile)

            def do():
                layer_data["tiles"].pop(key, None)

            def undo():
                layer_data["tiles"][key] = copy.deepcopy(old_copy)

            return Action(do, undo, f"Remove tile at {key}")

        return None  # offgrid removal handled by canvas directly

    def remove_offgrid_tile(self, layer: str, index: int) -> Action | None:
        """Remove an offgrid tile by its list index."""
        layer_data = self.layers[layer]
        if index < 0 or index >= len(layer_data["offgrid"]):
            return None
        old_tile = copy.deepcopy(layer_data["offgrid"][index])

        def do():
            if index < len(layer_data["offgrid"]):
                layer_data["offgrid"].pop(index)

        def undo():
            layer_data["offgrid"].insert(index, copy.deepcopy(old_tile))

        return Action(do, undo, f"Remove offgrid tile")

    def move_tile(
        self,
        layer: str,
        old_pos: tuple[int, int],
        new_pos: tuple[int, int],
        on_grid: bool,
    ) -> Action | None:
        """Return an Action that moves a tile from old_pos to new_pos."""
        layer_data = self.layers[layer]
        if not on_grid:
            return None

        old_key = f"{int(old_pos[0])};{int(old_pos[1])}"
        new_key = f"{int(new_pos[0])};{int(new_pos[1])}"
        tile = layer_data["tiles"].get(old_key)
        if tile is None:
            return None
        tile_copy = copy.deepcopy(tile)
        replaced = copy.deepcopy(layer_data["tiles"].get(new_key))

        def do():
            layer_data["tiles"].pop(old_key, None)
            moved = copy.deepcopy(tile_copy)
            moved["pos"] = list(new_pos)
            layer_data["tiles"][new_key] = moved

        def undo():
            layer_data["tiles"].pop(new_key, None)
            restored = copy.deepcopy(tile_copy)
            restored["pos"] = list(old_pos)
            layer_data["tiles"][old_key] = restored
            if replaced is not None:
                layer_data["tiles"][new_key] = copy.deepcopy(replaced)

        return Action(do, undo, f"Move tile {old_key} → {new_key}")

    def get_tile_at(
        self, pos: tuple[int, int], on_grid: bool, assets: dict | None = None
    ) -> tuple[str, dict, int | None] | None:
        """
        Search layers top-down for a tile at *pos*.
        Returns (layer_name, tile_data, offgrid_index_or_None) or None.
        For on_grid, pos is tile coords.  For offgrid, pos is pixel.
        """
        for layer_name in reversed(self.layers):
            layer_data = self.layers[layer_name]
            if not layer_data["visible"]:
                continue

            if on_grid:
                key = f"{int(pos[0])};{int(pos[1])}"
                if key in layer_data["tiles"]:
                    return (layer_name, layer_data["tiles"][key], None)
            else:
                # Check offgrid tiles (reverse so topmost wins)
                import pygame
                for i in range(len(layer_data["offgrid"]) - 1, -1, -1):
                    tile = layer_data["offgrid"][i]
                    if assets and tile["type"] in assets:
                        img = assets[tile["type"]][tile["variant"]]
                        r = pygame.Rect(tile["pos"][0], tile["pos"][1],
                                        img.get_width(), img.get_height())
                        if r.collidepoint(pos):
                            return (layer_name, tile, i)
        return None

    # ── persistence ─────────────────────────────────────────────────────
    def save(self, path: str) -> None:
        """Save to the multi-layer JSON v2 format."""
        data: dict[str, Any] = {
            "version": CURRENT_VERSION,
            "tile_size": self.tile_size,
            "layers": {},
        }
        for name, layer in self.layers.items():
            data["layers"][name] = {
                "visible": layer["visible"],
                "tiles": layer["tiles"],
                "offgrid": layer["offgrid"],
            }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self, path: str) -> None:
        """Load a map file, auto-migrating v1 format when necessary."""
        with open(path, "r") as f:
            data = json.load(f)

        if "layers" in data:
            # ── v2 format ─────────────────────────────────────────
            self.tile_size = data.get("tile_size", 16)
            self.layers.clear()
            for name in DEFAULT_LAYERS:
                if name in data["layers"]:
                    self.layers[name] = data["layers"][name]
                else:
                    self.layers[name] = _empty_layer()
            # Preserve any extra custom layers
            for name, layer in data["layers"].items():
                if name not in self.layers:
                    self.layers[name] = layer
        else:
            # ── v1 legacy migration ───────────────────────────────
            self.tile_size = data.get("tile_size", 16)
            self.layers.clear()
            for name in DEFAULT_LAYERS:
                self.layers[name] = _empty_layer()
            self.layers["Terrain"]["tiles"] = data.get("tilemap", {})
            self.layers["Terrain"]["offgrid"] = data.get("offgrid", [])

    def export_for_game(self) -> dict:
        """
        Export back to the flat v1 format so the existing game.py / Tilemap
        class can load it without changes.
        """
        merged_tiles: dict[str, dict] = {}
        merged_offgrid: list[dict] = []
        for layer_data in self.layers.values():
            merged_tiles.update(layer_data["tiles"])
            merged_offgrid.extend(layer_data["offgrid"])
        return {
            "tilemap": merged_tiles,
            "tile_size": self.tile_size,
            "offgrid": merged_offgrid,
        }
