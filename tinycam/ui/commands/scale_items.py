from PySide6 import QtGui

from tinycam.globals import CncGlobals
from tinycam.ui.utils import Point


class ScaleItemsCommand(QtGui.QUndoCommand):
    def __init__(self, items, scale, offset=Point(0.0, 0.0), parent=None):
        super().__init__('Scale', parent=parent)
        self._items = items
        self._scale = scale
        self._offset = offset

    def redo(self):
        for item in self._items:
            item.geometry = CncGlobals.GEOMETRY.translate(
                CncGlobals.GEOMETRY.scale(item.geometry, self._scale),
                self._offset
            )

    def undo(self):
        for item in self._items:
            item.geometry = CncGlobals.GEOMETRY.scale(
                CncGlobals.GEOMETRY.translate(item.geometry, -self._offset),
                1.0/self._scale
            )
