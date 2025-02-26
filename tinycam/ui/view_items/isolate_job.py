from PySide6 import QtGui
from tinycam.commands import CncPathType, CncPathTracer
from tinycam.globals import GLOBALS
from tinycam.types import Vector3, Vector4, Matrix44
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


class CncIsolateJobView(CncProjectItemView):

    def _model_matrix(self):
        return Matrix44.identity()

    def _update_geometry(self):
        if self._view_geometry is self._model.geometry and self._model.tool_diameter == self._tool_diameter:
            return

        self.clear_items()

        G = GLOBALS.GEOMETRY

        if self._model.geometry is not None:
            for line in G.lines(self._model.geometry):
                line_view = Line2D(
                    self.context,
                    G.points(self._transform_geometry(self._model, line)),
                    closed=line.is_closed,
                    color=qcolor_to_vec4(self._model.color),
                    width=self._model.tool_diameter,
                )
                self.add_item(line_view)

            commands = self._model.generate_commands()
            tracer = CncPathTracer()
            tracer.execute_commands(commands)

            current_path_points = []
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

                    current_path_points = [path.start * Vector3(1, -1, 1), path.end * Vector3(1, -1, 1)]
                    current_path_type = path.type
                else:
                    current_path_points.append(path.end * Vector3(1, -1, 1))

            if current_path_points:
                path_view = CncPathView(
                    self.context,
                    current_path_points,
                    color=PATH_COLORS[current_path_type],
                )
                self.add_item(path_view)

            self._view_geometry = self._model.geometry
            self._tool_diameter = self._model.tool_diameter
