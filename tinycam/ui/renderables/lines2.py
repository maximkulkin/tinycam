import moderngl
import numpy as np
from tinycam.ui.canvas import Renderable, RenderState


class Lines2(Renderable):
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
            geometry_shader='''
                #version 410 core

                uniform float line_width;
                uniform vec2 screen_size;

                layout(lines) in;
                layout(triangle_strip, max_vertices = 4) out;

                void main() {
                    vec3 p0 = gl_in[0].gl_Position.xyz;
                    vec3 p1 = gl_in[1].gl_Position.xyz;

                    vec3 d = normalize(p1 - p0);
                    vec3 n = vec3(d.y, -d.x, 0) * line_width * 0.5; // min(screen_size.x, screen_size.y);

                    gl_Position = vec4(p0 + n, 0);
                    EmitVertex();
                    gl_Position = vec4(p0 - n, 0);
                    EmitVertex();
                    gl_Position = vec4(p1 + n, 0);
                    EmitVertex();

                    gl_Position = vec4(p1 + n, 0);
                    EmitVertex();
                    gl_Position = vec4(p0 - n, 0);
                    EmitVertex();
                    gl_Position = vec4(p1 - n, 0);
                    EmitVertex();
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
        self._program['line_width'] = 2.0

        vertices = np.array(points, dtype='f4')

        self._vbo = self.context.buffer(vertices.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '2f', 'position'),
        ])

    def render(self, state: RenderState):
        self._program['mvp'].write(
            (state.camera.projection_matrix * state.camera.view_matrix).astype('f4').tobytes()
        )
        # self._program['screen_size'] = state.screen_size

        self._vao.render(moderngl.LINE_STRIP)
