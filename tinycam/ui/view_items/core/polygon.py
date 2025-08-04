import moderngl as mgl
import numpy as np
import shapely
import shapely.geometry as sg
from tinycam.types import Vector4
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core import Node3D


class Polygon(Node3D):
    def __init__(
        self,
        context: Context,
        polygon: shapely.Polygon | shapely.MultiPolygon,
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
        self._program['color'].value = color

        polygons = []
        if isinstance(polygon, sg.Polygon):
            polygons = [polygon]
        elif isinstance(polygon, sg.MultiPolygon):
            polygons = polygon.geoms
        else:
            raise ValueError(f'Unsupported polygon type {type(polygon)}')

        for polygon in polygons:
            shapely.prepare(polygon)

        vertices = np.array([
            coord
            for polygon in polygons
            # for triangle in shapely.delaunay_triangles(polygon.segmentize(max_segment_length=0.25)).geoms
            for triangle in shapely.delaunay_triangles(polygon.segmentize(max_segment_length=1.0)).geoms
            if polygon.contains(triangle.centroid)
            for coord in triangle.exterior.coords[:-1]
        ], dtype='f4')

        for polygon in polygons:
            shapely.destroy_prepared(polygon)

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
        self._program['color'].value = self._color

    def render(self, state: RenderState):
        camera = state.camera
        self._program['mvp'].write(
            (camera.projection_matrix * camera.view_matrix * self.world_matrix)
        )

        self._vao.render()
