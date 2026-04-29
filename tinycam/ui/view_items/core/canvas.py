import moderngl as mgl
import numpy as np
from typing import Sequence, cast

from tinycam.math_types import Vector2, Vector3, Vector4
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core.node2d import Node2D
from tinycam.ui.view_items.core.node3d import Node3D


class CanvasItem(Node2D):

    def __init__(self, context: Context, **kwargs):
        super().__init__(context, **kwargs)

        self._canvas = None

    @Node2D.parent.setter
    def parent(self, value: 'Node2D | None'):
        if value is not None and not isinstance(value, CanvasItem):
            raise ValueError('Invalid parent for canvas item')

        assert Node2D.parent.fset
        Node2D.parent.fset(self, value)

    @property
    def canvas(self) -> 'Canvas | None':
        if self._canvas is not None:
            return self._canvas
        if self.parent is not None:
            return cast(CanvasItem, self.parent).canvas

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
        fill_color: Vector4 = Vector4(1, 1, 1, 1),
        edge_color: Vector4 = Vector4(1, 1, 1, 1),
        edge_width: float = 0.1,
        screen_space_size: bool = False,
        screen_space_edge_width: bool = False,
        **kwargs
    ):
        super().__init__(context, **kwargs)

        self.size = size
        self._screen_space_size = screen_space_size
        self._screen_space_edge_width = screen_space_edge_width
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

                uniform mat4 model_view_matrix;
                uniform mat4 projection_matrix;

                // size of the SDF shape in pixels
                uniform vec2 size;

                // UV coordinates in pixels with zero in the center
                out vec2 uv;

                void main() {
                    vec2 position = positions[gl_VertexID] * size;

                    gl_Position =
                        projection_matrix * (
                            model_view_matrix * vec4(0, 0, 0, 1) +
                            vec4(position, 0.0, 0.0)
                        );

                    uv = position;
                }
            '''

            fragment_shader = '''
                #version 410 core

                uniform vec4 fill_color;
                uniform vec4 edge_color;
                // edge width in pixels
                uniform float edge_width;

                in vec2 uv;

            ''' + self.shape_code + '''

                out vec4 color;

                void main() {
                    float d = shape(uv);
                    float edge = smoothstep(-edge_width, 0, d);

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

                uniform mat4 model_view_matrix;
                uniform mat4 projection_matrix;

                // size of the SDF shape in world units
                uniform vec2 size;

                // UV coordinates in world units with zero in the center
                out vec2 uv;

                void main() {
                    vec2 position = positions[gl_VertexID] * size;
                    gl_Position = projection_matrix * model_view_matrix * vec4(position, 0.0, 1.0);
                    uv = position;
                }
            '''

            fragment_shader = '''
                #version 410 core

                uniform vec4 fill_color;
                uniform vec4 edge_color;
                // edge width in world units
                uniform float edge_width;

                in vec2 uv;

            ''' + self.shape_code + '''

                out vec4 color;

                void main() {
                    float d = shape(uv);
                    float edge = smoothstep(-edge_width, 0.0, d);

                    if (d > 0) {
                        discard;
                    }
                    color = mix(fill_color, edge_color, edge);
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

        p1 = state.camera.unproject(Vector2(0, 0)).xy
        p2 = state.camera.unproject(Vector2(1, 1)).xy
        pixel_size = abs(p2 - p1) * 0.5

        if self._screen_space_size:
            self._program['size'] = self.size * pixel_size
        else:
            self._program['size'] = self.size

        if self._screen_space_edge_width:
            self._program['edge_width'] = self.edge_width * min(pixel_size.x, pixel_size.y)
        else:
            self._program['edge_width'] = self.edge_width

        self._program['fill_color'] = self.fill_color
        self._program['edge_color'] = self.edge_color
        self._program['projection_matrix'] = state.camera.projection_matrix
        self._program['model_view_matrix'] = (
            state.camera.view_matrix *
            self.world_matrix
        )

        with self.context.scope(flags=mgl.BLEND):
            self._vao.render()


class Circle(SdfShape):
    shape_code = '''
    uniform vec2 size;

    float shape(vec2 uv) {
        return length(uv) - size.x * 0.5;
    }
    '''

    def __init__(self, context: Context, radius: float, **kwargs):
        super().__init__(context, **kwargs)

        self.radius = radius

    @property
    def radius(self) -> float:
        return self.size.x * 0.5

    @radius.setter
    def radius(self, value: float):
        self.size = Vector2(2, 2) * value


class Rectangle(SdfShape):
    shape_code = '''
    uniform vec2 size;

    float shape(vec2 uv) {
        vec2 d = abs(uv) - size * 0.5;
        return length(max(d, 0)) + min(max(d.x, d.y), 0);
    }
    '''


class VerticalCross(SdfShape):
    shape_code = '''
        float shape(vec2 p) {
            return min(abs(p.x) - edge_width * 0.5,
                       abs(p.y) - edge_width * 0.5);
        }
    '''


class DiagonalCross(SdfShape):
    shape_code = '''
        float shape(vec2 p) {
            return min(abs(p.x - p.y) - edge_width * 0.5,
                       abs(p.y + p.x) - edge_width * 0.5);
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
