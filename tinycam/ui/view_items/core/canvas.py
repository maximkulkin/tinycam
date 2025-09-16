import moderngl as mgl
import numpy as np
from typing import Sequence, cast

from tinycam.types import Vector2, Vector4
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core.node2d import Node2D
from tinycam.ui.view_items.core.node3d import Node3D


class CanvasItem(Node2D):

    def __init__(self, context: Context, **kwargs):
        super().__init__(context, **kwargs)

        self._canvas = None

    # @Node2D.parent.getter
    # def parent(self) -> 'CanvasItem | None':
    #     return cast(CanvasItem | None, super().parent)

    # @Node2D.parent.setter
    # def parent(self, value: 'Node2D | None'):
    #     if value is not None and not isinstance(value, CanvasItem):
    #         raise ValueError('Invalid parent for canvas item')

    #     super().parent = value

    @property
    def canvas(self) -> 'Canvas | None':
        if self._canvas is not None:
            return self._canvas
        if self.parent is not None:
            return self.parent.canvas

        return self._canvas

    @canvas.setter
    def canvas(self, value: 'Canvas | None'):
        self._canvas = value


class SdfShape(CanvasItem):
    shape_code = '''
    float shape(vec2 uv) {
        return 100;
    }
    '''

    size: Vector2 = Vector2(1, 1)
    fill_color: Vector4 = Vector4(1, 1, 1, 1)
    edge_color: Vector4 = Vector4(1, 1, 1, 1)
    edge_width: float = 0.1

    def __init__(
        self,
        context: Context,
        *,
        size: Vector2 = Vector2(1, 1),
        screen_space_size: bool = False,
        fill_color: Vector4 = Vector4(1, 1, 1, 1),
        edge_color: Vector4 = Vector4(1, 1, 1, 1),
        edge_width: float = 0.1,
        **kwargs
    ):
        super().__init__(context, **kwargs)

        self.size = size
        self._screen_space_size = screen_space_size
        self.fill_color = fill_color
        self.edge_color = edge_color
        self.edge_width = edge_width

        if self._screen_space_size:
            vertex_shader = '''
                #version 410 core

                const vec2 positions[] = vec2[](
                    vec2(-0.5,  0.5),
                    vec2( 0.5,  0.5),
                    vec2(-0.5, -0.5),
                    vec2( 0.5, -0.5)
                );

                uniform mat4 mvp;

                // size of the SDF shape in pixels
                uniform vec2 size;

                out vec2 uv;

                void main() {
                    vec2 position = positions[gl_VertexID];

                    gl_Position =
                        mvp * vec4(0, 0, 0, 1) +
                        vec4(position * size, 0.0, 0.0);

                    uv = position;
                }
            '''

            fragment_shader = '''
                #version 410 core

                uniform vec4 fill_color;
                uniform vec4 edge_color;
                uniform float edge_width;

                in vec2 uv;

            ''' + self.shape_code + '''

                out vec4 color;

                void main() {
                    float d = shape(uv);
                    float edge = smoothstep(-edge_width * 0.5, -edge_width, d);

                    if (d > 0) {
                        discard;
                    }
                    color = mix(edge_color, fill_color, edge);
                    if (color.a < 0.01) {
                        discard;
                    }
                }
            '''
        else:
            vertex_shader = '''
                #version 410 core

                const vec2 positions[] = vec2[](
                    vec2(-0.5,  0.5),
                    vec2( 0.5,  0.5),
                    vec2(-0.5, -0.5),
                    vec2( 0.5, -0.5)
                );

                uniform mat4 mvp;

                uniform vec2 size;

                out vec2 uv;

                void main() {
                    vec2 position = positions[gl_VertexID];
                    gl_Position = mvp * vec4(position * size, 0.0, 1.0);
                    uv = positions[gl_VertexID];
                }
            '''

            fragment_shader = '''
                #version 410 core

                uniform vec4 fill_color;
                uniform vec4 edge_color;
                uniform float edge_width;

                in vec2 uv;

            ''' + self.shape_code + '''

                out vec4 color;

                void main() {
                    float d = shape(uv);
                    float edge = smoothstep(-edge_width * 0.5, -edge_width, d);

                    if (d > 0) {
                        discard;
                    }
                    color = mix(edge_color, fill_color, edge);
                    if (color.a < 0.01) {
                        discard;
                    }
                }
            '''

        self._program = self.context.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
        )

        self._ibo = self.context.buffer(np.array([0, 1, 2, 3], dtype='i4'))
        self._vao = self.context.vertex_array(
            self._program,
            [],
            index_buffer=self._ibo,
            mode=mgl.TRIANGLE_STRIP,
        )

    def render(self, state: RenderState):
        if not self.visible:
            return

        self._program['fill_color'] = self.fill_color
        self._program['edge_color'] = self.edge_color
        self._program['edge_width'] = self.edge_width / min(self.size.x, self.size.y)
        self._program['mvp'] = (
            state.camera.projection_matrix *
            state.camera.view_matrix *
            self.world_matrix
        )
        if self._screen_space_size:
            self._program['size'] = self.size / state.camera.pixel_size
        else:
            self._program['size'] = self.size

        with self.context.scope(flags=mgl.BLEND):
            self._vao.render()


class Circle(SdfShape):
    shape_code = '''
    float shape(vec2 uv) {
        return length(uv) - 0.5;
    }
    '''

    def __init__(self, context: Context, radius: float, **kwargs):
        super().__init__(context, **kwargs)

        self.radius = radius

    @property
    def radius(self) -> float:
        return self.size.x

    @radius.setter
    def radius(self, value: float):
        self.size = Vector2(1, 1) * value


class VerticalCross(SdfShape):
    shape_code = '''
        float shape(vec2 p) {
            return min(abs(p.x) - edge_width,
                       abs(p.y) - edge_width);
        }
    '''


class DiagonalCross(SdfShape):
    shape_code = '''
        float shape(vec2 p) {
            return min(abs(p.x - p.y) - edge_width,
                       abs(p.y + p.x) - edge_width);
        }
    '''


class Canvas(Node3D):

    def __init__(
        self,
        context: Context,
        **kwargs
    ):
        super().__init__(context, **kwargs)

        self._items = []

    @property
    def items(self) -> 'Sequence[CanvasItem]':
        return self._items

    def add_item(self, item: 'CanvasItem', update_parent: bool = True):
        self._items.append(item)
        if update_parent:
            item.canvas = self
            item.parent = None

    def remove_item(self, item: 'CanvasItem', update_parent: bool = True):
        if item not in self._items:
            return

        self._items.remove(item)
        if update_parent:
            item.canvas = None
            item.parent = None

    def has_item(self, item: 'CanvasItem') -> bool:
        return item in self._items

    def render(self, state: RenderState):
        super().render(state)

        for item in self.items:
            item.render(state)
