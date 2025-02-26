from collections.abc import Sequence
from tinycam.ui.view import Context, ViewItem


class Composite(ViewItem):
    def __init__(
        self,
        context: Context,
        items: Sequence[ViewItem] = None,
    ):
        super().__init__(context)
        self._items = items or []

    @property
    def items(self) -> Sequence[ViewItem]:
        return self._items

    def add_item(self, item: ViewItem):
        self._items.append(item)

    def remove_item(self, item: ViewItem):
        self._items.remove(item)

    def clear_items(self):
        self._items.clear()

    def render(self, state: ViewItem):
        for item in self._items:
            item.render(state)
