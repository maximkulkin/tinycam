import moderngl as mgl
import numpy as np
from tinycam.ui.view import Context, ViewItem, RenderState


class TexturedQuad(ViewItem):
    def __init__(self, context: Context, texture: mgl.Texture, size: tuple[int, int]):
        super().__init__(context)
        self.texture = texture

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                in vec2 aPosition;
                in vec2 aUV;

                out vec2 UV;

                void main() {
                    gl_Position = vec4(aPosition, 0.0, 1.0);
                    UV = aUV;
                }
            ''',
            fragment_shader='''
                #version 410 core

                uniform sampler2D tex;

                in vec2 UV;
                out vec4 color;

                void main() {
                    color = texture(tex, UV);
                }
            ''',
        )

        x, y = -size[0] / 2, -size[1] / 2
        width, height = size[0], size[1]

        positions = np.array([
            (x, y),
            (x + width, y),
            (x, y + height),
            (x + width, y + height),
        ], dtype='f4')

        uvs = np.array([
            (0.0, 1.0),
            (1.0, 1.0),
            (0.0, 0.0),
            (1.0, 0.0),
        ], dtype='f4')

        self._vbo_positions = self.context.buffer(positions.tobytes())
        self._vbo_uvs = self.context.buffer(uvs.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo_positions, '2f', 'aPosition'),
            (self._vbo_uvs, '2f', 'aUV'),
        ])

    def render(self, state: RenderState):
        self._program['tex'] = 0
        self.texture.use(0)
        self._vao.render(mgl.TRIANGLE_STRIP)
