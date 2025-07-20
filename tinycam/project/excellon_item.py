from PySide6 import QtGui
import os.path

from tinycam.geometry import Shape
from tinycam.formats import excellon
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem


class ExcellonItem(CncProjectItem):
    def __init__(self, name: str, excellon_file: excellon.ExcellonFile):
        super().__init__(name, color=QtGui.QColor.fromRgbF(0.6, 0.0, 0.0, 0.6))
        self._excellon_file = excellon_file
        self._geometry = self._excellon_file.geometry

    def clone(self) -> CncProjectItem:
        clone = ExcellonItem(self.name, self._excellon_file)
        clone.color = self.color
        clone.selected = self.selected
        clone.offset = self.offset
        clone.scale = self.scale
        return clone

    @property
    def tools(self) -> list[excellon.Tool]:
        return self._excellon_file.tools

    @property
    def drills(self) -> list[excellon.Drill]:
        return self._excellon_file.drills

    @property
    def mills(self) -> list[excellon.Mill]:
        return self._excellon_file.mills

    @property
    def geometry(self) -> Shape:
        return self._excellon_file.geometry

    @staticmethod
    def from_file(path) -> 'ExcellonItem':
        with open(path, 'rt') as f:
            G = GLOBALS.GEOMETRY
            excellon_file = excellon.parse_excellon(f.read(), geometry=G)
            name = os.path.basename(path)
            bounds = G.bounds(excellon_file.geometry)
            for drill in excellon_file.drills:
                drill.position -= bounds.center
            for mill in excellon_file.mills:
                for i in range(len(mill.positions)):
                    mill.positions[i] -= bounds.center
            excellon_file.geometry = G.translate(excellon_file.geometry, -bounds.center)
            item = ExcellonItem(name, excellon_file)
            item.offset = bounds.center
            return item
