import moderngl
import numpy as np
from tinycam.ui.canvas import Renderable, RenderState


class Quad(Renderable):
    def __init__(self, context):
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
        self.context.disable(moderngl.CULL_FACE)
        self.context.enable(moderngl.DEPTH_TEST)

        self._program['mvp'].write(
            (state.camera.projection_matrix * state.camera.view_matrix).astype('f4').tobytes()
        )

        self._vao.render(moderngl.TRIANGLE_STRIP)
