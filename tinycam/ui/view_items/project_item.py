import moderngl as mgl
import shapely as s
from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.types import Vector4, Matrix44, Box
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core.composite import Composite
from tinycam.ui.view_items.core.polygon import Polygon
from tinycam.ui.utils import qcolor_to_vec4


class CncProjectItemView[T: CncProjectItem](Composite):
    priority = 100

    def __init__(self, context: Context, model: T):
        super().__init__(
            context,
        )
        self._model = model
        self._model.changed.connect(self._on_model_changed)
        self._model.updated.connect(self._on_model_changed)
        self._view = None
        self._view_geometry = None
        self._tool_diameter = None
        self._update_geometry()

    @property
    def model(self) -> T:
        return self._model

    @property
    def bounds(self) -> Box:
        if self._view_geometry is None:
            return Box(0, 0, 0, 0, 0, 0).extend(0.2, 0.2, 0.2)
        match self._view_geometry:
            case s.MultiPolygon():
                xmin = min(
                    coord[0]
                    for geom in self._view_geometry.geoms
                    for coord in geom.exterior.coords
                )
                ymin = min(
                    coord[1]
                    for geom in self._view_geometry.geoms
                    for coord in geom.exterior.coords
                )

                xmax = max(
                    coord[0]
                    for geom in self._view_geometry.geoms
                    for coord in geom.exterior.coords
                )
                ymax = max(
                    coord[1]
                    for geom in self._view_geometry.geoms
                    for coord in geom.exterior.coords
                )
            case _:
                G = GLOBALS.GEOMETRY
                points = G.points(self._view_geometry)
                xmin = min(float(coord.x) for coord in points)
                ymin = min(float(coord.y) for coord in points)

                xmax = max(float(coord.x) for coord in points)
                ymax = max(float(coord.y) for coord in points)

        return Box.from_coords(xmin, ymin, -0.5, xmax, ymax, 0.5)

    def _update_geometry(self):
        geometry = self._model.geometry
        if self._view_geometry is geometry:
            return

        if self._view is not None:
            self.remove_item(self._view)

        if geometry is not None:
            self._view = Polygon(
                self.context,
                geometry,
                model_matrix=self._model_matrix(),
                color=qcolor_to_vec4(self._model.color),
            )
            self._view_geometry = geometry
            self.add_item(self._view)

    def _model_matrix(self):
        return Matrix44.identity()

    def _on_model_changed(self, model: T):
        self._update_geometry()

        for item in self.items:
            item.model_matrix = self._model_matrix()

    def render(self, state: RenderState):
        if not self._model.visible:
            return

        if state.picking:
            color = state.register_pickable(self)
            color = Vector4(float(color[0]) / 255.0, float(color[1]) / 255.0, float(color[2]) / 255.0, float(color[3]) / 255.0)
        else:
            color = self._model.color
            if self._model.selected:
                color = color.lighter(150)
            color = qcolor_to_vec4(color)

        for item in self.items:
            item.color = color

        with self.context.scope(disable=mgl.DEPTH_TEST, wireframe=self._model.debug, depth_func='<='):
            super().render(state)
