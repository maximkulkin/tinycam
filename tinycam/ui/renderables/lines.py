import moderngl
import numpy as np
from tinycam.ui.canvas import Renderable, RenderState


class Lines(Renderable):
    def __init__(
        self,
        context: moderngl.Context,
        points: list[tuple[float, float]],
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

                out vec4 fragColor;

                void main() {
                    fragColor = vec4(0.8, 0.8, 0.8, 1.0);
                }
            ''',
        )

        vertices = np.array(points, dtype='f4')

        self._vbo = self.context.buffer(vertices.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '2f', 'position'),
        ])

    def render(self, state: RenderState):
        self._program['mvp'].write(
            (state.camera.projection_matrix * state.camera.view_matrix).astype('f4').tobytes()
        )

        self.context.line_width = 2.0
        self._vao.render(moderngl.LINE_STRIP)
