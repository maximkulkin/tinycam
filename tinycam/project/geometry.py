from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem


class GeometryItem(CncProjectItem):
    def __init__(self):
        super().__init__()
        self.name = 'Geometry'
        self.color = QtGui.QColor.fromRgbF(0.5, 0.5, 0.5, 1.0)
        self._geometry = GLOBALS.GEOMETRY.group()
