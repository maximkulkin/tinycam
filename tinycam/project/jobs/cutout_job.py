import enum
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
from tinycam.tools import CncTool, save_tool, load_tool


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
    CUT_DEPTH = S.register(
        'cut_depth', s.CncFloatSetting,
        default=2, minimum=0.0, suffix='{units}',
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
    def __init__(self):
        super().__init__()

        self.name = 'Cutout'
        self.color = QtGui.QColor.fromRgbF(1, 1, 0, 0.6)
        self._source_item = None

        self._tool = None
        self._cut_side = CutSide.OUTER
        self._cut_depth = CUT_DEPTH.value
        self._cut_multi_step = False
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

    @property
    def source_item(self) -> CncProjectItem | None:
        return self._source_item

    @source_item.setter
    def source_item(self, value: CncProjectItem):
        if self._source_item is value:
            return

        if self._source_item is not None:
            self._source_item.updated.disconnect(self._on_source_item_updated)

        self._source_item = value
        self.name = f'Cutout {self._source_item.name}'
        if self._source_item is not None:
            self._source_item.updated.connect(self._on_source_item_updated)
            self._update_geometry()

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
        p.Order(6),
        p.MinValue(0),
        p.Suffix('{units}'),
        p.EnabledIf(condition=lambda job: job.cut_multi_step),
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

    def save(self) -> dict:
        data = super().save()
        data['source_item_id'] = self._source_item.id if self._source_item else None
        data['cut_side'] = self.cut_side.name
        data['cut_depth'] = self.cut_depth
        data['cut_multi_step'] = self.cut_multi_step
        data['cut_depth_step'] = self.cut_depth_step
        data['cut_speed'] = self.cut_speed
        data['spindle_speed'] = self.spindle_speed
        data['travel_height'] = self.travel_height
        data['travel_speed'] = self.travel_speed
        data['tool'] = save_tool(self.tool)
        return data

    def load(self, data: dict) -> None:
        with self:
            super().load(data)
            self._source_item_id = data.get('source_item_id')
            if 'cut_side' in data:
                self.cut_side = CutSide[data['cut_side']]
            if 'cut_depth' in data:
                self.cut_depth = data['cut_depth']
            if 'cut_multi_step' in data:
                self.cut_multi_step = data['cut_multi_step']
            if 'cut_depth_step' in data:
                self.cut_depth_step = data['cut_depth_step']
            if 'cut_speed' in data:
                self.cut_speed = data['cut_speed']
            if 'spindle_speed' in data:
                self.spindle_speed = data['spindle_speed']
            if 'travel_height' in data:
                self.travel_height = data['travel_height']
            if 'travel_speed' in data:
                self.travel_speed = data['travel_speed']
            if 'tool' in data:
                self.tool = load_tool(data['tool'])

    def resolve_references(self, items_by_id: dict) -> None:
        if self._source_item_id and self._source_item_id in items_by_id:
            self.source_item = items_by_id[self._source_item_id]

    def _on_source_item_updated(self, _item):
        self._update_geometry()

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
            g = self._source_item.geometry

            match self.cut_side:
                case CutSide.INNER:
                    g = G.buffer(g, -tool_radius)
                case CutSide.OUTER:
                    g = G.buffer(g, tool_radius)
                case CutSide.CENTER:
                    pass

            g = G.simplify(g, tolerance=0.01)

            status.min_value = 0
            status.max_value = 1
            status.value = 0

            geometry = None

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

        if self.cut_multi_step:
            depths = []
            depth = 0.0
            while depth - self.cut_depth_step >= self.cut_depth:
                depth -= self.cut_depth_step
                depths.append(depth)

            if not math.isclose(depth, self.cut_depth):
                depths.append(self.cut_depth)
        else:
            depths = [self.cut_depth]

        for depth in depths:

            lines = list(GLOBALS.GEOMETRY.lines(self._geometry))
            while lines:
                line_idx = self._find_closest(lines, builder.current_position)
                line = lines.pop(line_idx)

                points = line.coords[:]

                builder.set_move_speed(self.travel_speed)
                builder.travel(z=self.travel_height)
                point = points[0]
                builder.travel(x=point[0], y=point[1])
                builder.set_move_speed(self.cut_speed)
                builder.cut(z=depth)

                for point in points[1:]:
                    builder.cut(x=point[0], y=point[1])

        builder.travel(z=self.travel_height)
        builder.travel(x=start_position[0], y=start_position[1])
        builder.travel(z=start_position[2])

        return builder.build()
