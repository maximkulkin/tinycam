import moderngl as mgl
import numpy as np
from tinycam.types import Vector2, Vector3, Vector4
from tinycam.ui.view import Context, ViewItem, RenderState


class DirectionMarkers(ViewItem):
    def __init__(
        self,
        context: Context,
        positions: list[Vector3] = [],
        directions: list[Vector3] = [],
        size: Vector2 = Vector2(1, 1),
        color: Vector4 = Vector4(1, 1, 1, 1),
    ):
        super().__init__(context)

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                in vec3 position;
                in vec3 direction;
                uniform vec3 camera_position;
                uniform vec2 size;

                uniform mat4 vp;

                const vec3 POINTS[] = vec3[](
                    vec3(-0.5,  0.5, 0.0),
                    vec3( 0.5,  0.0, 0.0),
                    vec3(-0.5, -0.5, 0.0)
                );

                void main() {
                    vec3 v = normalize(cross(direction, position - camera_position));
                    mat4 m = mat4(
                        vec4(normalize(direction), 0.0) * size.x,
                        vec4(v, 0.0) * size.y,
                        vec4(0.0, 0.0, 0.0, 0.0),
                        vec4(position, 1.0)
                    );
                    gl_Position = vp * m * vec4(POINTS[gl_VertexID], 1.0);
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
        self._program['color'] = color
        self._program['size'] = size

        self._instance_count = min(len(positions), len(directions))
        self._position_vbo = self.context.buffer(np.array(positions, dtype='f4'))
        self._direction_vbo = self.context.buffer(np.array(directions, dtype='f4'))

        self._vao = self.context.vertex_array(self._program, [
            (self._position_vbo, '3f/i', 'position'),
            (self._direction_vbo, '3f/i', 'direction'),
        ], mode=mgl.TRIANGLES)

    def render(self, state: RenderState):
        camera = state.camera
        self._program['camera_position'] = camera.position
        self._program['vp'] = camera.projection_matrix * camera.view_matrix

        with self.context.scope(enable=mgl.DEPTH_TEST):
            self._vao.render(vertices=3, instances=self._instance_count)
