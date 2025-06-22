from PySide6 import QtGui


class UpdateItemsCommand(QtGui.QUndoCommand):
    def __init__(self, items, updates, parent=None):
        super().__init__('Update item', parent=parent)
        self._items = items
        self._updates = updates
        self._previous_values = {}

    def redo(self):
        self._previous_values = {
            item: {k: getattr(item, k) for k in self._updates}
            for item in self._items
        }
        for item in self._items:
            with item:
                for k, v in self._updates.items():
                    setattr(item, k, v)

    def undo(self):
        for item in self._items:
            with item:
                for k, v in self._previous_values[item].items():
                    setattr(item, k, v)
        self._previous_values = {}


