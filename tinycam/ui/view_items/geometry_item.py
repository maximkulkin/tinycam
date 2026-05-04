from tinycam import geometry as g
from tinycam.globals import GLOBALS
from tinycam.math_types import Vector4
from tinycam.project.geometry import (
    CapStyle as ModelCapStyle,
    JointStyle as ModelJointStyle,
)
from tinycam.ui.view_items.core import Node3D, Line2D, Polygon, Colored, ColoredNode3D
from tinycam.ui.view_items.core.line2d import (
    CapStyle as Line2DCapStyle,
    JointStyle as Line2DJointStyle,
)
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.utils import qcolor_to_vec4


class GeometryItemView(CncProjectItemView):

    def _update_geometry(self):
        geometry = self._model.geometry
        line_thickness = self._model.line_thickness
        cap_style = self._model.cap_style
        joint_style = self._model.joint_style

        if (self._geometry is geometry and
                getattr(self, '_cached_line_thickness', None) == line_thickness and
                getattr(self, '_cached_cap_style', None) == cap_style and
                getattr(self, '_cached_joint_style', None) == joint_style):
            return

        if self._geometry_view is not None:
            self.remove_child(self._geometry_view)
            self._geometry_view = None

        if geometry is not None:
            self._geometry_view = self._make_geometry_view(
                geometry,
                color=qcolor_to_vec4(self.model.color),
            )
            self._geometry = geometry
            self._cached_line_thickness = line_thickness
            self._cached_cap_style = cap_style
            self._cached_joint_style = joint_style
            self.add_child(self._geometry_view)

    def _on_model_changed(self, model):
        super()._on_model_changed(model)

        color = self._model.color
        if color == getattr(self, '_cached_color', None):
            return
        self._cached_color = color

        if self._geometry_view is None:
            return

        if isinstance(self._geometry_view, Colored):
            self._geometry_view.color = qcolor_to_vec4(color)

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
                )

            case g.Polygon() | g.MultiPolygon():
                item = Polygon(self.context, polygon=geometry, color=color)

            case g.MultiLineString() | g.Group():
                item = ColoredNode3D(self.context, color=color)
                for line in G.shapes(geometry):
                    item.add_child(self._make_geometry_view(line, color=color))

            case _:
                raise ValueError('Unsupported geometry: %s' % geometry.__class__)

        return item
