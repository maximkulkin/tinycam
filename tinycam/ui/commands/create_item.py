from typing import Sequence

from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem


class CreateItemCommandBase(QtGui.QUndoCommand):
    def __init__(self, title: str):
        super().__init__(title)
        self._previous_selection = []

    @property
    def item(self) -> CncProjectItem | None:
        raise NotImplementedError()

    def redo(self):
        self._previous_selection = list(GLOBALS.APP.project.selection)
        if self.item is not None:
            GLOBALS.APP.project.items.append(self.item)
            GLOBALS.APP.project.selection.set([self.item])

    def undo(self):
        if self.item is not None:
            GLOBALS.APP.project.items.remove(self.item)
            GLOBALS.APP.project.selection.set(self._previous_selection)
