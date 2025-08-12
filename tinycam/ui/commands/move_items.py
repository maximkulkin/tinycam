from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.types import Vector2


class MoveItemsCommand(QtGui.QUndoCommand):
    def __init__(self, items: list[CncProjectItem], offset: Vector2):
        super().__init__('Move items')
        self._items = items
        self._offset = offset

    def _move(self, offset: Vector2):
        for item in self._items:
            item.geometry = GLOBALS.GEOMETRY.translate(item.geometry, offset)

    def redo(self):
        self._move(self._offset)

    def undo(self):
        self._move(-self._offset)
