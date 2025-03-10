from PySide6 import QtGui
import os.path

from tinycam.geometry import Shape
from tinycam.formats import excellon
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem
from tinycam.types import Vector2
from tinycam.properties import Vector2Property


class ExcellonItem(CncProjectItem):
    def __init__(self, name: str, excellon_file: excellon.ExcellonFile):
        super().__init__(name, color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6))
        self._excellon_file = excellon_file
        self._geometry = self._excellon_file.geometry

        self._offset = Vector2(0, 0)
        self._scale = Vector2(1, 1)

    def _update(self):
        self._update_geometry()
        self._signal_updated()

    offset = Vector2Property(on_update=_update)
    scale = Vector2Property(on_update=_update)

    def clone(self) -> CncProjectItem:
        clone = ExcellonItem(self.name, self._excellon_file)
        clone.color = self.color
        clone.selected = self.selected
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

    @geometry.setter
    def geometry(self, value: Shape):
        self._geometry = value

    def _update_geometry(self):
        pass

    @staticmethod
    def from_file(path) -> 'ExcellonItem':
        with open(path, 'rt') as f:
            excellon_file = excellon.parse_excellon(f.read(), geometry=GLOBALS.GEOMETRY)
            name = os.path.basename(path)
            return ExcellonItem(name, excellon_file)
