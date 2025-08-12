from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project import GeometryItem
from tinycam.types import Rect


class CreateRectangleCommand(QtGui.QUndoCommand):
    def __init__(self, rect: Rect):
        super().__init__('Create rectangle')
        self._item = GeometryItem()
        self._item.name = 'Rectangle'
        self._item.geometry = GLOBALS.GEOMETRY.box(rect.pmin, rect.pmax).exterior

    def redo(self):
        GLOBALS.APP.project.items.append(self._item)

    def undo(self):
        GLOBALS.APP.project.items.remove(self._item)
