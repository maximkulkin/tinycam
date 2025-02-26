from tinycam.project import CncProject
from tinycam.ui.camera_controllers import PanAndZoomController
from tinycam.ui.view import CncView
from tinycam.ui.view_items.core.grid_xy import GridXY


class CncCanvas2D(CncView):
    def __init__(self, project: CncProject, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._project = project

        self._pan_and_zoom_controller = PanAndZoomController(self._camera)
        self.installEventFilter(self._pan_and_zoom_controller)

    def initializeGL(self):
        super().initializeGL()

        self.add_item(GridXY(self.ctx))

    @property
    def project(self) -> CncProject:
        return self._project
