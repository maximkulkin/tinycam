from PySide6 import QtGui
import os.path

from tinycam.formats import gerber
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem
from tinycam.math_types import Vector2


class GerberItem(CncProjectItem):
    def __init__(self):
        super().__init__()
        self.color = QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6)

    def translate(self, offset: Vector2):
        self.geometry = GLOBALS.GEOMETRY.translate(self.geometry, offset)

    def scale(self, scale: Vector2, origin: Vector2 = Vector2()):
        self.geometry = GLOBALS.GEOMETRY.scale(
            self.geometry,
            factor=scale,
            origin=origin,
        )

    def save(self) -> dict:
        data = super().save()
        data['geometry'] = GLOBALS.GEOMETRY.to_wkt(self._geometry)
        return data

    def load(self, data: dict) -> None:
        super().load(data)
        if 'geometry' in data:
            self._geometry = GLOBALS.GEOMETRY.from_wkt(data['geometry'])
            self._bounds = None

    @staticmethod
    def from_file(path) -> 'GerberItem':
        with open(path, 'rt') as f:
            G = GLOBALS.GEOMETRY

            geometry = gerber.parse_gerber(f.read(), geometry=G)
            assert geometry is not None

            item = GerberItem()
            item.name = os.path.basename(path)
            item.geometry = geometry

            return item
