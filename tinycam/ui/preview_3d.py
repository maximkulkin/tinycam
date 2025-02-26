import math
from tinycam.project import GerberItem, ExcellonItem, CncJob, CncIsolateJob
import tinycam.settings as s
from tinycam.ui.view import CncView
from tinycam.ui.camera_controllers import PanAndZoomController, OrbitController
from tinycam.ui.view_items.core.grid_xy import GridXY
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.view_items.isolate_job import CncIsolateJobView
from tinycam.ui.view_items.orientation_cube import OrientationCube, Orientation, OrientationCubePosition
from tinycam.ui.tools import SelectTool


s.SETTINGS.register('3D/orientation_cube_position',
                    s.CncEnumSetting, enum_type=OrientationCubePosition,
                    default=OrientationCubePosition.TOP_RIGHT)


class CncPreview3D(CncView):
    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project

        self._tool = SelectTool(self.project, self)
        self._tool.activate()

        self._camera_orbit_controller = OrbitController(self._camera)
        self._pan_and_zoom_controller = PanAndZoomController(self._camera)
        self._controllers = [
            self._pan_and_zoom_controller,
            self._camera_orbit_controller,
        ]
        for controller in self._controllers:
            self.installEventFilter(controller)

    def initializeGL(self):
        super().initializeGL()

        self.add_item(GridXY(self.ctx))

        self._orientation_cube = OrientationCube(
            self.ctx,
            self._camera,
            position=s.SETTINGS.get('3D/orientation_cube_position'),
        )
        self._orientation_cube.orientation_selected.connect(self._on_orientation_selected)
        s.SETTINGS['3D/orientation_cube_position'].changed.connect(self._on_orienation_cube_position_changed)

        self.add_item(self._orientation_cube)

        self.project.items.added.connect(self._on_project_item_added)
        self.project.items.removed.connect(self._on_project_item_removed)
        self.project.items.changed.connect(self._on_project_item_changed)
        self.project.items.updated.connect(self._on_project_item_updated)
        for i, _ in enumerate(self.project.items):
            self._on_project_item_added(i)

    def _on_orienation_cube_position_changed(self, value: OrientationCubePosition):
        self._orientation_cube.orientation_cube_position = value
        self.update()

    def _on_orientation_selected(self, orientation: Orientation):
        pitch = self._camera_orbit_controller.pitch
        yaw = self._camera_orbit_controller.yaw

        PI = math.pi
        PI2 = PI * 2.0
        HPI = PI * 0.5

        def pick_closest_angle(angle: float, target: float) -> float:
            return min([target, target - PI2, target + PI2],
                       key=lambda x: abs(x - angle))

        def pick_closest_pitch_yaw(
            target_pitch: float,
            target_yaw: float,
        ) -> tuple[float, float]:
            return (
                pick_closest_angle(pitch, target_pitch),
                pick_closest_angle(yaw, target_yaw),
            )

        match orientation:
            case Orientation.FRONT:
                pitch, yaw = pick_closest_pitch_yaw(-HPI, 0.0)
            case Orientation.BACK:
                pitch, yaw = pick_closest_pitch_yaw(-HPI, PI)
            case Orientation.TOP:
                pitch, yaw = pick_closest_pitch_yaw(0.0, round(yaw / HPI) * HPI)
            case Orientation.BOTTOM:
                pitch, yaw = pick_closest_pitch_yaw(PI, round(yaw / HPI) * HPI)
            case Orientation.LEFT:
                pitch, yaw = pick_closest_pitch_yaw(-HPI, HPI)
            case Orientation.RIGHT:
                pitch, yaw = pick_closest_pitch_yaw(-HPI, -HPI)

        self._camera_orbit_controller.rotate(pitch=pitch, yaw=yaw, duration=0.5)

    def _on_project_item_added(self, index: int):
        item = self.project.items[index]

        match item:
            case CncIsolateJob():
                view = CncIsolateJobView(self.ctx, index, item)
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
