from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem, GeometryItem
from tinycam.types import Vector2
from tinycam.ui.commands.create_item import CreateItemCommandBase


class CreateCircleCommand(CreateItemCommandBase):
    def __init__(self, center: Vector2, radius: float):
        super().__init__('Create circle')
        self._item = None
        self._center = center
        self._radius = radius

    @property
    def center(self) -> Vector2:
        return self._center

    @property
    def radius(self) -> float:
        return self._radius

    @property
    def item(self) -> CncProjectItem | None:
        if self._item is None:
            self._item = GeometryItem()
            self._item.name = 'Circle'
            self._item.geometry = GLOBALS.GEOMETRY.circle(
                diameter=2 * self.radius,
                center=self.center,
            ).exterior

        return self._item
