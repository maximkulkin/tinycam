from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project import GeometryItem
from tinycam.types import Vector2


class CreateCircleCommand(QtGui.QUndoCommand):
    def __init__(self, center: Vector2, radius: float):
        super().__init__('Create circle')
        self._item = GeometryItem()
        self._item.name = 'Circle'
        self._item.geometry = GLOBALS.GEOMETRY.circle(
            diameter=2 * radius,
            center=center,
        ).exterior

    def redo(self):
        GLOBALS.APP.project.items.append(self._item)

    def undo(self):
        GLOBALS.APP.project.items.remove(self._item)


