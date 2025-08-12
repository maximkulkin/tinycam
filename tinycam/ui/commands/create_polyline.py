from typing import Sequence

from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project import GeometryItem
from tinycam.types import Vector2


class CreatePolylineCommand(QtGui.QUndoCommand):
    def __init__(self, points: Sequence[Vector2], closed: bool = False):
        super().__init__('Create line')
        self._item = GeometryItem()
        self._item.name = 'Line'
        self._item.geometry = GLOBALS.GEOMETRY.line(points, closed=closed)

    def redo(self):
        GLOBALS.APP.project.items.append(self._item)

    def undo(self):
        GLOBALS.APP.project.items.remove(self._item)
