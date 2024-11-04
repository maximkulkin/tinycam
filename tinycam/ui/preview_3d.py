from PySide6 import QtCore, QtGui
import shapely
import moderngl
from tinycam.types import Vector3, Vector4
from tinycam.project import CncProjectItem, GerberItem, ExcellonItem
from tinycam.ui.view import CncView
from tinycam.ui.canvas import CncCanvas, RenderState
from tinycam.ui.camera_controllers import PanAndZoomController
from tinycam.ui.renderables.grid_xy import GridXY
from tinycam.ui.renderables.lines import Lines
from tinycam.ui.renderables.polygon import Polygon
from typing import Optional
from tinycam.ui.utils import unproject


def qcolor_to_vec4(color: QtGui.QColor) -> Vector4:
    return Vector4((color.redF(), color.greenF(), color.blueF(), color.alphaF()))


class CncProjectItemView(Polygon):
    def __init__(self, context: moderngl.Context, index: int, model: CncProjectItem):
        super().__init__(
            context,
            shapely.transform(model.geometry, lambda p: p * (1.0, -1.0)),
            qcolor_to_vec4(model.color),
        )
        self.index = index
        self._model = model
        self._model.changed.connect(self._on_model_changed)

    def _on_model_changed(self):
        color = self._model.color
        if self._model.selected:
            color = color.lighter(150)

        self._program['color'].write(qcolor_to_vec4(color).astype('f4').tobytes())

    def render(self, state: RenderState):
        if not self._model.visible:
            return

        if self._model.debug:
            self.context.wireframe = True
        super().render(state)
        if self._model.debug:
            self.context.wireframe = False


class CncPreview3DView(CncCanvas, CncView):
    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project
        self.project.items.added.connect(self._on_project_item_added)
        self.project.items.removed.connect(self._on_project_item_removed)
        self.project.items.changed.connect(self._on_project_item_changed)

        self._controller = PanAndZoomController(self._camera)
        self.installEventFilter(self._controller)

    def initializeGL(self):
        super().initializeGL()
        self.objects = [
            GridXY(self.ctx),
            Lines(self.ctx, [
                (-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1),
            ]),
        ]

        for i, _ in enumerate(self.project.items):
            self._on_project_item_added(i)

    def screen_to_canvas_point(self, p: QtCore.QPoint, depth: float = 0.0) -> Vector3:
        return unproject((p.x(), p.y()), (self.width(), self.height()), self.camera)

    def canvas_to_screen_point(self, p: Vector3) -> QtCore.QPoint:
        sp = self.camera.projection_matrix * self.camera.view_matrix * Vector4((p[0], p[1], p[2], 1.0))
        return QtCore.QPoint(
            (sp[0] * 0.5 + 0.5) * self.width(),
            (0.5 - sp[1] * 0.5) * self.height(),
        )

    def _zoom(self, amount: float, point: Optional[QtCore.QPoint] = None):
        p0 = self.screen_to_canvas_point(point)

        self._camera.position *= Vector3((1.0, 1.0, 1.0 / amount))

        p1 = self.screen_to_canvas_point(point)
        d = p0 - p1

        self._camera.position += Vector3((d.x, d.y, 0))
        self.update()

    def _on_project_item_added(self, index: int):
        item = self.project.items[index]

        view = None
        if isinstance(item, (GerberItem, ExcellonItem)):
            view = CncProjectItemView(self.ctx, index, item)
            for existing_view in self.objects:
                if hasattr(existing_view, 'index') and existing_view.index >= index:
                    existing_view.index += 1

        if view is None:
            return

        self.objects.append(view)
        self.update()

    def _on_project_item_removed(self, index: int):
        for view in self.objects:
            if hasattr(view, 'index') and view.index == index:
                self.objects.remove(view)
                self.update()
                break

        for view in self.objects:
            if hasattr(view, 'index') and view.index > index:
                view.index -= 1

    def _on_project_item_changed(self, index: int):
        self.update()

    def paintGL(self):
        super().paintGL()

        self.ctx.clear(color=(0.0, 0.0, 0.0, 1.0))
        self.makeCurrent()

        state = RenderState()
        state.screen_size = self.width(), self.height()
        state.camera = self._camera

        for obj in self.objects:
            obj.render(state)
