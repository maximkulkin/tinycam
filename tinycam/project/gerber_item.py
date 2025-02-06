from PySide6 import QtGui
import os.path

from tinycam.formats import gerber
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem
from tinycam.types import Vector2
from tinycam.properties import Vector2Property


class GerberItem(CncProjectItem):
    def __init__(self, name, geometry):
        super().__init__(name, QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6))
        self._geometry = geometry

        self._offset = Vector2(0, 0)
        self._scale = Vector2(1, 1)

        self._update_geometry()

    def _update(self):
        self._update_geometry()
        self._signal_updated()

    offset = Vector2Property(on_update=_update)
    scale = Vector2Property(on_update=_update)

    def clone(self):
        clone = GerberItem(self.name, self._geometry)
        clone.color = self.color
        clone.selected = self.selected
        return clone

    @property
    def geometry(self):
        return self._geometry

    def _update_geometry(self):
        pass

    @staticmethod
    def from_file(path):
        with open(path, 'rt') as f:
            geometry = gerber.parse_gerber(f.read(), geometry=GLOBALS.GEOMETRY)
            # name, ext = os.path.splitext(os.path.basename(path))
            name = os.path.basename(path)
            return GerberItem(name, geometry)
