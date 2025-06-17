from tinycam.globals import GLOBALS
from tinycam.project import CncDrillJob
from tinycam.types import Matrix44
from tinycam.ui.utils import qcolor_to_vec4
from tinycam.ui.view_items.core.polygon import Polygon
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.view_items.commands_view import CncCommandsView


class CncDrillJobView(CncProjectItemView[CncDrillJob]):

    def _model_matrix(self):
        return Matrix44.identity()

    def _update_geometry(self):
        model = self._model
        tool_diameter = model.tool.get_diameter(model.cut_depth) if model.tool is not None else 0

        if model.geometry is self._geometry and tool_diameter == self._tool_diameter:
            return

        self.clear_items()

        G = GLOBALS.GEOMETRY

        if model.geometry is not None and model.show_outline:
            for polygon in G.polygons(model.geometry):
                polygon_view = Polygon(
                    self.context,
                    polygon,
                    color=qcolor_to_vec4(self._model.color),
                )
                self.add_item(polygon_view)

        if model.show_path:
            commands = model.generate_commands()
            commands_view = CncCommandsView(self.context, commands)
            self.add_item(commands_view)

        self._geometry = self._model.geometry
        self._tool_diameter = tool_diameter
