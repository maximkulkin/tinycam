import moderngl as mgl
import shapely
from tinycam.project import CncProjectItem
from tinycam.types import Vector4, Matrix44
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core.composite import Composite
from tinycam.ui.view_items.core.polygon import Polygon
from tinycam.ui.utils import qcolor_to_vec4


class CncProjectItemView(Composite):
    priority = 100

    def __init__(self, context: Context, index: int, model: CncProjectItem):
        super().__init__(
            context,
        )
        self.index = index
        self._model = model
        self._model.changed.connect(self._on_model_changed)
        self._model.updated.connect(self._on_model_changed)
        self._view = None
        self._view_geometry = None
        self._tool_diameter = None
        self._update_geometry()

    def _update_geometry(self):
        if self._view_geometry is self._model.geometry:
            return

        if self._view is not None:
            self.remove_item(self._view)

        if self._model.geometry is not None:
            view = Polygon(
                self.context,
                self._transform_geometry(self._model, self._model.geometry),
                model_matrix=self._model_matrix(),
                color=qcolor_to_vec4(self._model.color),
            )
            self._view_geometry = self._model.geometry
            self.add_item(view)

    def _transform_geometry(self, model, geometry):
        return shapely.transform(geometry, lambda p: p * (1.0, -1.0))

    def _model_matrix(self):
        return (
            Matrix44.from_translation((self._model.offset[0], self._model.offset[1], 0.0)) *
            Matrix44.from_scale((self._model.scale[0], self._model.scale[1], 1.0))
        )

    def _on_model_changed(self):
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
