from PySide6 import QtCore, QtGui
import os.path

from tinycam.formats import gerber
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem


class GerberItem(CncProjectItem):
    def __init__(self, name, geometry):
        super().__init__(name, QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6))
        self._geometry = geometry
        self._geometry_cache = None

    def clone(self):
        clone = GerberItem(self.name, self._geometry)
        clone.color = self.color
        clone.selected = self.selected
        return clone

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, value):
        self._geometry = value
        self._geometry_cache = None
        self._changed()

    def _precache_geometry(self):
        path = QtGui.QPainterPath()

        for polygon in GLOBALS.GEOMETRY.polygons(self._geometry):
            p = QtGui.QPainterPath()

            for exterior in GLOBALS.GEOMETRY.exteriors(polygon):
                p.addPolygon(
                    QtGui.QPolygonF.fromList([
                        QtCore.QPointF(x, y)
                        for x, y in GLOBALS.GEOMETRY.points(exterior)
                    ])
                )

            for interior in GLOBALS.GEOMETRY.interiors(polygon):
                pi = QtGui.QPainterPath()
                pi.addPolygon(
                    QtGui.QPolygonF.fromList([
                        QtCore.QPointF(x, y)
                        for x, y in GLOBALS.GEOMETRY.points(interior)
                    ])
                )
                p = p.subtracted(pi)

            path = path.united(p)

        self._geometry_cache = path

    def draw(self, painter):
        if not self.visible:
            return

        if not self._geometry_cache:
            self._precache_geometry()

        with painter:
            color = self.color
            if self.selected:
                color = color.lighter(150)

            painter.setBrush(QtGui.QBrush(color))
            pen = QtGui.QPen(color.darker(150), 2.0)
            pen.setCosmetic(True)
            painter.setPen(pen)

            painter.drawPath(self._geometry_cache)

    @staticmethod
    def from_file(path):
        with open(path, 'rt') as f:
            geometry = gerber.parse_gerber(f.read(), geometry=GLOBALS.GEOMETRY)
            # name, ext = os.path.splitext(os.path.basename(path))
            name = os.path.basename(path)
            return GerberItem(name, geometry)


