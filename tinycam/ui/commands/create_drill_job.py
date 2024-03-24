from PySide6 import QtGui

from tinycam.globals import CncGlobals
from tinycam.project import CncDrillJob


class CreateDrillJobCommand(QtGui.QUndoCommand):
    def __init__(self, item, parent=None):
        super().__init__('Create Drill Job', parent=parent)
        self._source_item = item
        self._result_item = None

    @property
    def source_item(self):
        return self._source_item

    @property
    def result_item(self):
        return self._result_item

    def redo(self):
        self._result_item = CncDrillJob(self._source_item)
        CncGlobals.APP.project.items.append(self._result_item)

    def undo(self):
        CncGlobals.APP.project.items.remove(self._result_item)
