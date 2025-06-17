import math

from PySide6 import QtGui

from tinycam.commands import CncCommand, CncCommandBuilder
from tinycam.geometry import Line
from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.project.jobs.job import CncJob
import tinycam.properties as p
import tinycam.settings as s
from tinycam.tasks import run_task
from tinycam.tools import CncTool, CncToolType


with s.SETTINGS.section('jobs/isolate') as S:
    PASS_COUNT = S.register(
        'pass_count', s.CncIntegerSetting,
        default=1, minimum=1,
    )
    PASS_OVERLAP = S.register(
        'pass_overlap', s.CncIntegerSetting,
        default=10, minimum=0, maximum=99, suffix='%',
    )
    CUT_DEPTH = S.register(
        'cut_depth', s.CncFloatSetting,
        default=0.1, minimum=0.0, suffix='{units}',
    )
    CUT_SPEED = S.register(
        'cut_speed', s.CncFloatSetting,
        default=120.0, minimum=1.0, suffix='{units}/min',
    )
    TRAVEL_HEIGHT = S.register(
        'travel_height', s.CncFloatSetting,
        default=2.0, suffix='{units}',
    )
    TRAVEL_SPEED = S.register(
        'travel_speed', s.CncFloatSetting,
        default=300.0, minimum=0.0, suffix='{units}/min',
    )
    SPINDLE_SPEED = S.register(
        'spindle_speed', s.CncIntegerSetting,
        default=1000, minimum=0, maximum=100000, suffix='rpm',
    )


class CncIsolateJob(CncJob):
    def __init__(self,
                 source_item: CncProjectItem,
                 color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6),
                 tool: CncTool | None = None,
                 spindle_speed: int | None = None,
                 cut_depth: float | None = None,
                 cut_speed: float | None = None,
                 travel_height: float | None = None,
                 travel_speed: float | None = None,
                 pass_count: int | None = None,
                 pass_overlap: int | None = None):
        super().__init__(
            'Isolate %s' % source_item.name,
            color=color,
        )

        self._source_item = source_item

        self._show_outline = True
        self._show_path = True
        self._tool = tool
        self._pass_count = pass_count or PASS_COUNT.value
        self._pass_overlap = pass_overlap or PASS_OVERLAP.value
        self._cut_depth = cut_depth or CUT_DEPTH.value
        self._cut_speed = cut_speed or CUT_SPEED.value
        self._spindle_speed = spindle_speed or SPINDLE_SPEED.value
        self._travel_height = travel_height or TRAVEL_HEIGHT.value
        self._travel_speed = travel_speed or TRAVEL_SPEED.value

        self._geometry = None

        self._updating_geometry = False
        self._update_geometry()

    @property
    def geometry(self):
        return self._geometry

    def _update(self):
        self._update_geometry()
        self._signal_changed()

    show_outline = p.Property[bool](on_update=_update, metadata=[p.Order(0)])
    show_path = p.Property[bool](on_update=_update, metadata=[p.Order(1)])
    tool = p.Property[CncTool](on_update=_update, default=None, metadata=[
        p.Order(2),
    ])
    pass_count = p.Property[int](on_update=_update, metadata=[
        p.Order(4),
        p.MinValue(1),
    ])
    pass_overlap = p.Property[int](on_update=_update, metadata=[
        p.Order(5),
        p.Suffix(' %'),
        p.MinValue(0),
        p.MaxValue(99),
    ])
    cut_depth = p.Property[float](on_update=_update, metadata=[
        p.Order(6),
        p.MinValue(0),
        p.Suffix('{units}'),
    ])
    cut_speed = p.Property[float](on_update=_update, metadata=[
        p.Order(7),
        p.Suffix('{units}/min'),
    ])
    spindle_speed = p.Property[int](on_update=_update, metadata=[
        p.Order(8),
        p.Suffix('rpm'),
        p.MinValue(0),
        p.MaxValue(100000),
    ])
    travel_height = p.Property[float](on_update=_update, metadata=[
        p.Order(9),
        p.Suffix('{units}'),
    ])
    travel_speed = p.Property[float](on_update=_update, metadata=[
        p.Order(10),
        p.MinValue(0),
        p.Suffix('{units}/min'),
    ])

    def _on_source_item_changed(self, _item):
        self._update()

    def _update_geometry(self):
        if self._updating_geometry:
            return

        if self.tool is None:
            self._geometry = None
            return

        self._updating_geometry = True

        @run_task('Isolate job', self._signal_changed)
        def work(status):
            tool_diameter = self.tool.get_diameter(self.cut_depth)

            tool_radius = tool_diameter * 0.5
            pass_offset = tool_diameter * (1 - self._pass_overlap / 100.0)

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

    def _find_closest(self, lines: list[Line], point) -> int:
        # TODO: implement finding index of nearest line
        return 0

    def generate_commands(self) -> list[CncCommand]:
        # TODO: allow selecting different starting positions
        start_position = (0, 0, 0)
        builder = CncCommandBuilder(start_position=start_position)

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

            builder.set_cut_speed(self.travel_speed)
            builder.travel(z=self.travel_height)
            builder.travel(x=points[0][0], y=points[0][1])
            builder.set_cut_speed(self.cut_speed)
            builder.cut(z=-self.cut_depth)

            for point in points[1:]:
                builder.cut(x=point[0], y=point[1])

        builder.travel(z=self.travel_height)
        builder.travel(x=start_position[0], y=start_position[1])
        builder.travel(z=start_position[2])

        return builder.build()
