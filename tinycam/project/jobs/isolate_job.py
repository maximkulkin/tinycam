from PySide6 import QtGui

from tinycam.commands import CncCommandBuilder
from tinycam.geometry import Line
from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.project.jobs.job import CncJob
from tinycam.properties import IntProperty, FloatProperty, BoolProperty
import tinycam.settings as s
from tinycam.tasks import run_task


with s.SETTINGS.section('jobs/isolate') as S:
    S.register('spindle_speed', s.CncIntegerSetting, default=1000, minimum=0, maximum=100000, suffix='rpm')
    S.register('cut_depth', s.CncFloatSetting, default=0.1, suffix='{units}')
    S.register('cut_speed', s.CncFloatSetting, default=120.0, suffix='{units}/s')
    S.register('travel_height', s.CncFloatSetting, default=2.0, suffix='{units}')
    S.register('pass_count', s.CncIntegerSetting, minimum=1, default=1)
    S.register('pass_overlap', s.CncIntegerSetting,
               minimum=0, maximum=100, default=10, suffix='%')


class CncIsolateJob(CncJob):
    def __init__(self,
                 source_item: CncProjectItem,
                 color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6),
                 tool_diameter: float = 0.1,
                 spindle_speed: int | None = None,
                 cut_depth: float | None = None,
                 cut_speed: float | None = None,
                 travel_height: float | None = None,
                 pass_count: int | None = None,
                 pass_overlap: int | None = None):
        super().__init__(
            'Isolate %s' % source_item.name,
            color=color,
        )

        self._source_item = source_item
        # self._source_item.changed.connect(self._on_source_item_changed)

        defaults = s.SETTINGS.section('jobs/isolate')

        self._tool_diameter = tool_diameter
        self._cut_depth = cut_depth or defaults['cut_depth'].value
        self._cut_speed = cut_speed or defaults['cut_speed'].value
        self._pass_count = pass_count or defaults['pass_count'].value
        self._pass_overlap = pass_overlap or defaults['pass_overlap'].value
        self._spindle_speed = spindle_speed or defaults['spindle_speed'].value
        self._travel_height = travel_height or defaults['travel_height'].value
        self._show_outline = True
        self._show_path = True

        self._geometry = None

        self._updating_geometry = False
        self._update_geometry()

    @property
    def geometry(self):
        return self._geometry

    def _update(self):
        self._update_geometry()
        self._signal_changed()

    tool_diameter = FloatProperty(on_update=_update)
    pass_count = IntProperty(on_update=_update)
    pass_overlap = IntProperty(on_update=_update, suffix=' %')
    cut_depth = FloatProperty(on_update=_update)
    cut_speed = FloatProperty(on_update=_update)
    spindle_speed = IntProperty(on_update=_update)
    travel_height = FloatProperty(on_update=_update)
    show_outline = BoolProperty(on_update=_update)
    show_path = BoolProperty(on_update=_update)

    def _on_source_item_changed(self, _item):
        self._update()

    def _update_geometry(self):
        if self._updating_geometry:
            return

        self._updating_geometry = True

        @run_task('Isolate job')
        def work(status):
            tool_radius = self._tool_diameter * 0.5
            pass_offset = self._tool_diameter * (1 - self._pass_overlap / 100.0)

            G = GLOBALS.GEOMETRY
            g = G.simplify(
                G.buffer(
                    G.translate(
                        G.scale(
                            self._source_item.geometry,
                            self._source_item.scale,
                        ),
                        self._source_item.offset,
                    ),
                    tool_radius,
                ),
                # TODO: parametrize into settings
                tolerance=0.01,
            )

            status.min_value = 0
            status.max_value = self._pass_count * len(G.polygons(g))
            status.value = 0

            geometry = None

            for pass_index in range(self._pass_count):
                for polygon in G.polygons(g):
                    for exterior in G.exteriors(polygon):
                        geometry = G.union(geometry, exterior)
                    for interior in G.interiors(polygon):
                        geometry = G.union(geometry, interior)

                    status.value += 1

                g = G.buffer(g, pass_offset)

            self._geometry = geometry
            self._updating_geometry = False
            self._signal_updated()

    def _find_closest(self, lines: list[Line], point) -> int:
        # TODO: implement finding index of nearest line
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
            #     # It's a closed shape, find any closest point and rotate all points
            #     # to make that one first
            #     p, _ = GLOBALS.GEOMETRY.nearest(line, shapely.Point(builder.current_position[:2]))
            #     print(points)
            #     start_index = points.index(p)
            #     points = points[start_index:] + points[:start_index]
            # else:
            #     # Shape is open, pick the closest end and start with it
            #     # TODO:

            builder.travel(z=self._travel_height)
            builder.travel(x=points[0][0], y=points[0][1])
            builder.cut(z=-self._cut_depth)

            for p in points[1:]:
                builder.cut(x=p[0], y=p[1])

        return builder.build()
