import math
import moderngl
import numpy as np
from tinycam.types import Vector3
from tinycam.ui.canvas import Context, Renderable, RenderState


class GridXY(Renderable):
    def __init__(self, context: Context):
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
                uniform float subscale;
                uniform mat4 mvp_matrix;
                uniform vec2 screen_size;

                const float axes_width = 1.0;
                const float grid_major_width = 1.0;
                const float grid_minor_width = 1.0;
                const vec4 grid_major_color = vec4(0.2, 0.2, 0.2, 1.0);
                const vec4 grid_minor_color = vec4(0.1, 0.1, 0.1, 1.0);

                vec4 normalize(vec4 v) {
                    return v / max(v.w, 1e-6);
                }

                float grid(vec3 pos, float scale) {
                    float closest_x = round(pos.x * scale) / scale;
                    float closest_y = round(pos.y * scale) / scale;

                    vec3 closest_grid_point = pos;
                    if (abs(closest_x - pos.x) < abs(closest_y - pos.y)) {
                        closest_grid_point.x = closest_x;
                    } else {
                        closest_grid_point.y = closest_y;
                    }

                    vec2 screen_pos = normalize(mvp_matrix * vec4(pos, 1.0)).xy;
                    vec2 screen_closest_grid_point = normalize(mvp_matrix * vec4(closest_grid_point, 1.0)).xy;

                    return length(screen_pos - screen_closest_grid_point) * screen_size.y;
                }

                void main() {
                    float t = -near_point.z / (far_point.z - near_point.z);
                    if (t <= 0)
                        discard;

                    vec3 fragPos = near_point + t * (far_point - near_point);

                    gl_FragDepth = fragPos.z;

                    fragColor = vec4(0);

                    if (grid(fragPos, 0.1 * scale) <= grid_major_width) {
                        fragColor = grid_major_color;
                    } else if(grid(fragPos, 1.0 * scale) <= grid_minor_width) {
                        fragColor = vec4(grid_minor_color.xyz, subscale);
                    }

                    if (abs(fragPos.x) < abs(fragPos.y)) {
                        vec4 p1 = normalize(mvp_matrix * vec4(fragPos, 1.0));
                        vec4 p2 = normalize(mvp_matrix * vec4(0, fragPos.y, fragPos.z, 1.0));

                        float d = length(p1.xy - p2.xy) * screen_size.y;
                        if (d <= 1.0) {
                            fragColor.xyz = vec3(0, 1, 0);
                        }
                    } else {
                        vec4 p1 = normalize(mvp_matrix * vec4(fragPos, 1.0));
                        vec4 p2 = normalize(mvp_matrix * vec4(fragPos.x, 0, fragPos.z, 1.0));

                        float d = length(p1.xy - p2.xy) * screen_size.y;
                        if (d <= 1.0) {
                            fragColor.xyz = vec3(1, 0, 0);
                        }
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
        d = Vector3.dot(state.camera.rotation * state.camera.FORWARD, Vector3(0, 0, 1))
        if d != 0:
            d = state.camera.position.z / d
        self._program['scale'] = pow(10, 0.4 - int(math.log(abs(d * 0.25), 10)))
        scale_fraction, _ = math.modf(math.log(abs(d * 0.25), 10))
        self._program['subscale'] = 1.0 - scale_fraction
        self._program['screen_size'] = state.camera.pixel_size

        with self.context.scope(enable=moderngl.DEPTH_TEST | moderngl.BLEND, disable=moderngl.CULL_FACE):
            self._vao.render(moderngl.TRIANGLE_STRIP)
