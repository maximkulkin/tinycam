import moderngl as mgl
import numpy as np
from tinycam.ui.view import Context, ViewItem, RenderState
from tinycam.types import Vector2, Vector4


class CanvasItem(ViewItem):
    priority = 150

    def __init__(
        self,
        context: Context,
        fragment_shader: str = '''
            #version 410 core

            out vec4 color;

            void main() {
                color = vec4(1);
            }
        ''',
        center: Vector2 | None = None,
        size: Vector2 | None = None
    ):
        super().__init__(context)

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                const vec2 positions[] = vec2[](
                    vec2(-0.5,  0.5),
                    vec2( 0.5,  0.5),
                    vec2(-0.5, -0.5),
                    vec2( 0.5, -0.5)
                );

                // position of quad center in OpenGL screen coordinates
                // (bottom left = (0, 0), top right = (screen width, screen height)
                uniform vec2 center;
                // size of quad in screen coordinates
                uniform vec2 size;

                uniform vec2 screen_size;

                void main() {
                    vec2 position = (center + positions[gl_VertexID] * size) * 2.0 / screen_size - 1.0;
                    gl_Position = vec4(position, 0.0, 1.0);
                }
            ''',
            fragment_shader=fragment_shader,
        )
        if center is None:
            center = Vector2(0, 0)
        if size is None:
            size = Vector2(1, 1)

        self.center = center
        self.size = size

        self._ibo = self.context.buffer(np.array([0, 1, 2, 3], dtype='i4'))
        self._vao = self.context.vertex_array(self._program, [], index_buffer=self._ibo)

    @property
    def center(self) -> Vector2:
        return self._center

    @center.setter
    def center(self, value: Vector2):
        self._center = value

    @property
    def size(self) -> Vector2:
        return self._size

    @size.setter
    def size(self, value: Vector2):
        self._size = value
        self._program['size'] = self._size

    def render(self, state: RenderState):
        self._program['screen_size'] = state.camera.pixel_size
        self._program['center'] = Vector2(self._center.x, state.camera.pixel_height - self._center.y)

        with self.context.scope(flags=mgl.BLEND):
            self._vao.render(mgl.TRIANGLE_STRIP)
