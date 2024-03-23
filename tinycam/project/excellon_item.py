from PySide6 import QtCore, QtGui
import os.path

from tinycam.formats import excellon
from tinycam.globals import GEOMETRY
from tinycam.project.item import CncProjectItem


class ExcellonItem(CncProjectItem):
    def __init__(self, name, excellon_file):
        super().__init__(name, color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6))
        self._excellon_file = excellon_file
        self._geometry = self._excellon_file.geometry
        self._geometry_cache = None

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
        self._geometry_cache = None

    def _precache_geometry(self):
        path = QtGui.QPainterPath()

        for polygon in GEOMETRY.polygons(self._geometry):
            p = QtGui.QPainterPath()

            for exterior in GEOMETRY.exteriors(polygon):
                p.addPolygon(
                    QtGui.QPolygonF.fromList([
                        QtCore.QPointF(x, y)
                        for x, y in GEOMETRY.points(exterior)
                    ])
                )

            for interior in GEOMETRY.interiors(polygon):
                pi = QtGui.QPainterPath()
                pi.addPolygon(
                    QtGui.QPolygonF.fromList([
                        QtCore.QPointF(x, y)
                        for x, y in GEOMETRY.points(interior)
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
            excellon_file = excellon.parse_excellon(f.read(), geometry=GEOMETRY)
            name = os.path.basename(path)
            return ExcellonItem(name, excellon_file)


