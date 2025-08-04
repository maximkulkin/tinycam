import moderngl
import numpy as np
from tinycam.types import Vector4, Matrix44
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core import Node3D


class Triangle(Node3D):
    def __init__(
        self,
        context: Context,
        color: Vector4 = Vector4(1, 1, 1, 1),
    ):
        super().__init__(context)

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                in vec3 position;

                uniform mat4 mvp;

                void main() {
                    gl_Position = mvp * vec4(position, 1);
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

        vertices = np.array([
            (-0.5,  0.5, 0.0),
            ( 0.5,  0.5, 0.0),
            ( 0.0, -0.5, 0.0),
        ], dtype='f4')

        self._vbo = self.context.buffer(vertices)
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '3f', 'position'),
        ])
        self._program['color'] = color

    def render(self, state: RenderState):
        camera = state.camera
        self._program['mvp'] = (
            (camera.projection_matrix * camera.view_matrix * self.world_matrix)
        )

        with self.context.scope(enable=moderngl.DEPTH_TEST):
            self._vao.render(moderngl.TRIANGLE_STRIP)
