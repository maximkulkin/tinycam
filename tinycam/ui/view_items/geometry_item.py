from tinycam import geometry as g
from tinycam.globals import GLOBALS
from tinycam.types import Vector4
from tinycam.project.geometry import (
    CapStyle as ModelCapStyle,
    JointStyle as ModelJointStyle,
)
from tinycam.ui.view_items.core import Node3D, Line2D, Polygon
from tinycam.ui.view_items.core.line2d import (
    CapStyle as Line2DCapStyle,
    JointStyle as Line2DJointStyle,
)
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.utils import qcolor_to_vec4


class GeometryItemView(CncProjectItemView):

    def _update_geometry(self):
        geometry = self._model.geometry

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

        cap_style = Line2DCapStyle.BUTT
        joint_style = Line2DJointStyle.MITER

        match self.model.cap_style:
            case ModelCapStyle.BUTT:
                cap_style = Line2DCapStyle.BUTT
            case ModelCapStyle.SQUARE:
                cap_style = Line2DCapStyle.SQUARE
            case ModelCapStyle.ROUND:
                cap_style = Line2DCapStyle.ROUND

        match self.model.joint_style:
            case ModelJointStyle.MITER:
                joint_style = Line2DJointStyle.MITER
            case ModelJointStyle.BEVEL:
                joint_style = Line2DJointStyle.BEVEL
            case ModelJointStyle.ROUND:
                joint_style = Line2DJointStyle.ROUND

        item = None
        match geometry:
            case g.Ring():
                item = Line2D(
                    self.context,
                    list(G.points(geometry)),
                    closed=True,
                    color=color,
                    width=self.model.line_thickness if self.model.line_thickness > 0 else None,
                    cap_style=cap_style,
                    joint_style=joint_style,
                    max_segment_length=self.model.line_thickness * 10.0 if self.model.line_thickness > 0 else None,
                )

            case g.Line():
                item = Line2D(
                    self.context,
                    list(G.points(geometry)),
                    closed=False,
                    color=color,
                    width=self.model.line_thickness if self.model.line_thickness > 0 else None,
                    cap_style=cap_style,
                    joint_style=joint_style,
                    max_segment_length=self.model.line_thickness * 10.0 if self.model.line_thickness > 0 else None,
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
