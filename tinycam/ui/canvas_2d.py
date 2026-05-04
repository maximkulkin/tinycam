from functools import reduce
from typing import cast

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from tinycam.globals import GLOBALS
from tinycam.project import (
    CncProject, CncProjectItem, GerberItem, ExcellonItem, ImageItem, SvgItem,
    CncJob, CncCutoutJob, CncIsolateJob, CncDrillJob,
    GeometryItem,
)
import tinycam.settings as s
from tinycam.ui.camera import OrthographicCamera
from tinycam.ui.camera_controllers import (
    PanAndZoomController,
    CameraPanAndZoomAnimation,
)
from tinycam.ui.view import CncView, SnapFlags, SnapResult
from tinycam.ui.view_items.grid import Grid
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.view_items.gerber_item import GerberItemView
from tinycam.ui.view_items.excellon_item import ExcellonItemView
from tinycam.ui.view_items.cutout_job import CncCutoutJobView
from tinycam.ui.view_items.drill_job import CncDrillJobView
from tinycam.ui.view_items.isolate_job import CncIsolateJobView
from tinycam.ui.view_items.geometry_item import GeometryItemView
from tinycam.ui.view_items.image_item import ImageItemView
from tinycam.ui.tools import CncTool, DummyTool
from tinycam.ui.utils import vector2
from tinycam.math_types import Box, Vector2, Vector3


