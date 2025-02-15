from collections.abc import Sequence
from tinycam.ui.canvas import Context, Renderable, RenderState


class Composite(Renderable):
    def __init__(
        self,
        context: Context,
        items: Sequence[Renderable] = None,
    ):
        super().__init__(context)
        self._items = items or []

    @property
    def items(self) -> Sequence[Renderable]:
        return self._items

    def add_item(self, item: Renderable):
        self._items.append(item)

    def remove_item(self, item: Renderable):
        self._items.remove(item)

    def clear_items(self):
        self._items.clear()

    def render(self, state: RenderState):
        for item in self._items:
            item.render(state)
