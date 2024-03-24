from PySide6 import QtGui

from tinycam.globals import CncGlobals


class DeleteItemsCommand(QtGui.QUndoCommand):
    def __init__(self, items, parent=None):
        super().__init__('Delete items', parent=parent)
        self._items = items
        self._item_indexes = []

    def redo(self):
        self._item_indexes = [
            (CncGlobals.APP.project.items.index(item), item)
            for item in self._items
        ]
        self._item_indexes.sort()

        for item in self._items:
            CncGlobals.APP.project.items.remove(item)

    def undo(self):
        for idx, item in self._item_indexes:
            CncGlobals.APP.project.items.insert(idx, item)


