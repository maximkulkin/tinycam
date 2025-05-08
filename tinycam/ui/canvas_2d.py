from typing import cast

from PySide6 import QtCore
from tinycam.project import CncProject, CncProjectItem, GerberItem, ExcellonItem, CncJob, CncIsolateJob
from tinycam.ui.camera import OrthographicCamera
from tinycam.ui.camera_controllers import PanAndZoomController
from tinycam.ui.view import CncView
from tinycam.ui.view_items.core.grid_xy import GridXY
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.view_items.gerber_item import GerberItemView
from tinycam.ui.view_items.excellon_item import ExcellonItemView
from tinycam.ui.view_items.isolate_job import CncIsolateJobView
from tinycam.ui.tools import CncTool, SelectTool
from tinycam.types import Vector3


class CncCanvas2D(CncView):
    def __init__(self, project: CncProject, *args, **kwargs):
        camera = OrthographicCamera()
        camera.position = Vector3(0, 0, 5)

        super().__init__(camera=camera, *args, **kwargs)

        self._project = project

        self._pan_and_zoom_controller = PanAndZoomController(self._camera)
        self.installEventFilter(self._pan_and_zoom_controller)

    def initializeGL(self):
        super().initializeGL()

        self.add_item(GridXY(self.ctx))

        self.project.items.added.connect(self._on_project_item_added)
        self.project.items.removed.connect(self._on_project_item_removed)
        self.project.items.changed.connect(lambda _: self.update())
        self.project.items.updated.connect(lambda _: self.update())

        for item in self.project.items:
            self._on_project_item_added(item)

        self._tool = SelectTool(self.project, self)
        self._tool.activate()

    def resizeGL(self, width, height):
        super().resizeGL(width, height)
        if isinstance(self._camera, OrthographicCamera):
            self._camera.resize(width, height, keep_aspect=False)

    @property
    def tool(self) -> CncTool:
        return self._tool

    def event(self, event: QtCore.QEvent) -> bool:
        super().event(event)

        if event.isAccepted():
            return True

        if self.tool.eventFilter(self, event):
            return True

        return False

    @property
    def project(self) -> CncProject:
        return self._project

    def _on_project_item_added(self, item: CncProjectItem):
        assert(self.ctx is not None)

        match item:
            case GerberItem():
                view = GerberItemView(self.ctx, item)
            case ExcellonItem():
                view = ExcellonItemView(self.ctx, item)
            case CncIsolateJob():
                view = CncIsolateJobView(self.ctx, item)
            case CncJob():
                view = CncProjectItemView(self.ctx, item)
            case _:
                return

        self.add_item(view)

    def _on_project_item_removed(self, item: CncProjectItem):
        for view in self.items:
            if isinstance(view, CncProjectItemView) and view.model is item:
                self.remove_item(view)
                self.update()
                break

    def zoom_to_fit(self):
        items = [item for item in self.items if isinstance(item, CncProjectItemView)]
        if not items:
            return

        bounds = items[0].bounds
        for item in items[1:]:
            bounds = bounds.merge(item.bounds)

        self.camera.position = Vector3(
            bounds.center.x,
            bounds.center.y,
            bounds.zmax + 5.0
        )
        c = cast(OrthographicCamera, self.camera)
        c.zoom = max(float((bounds.width + 10) / c.width),
                     float((bounds.height + 10) / c.height))

        self.update()
