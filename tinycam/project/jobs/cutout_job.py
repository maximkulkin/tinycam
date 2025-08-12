import enum

from PySide6 import QtGui

from tinycam.commands import CncCommand, CncCommandBuilder
from tinycam.geometry import Line
from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.project.jobs.job import CncJob
import tinycam.properties as p
import tinycam.settings as s
from tinycam.tasks import run_task
from tinycam.tools import CncTool


class CutSide(enum.Enum):
    INNER = enum.auto()
    OUTER = enum.auto()
    CENTER = enum.auto()

    def __str__(self) -> str:
        match self:
            case CutSide.INNER: return 'Inner'
            case CutSide.OUTER: return 'Outer'
            case CutSide.CENTER: return 'Center'


with s.SETTINGS.section('jobs/cutout') as S:
    CUT_SIDE = S.register(
        'cut_side', s.CncEnumSetting[CutSide],
        default=CutSide.OUTER,
    )
    CUT_DEPTH = S.register(
        'cut_depth', s.CncFloatSetting,
        default=2, minimum=0.0, suffix='{units}',
    )
    CUT_DEPTH_STEP = S.register(
        'cut_depth_step', s.CncFloatSetting,
        default=0.5, minimum=0.0, suffix='{units}',
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


class CncCutoutJob(CncJob):
    def __init__(self, source_item: CncProjectItem):
        super().__init__(
            'Isolate %s' % source_item.name,
            color=QtGui.QColor.fromRgbF(1, 1, 0, 0.6),
        )

        self._source_item = source_item

        self._tool = None
        self._cut_side = CUT_SIDE.value
        self._cut_depth = CUT_DEPTH.value
        self._cut_depth_step = CUT_DEPTH.value
        self._cut_speed = CUT_SPEED.value
        self._spindle_speed = SPINDLE_SPEED.value
        self._travel_height = TRAVEL_HEIGHT.value
        self._travel_speed = TRAVEL_SPEED.value

        self._geometry = None

        self._updating_geometry = False
        self._update_geometry()

    @property
    def geometry(self):
        return self._geometry

    def _update(self):
        self._update_geometry()
        self._signal_changed()

    tool = p.Property[CncTool](on_update=_update, default=None, metadata=[
        p.Order(2),
    ])
    cut_side = p.Property[CutSide](on_update=_update, metadata=[
        p.Order(3),
    ])
    cut_depth = p.Property[float](on_update=_update, metadata=[
        p.Order(4),
        p.MinValue(0),
        p.Suffix('{units}'),
    ])
    cut_multi_step = p.Property[bool](on_update=_update, metadata=[
        p.Order(5),
        p.Description('Cut with multiple passes, slowly descending'),
    ])
    cut_depth_step = p.Property[float](on_update=_update, metadata=[
        p.Order(5),
        p.MinValue(0),
        p.Suffix('{units}'),
        p.EnabledIf(condition=lambda job: job.cut_multi_step.value),
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

        @run_task('Cutout job', self._signal_changed)
        def work(status):
            tool_diameter = self.tool.get_diameter(self.cut_depth)

            tool_radius = tool_diameter * 0.5

            G = GLOBALS.GEOMETRY
            g = G.translate(
                G.scale(
                    self._source_item.geometry,
                    self._source_item.scale,
                ),
                self._source_item.offset,
            )
            match self.cut_side:
                case CutSide.INNER:
                    g = G.buffer(g, -tool_radius)
                case CutSide.OUTER:
                    g = G.buffer(g, tool_radius)
                case CutSide.CENTER:
                    pass

            g = G.simplify(g, tolerance=0.01)

            if self.cut_multi_step:
                passes = self.cut_depth / self.cut_depth_step
                if self.cut_depth > self.cut_depth_step * passes:
                    passes += 1
            else:
                passes = 1

            status.min_value = 0
            status.max_value = passes
            status.value = 0

            geometry = None

            for pass_index in range(self._pass_count):
                for polygon in G.polygons(g):
                    for exterior in G.exteriors(polygon):
                        geometry = G.union(geometry, exterior)
                    for interior in G.interiors(polygon):
                        geometry = G.union(geometry, interior)

                    status.value += 1

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
            point = self._transform_point(points[0])
            builder.travel(x=point[0], y=point[1])
            builder.set_cut_speed(self.cut_speed)
            builder.cut(z=-self.cut_depth)

            for point in points[1:]:
                point = self._transform_point(point)
                builder.cut(x=point[0], y=point[1])

        builder.travel(z=self.travel_height)
        builder.travel(x=start_position[0], y=start_position[1])
        builder.travel(z=start_position[2])

        return builder.build()

    def _transform_point(self, point: tuple[float, float]) -> tuple[float, float]:
        return point * self._source_item.scale + self._source_item.offset
