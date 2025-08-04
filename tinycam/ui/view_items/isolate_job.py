from tinycam.globals import GLOBALS
from tinycam.project import CncIsolateJob
from tinycam.types import Vector3
from tinycam.ui.utils import qcolor_to_vec4
from tinycam.ui.view_items.core import Line2D, Node3D
from tinycam.ui.view_items.commands_view import CncCommandsView
from tinycam.ui.view_items.project_item import CncProjectItemView


class CncIsolateJobView(CncProjectItemView[CncIsolateJob]):

    def _update_geometry(self):
        model = self._model
        tool_diameter = model.tool.get_diameter(model.cut_depth) if model.tool is not None else 0

        # if model.geometry is self._geometry and tool_diameter == self._tool_diameter:
        #     return

        self.clear_children()
        self._outline = None
        self._path = None

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
                )
                self._outline.add_child(line_view)

            self._path = CncCommandsView(self.context, model.generate_commands())
            self._path.global_position = Vector3()

            self._geometry = self._model.geometry
            self._tool_diameter = tool_diameter

        if self._outline is not None:
            if model.show_outline:
                self.add_child(self._outline)
            else:
                self.remove_child(self._outline)

        if self._path is not None:
            if model.show_path:
                self.add_child(self._path)
            else:
                self.remove_child(self._path)
