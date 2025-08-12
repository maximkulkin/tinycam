from PySide6 import QtGui
import os.path

from tinycam.formats import excellon
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem


class ExcellonItem(CncProjectItem):
    def __init__(self):
        super().__init__()
        self.color = QtGui.QColor.fromRgbF(0.6, 0.0, 0.0, 0.6)
        self._tools = []
        self._drills = []
        self._mills = []

    @property
    def tools(self) -> list[excellon.Tool]:
        return self._tools

    @tools.setter
    def tools(self, value: list[excellon.Tool]):
        if self._tools == value:
            return
        self._tools = value
        self._signal_changed()

    @property
    def drills(self) -> list[excellon.Drill]:
        return self._drills

    @drills.setter
    def drills(self, value: list[excellon.Drill]):
        if self._drills == value:
            return
        self._drills = value
        self._signal_changed()

    @property
    def mills(self) -> list[excellon.Mill]:
        return self._mills

    @mills.setter
    def mills(self, value: list[excellon.Mill]):
        if self._mills == value:
            return
        self._mills = value
        self._signal_changed()

    @staticmethod
    def from_file(path) -> 'ExcellonItem':
        with open(path, 'rt') as f:
            G = GLOBALS.GEOMETRY
            excellon_file = excellon.parse_excellon(f.read(), geometry=G)

            item = ExcellonItem()
            item.name = os.path.basename(path)
            item.geometry = excellon_file.geometry
            item.tools = excellon_file.tools
            item.drills = excellon_file.drills
            item.mills = excellon_file.mills

            return item
