from collections.abc import Sequence
import moderngl as mgl
import numpy as np
from typing import Optional
from tinycam.types import Vector2, Vector4
from tinycam.ui.view import Context, ViewItem, RenderState


type Point2 = Vector2


class Line2D(ViewItem):
    def __init__(
        self,
        context: Context,
        points: Sequence[Vector2],
        closed: bool = False,
        color: Vector4 = Vector4(0.8, 0.8, 0.8, 1.0),
        width: Optional[float] = None,
    ):
        super().__init__(context)

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                uniform mat4 mvp;
                in vec2 position;

                void main() {
                    gl_Position = mvp * vec4(position.x, position.y, 0.0, 1.0);
                }
            ''',
            fragment_shader='''
                #version 410 core

                uniform vec4 color;
                out vec4 fragColor;

                void main() {
                    fragColor = color;
                }
            ''',
        )

        self._color = color
        self._width = width
        self._program['color'].write(color.astype('f4').tobytes())

        positions = np.array(points, dtype='f4')

        def intersect_lines(p1: Vector2, d1: Vector2, p2: Vector2, d2: Vector2) -> Point2:
            A = np.array([d1, -d2]).T
            b = p2 - p1

            if np.abs(np.linalg.det(A)) < 1e-10:
                return p2

            t_s = np.linalg.solve(A, b)

            return p1 + t_s[0] * d1

        if self._width is not None:
            polygon_points = np.zeros((positions.shape[0] * 2, 2), dtype='f4')

            vectors = positions[1:] - positions[:-1]
            normals = np.zeros_like(vectors)
            normals[:, 0] = -vectors[:, 1]
            normals[:, 1] = vectors[:, 0]

            norms = np.linalg.norm(normals, axis=1, keepdims=True)
            normals /= norms

            hwidth = 0.5 * width

            if closed:
                polygon_points[0] = polygon_points[-2] = intersect_lines(
                    positions[0] - normals[0] * hwidth, vectors[0],
                    positions[-1] - normals[-1] * hwidth, vectors[-1]
                )
                polygon_points[1] = polygon_points[-1] = intersect_lines(
                    positions[0] + normals[0] * hwidth, vectors[0],
                    positions[-1] + normals[-1] * hwidth, vectors[-1]
                )
            else:
                polygon_points[0] = positions[0] - normals[0] * hwidth
                polygon_points[1] = positions[0] + normals[0] * hwidth
                polygon_points[-2] = positions[-1] - normals[-1] * hwidth
                polygon_points[-1] = positions[-1] + normals[-1] * hwidth

            for i in range(1, len(positions) - 1):
                polygon_points[2 * i] = intersect_lines(
                    polygon_points[2 * i - 2], vectors[i - 1],
                    positions[i] - normals[i] * hwidth, vectors[i]
                )

                polygon_points[2 * i + 1] = intersect_lines(
                    polygon_points[2 * i - 1], vectors[i - 1],
                    positions[i] + normals[i] * hwidth, vectors[i]
                )

            vertices = polygon_points
        else:
            vertices = positions

        self._vbo = self.context.buffer(vertices)
        self._vao = self.context.vertex_array(
            self._program,
            [(self._vbo, '2f', 'position')],
            mode=mgl.LINE_STRIP if self._width is None else mgl.TRIANGLE_STRIP,
        )

    @property
    def color(self) -> Vector4:
        return self._color

    @color.setter
    def color(self, value: Vector4):
        self._color = value
        self._program['color'].write(self._color.astype('f4').tobytes())

    def render(self, state: RenderState):
        self._program['mvp'].write(
            (state.camera.projection_matrix * state.camera.view_matrix).astype('f4').tobytes()
        )

        self._vao.render()
