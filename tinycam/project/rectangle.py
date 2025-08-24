from tinycam.globals import GLOBALS
from tinycam.geometry import AnyShape
from tinycam.project.geometry import GeometryItem
import tinycam.properties as p
from tinycam.types import Rect


class RectangleItem(GeometryItem):

    def __init__(self, rect: Rect):
        super().__init__()
        self.name = 'Rectangle'
        self._rect = rect
        self._corner_radius = 0
        self._update_geometry()

    @property
    def geometry(self) -> AnyShape:
        return self._geometry

    @property
    def rect(self) -> Rect:
        return self._rect

    def _update(self):
        self._update_geometry()
        self._signal_updated()

    corner_radius = p.Property[float](
        on_update=_update,
        default=0.0,
        metadata=[p.Order(3)],
    )

    def _update_geometry(self):
        G = GLOBALS.GEOMETRY

        if self._corner_radius == 0:
            self._geometry = G.box(self.rect.pmin, self.rect.pmax).exterior
            return

        radius = self._corner_radius
        if 2 * radius > min(float(self.rect.width), float(self.rect.height)):
            radius = min(float(self.rect.width), float(self.rect.height)) * 0.5

        rect = self.rect.extend(-radius, -radius)
        self._geometry = G.buffer(G.box(rect.pmin, rect.pmax).exterior, radius).exterior
