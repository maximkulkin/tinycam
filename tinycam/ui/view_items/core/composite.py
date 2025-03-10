from collections.abc import Sequence

from tinycam.ui.view import Context, ViewItem, RenderState


class Composite(ViewItem):
    def __init__(
        self,
        context: Context,
        items: Sequence[ViewItem] | None = None,
    ):
        super().__init__(context)
        self._items = list(items or [])

    @property
    def items(self) -> Sequence[ViewItem]:
        return self._items

    def add_item(self, item: ViewItem):
        self._items.append(item)

    def remove_item(self, item: ViewItem):
        self._items.remove(item)

    def clear_items(self):
        self._items.clear()

    def render(self, state: RenderState):
        for item in self._items:
            item.render(state)
