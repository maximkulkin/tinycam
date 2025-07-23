from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.types import Vector2


class FlipVerticallyCommand(QtGui.QUndoCommand):
    def __init__(self, items: list[CncProjectItem]):
        super().__init__('Flip vertically')
        self._items = items

    def _flip(self):
        for item in self._items:
            item.scale *= Vector2(1, -1)

    def redo(self):
        self._flip()

    def undo(self):
        self._flip()
