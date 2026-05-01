from typing import override

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt

from tinycam.commands import CncCommand, CncCommandBuilder
from tinycam.geometry import Line
from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.project.jobs.job import CncJob
import tinycam.properties as p
import tinycam.settings as s
from tinycam.signals import Signal
from tinycam.tasks import run_task
from tinycam.tools import CncTool, save_tool, load_tool
import tinycam.ui.property_editor as pe


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


class ProgressEditor(pe.BasePropertyEditor[float]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._editor = QtWidgets.QSlider(Qt.Orientation.Horizontal, parent=self)
        self._editor.setMinimum(0)
        self._editor.setMaximum(100000)
        self._editor.valueChanged.connect(self._on_value_changed)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    def value(self) -> float:
        return self._editor.value()

    def setValue(self, value: float):
        self._editor.setValue(int(value))

    @override
    def setEnabled(self, value: bool):
        super().setEnabled(value)
        self._editor.setEnabled(self.enabled())

    def _on_value_changed(self, value: int):
        self.valueChanged.emit(value)


class CncIsolateJob(CncJob):
    progress_changed = Signal[float]()

    def __init__(self):
        super().__init__()

        self._source_item = None
        self.color = QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6)

        self._show_outline = True
        self._show_path = True
        self._tool = None
        self._pass_count = PASS_COUNT.value
        self._pass_overlap = PASS_OVERLAP.value
        self._cut_depth = CUT_DEPTH.value
        self._cut_speed = CUT_SPEED.value
        self._spindle_speed = SPINDLE_SPEED.value
        self._travel_height = TRAVEL_HEIGHT.value
        self._travel_speed = TRAVEL_SPEED.value

        self._updating_geometry = False
        self._update_geometry()

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
        self.name = f'Isolate {self._source_item.name}'
        if self._source_item is not None:
            self._source_item.updated.connect(self._on_source_item_updated)
            self._update_geometry()

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

    def _on_progress_changed(self):
        self.progress_changed.emit(self.progress)

    progress = p.Property[float](on_update=_on_progress_changed, default=0., metadata=[
        p.Order(11),
        p.MinValue(0),
        pe.Editor(ProgressEditor),
    ])

    def save(self) -> dict:
        data = super().save()
        data['source_item_id'] = self._source_item.id if self._source_item else None
        data['show_outline'] = self.show_outline
        data['show_path'] = self.show_path
        data['pass_count'] = self.pass_count
        data['pass_overlap'] = self.pass_overlap
        data['cut_depth'] = self.cut_depth
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
            if 'show_outline' in data:
                self.show_outline = data['show_outline']
            if 'show_path' in data:
                self.show_path = data['show_path']
            if 'pass_count' in data:
                self.pass_count = data['pass_count']
            if 'pass_overlap' in data:
                self.pass_overlap = data['pass_overlap']
            if 'cut_depth' in data:
                self.cut_depth = data['cut_depth']
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

        if self.source_item is None:
            self._geometry = None
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
                    self._source_item.geometry,
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

            builder.set_move_speed(self.travel_speed)
            builder.travel(z=self.travel_height)
            point = points[0]
            builder.travel(x=point[0], y=point[1])
            builder.set_move_speed(self.cut_speed)
            builder.cut(z=-self.cut_depth)

            for point in points[1:]:
                builder.cut(x=point[0], y=point[1])

        builder.travel(z=self.travel_height)
        builder.travel(x=start_position[0], y=start_position[1])
        builder.travel(z=start_position[2])

        return builder.build()
