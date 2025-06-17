from functools import partial
from typing import override

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt

from tinycam.formats import excellon
from tinycam.geometry import Line
from tinycam.globals import GLOBALS
from tinycam.project import ExcellonItem
from tinycam.commands import CncCommand, CncCommandBuilder
from tinycam.project.jobs.job import CncJob
import tinycam.properties as p
import tinycam.ui.property_editor as pe
import tinycam.settings as s
from tinycam.tasks import run_task
from tinycam.tools import CncTool


with s.SETTINGS.section('jobs/drill') as S:
    CUT_DEPTH = S.register(
        'cut_depth', s.CncFloatSetting,
        default=0.1, minimum=0.0, suffix='{units}',
    )
    CUT_SPEED = S.register(
        'cut_speed', s.CncFloatSetting,
        default=120.0, minimum=0.0, suffix='{units}/s',
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


class SelectedHoleSizesEditor(pe.BasePropertyEditor[dict[excellon.Tool, bool]]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._editor = QtWidgets.QTableWidget()
        self._editor.setRowCount(0)
        self._editor.setColumnCount(2)
        self._editor.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self._editor.horizontalHeader().hide()
        self._editor.verticalHeader().hide()

        self._updating = False

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    @override
    def value(self) -> dict[excellon.Tool, CncTool]:
        return self._value

    @override
    def setValue(self, value: dict[excellon.Tool, CncTool]):
        self._updating = True

        self._value = value
        self._editor.clearContents()
        self._editor.setRowCount(len(value))
        for i, (k, v) in enumerate(sorted(value.items(), key=lambda x: x[0].diameter)):
            self._editor.setItem(i, 0, QtWidgets.QTableWidgetItem(
                f'dia={k.diameter}'
            ))

            selector = QtWidgets.QCheckBox()
            selector.setChecked(v)
            selector.checkStateChanged.connect(partial(self._on_check_changed, k))
            self._editor.setCellWidget(i, 1, selector)

        self._updating = False

    def _on_check_changed(self, tool: excellon.Tool, state: Qt.CheckState):
        if self._updating:
            return

        new_value = state == Qt.CheckState.Checked
        if new_value == self._value[tool]:
            return

        self._value[tool] = new_value
        self.valueChanged.emit(self._value)


class CncDrillJob(CncJob):
    def __init__(self,
                 source_item: ExcellonItem,
                 color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6),
                 tool: CncTool | None = None,
                 mill_holes: bool | None = None,
                 cut_depth: float | None = None,
                 cut_speed: float | None = None,
                 spindle_speed: float | None = None,
                 travel_height: float | None = None,
                 travel_speed: float | None = None):
        super().__init__(
            'Drill %s' % source_item.name,
            color=color,
        )

        self._source_item = source_item

        self._tool = tool
        self._hole_sizes = {
            tool: False
            for tool in self._source_item.tools
        }
        self._mill_holes = mill_holes or False
        self._cut_depth = cut_depth or CUT_DEPTH.value
        self._cut_speed = cut_speed or CUT_SPEED.value
        self._travel_height = travel_height or TRAVEL_HEIGHT.value
        self._travel_speed = travel_speed or TRAVEL_SPEED.value
        self._spindle_speed = spindle_speed or SPINDLE_SPEED.value

        self._geometry = None
        self._updating_geometry = False

        self._update_geometry()

    @property
    def geometry(self):
        return self._geometry

    def _update(self):
        self._update_geometry()
        self._signal_changed()

    show_outline = p.Property[bool](on_update=_update, default=True, metadata=[p.Order(0)])
    show_path = p.Property[bool](on_update=_update, default=True, metadata=[p.Order(1)])
    tool = p.Property[CncTool](on_update=_update, default=None, metadata=[
        p.Order(2),
    ])
    hole_sizes = p.Property[dict[excellon.Tool, CncTool]](on_update=_update, metadata=[
        p.Order(3),
        pe.Editor(SelectedHoleSizesEditor),
    ])
    mill_holes = p.Property[bool](on_update=_update, metadata=[
        p.Order(4),
    ])
    cut_depth = p.Property[float](on_update=_update, metadata=[
        p.Order(5),
        p.MinValue(0),
        p.Suffix('{units}'),
    ])
    cut_speed = p.Property[float](on_update=_update, metadata=[
        p.Order(6),
        p.Suffix('{units}/min'),
    ])
    spindle_speed = p.Property[int](on_update=_update, metadata=[
        p.Order(7),
        p.Suffix('rpm'),
        p.MinValue(0),
        p.MaxValue(100000),
    ])
    travel_height = p.Property[float](on_update=_update, metadata=[
        p.Order(8),
        p.Suffix('{units}'),
    ])
    travel_speed = p.Property[float](on_update=_update, metadata=[
        p.Order(9),
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

        tools = {
            tool.id: tool
            for tool in self._source_item.tools
        }
        tool_enabled = {
            tool.id: self._hole_sizes.get(tool, False)
            for tool in self._source_item.tools
        }

        @run_task('Drill Job', self._signal_updated)
        def work(status):
            tool_diameter = self.tool.get_diameter(self.cut_depth)

            G = GLOBALS.GEOMETRY

            geometry = None

            for drill in self._source_item.drills:
                if not tool_enabled[drill.tool_id]:
                    continue

                point = self._transform_point(drill.position)
                diameter = tool_diameter
                if self.mill_holes:
                    diameter = max(diameter, tools[drill.tool_id].diameter)
                geometry = G.union(
                    geometry,
                    G.circle(diameter, center=point),
                )

            if self.mill_holes:
                for mill in self._source_item.mills:
                    if not tool_enabled[drill.tool_id]:
                        continue

                    diameter = tool_diameter
                    if self.mill_holes:
                        diameter = max(diameter, tools[drill.tool_id].diameter)

                    # TODO: implement proper milling algorithm
                    line = G.buffer(
                        G.line([self._transform_point(point)
                                for point in mill.positions]),
                        0.5 * diameter,
                    )
                    geometry = G.union(geometry, line)

            self._geometry = geometry
            self._updating_geometry = False

    def _transform_point(self, point: tuple[float, float]) -> tuple[float, float]:
        return point * self._source_item.scale + self._source_item.offset

    def _find_closest(self, lines: list[Line], point) -> int:
        # TODO: implement finding closest line
        return 0

    def generate_commands(self) -> list[CncCommand]:
        # TODO: allow selecting different starting positions
        start_position = (0, 0, 0)
        builder = CncCommandBuilder(start_position=start_position)

        tool_enabled = {
            tool.id: self._hole_sizes.get(tool, False)
            for tool in self._source_item.tools
        }

        for drill in self._source_item.drills:
            if not tool_enabled[drill.tool_id]:
                continue

            point = self._transform_point(drill.position)

            builder.travel(z=self._travel_height)
            builder.travel(x=point[0], y=point[1])
            if not self.mill_holes:
                builder.cut(z=-self._cut_depth)
            else:
                pass

        if self.mill_holes:
            for mill in self._source_item.mills:
                if not tool_enabled[mill.tool_id]:
                    continue

                point = self._transform_point(mill.positions[0])

                builder.travel(z=self._travel_height)
                builder.travel(x=point[0], y=point[1])
                builder.cut(z=-self._cut_depth)

                # TODO: implement proper milling algorithm
                for point in mill.positions[1:]:
                    point = self._transform_point(point)
                    builder.cut(x=point[0], y=point[1])

        builder.travel(z=self.travel_height)
        builder.travel(x=start_position[0], y=start_position[1])
        builder.travel(z=start_position[2])

        return builder.build()
