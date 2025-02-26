from tinycam.project import CncProject, GerberItem, ExcellonItem, CncJob
from tinycam.ui.camera_controllers import PanAndZoomController
from tinycam.ui.view import CncView
from tinycam.ui.view_items.core.grid_xy import GridXY
from tinycam.ui.view_items.project_item import CncProjectItemView


class CncCanvas2D(CncView):
    def __init__(self, project: CncProject, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._project = project

        self._pan_and_zoom_controller = PanAndZoomController(self._camera)
        self.installEventFilter(self._pan_and_zoom_controller)

    def initializeGL(self):
        super().initializeGL()

        self.add_item(GridXY(self.ctx))

        self.project.items.added.connect(self._on_project_item_added)
        self.project.items.removed.connect(self._on_project_item_removed)
        self.project.items.changed.connect(self._on_project_item_changed)
        self.project.items.updated.connect(self._on_project_item_updated)
        for i, _ in enumerate(self.project.items):
            self._on_project_item_added(i)

    @property
    def project(self) -> CncProject:
        return self._project

    def _on_project_item_added(self, index: int):
        item = self.project.items[index]

        match item:
            case GerberItem() | ExcellonItem() | CncJob():
                view = CncProjectItemView(self.ctx, index, item)
            case _:
                return

        for existing_view in self.items:
            if hasattr(existing_view, 'index') and existing_view.index >= index:
                existing_view.index += 1
        self.add_item(view)

        self.update()

    def _on_project_item_removed(self, index: int):
        for view in self.items:
            if hasattr(view, 'index') and view.index == index:
                self.remove_item(view)
                self.update()
                break

        for view in self.items:
            if hasattr(view, 'index') and view.index > index:
                view.index -= 1

    def _on_project_item_changed(self, index: int):
        self.update()

    def _on_project_item_updated(self, index: int):
        self.update()
