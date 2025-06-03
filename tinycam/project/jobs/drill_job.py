from PySide6 import QtGui

from tinycam.commands import CncCommandBuilder
from tinycam.globals import GLOBALS
from tinycam.project.jobs.job import CncJob
import tinycam.properties as p
import tinycam.settings as s
from tinycam.tasks import run_task


with s.SETTINGS.section('jobs/drill') as S:
    S.register('spindle_speed', s.CncIntegerSetting, default=1000, minimum=0, suffix='rpm')
    S.register('cut_depth', s.CncFloatSetting, default=0.1, minimum=0.0, suffix='{units}')
    S.register('cut_speed', s.CncFloatSetting, default=120.0, minimum=0.0, suffix='{units}/s')
    S.register('travel_height', s.CncFloatSetting, default=2.0, suffix='{units}')


class CncDrillJob(CncJob):
    def __init__(self,
                 source_item,
                 color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6),
                 tool_diameter=0.1,
                 spindle_speed=None,
                 cut_depth=None,
                 cut_speed=None,
                 travel_height=None):
        super().__init__(
            'Drill %s' % source_item.name,
            color=color,
        )

        self._source_item = source_item

        defaults = s.SETTINGS.section('jobs/drill')

        self._tool_diameter = tool_diameter
        self._spindle_speed = spindle_speed or defaults['spindle_speed'].value
        self._cut_depth = cut_depth or defaults['cut_depth'].value
        self._cut_speed = cut_speed or defaults['cut_speed'].value
        self._travel_height = travel_height or defaults['travel_height'].value

        self._geometry = None
        self._updating_geometry = False
        # TODO:
        # self._source_item.changed.connect(self._on_source_item_changed)
        self._update_geometry()

    @property
    def geometry(self):
        return self._geometry

    def _update(self):
        self._update_geometry()
        self._signal_changed()

    tool_diameter = p.Property[float](on_update=_update)
    mill_bigger_holes = p.Property[bool](on_update=_update)
    cut_depth = p.Property[float](on_update=_update)
    cut_speed = p.Property[float](on_update=_update)
    spindle_speed = p.Property[int](on_update=_update)
    travel_height = p.Property[float](on_update=_update)

    def _on_source_item_changed(self, _item):
        self._update()

    def _update_geometry(self):
        if self._updating_geometry:
            return

        self._updating_geometry = True

        @run_task('Drill Job')
        def work(status):
            tool_radius = self._tool_diameter * 0.5
            pass_offset = self._tool_diameter * (1 - self._pass_overlap / 100.0)

            geometry = None

            g = GLOBALS.GEOMETRY.simplify(
                GLOBALS.GEOMETRY.buffer(self._source_item.geometry, tool_radius),
                # TODO: parametrize into settings
                tolerance=0.01,
            )

            for pass_index in range(self._pass_count):
                for polygon in GLOBALS.GEOMETRY.polygons(g):
                    for exterior in GLOBALS.GEOMETRY.exteriors(polygon):
                        geometry = GLOBALS.GEOMETRY.union(geometry, exterior)
                    for interior in GLOBALS.GEOMETRY.interiors(polygon):
                        geometry = GLOBALS.GEOMETRY.union(geometry, interior)
                g = GLOBALS.GEOMETRY.buffer(g, pass_offset)

            self._geometry = geometry
            self._updating_geometry = False
            self._signal_updated()

    def _find_closest(self, lines, point):
        # TODO: implement finding closest line
        return 0

    def generate_commands(self):
        # TODO: allow selecting different starting positions
        builder = CncCommandBuilder(start_position=(0, 0, 0))

        lines = list(GLOBALS.GEOMETRY.lines(self._geometry))
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
