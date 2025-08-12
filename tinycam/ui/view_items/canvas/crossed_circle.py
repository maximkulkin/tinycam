from tinycam.ui.view import Context
from tinycam.ui.view_items.canvas.sdf_shape import SdfShape
from tinycam.types import Vector2


class CrossedCircle(SdfShape):
    shape_code = '''
        uniform float radius;
        uniform float line_width;

        float shape(vec2 p) {
            return min(min(length(p) - radius, abs(p.x) - line_width), abs(p.y) - line_width);
        }
    '''

    def __init__(
        self,
        context: Context,
        radius: float = 1.0,
        line_width: float = 0.2,
        **kwargs
    ):
        super().__init__(context, **kwargs)

        self.radius = radius
        self.line_width = line_width

    @property
    def line_width(self) -> float:
        return self._line_width

    @line_width.setter
    def line_width(self, value: float):
        self._line_width = value
        self._program['line_width'] = self._line_width

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, value: float):
        self._radius = value
        self.size = Vector2(self._radius * 1.5, self._radius * 1.5) * 2.0
        self._program['radius'] = self._radius
