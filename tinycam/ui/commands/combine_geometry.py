from PySide6 import QtGui

from tinycam.globals import GLOBALS


class CombineGeometryCommand(QtGui.QUndoCommand):
    """Combine multiple items into one item whose geometry is a collection."""

    def __init__(self, items, parent=None):
        super().__init__('Combine geometry', parent=parent)
        # Sort items by their current project order so the combined item lands
        # at the position of the first (topmost) source item.
        project = GLOBALS.APP.project
        self._originals = sorted(items, key=lambda it: project.items.index(it))
        self._original_indexes = []
        self._combined = None

    def redo(self):
        G = GLOBALS.GEOMETRY
        project = GLOBALS.APP.project

        if self._combined is None:
            first = self._originals[0]
            combined = first.clone()
            combined.name = first.name
            combined.geometry = G.group(*[it.geometry for it in self._originals])
            self._combined = combined

        self._original_indexes = [
            project.items.index(item) for item in self._originals
        ]

        for item in self._originals:
            project.items.remove(item)

        project.items.insert(self._original_indexes[0], self._combined)

    def undo(self):
        project = GLOBALS.APP.project

        project.items.remove(self._combined)

        for idx, item in sorted(zip(self._original_indexes, self._originals)):
            project.items.insert(idx, item)
