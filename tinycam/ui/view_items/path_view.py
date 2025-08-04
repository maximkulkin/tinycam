from tinycam.commands import CncPathType
from tinycam.types import Vector2, Vector3, Vector4
from tinycam.ui.view import Context
from tinycam.ui.view_items.core.direction_markers import DirectionMarkers
from tinycam.ui.view_items.core import Node3D
from tinycam.ui.view_items.core.line3d import Line3D


PATH_COLORS = {
    CncPathType.TRAVEL: Vector4(0, 0, 1, 1),
    CncPathType.CUT: Vector4(1, 0, 1, 1),
}


class CncPathView(Node3D):
    def __init__(
        self,
        context: Context,
        path_type: CncPathType,
        points: list[Vector3],
        closed: bool = False,
        width: float | None = None,
    ):
        super().__init__(context)

        self._color = PATH_COLORS[path_type]

        if len(points) > 1:
            self._line = Line3D(
                context,
                points=points,
                closed=closed,
                width=width,
                color=self._color,
            )
            self.add_child(self._line)

        marker_positions = []
        marker_directions = []
        for p1, p2 in zip(points, points[1:]):
            v = p2 - p1

            if v.length > 2.0:
                marker_positions.append(p1 + 0.3 * v)
                marker_directions.append(v)

        if len(marker_positions) > 0:
            self._markers = DirectionMarkers(
                self.context,
                positions=marker_positions,
                directions=marker_directions,
                size=Vector2(0.5, 0.25),
                color=self._color,
            )
            self.add_child(self._markers)

    @property
    def color(self) -> Vector4:
        return self._color

    @color.setter
    def color(self, value: Vector4):
        # Can't change the color, it is determined by path type
        pass
