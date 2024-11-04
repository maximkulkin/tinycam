import math
import moderngl
import numpy as np
from tinycam.ui.canvas import Renderable, RenderState


class GridXY(Renderable):
    def __init__(self, context: moderngl.Context):
        super().__init__(context)

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                in vec2 position;

                out vec3 near_point;
                out vec3 far_point;

                uniform mat4 mvp_matrix;

                vec3 unproject(mat4 imvp, vec3 p) {
                    vec4 p1 = imvp * vec4(p, 1.0);
                    return p1.xyz / p1.w;
                }

                void main() {
                    mat4 imvp = inverse(mvp_matrix);
                    near_point = unproject(imvp, vec3(position.xy, 0.0));
                    far_point  = unproject(imvp, vec3(position.xy, 1.0));
                    gl_Position = vec4(position, 0.0, 1.0);
                }
            ''',
            fragment_shader='''
                #version 410 core

                in vec3 near_point;
                in vec3 far_point;

                out vec4 fragColor;

                uniform float scale;
                uniform mat4 mvp_matrix;
                uniform vec2 screen_size;

                float grid(vec3 pos, float scale) {
                    vec2 coord = pos.xy * scale;
                    vec2 grid = abs(fract(coord - 0.5) - 0.5) / fwidth(coord);
                    return 1 - min(min(grid.x, grid.y), 1.0);
                }

                void main() {
                    float t = -near_point.z / (far_point.z - near_point.z);
                    vec3 fragPos = near_point + t * (far_point - near_point);
                    float w = 4.0 / max(screen_size.x, screen_size.y) * 0.5;

                    if (t <= 0)
                        discard;

                    fragColor = vec4(0);

                    float a = grid(fragPos, 0.01 * scale);
                    if (a > 0) {
                        fragColor += vec4(0.2, 0.2, 0.2, a * 0.1);
                    }

                    a = grid(fragPos, 0.1 * scale);
                    if (a > 0) {
                        fragColor += vec4(0.2, 0.2, 0.2, a * 0.1);
                    }

                    a = grid(fragPos, 1 * scale);
                    if (a > 0) {
                        fragColor += vec4(0.4, 0.4, 0.4, a * 0.2);
                    }

                    if (abs(fragPos.y) * scale < 0.1 && abs(fragPos.y) < abs(fragPos.x)) {
                        fragColor.xyz = vec3(1, 0, 0);
                    }
                    if (abs(fragPos.x) * scale < 0.1 && abs(fragPos.x) < abs(fragPos.y)) {
                        fragColor.xyz = vec3(0, 1, 0);
                    }
                }
            '''
        )

        vertices = np.array([
            (1,  -1), (-1,  -1), (1, 1), (-1, 1),
        ], dtype='f4')

        self._vbo = self.context.buffer(vertices.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '2f', 'position'),
        ])
        self._program['scale'] = 1.0

    def render(self, state: RenderState):
        mvp = state.camera.projection_matrix * state.camera.view_matrix

        self._program['mvp_matrix'].write(mvp.astype('f4').tobytes())
        self._program['scale'] = pow(10, 1 - int(math.log(abs(state.camera.position.z * 0.25), 10)))
        self._program['screen_size'] = state.screen_size

        self._vao.render(moderngl.TRIANGLE_STRIP)
