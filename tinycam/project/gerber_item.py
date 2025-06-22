from PySide6 import QtGui
import os.path

from tinycam.formats import gerber
from tinycam.geometry import Shape
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem
from tinycam.types import Vector2
import tinycam.properties as p


class GerberItem(CncProjectItem):
    def __init__(self, name: str, geometry: Shape):
        super().__init__(name, QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6))
        self._geometry = geometry

        self._update_geometry()

    def _update(self):
        self._update_geometry()
        self._signal_changed()

    offset = p.Property[Vector2](on_update=_update, default=Vector2(0, 0))
    scale = p.Property[Vector2](on_update=_update, default=Vector2(1, 1))

    def clone(self) -> CncProjectItem:
        clone = GerberItem(self.name, self._geometry)
        clone.color = self.color
        clone.selected = self.selected
        return clone

    @property
    def geometry(self) -> Shape:
        return self._geometry

    def _update_geometry(self):
        pass

    @staticmethod
    def from_file(path) -> 'GerberItem':
        with open(path, 'rt') as f:
            geometry = gerber.parse_gerber(f.read(), geometry=GLOBALS.GEOMETRY)
            # name, ext = os.path.splitext(os.path.basename(path))
            name = os.path.basename(path)
            return GerberItem(name, geometry)
