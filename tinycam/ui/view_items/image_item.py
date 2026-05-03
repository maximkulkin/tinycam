import moderngl as mgl
import numpy as np
from PIL import Image as PilImage

from tinycam.project.image_item import ImageItem
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.math_types import Box


_VERTEX_SHADER = '''
    #version 410 core

    uniform mat4 mvp;

    in vec2 aPosition;
    in vec2 aUV;

    out vec2 UV;

    void main() {
        gl_Position = mvp * vec4(aPosition, 0.0, 1.0);
        UV = aUV;
    }
'''

_FRAGMENT_SHADER = '''
    #version 410 core

    uniform sampler2D tex;
    uniform float alpha;
    uniform int picking_mode;
    uniform vec4 pick_color;

    in vec2 UV;
    out vec4 color;

    void main() {
        if (picking_mode == 1) {
            color = pick_color;
        } else {
            vec4 c = texture(tex, UV);
            c.a *= alpha;
            color = c;
        }
    }
'''


class ImageItemView(CncProjectItemView[ImageItem]):

    def __init__(self, context: Context, model: ImageItem):
        self._texture: mgl.Texture | None = None
        self._vbo_positions: mgl.Buffer | None = None
        self._vbo_uvs: mgl.Buffer | None = None
        self._vao: mgl.VertexArray | None = None
        self._program = None
        self._cached_bounds: tuple | None = None

        super().__init__(context, model)
        self._setup_gl()

    def _setup_gl(self):
        image = self._model.image
        if image is None:
            return

        # Flip for OpenGL texture coordinates (origin bottom-left)
        flipped = image.transpose(PilImage.FLIP_TOP_BOTTOM)
        self._texture = self.context.texture(
            size=flipped.size,
            components=4,
            data=flipped.tobytes(),
        )
        self._texture.filter = (mgl.LINEAR, mgl.LINEAR)

        self._program = self.context.program(_VERTEX_SHADER, _FRAGMENT_SHADER)

        uvs = np.array([
            (0.0, 0.0),
            (1.0, 0.0),
            (0.0, 1.0),
            (1.0, 1.0),
        ], dtype='f4')
        self._vbo_uvs = self.context.buffer(uvs.tobytes())

        self._vbo_positions = self.context.buffer(
            np.zeros((4, 2), dtype='f4').tobytes()
        )
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo_positions, '2f', 'aPosition'),
            (self._vbo_uvs, '2f', 'aUV'),
        ])

        self._update_positions()

    def _update_positions(self):
        if self._vbo_positions is None:
            return

        b = self._model.bounds
        positions = np.array([
            (b.xmin, b.ymin),
            (b.xmax, b.ymin),
            (b.xmin, b.ymax),
            (b.xmax, b.ymax),
        ], dtype='f4')
        self._vbo_positions.write(positions.tobytes())
        self._cached_bounds = (b.xmin, b.ymin, b.xmax, b.ymax)

    @property
    def bounds(self) -> Box:
        b = self._model.bounds
        return Box.from_coords(b.xmin, b.ymin, -0.1, b.xmax, b.ymax, 0.1)

    def _update_geometry(self):
        pass

    def _on_model_changed(self, model: ImageItem):
        b = self._model.bounds
        if (b.xmin, b.ymin, b.xmax, b.ymax) != self._cached_bounds:
            self._update_positions()

    def render(self, state: RenderState):
        if not self._model.visible or self._vao is None or self._texture is None:
            return

        mvp = state.camera.projection_matrix * state.camera.view_matrix * self.world_matrix
        self._program['mvp'].write(mvp.tobytes())

        if state.picking:
            raw = state.register_pickable(self)
            self._program['picking_mode'] = 1
            self._program['pick_color'].write(
                np.array([raw[0], raw[1], raw[2], raw[3]], dtype='f4') / 255.0
            )
            self._vao.render(mgl.TRIANGLE_STRIP)
        else:
            self._program['picking_mode'] = 0
            self._program['tex'] = 0
            self._program['alpha'] = 0.5 if self._model.selected else 1.0
            self._texture.use(0)
            with self.context.scope(enable=mgl.BLEND, disable=mgl.DEPTH_TEST):
                self._vao.render(mgl.TRIANGLE_STRIP)
