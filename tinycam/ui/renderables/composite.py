from collections.abc import Sequence
import moderngl
from tinycam.ui.canvas import Renderable, RenderState


class Composite(Renderable):
    def __init__(
        self,
        context: moderngl.Context,
        items: Sequence[Renderable] = None,
    ):
        super().__init__(context)
        self._items = items or []

    def render(self, state: RenderState):
        for item in self._items:
            item.render(state)
