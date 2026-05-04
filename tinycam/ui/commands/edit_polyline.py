from PySide6 import QtGui

from tinycam.geometry import Shape


class EditPolylineCommand(QtGui.QUndoCommand):
    """Replace the geometry of a GeometryItem (undo/redo for line editing)."""

    def __init__(self, item, old_geometry: Shape, new_geometry: Shape, parent=None):
        super().__init__('Edit line', parent=parent)
        self._item = item
        self._old = old_geometry
        self._new = new_geometry

    def redo(self):
        self._item.geometry = self._new

    def undo(self):
        self._item.geometry = self._old
