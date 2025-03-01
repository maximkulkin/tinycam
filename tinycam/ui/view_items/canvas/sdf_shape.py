from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.canvas.canvas_item import CanvasItem
from tinycam.types import Vector4


class SdfShape(CanvasItem):
    shape_code = '''
    float shape(vec2 point) {
        return 100;
    }
    '''

    def __init__(
        self,
        context: Context,
        *,
        fill_color: Vector4 | None = None,
        edge_color: Vector4 | None = None,
        edge_width: int = 0,
        **kwargs
    ):
        super().__init__(
            context=context,
            fragment_shader='''
                #version 410 core

                uniform vec4 fillColor;
                uniform vec4 edgeColor;
                uniform float edgeWidth;

                // position of quad center in screen coordinates
                uniform vec2 center;
                // size of quad in screen coordinates
                uniform vec2 size;

                uniform vec2 screen_size;
                uniform float screen_pixel_ratio;

            ''' + self.shape_code + '''

                out vec4 color;

                void main() {
                    float d = shape(gl_FragCoord.xy / screen_pixel_ratio - center);
                    float edge = smoothstep(-edgeWidth * 0.5, -edgeWidth, d);

                    if (d > 0) {
                        discard;
                    }
                    color = mix(edgeColor, fillColor, edge);
                }
            ''',
            **kwargs
        )

        self._fill_color = fill_color if fill_color is not None else Vector4()
        self._edge_color = edge_color if edge_color is not None else self.fill_color
        self._edge_width = edge_width

        self._program['fillColor'] = self._fill_color
        self._program['edgeColor'] = self._edge_color
        self._program['edgeWidth'] = self._edge_width

    @property
    def fill_color(self) -> Vector4:
        return self._fill_color

    @fill_color.setter
    def fill_color(self, value: Vector4):
        self._fill_color = value
        self._program['fillColor'] = self._fill_color

    @property
    def edge_color(self) -> Vector4:
        return self._edge_color

    @edge_color.setter
    def edge_color(self, value: Vector4):
        self._edge_color = value
        self._program['edgeColor'] = self._edge_color

    @property
    def edge_width(self) -> float:
        return self._edge_width

    @edge_width.setter
    def edge_width(self, value: float):
        self._edge_width = value
        self._program['edgeWidth'] = self._edge_width

    def render(self, state: RenderState):
        self._program['screen_pixel_ratio'] = state.camera.device_pixel_ratio
        super().render(state)
