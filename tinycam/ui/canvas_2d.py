from PySide6 import QtCore
from tinycam.project import CncProject, GerberItem, ExcellonItem, CncJob
from tinycam.ui.camera import OrthographicCamera
from tinycam.ui.camera_controllers import PanAndZoomController
from tinycam.ui.view import CncView
from tinycam.ui.view_items.core.grid_xy import GridXY
from tinycam.ui.view_items.project_item import CncProjectItemView
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
            case GerberItem() | ExcellonItem() | CncJob():
                view = CncProjectItemView(self.ctx, index, item)
            case _:
                return

        self.add_item(view)

    def _on_project_item_removed(self, item: CncProjectItem):
        for view in self.items:
            if isinstance(view, CncProjectItemView) and view.model is item:
                self.remove_item(view)
                self.update()
                break



