import math

from PySide6 import QtGui

from tinycam.globals import GLOBALS
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
        if abs(self._scale.x) < 0.001:
            self._scale.x = math.copysign(0.001, self._scale.x)
        if abs(self._scale.y) < 0.001:
            self._scale.y = math.copysign(0.001, self._scale.y)
        self._pivot = pivot

    def _apply_scale(self, scale: Vector2):
        assert self._pivot is not None

        for item in self._items:
            item.geometry = GLOBALS.GEOMETRY.scale(
                item.geometry,
                factor=scale,
                origin=self._pivot,
            )

    def redo(self):
        self._apply_scale(self._scale)

    def undo(self):
        self._apply_scale(1.0 / self._scale)
