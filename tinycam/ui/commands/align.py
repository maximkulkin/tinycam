from typing import override

from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.math_types import Vector2


class AlignCommandBase(QtGui.QUndoCommand):
    def __init__(self, name: str, items: list[CncProjectItem]):
        super().__init__(name)
        self._items = items
        self._offsets = []

    def _calculate_offsets(self, items: list[CncProjectItem]) -> list[Vector2]:
        raise NotImplementedError()

    def _move(self, item: CncProjectItem, offset: Vector2):
        item.geometry = GLOBALS.GEOMETRY.translate(item.geometry, offset)

    def redo(self):
        self._offsets = self._calculate_offsets(self._items)
        for item, offset in zip(self._items, self._offsets):
            self._move(item, offset)

    def undo(self):
        for item, offset in zip(self._items, self._offsets):
            self._move(item, -offset)


class AlignLeftCommand(AlignCommandBase):
    def __init__(self, items: list[CncProjectItem]):
        super().__init__('Align Left', items)

    @override
    def _calculate_offsets(self, items: list[CncProjectItem]) -> list[Vector2]:
        x = min(item.bounds.xmin for item in items)
        return [Vector2(x - item.bounds.xmin, 0) for item in items]


class AlignRightCommand(AlignCommandBase):
    def __init__(self, items: list[CncProjectItem]):
        super().__init__('Align Right', items)

    @override
    def _calculate_offsets(self, items: list[CncProjectItem]) -> list[Vector2]:
        x = max(item.bounds.xmax for item in items)
        return [Vector2(x - item.bounds.xmax, 0) for item in items]


class AlignCenterCommand(AlignCommandBase):
    def __init__(self, items: list[CncProjectItem]):
        super().__init__('Align Center', items)

    @override
    def _calculate_offsets(self, items: list[CncProjectItem]) -> list[Vector2]:
        xmin = min(item.bounds.xmin for item in items)
        xmax = max(item.bounds.xmax for item in items)
        x = (xmin + xmax) * 0.5
        return [Vector2(x - item.bounds.center.x, 0) for item in items]


class AlignTopCommand(AlignCommandBase):
    def __init__(self, items: list[CncProjectItem]):
        super().__init__('Align Top', items)

    @override
    def _calculate_offsets(self, items: list[CncProjectItem]) -> list[Vector2]:
        y = max(item.bounds.ymax for item in items)
        return [Vector2(0, y - item.bounds.ymax) for item in items]


class AlignBottomCommand(AlignCommandBase):
    def __init__(self, items: list[CncProjectItem]):
        super().__init__('Align Bottom', items)

    @override
    def _calculate_offsets(self, items: list[CncProjectItem]) -> list[Vector2]:
        y = min(item.bounds.ymin for item in items)
        return [Vector2(0, y - item.bounds.ymin) for item in items]


class AlignVCenterCommand(AlignCommandBase):
    def __init__(self, items: list[CncProjectItem]):
        super().__init__('Align VCenter', items)

    @override
    def _calculate_offsets(self, items: list[CncProjectItem]) -> list[Vector2]:
        ymin = min(item.bounds.ymin for item in items)
        ymax = max(item.bounds.ymax for item in items)
        y = (ymin + ymax) * 0.5
        return [Vector2(0, y - item.bounds.center.y) for item in items]
