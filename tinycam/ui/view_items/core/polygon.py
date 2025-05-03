import moderngl as mgl
import numpy as np
import shapely
import shapely.geometry as sg
from tinycam.types import Vector4, Matrix44
from tinycam.ui.view import Context, ViewItem, RenderState
from typing import Union, Optional


class Polygon(ViewItem):
    def __init__(
        self,
        context: Context,
        polygon: Union[shapely.Polygon, shapely.MultiPolygon],
        model_matrix: Optional[Matrix44] = None,
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

        self._model_matrix = model_matrix if model_matrix is not None else Matrix44.identity()
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

    @property
    def model_matrix(self) -> Matrix44:
        return self._model_matrix

    @model_matrix.setter
    def model_matrix(self, matrix: Matrix44):
        self._model_matrix = matrix

    def render(self, state: RenderState):
        self._program['mvp'].write(
            (state.camera.projection_matrix * state.camera.view_matrix * self._model_matrix)
        )

        self._vao.render()
