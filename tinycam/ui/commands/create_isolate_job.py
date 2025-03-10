from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem, CncIsolateJob


class CreateIsolateJobCommand(QtGui.QUndoCommand):
    def __init__(self, item: CncProjectItem, parent=None):
        super().__init__('Create Isolate Job', parent=parent)
        self._source_item = item
        self._result_item = None

    @property
    def source_item(self) -> CncProjectItem:
        return self._source_item

    @property
    def result_item(self) -> CncProjectItem | None:
        return self._result_item

    def redo(self):
        self._result_item = CncIsolateJob(self._source_item)
        GLOBALS.APP.project.items.append(self._result_item)

    def undo(self):
        if self._result_item is not None:
            GLOBALS.APP.project.items.remove(self._result_item)
