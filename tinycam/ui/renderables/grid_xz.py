import math
import moderngl
import numpy as np
from tinycam.ui.canvas import Context, ViewItem, RenderState


class GridXZ(ViewItem):
    def __init__(self, context: Context, scale: float = 1.0):
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

                float grid(vec3 pos, float scale) {
                    vec2 coord = pos.xz * scale;
                    vec2 grid = abs(fract(coord - 0.5) - 0.5) / fwidth(coord);
                    return 1 - min(min(grid.x, grid.y), 1.0);
                }

                void main() {
                    float t = -near_point.y / (far_point.y - near_point.y);
                    vec3 fragPos = near_point + t * (far_point - near_point);

                    if (t <= 0)
                        discard;

                    float a = grid(fragPos, 0.1 * scale);
                    if (a > 0) {
                        fragColor = vec4(0.6, 0.6, 0.6, a);
                        if (abs(fragPos.z) * scale < 0.1 && abs(fragPos.z) < abs(fragPos.x)) {
                            fragColor.x = 1.0;
                        }
                        if (abs(fragPos.x) * scale < 0.1 && abs(fragPos.x) < abs(fragPos.z)) {
                            fragColor.y = 1.0;
                        }

                        return;
                    }

                    a = grid(fragPos, 1 * scale);
                    if (a > 0) {
                        fragColor = vec4(0.2, 0.2, 0.2, a);
                        return;
                    }

                    fragColor = vec4(0, 0, 0, 0);
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
        self._program['scale'] = pow(10, -int(math.log(abs(state.camera.position.z), 10)))

        self._vao.render(moderngl.TRIANGLE_STRIP)
