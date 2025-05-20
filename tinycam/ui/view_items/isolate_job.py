from typing import cast

from tinycam.commands import CncPathType, CncPathTracer
from tinycam.globals import GLOBALS
from tinycam.project import CncIsolateJob
from tinycam.types import Vector3, Vector4, Matrix44
from tinycam.ui.utils import qcolor_to_vec4
from tinycam.ui.view_items.core.line2d import Line2D
from tinycam.ui.view_items.core.line3d import Line3D
from tinycam.ui.view_items.project_item import CncProjectItemView


PATH_COLORS = {
    CncPathType.TRAVEL: Vector4(0, 0, 1, 1),
    CncPathType.CUT: Vector4(1, 0, 1, 1),
}


class CncPathView(Line3D):
    @property
    def color(self) -> Vector4:
        return self._color

    @color.setter
    def color(self, value: Vector4):
        pass


class CncIsolateJobView(CncProjectItemView[CncIsolateJob]):

    def _model_matrix(self):
        return Matrix44.identity()

    def _update_geometry(self):
        model = self._model

        if self._view_geometry is model.geometry and model.tool_diameter == self._tool_diameter:
            return

        self.clear_items()

        G = GLOBALS.GEOMETRY

        if model.geometry is not None:
            for line in G.lines(model.geometry):
                line_view = Line2D(
                    self.context,
                    G.points(line),
                    closed=line.is_closed,
                    color=qcolor_to_vec4(self._model.color),
                    width=model.tool_diameter,
                )
                self.add_item(line_view)

            commands = model.generate_commands()
            tracer = CncPathTracer()
            tracer.execute_commands(commands)

            current_path_points: list[Vector3] = []
            current_path_type = None
            for path in tracer.paths:
                if path.type != current_path_type:
                    if current_path_points:
                        path_view = CncPathView(
                            self.context,
                            current_path_points,
                            color=PATH_COLORS[current_path_type],
                        )
                        self.add_item(path_view)

                    current_path_points = [path.start, path.end]
                    current_path_type = path.type
                else:
                    current_path_points.append(path.end)

            if current_path_points:
                path_view = CncPathView(
                    self.context,
                    current_path_points,
                    color=PATH_COLORS[current_path_type],
                )
                self.add_item(path_view)

            self._view_geometry = self._model.geometry
            self._tool_diameter = self._model.tool_diameter
