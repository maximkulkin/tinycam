from tinycam.commands import CncPathTracer
from tinycam.globals import GLOBALS
from tinycam.project import CncIsolateJob
from tinycam.ui.utils import qcolor_to_vec4
from tinycam.ui.view import Context
from tinycam.ui.view_items.core import Line2D, Node3D
from tinycam.ui.view_items.core.line2d import JointStyle
from tinycam.ui.view_items.commands_view import CncCommandsView
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.view_items.tool import Tool


class CncIsolateJobView(CncProjectItemView[CncIsolateJob]):
    def __init__(self, context: Context, model: CncIsolateJob):
        super().__init__(context, model)

        model.progress_changed.connect(self._on_progress_changed)

    def _update_geometry(self):
        model = self._model
        tool_diameter = model.tool.get_diameter(model.cut_depth) if model.tool is not None else 0

        self.clear_children()

        self._outline = None
        self._path = None
        self._tool = None
        self._tracer = None

        G = GLOBALS.GEOMETRY

        if model.geometry is not None:
            self._outline = Node3D(self.context)
            for line in G.lines(model.geometry):
                line_view = Line2D(
                    self.context,
                    G.points(line),
                    closed=line.is_closed,
                    color=qcolor_to_vec4(self._model.color),
                    width=tool_diameter,
                    miter_limit=tool_diameter,
                    max_segment_length=tool_diameter * 8,
                    joint_style=JointStyle.MITER,
                )
                self._outline.add_child(line_view)

            commands = model.generate_commands()
            self._path = CncCommandsView(self.context, commands)

            self._tracer = CncPathTracer()
            self._tracer.execute_commands(commands)

            self._geometry = self._model.geometry

        if self.model.tool is not None:
            if self._tool is not None and self._tool.tool != self.model.tool:
                if self.has_child(self._tool):
                    self.remove_child(self._tool)

            self._tool = Tool(self.context, tool=self.model.tool)

        if self._outline is not None:
            if model.show_outline:
                self.add_child(self._outline)
            else:
                self.remove_child(self._outline)

        if self._path is not None:
            if model.show_path:
                self.add_child(self._path)
                if self._tool and self.model.selected:
                    self.add_child(self._tool)
            else:
                self.remove_child(self._path)
                if self._tool:
                    self.remove_child(self._tool)

    def _on_progress_changed(self, progress: float):
        assert self._tool is not None
        assert self._tracer is not None

        self._tool.world_position = self._tracer.calculate_position(
            distance=progress,
        )
