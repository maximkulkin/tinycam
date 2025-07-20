from copy import copy

from PySide6 import QtGui

from tinycam.project import CncProjectItem
from tinycam.types import Vector2


class ScaleItemsCommand(QtGui.QUndoCommand):
    def __init__(
        self,
        items: list[CncProjectItem],
        scale: Vector2,
        pivot: Vector2 | None = None,
    ):
        super().__init__('Scale')
        self._items = items
        self._scale = scale
        self._pivot = pivot
        self._original_values = None

    def redo(self):
        self._original_values = [
            (copy(item.offset), copy(item.scale))
            for item in self._items
        ]

        for item in self._items:
            with item:
                item.scale *= self._scale

                if self._pivot is not None:
                    v = self._pivot - item.offset
                    item.offset += v - v * self._scale

    def undo(self):
        for item, (offset, scale) in zip(self._items, self._original_values):
            with item:
                item.scale = scale
                item.offset = offset
