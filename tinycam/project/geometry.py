import enum
from typing import cast

from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem
import tinycam.properties as p
from tinycam.math_types import Vector2


class JointStyle(enum.Enum):
    MITER = enum.auto()
    BEVEL = enum.auto()
    ROUND = enum.auto()

    def __str__(self) -> str:
        return self.name


class CapStyle(enum.Enum):
    BUTT = enum.auto()
    SQUARE = enum.auto()
    ROUND = enum.auto()

    def __str__(self) -> str:
        return self.name


class GeometryItem(CncProjectItem):
    def __init__(self):
        super().__init__()
        self.name = 'Geometry'
        self.color = QtGui.QColor.fromRgbF(0.5, 0.5, 0.5, 1.0)
        self._geometry = GLOBALS.GEOMETRY.group()

    def _update(self):
        self._signal_changed()

    @property
    def is_filled(self) -> bool:
        """True when the geometry contains at least one filled polygon."""
        return GLOBALS.GEOMETRY.is_filled(self._geometry)

    line_thickness = p.Property[float](
        on_update=_update,
        default=0.0,
        metadata=[
            p.Order(0),
            p.VisibleIf(lambda item: not cast(GeometryItem, item).is_filled),
        ],
    )
    joint_style = p.Property[JointStyle](
        on_update=_update,
        default=JointStyle.MITER,
        metadata=[
            p.Order(1),
            p.VisibleIf(lambda item: (
                not cast(GeometryItem, item).is_filled and
                cast(GeometryItem, item).line_thickness > 0
            )),
        ],
    )
    cap_style = p.Property[CapStyle](
        on_update=_update,
        default=CapStyle.BUTT,
        metadata=[
            p.Order(2),
            p.VisibleIf(lambda item: (
                not cast(GeometryItem, item).is_filled and
                cast(GeometryItem, item).line_thickness > 0
            )),
        ],
    )

    def translate(self, offset: Vector2):
        self.geometry = GLOBALS.GEOMETRY.translate(self.geometry, offset)

    def scale(self, scale: Vector2, origin: Vector2 = Vector2()):
        self.geometry = GLOBALS.GEOMETRY.scale(
            self.geometry,
            factor=scale,
            origin=origin,
        )
