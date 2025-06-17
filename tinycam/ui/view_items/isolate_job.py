from tinycam.globals import GLOBALS
from tinycam.project import CncIsolateJob
from tinycam.types import Matrix44
from tinycam.ui.utils import qcolor_to_vec4
from tinycam.ui.view_items.core.line2d import Line2D
from tinycam.ui.view_items.commands_view import CncCommandsView
from tinycam.ui.view_items.project_item import CncProjectItemView


class CncIsolateJobView(CncProjectItemView[CncIsolateJob]):

    def _model_matrix(self):
        return Matrix44.identity()

    def _update_geometry(self):
        model = self._model
        tool_diameter = model.get_tool_diameter(model.cut_depth)

        if model.geometry is self._geometry and tool_diameter == self._tool_diameter:
            return

        self.clear_items()

        G = GLOBALS.GEOMETRY

        if model.geometry is not None:
            if model.show_outline:
                for line in G.lines(model.geometry):
                    line_view = Line2D(
                        self.context,
                        G.points(line),
                        closed=line.is_closed,
                        color=qcolor_to_vec4(self._model.color),
                        width=tool_diameter,
                    )
                    self.add_item(line_view)

            if model.show_path:
                commands = model.generate_commands()
                commands_view = CncCommandsView(self.context, commands)
                self.add_item(commands_view)

            self._geometry = self._model.geometry
            self._tool_diameter = tool_diameter
