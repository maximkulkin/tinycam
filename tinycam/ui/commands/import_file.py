import os.path
from PySide6 import QtGui

from tinycam.globals import GLOBALS


class ImportFileCommand(QtGui.QUndoCommand):
    def __init__(self, path, item, parent=None):
        super().__init__(f'Import {os.path.basename(path)}', parent=parent)
        self._path = path
        self._item = item

    def redo(self):
        GLOBALS.APP.project.items.append(self._item)

    def undo(self):
        GLOBALS.APP.project.items.remove(self._item)
