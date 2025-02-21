from PySide6 import QtGui
import os.path

from tinycam.formats import excellon
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem
from tinycam.types import Vector2
from tinycam.properties import Vector2Property


class ExcellonItem(CncProjectItem):
    def __init__(self, name, excellon_file):
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

    def clone(self):
        clone = ExcellonItem(self.name, self._excellon_file)
        clone.color = self.color
        clone.selected = self.selected
        return clone

    @property
    def tools(self):
        return self._excellon_file.tools

    @property
    def drills(self):
        return self._excellon_file.drills

    @property
    def mills(self):
        return self._excellon_file.mills

    @property
    def geometry(self):
        return self._excellon_file.geometry

    @geometry.setter
    def geometry(self, value):
        self._geometry = value

    def _update_geometry(self):
        pass

    @staticmethod
    def from_file(path):
        with open(path, 'rt') as f:
            excellon_file = excellon.parse_excellon(f.read(), geometry=GLOBALS.GEOMETRY)
            name = os.path.basename(path)
            return ExcellonItem(name, excellon_file)
