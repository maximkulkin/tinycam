
from PySide6 import QtGui
import os.path

from tinycam.formats import svg
from tinycam.globals import GLOBALS
from tinycam.project.geometry import GeometryItem
from tinycam.project.item import CncProjectItem
from tinycam.math_types import Vector2


class SvgItem(GeometryItem):
    def __init__(self):
        super().__init__()
        self.color = QtGui.QColor.fromRgbF(0.8, 0.8, 0.0, 0.6)

    @staticmethod
    def from_file(path) -> 'SvgItem':
        shapes = svg.load(path)
        print(f'Loaded {len(shapes)} shapes from SVG {path}')
        G = GLOBALS.GEOMETRY
        geometry = G.group(*shapes)

        item = SvgItem()
        item.name = os.path.basename(path)
        item.geometry = geometry
        return item
