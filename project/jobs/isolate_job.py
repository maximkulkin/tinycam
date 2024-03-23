from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt

from globals import GEOMETRY
from project.jobs.job import CncJob


class CncIsolateJob(CncJob):
    def __init__(self,
                 source_item,
                 tool_diameter=0.1,
                 spindle_speed=1000,
                 cut_depth=0.1,
                 cut_speed=120,
                 travel_height=2,
                 pass_count=1,
                 pass_overlap=10):
        super().__init__(
            'Isolate %s' % source_item.name,
            color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6),
        )

        self._source_item = source_item

        self._tool_diameter = tool_diameter
        self._cut_depth = cut_depth
        self._pass_count = pass_count
        self._pass_overlap = pass_overlap
        self._spindle_speed = spindle_speed
        self._cut_speed = cut_speed
        self._travel_height = travel_height

        self._geometry = None
        self._geometry_cache = None
        # TODO:
        # self._source_item.changed.connect(self._on_source_item_changed)
        self._calculate_geometry()

    @property
    def geometry(self):
        return self._geometry

    @property
    def tool_diameter(self):
        return self._tool_diameter

    @tool_diameter.setter
    def tool_diameter(self, value):
        self._tool_diameter = value
        self._update()

    @property
    def cut_depth(self):
        return self._cut_depth

    @cut_depth.setter
    def cut_depth(self, value):
        self._cut_depth = value
        self._update()

    @property
    def pass_count(self):
        return self._pass_count

    @pass_count.setter
    def pass_count(self, value):
        self._pass_count = value
        self._update()

    @property
    def pass_overlap(self):
        return self._pass_overlap

    @pass_overlap.setter
    def pass_overlap(self, value):
        self._pass_overlap = value
        self._update()

    @property
    def cut_speed(self):
        return self._cut_speed

    @cut_speed.setter
    def cut_speed(self, value):
        self._cut_speed = value
        self._update()

    @property
    def spindle_speed(self):
        return self._spindle_speed

    @spindle_speed.setter
    def spindle_speed(self, value):
        self._spindle_speed = value
        self._update()

    @property
    def travel_height(self):
        return self._travel_height

    @travel_height.setter
    def travel_height(self, value):
        self._travel_height = value
        self._update()

    def _on_source_item_changed(self, _item):
        self._update()

    def _update(self):
        self._calculate_geometry()
        self._changed()

    def _calculate_geometry(self):
        tool_radius = self._tool_diameter * 0.5
        pass_offset = self._tool_diameter * (1 - self._pass_overlap / 100.0)

        geometry = None

        g = GEOMETRY.simplify(
            GEOMETRY.buffer(self._source_item.geometry, tool_radius),
            # TODO: parametrize into settings
            tolerance=0.01,
        )

        for pass_index in range(self._pass_count):
            for polygon in GEOMETRY.polygons(g):
                for exterior in GEOMETRY.exteriors(polygon):
                    geometry = GEOMETRY.union(geometry, exterior)
                for interior in GEOMETRY.interiors(polygon):
                    geometry = GEOMETRY.union(geometry, interior)
            g = GEOMETRY.buffer(g, pass_offset)

        self._geometry = geometry
        self._geometry_cache = None

    def _precache_geometry(self):
        path = QtGui.QPainterPath()
        count = 0
        for line in GEOMETRY.lines(self._geometry):
            path.addPolygon(
                QtGui.QPolygonF.fromList([
                    QtCore.QPointF(x, y)
                    for x, y in GEOMETRY.points(line)
                ])
            )
            count += len(GEOMETRY.points(line))

        self._geometry_cache = path

    def draw(self, painter):
        if not self.visible:
            return

        if self._geometry_cache is None:
            self._precache_geometry()

        with painter:
            color = self.color
            if self.selected:
                color = color.lighter(150)

            painter.setBrush(Qt.NoBrush)
            pen = QtGui.QPen(color.darker(150), 2.0)
            pen.setCosmetic(True)
            painter.setPen(pen)

            painter.drawPath(self._geometry_cache)

            color.setAlphaF(0.2)
            pen = QtGui.QPen(color, self._tool_diameter)
            pen.setJoinStyle(Qt.RoundJoin)

            painter.setPen(pen)

            painter.drawPath(self._geometry_cache)

    def _find_closest(self, lines, point):
        # TODO: implement finding closest line
        return 0

    def generate_commands(self):
        # TODO: allow selecting different starting positions
        builder = CncCommandBuilder(start_position=(0, 0, 0))

        lines = list(GEOMETRY.lines(self._geometry))
        while lines:
            line_idx = self._find_closest(lines, builder.current_position)
            line = lines.pop(line_idx)

            points = line.coords[:]
            # if line.is_closed:
            #     p, _ = shapely.ops.nearest_points(line, shapely.Point(builder.current_position[:2]))
            #     print(points)
            #     start_index = points.index(p)
            #     points = points[start_index:] + points[:start_index]

            builder.travel(z=self._travel_height)
            builder.travel(x=points[0][0], y=points[0][1])
            builder.cut(z=-self._cut_depth)

            for p in points[1:]:
                builder.cut(x=p[0], y=p[1])

        return builder.build()


