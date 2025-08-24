from typing import Sequence

from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem, GeometryItem
from tinycam.types import Vector2
from tinycam.ui.commands.create_item import CreateItemCommandBase


class CreatePolylineCommand(CreateItemCommandBase):
    def __init__(self, points: Sequence[Vector2], closed: bool = False):
        super().__init__('Create line')
        self._item = None

        self._points = points
        self._closed = closed

        self._previous_selection = []

    @property
    def points(self) -> Sequence[Vector2]:
        return self._points

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def item(self) -> CncProjectItem | None:
        if self._item is None:
            self._item = GeometryItem()
            self._item.name = 'Line'
            self._item.geometry = GLOBALS.GEOMETRY.line(
                self.points,
                closed=self.closed,
            )

        return self._item
