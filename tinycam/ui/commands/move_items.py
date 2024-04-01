from PySide6 import QtGui

from tinycam.globals import GLOBALS


class MoveItemsCommand(QtGui.QUndoCommand):
    def __init__(self, items, offset, parent=None):
        super().__init__('Move items', parent=parent)
        self._items = items
        self._offset = offset

    def _move(self, offset):
        for item in self._items:
            item.geometry = GLOBALS.GEOMETRY.translate(item.geometry, offset)

    def redo(self):
        self._move(self._offset)

    def undo(self):
        self._move((-self._offset[0], -self._offset[1]))
