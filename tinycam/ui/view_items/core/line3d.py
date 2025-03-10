import moderngl
import numpy as np
from typing import Optional
from tinycam.types import Vector3, Vector4
from tinycam.ui.view import Context, ViewItem, RenderState


type Point3 = Vector3


class Line3D(ViewItem):
    def __init__(
        self,
        context: Context,
        points: list[Point3],
        closed: bool = False,
        color: Vector4 = Vector4(0.8, 0.8, 0.8, 1.0),
        width: Optional[float] = None,
    ):
        super().__init__(context)

        self._closed = closed
        self._width = width
        self._color = color

        if self._width is not None:
            self._program = self.context.program(
                vertex_shader='''
                    #version 410 core

                    uniform mat4 mvp;
                    uniform float width;
                    uniform vec2 resolution;

                    in vec3 prev_position;
                    in vec3 curr_position;
                    in vec3 next_position;
                    in float side;

                    vec2 screen_space(vec4 p, float aspect) {
                        return vec2(p.x / p.w * aspect, p.y / p.w);
                    }

                    void main() {
                        float aspect = resolution.x / resolution.y;
                        vec4 position = mvp * vec4(curr_position, 1.0);

                        vec2 curr_screen = screen_space(position, aspect);
                        vec2 next_screen = screen_space(mvp * vec4(next_position, 1.0), aspect);
                        vec2 prev_screen = screen_space(mvp * vec4(prev_position, 1.0), aspect);

                        vec2 dir;
                        if (next_screen == curr_screen) {
                            dir = normalize(curr_screen - prev_screen);
                        } else if (prev_screen == curr_screen) {
                            dir = normalize(next_screen - curr_screen);
                        } else {
                            vec2 dir1 = normalize(curr_screen - prev_screen);
                            vec2 dir2 = normalize(next_screen - curr_screen);
                            dir = normalize(dir1 + dir2);
                        }

                        vec4 normal = vec4(-dir.y / aspect, dir.x, 0.0, 0.0) * 0.5 * width;

                        gl_Position = position + normal * side;
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

            self._vertex_count = len(points) * 2
            points = np.array(points, dtype='f4')

            points_data = np.zeros((len(points) * 2, 3), dtype='f4')
            points_data[0::2] = points
            points_data[1::2] = points

            prev_points_data = np.zeros((len(points) * 2, 3), dtype='f4')
            prev_points_data[2:] = points_data[:-2]

            next_points_data = np.zeros((len(points) * 2, 3), dtype='f4')
            next_points_data[:-2] = points_data[2:]

            if self._closed:
                prev_points_data[0:2] = points_data[-4:-2]
                next_points_data[-2:] = points_data[2:4]
            else:
                prev_points_data[0:2] = points_data[0:2]
                next_points_data[-2:] = points_data[-2:]

            side_data = np.zeros((2 * len(points), ), dtype='f4')
            side_data[0::2] = -1.0
            side_data[1::2] = 1.0

            self._program['width'] = self._width
            self._program['color'].write(color.astype('f4'))

            self._vbo_curr_points = self.context.buffer(points_data.tobytes())
            self._vbo_prev_points = self.context.buffer(prev_points_data.tobytes())
            self._vbo_next_points = self.context.buffer(next_points_data.tobytes())
            self._vbo_side = self.context.buffer(side_data.tobytes())
            self._vao = self.context.vertex_array(self._program, [
                (self._vbo_curr_points, '3f', 'curr_position'),
                (self._vbo_prev_points, '3f', 'prev_position'),
                (self._vbo_next_points, '3f', 'next_position'),
                (self._vbo_side, 'f', 'side'),
            ])
        else:
            self._program = self.context.program(
                vertex_shader='''
                    #version 410 core

                    uniform mat4 mvp;
                    in vec3 position;

                    void main() {
                        gl_Position = mvp * vec4(position, 1.0);
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
            self._program['color'].write(color.astype('f4'))
            self._vbo = self.context.buffer(np.array(points, dtype='f4').tobytes())
            self._vao = self.context.vertex_array(self._program, [
                (self._vbo, '3f', 'position'),
            ])

    @property
    def color(self) -> Vector4:
        return self._color

    @color.setter
    def color(self, value: Vector4):
        self._color = value
        self._program['color'].write(self._color.tobytes())

    def render(self, state: RenderState):
        self._program['mvp'].write(
            (state.camera.projection_matrix * state.camera.view_matrix).tobytes()
        )

        if self._width is None:
            self._vao.render(moderngl.LINE_STRIP)
        else:
            self._program['resolution'].write(state.camera.pixel_size.tobytes())
            self._vao.render(moderngl.TRIANGLE_STRIP)
