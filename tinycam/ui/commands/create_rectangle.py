from tinycam.project import CncProjectItem, RectangleItem
from tinycam.types import Rect
from tinycam.ui.commands.create_item import CreateItemCommandBase


class CreateRectangleCommand(CreateItemCommandBase):
    def __init__(self, rect: Rect):
        super().__init__('Create rectangle')
        self._rect = rect
        self._item = None

    @property
    def rect(self) -> Rect:
        return self._rect

    @property
    def item(self) -> CncProjectItem | None:
        if self._item is None:
            self._item = RectangleItem(self.rect)

        return self._item
