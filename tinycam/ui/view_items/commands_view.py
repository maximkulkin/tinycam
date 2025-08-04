from tinycam.commands import CncCommand, CncPathType, CncPathTracer
from tinycam.types import Vector3
from tinycam.ui.view_items.core import Node3D
from tinycam.ui.view_items.path_view import CncPathView
from tinycam.ui.view import Context


class CncCommandsView(Node3D):
    def __init__(self, context: Context, commands: list[CncCommand]):
        super().__init__(context)

        tracer = CncPathTracer()
        tracer.execute_commands(commands)

        # This will separate all lines into segments of same path type
        # (e.g. travel vs cut) to allow coloring them at once
        current_path_points: list[Vector3] = []
        current_path_type = CncPathType.TRAVEL
        for path in tracer.paths:
            if path.type != current_path_type:
                if current_path_points:
                    path_view = CncPathView(
                        self.context,
                        points=current_path_points,
                        path_type=current_path_type,
                    )
                    self.add_child(path_view)

                current_path_points = [path.start, path.end]
                current_path_type = path.type
            else:
                current_path_points.append(path.end)

        if current_path_points:
            path_view = CncPathView(
                self.context,
                points=current_path_points,
                path_type=current_path_type,
            )
            self.add_child(path_view)
