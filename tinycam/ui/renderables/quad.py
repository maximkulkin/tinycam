import moderngl
import numpy as np
from tinycam.ui.view import Context, ViewItem, RenderState


class Quad(ViewItem):
    def __init__(self, context: Context):
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

                out vec4 color;

                void main() {
                    color = vec4(1, 1, 1, 1);
                }
            ''',
        )

        vertices = np.array([
            (-0.5,  0.5, 0.0),
            ( 0.5,  0.5, 0.0),
            (-0.5, -0.5, 0.0),
            ( 0.5, -0.5, 0.0),
        ], dtype='f4')

        self._vbo = self.context.buffer(vertices.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '3f', 'position'),
        ])

    def render(self, state: RenderState):
        self._program['mvp'].write(
            (state.camera.projection_matrix * state.camera.view_matrix).tobytes()
        )

        with self.context.scope(enable_only=[moderngl.DEPTH_TEST]):
            self._vao.render(moderngl.TRIANGLE_STRIP)