class CncCanvas2D(CncView):

    def __init__(self, project: CncProject, *args, **kwargs):
        camera = OrthographicCamera()
        camera.position = Vector3(0, 0, 5)

        super().__init__(camera=camera, *args, **kwargs)

        self._camera_initialized = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._project = project

        self._pan_and_zoom_controller = PanAndZoomController(self._camera)
        self.installEventFilter(self._pan_and_zoom_controller)

        self._animation = None

        self._default_tool = DummyTool(self.project, self)
        self._tool = self._default_tool

    def initializeGL(self):
        super().initializeGL()

        self._grid = Grid(self.ctx, s.SETTINGS.get('general/machine_area_size'))
        self.add_item(self._grid)
        s.SETTINGS['general/machine_area_size'].changed.connect(
            self._on_machine_area_size_changed
        )

        self.project.items.added.connect(self._on_project_item_added)
        self.project.items.removed.connect(self._on_project_item_removed)
        self.project.items.changed.connect(lambda _: self.update())
        self.project.items.updated.connect(lambda _: self.update())

        for item in self.project.items:
            self._on_project_item_added(item)

        if self.tool is not None:
            self.tool.activate()

    def resizeGL(self, width, height):
        super().resizeGL(width, height)
        if isinstance(self._camera, OrthographicCamera):
            self._camera.resize(width, height, keep_aspect=False)

            if not self._camera_initialized:
                self._zoom_to_region(self._grid.bounds, duration=0)
                self._camera_initialized = True

    @property
    def tool(self) -> CncTool:
        return self._tool

    @tool.setter
    def tool(self, value: CncTool):
        if self._tool is not None:
            self._tool.deactivated.disconnect(self._on_tool_deactivated)
            self._tool.deactivate()
        self._tool = value
        if self.initialized:
            self.tool.deactivated.connect(self._on_tool_deactivated)
            self._tool.activate()

    @property
    def default_tool(self) -> CncTool:
        return self._default_tool

    @default_tool.setter
    def default_tool(self, value: CncTool):
        self._default_tool = value

    def _on_tool_deactivated(self):
        self._tool = self._default_tool
        self._tool.activate()

    def event(self, event: QtCore.QEvent) -> bool:
        super().event(event)

        if event.isAccepted():
            return True

        if self.tool is not None and self.tool.eventFilter(self, event):
            return True

        if event.type() == QtCore.QEvent.Type.MouseMove:
            mouse_event = cast(QMouseEvent, event)
            self.coordinateChanged.emit(
                self.camera.unproject(vector2(mouse_event.position()))
            )

        return False

    @property
    def project(self) -> CncProject:
        return self._project

    def _on_project_item_added(self, item: CncProjectItem):
        match item:
            case GerberItem():
                view = GerberItemView(self.ctx, item)
            case ExcellonItem():
                view = ExcellonItemView(self.ctx, item)
            case ImageItem():
                view = ImageItemView(self.ctx, item)
            case SvgItem():
                view = GeometryItemView(self.ctx, item)
            case CncCutoutJob():
                view = CncCutoutJobView(self.ctx, item)
            case CncIsolateJob():
                view = CncIsolateJobView(self.ctx, item)
            case CncDrillJob():
                view = CncDrillJobView(self.ctx, item)
            case CncJob():
                view = CncProjectItemView(self.ctx, item)
            case GeometryItem():
                view = GeometryItemView(self.ctx, item)
            case _:
                return

        self.add_item(view)

    def _on_project_item_removed(self, item: CncProjectItem):
        for view in self.items:
            if isinstance(view, CncProjectItemView) and view.model is item:
                self.remove_item(view)
                self.update()
                break

    def zoom_in(self):
        self._pan_and_zoom_controller.zoom(1.0, duration=0.2)

    def zoom_out(self):
        self._pan_and_zoom_controller.zoom(-1.0, duration=0.2)

    def zoom_to_fit(self):
        items = [
            item
            for item in self.items
            if isinstance(item, CncProjectItemView) and item.visible
        ]
        if not items:
            return

        bounds = reduce(Box.merge, (item.bounds for item in items))

        self._zoom_to_region(bounds)

    def _zoom_to_region(self, region: Box, duration: float=0.5):
        camera = cast(OrthographicCamera, self.camera)

        position = Vector3(region.center.x, region.center.y, region.zmax + 5.0)
        aspect = camera.pixel_width / camera.pixel_height if camera.pixel_height > 0 else 1.0
        zoom_x = camera.width / (region.width + 10)
        zoom_y = (camera.width / aspect) / (region.height + 10)
        zoom = min(zoom_x, zoom_y)

        if duration > 0:
            if self._animation is not None:
                self._animation.stop()

            self._animation = CameraPanAndZoomAnimation(
                camera,
                duration=duration,
                position=position,
                zoom=zoom,
                on_update=self.update,
            )
            self._animation.start()
        else:
            camera.position = position
            camera.zoom = zoom

    def is_item_visible(self, item: CncProjectItem) -> bool:
        if not self._camera_initialized:
            return False
        camera = cast(OrthographicCamera, self.camera)
        bounds = item.bounds
        cx, cy = camera.position.x, camera.position.y
        half_w = camera.width / (2.0 * camera.zoom)
        half_h = camera.height / (2.0 * camera.zoom)
        return (
            bounds.xmin >= cx - half_w and
            bounds.xmax <= cx + half_w and
            bounds.ymin >= cy - half_h and
            bounds.ymax <= cy + half_h
        )

    def zoom_to_grid(self):
        self._zoom_to_region(self._grid.bounds)

    def _on_machine_area_size_changed(self, _: Vector2):
        if self._grid is None:
            return

        self.remove_item(self._grid)
        self._grid = Grid(self.ctx, s.SETTINGS.get('general/machine_area_size'))
        self.add_item(self._grid)

    def snap_point(self, screen_point: Vector2, flags: SnapFlags) -> SnapResult:
        if not GLOBALS.APP.state.snap_to_grid.value:
            return SnapResult(point=screen_point, snapped=False)

        snap_step = GLOBALS.APP.state.snap_step.value
        snap_distance = s.SETTINGS.get('general/snapping/snap_distance')

        world_point = self.camera.screen_to_world_point(screen_point).xy
        grid_point = world_point + snap_step * 0.5
        grid_point -= grid_point % snap_step

        screen_grid_point = self.camera.world_to_screen_point(
            Vector3.from_vector2(grid_point)
        )
        if (flags & SnapFlags.GRID_CORNERS and
                (screen_point - screen_grid_point).length < snap_distance):
            return SnapResult(point=screen_grid_point, snapped=True)

        if flags & SnapFlags.GRID_EDGES:
            if abs(screen_point.x - screen_grid_point.x) < snap_distance:
                return SnapResult(
                    point=Vector2(screen_grid_point.x, screen_point.y),
                    snapped=True,
                )

            if abs(screen_point.y - screen_grid_point.y) < snap_distance:
                return SnapResult(
                    point=Vector2(screen_point.x, screen_grid_point.y),
                    snapped=True,
                )

        return SnapResult(point=screen_point, snapped=False)
