from PySide6 import QtGui


class SetItemsColorCommand(QtGui.QUndoCommand):
    def __init__(self, items, color, parent=None):
        super().__init__('Set items color', parent=parent)
        self._items = items
        self._color = color

        self._old_colors = {}

    def redo(self):
        for item in self._items:
            self._old_colors[item] = item.color
            item.color = self._color

    def undo(self):
        for item, color in self._old_colors.items():
            item.color = color
