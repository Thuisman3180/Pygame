"""
Stack-based Undo / Redo history for editor actions.
"""

from __future__ import annotations
from typing import Callable, NamedTuple

MAX_HISTORY = 100


class Action(NamedTuple):
    """An undoable action: *do* applies it, *undo* reverses it."""
    do: Callable[[], None]
    undo: Callable[[], None]
    description: str = ""


class History:
    """Manages undo/redo stacks of Actions."""

    def __init__(self) -> None:
        self._undo: list[Action] = []
        self._redo: list[Action] = []

    # ── public API ──────────────────────────────────────────────────────
    def push(self, action: Action) -> None:
        """Execute *action.do()* and record it on the undo stack."""
        action.do()
        self._undo.append(action)
        if len(self._undo) > MAX_HISTORY:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> str | None:
        """Undo the last action. Returns description or None."""
        if not self._undo:
            return None
        action = self._undo.pop()
        action.undo()
        self._redo.append(action)
        return action.description

    def redo(self) -> str | None:
        """Redo the last undone action. Returns description or None."""
        if not self._redo:
            return None
        action = self._redo.pop()
        action.do()
        self._undo.append(action)
        return action.description

    @property
    def can_undo(self) -> bool:
        return len(self._undo) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo) > 0

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
