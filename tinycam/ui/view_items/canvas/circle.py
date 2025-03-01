from tinycam.ui.view import Context
from tinycam.ui.view_items.canvas.sdf_shape import SdfShape
from tinycam.types import Vector2


class Circle(SdfShape):
    shape_code = '''
        uniform float radius;
        float shape(vec2 p) {
            return length(p) - radius;
        }
    '''

    def __init__(
        self,
        context: Context,
        radius: float = 1.0,
        **kwargs
    ):
        super().__init__(context, **kwargs)

        self.radius = radius

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, value: float):
        self._radius = value
        self.size = Vector2(self._radius, self._radius) * 2.0
        self._program['radius'] = self._radius
