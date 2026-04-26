from PySide6 import QtGui

from tinycam.globals import GLOBALS


class SplitGeometryCommand(QtGui.QUndoCommand):
    """Split an item whose geometry is a collection into one item per primitive shape."""

    def __init__(self, item, parent=None):
        super().__init__('Split geometry', parent=parent)
        self._original = item
        self._original_index = -1
        self._split_items = []

    def redo(self):
        G = GLOBALS.GEOMETRY
        project = GLOBALS.APP.project

        shapes = list(G.shapes(self._original.geometry))

        if not self._split_items:
            # Build split items on first redo
            for i, shape in enumerate(shapes):
                new_item = self._original.clone()
                new_item.name = f'{self._original.name} {i + 1}'
                new_item.geometry = shape
                self._split_items.append(new_item)

        self._original_index = project.items.index(self._original)
        project.items.remove(self._original)

        for i, item in enumerate(self._split_items):
            project.items.insert(self._original_index + i, item)

    def undo(self):
        project = GLOBALS.APP.project

        for item in self._split_items:
            project.items.remove(item)

        project.items.insert(self._original_index, self._original)
