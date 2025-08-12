from tinycam import geometry as g
from tinycam.globals import GLOBALS
from tinycam.types import Vector4
from tinycam.ui.view_items.core import Node3D, Line2D, Polygon
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.utils import qcolor_to_vec4


class GeometryItemView(CncProjectItemView):

    def _update_geometry(self):
        geometry = self._model.geometry
        if self._geometry is geometry:
            return

        if self._geometry_view is not None:
            self.remove_child(self._geometry_view)

        if geometry is not None:
            self._geometry_view = self._make_geometry_view(
                geometry,
                color=qcolor_to_vec4(self.model.color),
            )
            self._geometry = geometry
            self.add_child(self._geometry_view)

    def _make_geometry_view(
        self,
        geometry: g.Shape,
        color: Vector4 = Vector4(1, 1, 1, 1),
    ) -> Node3D:
        G = GLOBALS.GEOMETRY

        item = None
        match geometry:
            case g.Line():
                item = Line2D(
                    self.context,
                    list(G.points(geometry)),
                    closed=False,
                    color=color,
                )

            case g.Ring():
                item = Line2D(
                    self.context,
                    list(G.points(geometry)),
                    closed=True,
                    color=color,
                )

            case g.Polygon() | g.MultiPolygon():
                item = Polygon(self.context, polygon=geometry, color=color)

            case g.MultiLineString() | g.Group():
                item = Node3D(self.context)
                for line in G.shapes(geometry):
                    item.add_child(self._make_geometry_view(line, color=color))

            case _:
                raise ValueError('Unsupported geometry: %s' % geometry.__class__)

        return item
