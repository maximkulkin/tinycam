import moderngl
import numpy as np
from pyrr import Vector4
import shapely
import shapely.geometry as sg
from tinycam.ui.canvas import Renderable, RenderState
from typing import Union


class Polygon(Renderable):
    def __init__(
        self,
        context: moderngl.Context,
        polygon: Union[shapely.Polygon, shapely.MultiPolygon],
        color: Vector4 = Vector4((1, 1, 1, 1)),
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

        self._program['color'].write(color.astype('f4').tobytes())

        self._scope = self.context.scope()

        polygons = []
        if isinstance(polygon, sg.Polygon):
            polygons = [polygon]
        elif isinstance(polygon, sg.MultiPolygon):
            polygons = polygon.geoms

        vertices = np.array([
            coord
            for polygon in polygons
            for triangle in shapely.delaunay_triangles(polygon.segmentize(max_segment_length=0.5)).geoms
            # for triangle in shapely.delaunay_triangles(polygon).geoms
            if polygon.contains(triangle.centroid)
            for coord in triangle.exterior.coords[:-1]
        ], dtype='f4')

        self._vbo = self.context.buffer(vertices.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '2f', 'position'),
        ])

    def render(self, state: RenderState):
        self._program['mvp'].write(
            (state.camera.projection_matrix * state.camera.view_matrix).astype('f4').tobytes()
        )

        self._vao.render(moderngl.TRIANGLES)
