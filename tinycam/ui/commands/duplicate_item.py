from PySide6 import QtGui

from tinycam.globals import GLOBALS


class DuplicateItemCommand(QtGui.QUndoCommand):
    def __init__(self, item):
        super().__init__('Duplicate item')
        self._item = item
        self._new_item = None

    def redo(self):
        self._new_item = self._item.clone()
        self._new_item.name += ' Copy'
        GLOBALS.APP.project.items.append(self._new_item)

    def undo(self):
        GLOBALS.APP.project.items.remove(self._new_item)
