import moderngl
import numpy as np
from tinycam.types import Vector3, Vector4, Quaternion, Matrix44
from tinycam.ui.canvas import Context, Renderable, RenderState


class Triangle(Renderable):
    def __init__(
        self,
        context: Context,
        position: Vector3 = Vector3(),
        rotation: Quaternion = Quaternion(),
        color: Vector4 = Vector4(1, 1, 1, 1),
    ):
        super().__init__(context)

        self._position = position
        self._rotation = rotation
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

        self._vbo = self.context.buffer(vertices.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '3f', 'position'),
        ])
        self._program['color'].write(color.tobytes())

    def render(self, state: RenderState):
        model_matrix = (
            Matrix44.from_translation(self._position) *
            Matrix44.from_quaternion(self._rotation)
        )

        camera = state.camera
        self._program['mvp'].write(
            (camera.projection_matrix * camera.view_matrix * model_matrix).tobytes()
        )

        with self.context.scope(enable=moderngl.DEPTH_TEST):
            self._vao.render(moderngl.TRIANGLE_STRIP)
