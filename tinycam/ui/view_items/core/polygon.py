import moderngl as mgl
import numpy as np
from tinycam.geometry import Polygon as ShapePolygon, MultiPolygon as ShapeMultiPolygon
from tinycam.globals import GLOBALS
from tinycam.types import Vector4
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core import Node3D


class Polygon(Node3D):
    def __init__(
        self,
        context: Context,
        polygon: ShapePolygon | ShapeMultiPolygon,
        color: Vector4 = Vector4(1, 1, 1, 1),
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

        G = GLOBALS.GEOMETRY
        polygons = G.polygons(polygon)

        vertices = np.array([
            coord
            for poly in polygons
            for triangle_coords in G.triangulate(poly)
            for coord in triangle_coords
        ], dtype='f4')

        self._vbo = self.context.buffer(vertices)
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '2f', 'position'),
        ], mode=mgl.TRIANGLES)

    @property
    def color(self) -> Vector4:
        return self._color

    @color.setter
    def color(self, value: Vector4):
        self._color = value

    def render(self, state: RenderState):
        self._program['color'].value = self._color
        camera = state.camera
        self._program['mvp'].write(
            (camera.projection_matrix * camera.view_matrix * self.world_matrix)
        )

        self._vao.render()
