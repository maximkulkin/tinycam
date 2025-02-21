from PySide6 import QtCore, QtGui
import shapely
import math
from tinycam.globals import GLOBALS
from tinycam.commands import CncPathType, CncPathTracer
from tinycam.types import Vector3, Vector4
from tinycam.project import CncProjectItem, GerberItem, ExcellonItem, CncJob, CncIsolateJob
import tinycam.settings as s
from tinycam.ui.view import CncView
from tinycam.ui.canvas import Context, CncCanvas, RenderState
from tinycam.ui.camera_controllers import PanAndZoomController, OrbitController
from tinycam.ui.renderables.grid_xy import GridXY
from tinycam.ui.renderables.line2d import Line2D
from tinycam.ui.renderables.line3d import Line3D
from tinycam.ui.renderables.orientation_cube import OrientationCube, Orientation, OrientationCubePosition
from tinycam.ui.renderables.polygon import Polygon
from tinycam.ui.renderables.composite import Composite
from tinycam.types import Matrix44
from typing import Optional
from tinycam.ui.utils import project, unproject
from tinycam.ui.tools import PanTool


def qcolor_to_vec4(color: QtGui.QColor) -> Vector4:
    return Vector4(color.redF(), color.greenF(), color.blueF(), color.alphaF())


PATH_COLORS = {
    CncPathType.TRAVEL: Vector4(0, 0, 1, 1),
    CncPathType.CUT: Vector4(1, 0, 1, 1),
}


class CncProjectItemView(Composite):
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

        color = self._model.color
        if self._model.selected:
            color = color.lighter(150)

        for item in self.items:
            item.color = qcolor_to_vec4(color)
            item.model_matrix = self._model_matrix()

    def render(self, state: RenderState):
        if not self._model.visible:
            return

        with self.context.scope(wireframe=self._model.debug):
            super().render(state)


class CncPathView(Line3D):
    @property
    def color(self) -> Vector4:
        return self._color

    @color.setter
    def color(self, value: Vector4):
        pass


class CncIsolateJobView(CncProjectItemView):

    def _model_matrix(self):
        return Matrix44.identity()

    def _update_geometry(self):
        if self._view_geometry is self._model.geometry and self._model.tool_diameter == self._tool_diameter:
            return

        self.clear_items()

        G = GLOBALS.GEOMETRY

        if self._model.geometry is not None:
            for line in G.lines(self._model.geometry):
                line_view = Line2D(
                    self.context,
                    G.points(self._transform_geometry(self._model, line)),
                    closed=line.is_closed,
                    color=qcolor_to_vec4(self._model.color),
                    width=self._model.tool_diameter,
                )
                self.add_item(line_view)

            commands = self._model.generate_commands()
            tracer = CncPathTracer()
            tracer.execute_commands(commands)

            current_path_points = []
            current_path_type = None
            for path in tracer.paths:
                if path.type != current_path_type:
                    if current_path_points:
                        path_view = CncPathView(
                            self.context,
                            current_path_points,
                            color=PATH_COLORS[current_path_type],
                        )
                        self.add_item(path_view)

                    current_path_points = [path.start * Vector3(1, -1, 1), path.end * Vector3(1, -1, 1)]
                    current_path_type = path.type
                else:
                    current_path_points.append(path.end * Vector3(1, -1, 1))

            if current_path_points:
                path_view = CncPathView(
                    self.context,
                    current_path_points,
                    color=PATH_COLORS[current_path_type],
                )
                self.add_item(path_view)

            self._view_geometry = self._model.geometry
            self._tool_diameter = self._model.tool_diameter


s.SETTINGS.register('preview/orientation_cube_position',
                    s.CncEnumSetting, enum_type=OrientationCubePosition,
                    default=OrientationCubePosition.TOP_RIGHT)


class CncPreview3DView(CncCanvas, CncView):
    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project
        self.project.items.added.connect(self._on_project_item_added)
        self.project.items.removed.connect(self._on_project_item_removed)
        self.project.items.changed.connect(self._on_project_item_changed)
        self.project.items.updated.connect(self._on_project_item_updated)

        self._tool = PanTool(self.project, self)
        self._tool.activate()

        self._camera_orbit_controller = OrbitController(self._camera)
        self._controllers = [
            PanAndZoomController(self._camera),
            self._camera_orbit_controller,
        ]
        for controller in self._controllers:
            self.installEventFilter(controller)

    def initializeGL(self):
        super().initializeGL()

        self._orientation_cube = OrientationCube(
            self.ctx,
            self._camera,
            position=s.SETTINGS.get('preview/orientation_cube_position'),
        )
        self._orientation_cube.eventFilter.orientation_selected.connect(self._on_orientation_selected)
        s.SETTINGS['preview/orientation_cube_position'].changed.connect(self._on_orienation_cube_position_changed)
        self.installEventFilter(self._orientation_cube.eventFilter)

        self.objects = [
            GridXY(self.ctx),
            self._orientation_cube,
            # Line3D(
            #     self.ctx,
            #     points=[
            #         (0.0, 0.0, 0.0),
            #         (5.0, 0.0, 0.0),
            #         (5.0, 0.0, 5.0),
            #         (5.0, 5.0, 5.0),
            #     ],
            #     color=Vector4(1.0, 1.0, 0.0, 1.0),
            # ),
            # Line3D(
            #     self.ctx,
            #     points=[
            #         (0.0, 0.0, 0.0),
            #         (5.0, 0.0, 0.0),
            #         (5.0, 0.0, 5.0),
            #         (5.0, 5.0, 5.0),
            #     ],
            #     color=Vector4((1.0, 1.0, 0.0, 1.0)),
            #     width=0.2,
            # ),
        ]

        for i, _ in enumerate(self.project.items):
            self._on_project_item_added(i)

    def screen_to_canvas_point(self, p: QtCore.QPoint, depth: float = 0.0) -> Vector3:
        return unproject((p.x(), p.y()), self.camera)

    def canvas_to_screen_point(self, p: Vector3) -> QtCore.QPoint:
        v = project(p, self.camera)
        return QtCore.QPoint(v.x, v.y)

    def _zoom(self, amount: float, point: Optional[QtCore.QPoint] = None):
        p0 = self.screen_to_canvas_point(point)

        self._camera.position *= Vector3(1.0, 1.0, 1.0 / amount)

        p1 = self.screen_to_canvas_point(point)
        d = p0 - p1

        self._camera.position += Vector3(d.x, d.y, 0)
        self.update()

    def _zoom_region(self, region: QtCore.QRectF):
        z = max(region.width() * 1.1 * 0.5 / math.tan(self._camera.fov * 0.5),
                region.height() * 1.1 * 0.5 / math.tan(self._camera.fov * 0.5))
        self._camera.position = Vector3(region.center().x(), -region.center().y(), z)
        self.update()

    def zoom_to_fit(self):
        pass

    def _on_orienation_cube_position_changed(self, value: OrientationCubePosition):
        self._orientation_cube.position = value
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

        view = None
        if isinstance(item, CncIsolateJob):
            view = CncIsolateJobView(self.ctx, index, item)
        elif isinstance(item, (GerberItem, ExcellonItem, CncJob)):
            view = CncProjectItemView(self.ctx, index, item)

        if view is None:
            return

        for existing_view in self.objects:
            if hasattr(existing_view, 'index') and existing_view.index >= index:
                existing_view.index += 1
        self.objects.insert(index, view)
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

    def _on_project_item_updated(self, index: int):
        self.update()

    def _render(self):
        self.ctx.clear(color=(0.0, 0.0, 0.0, 1.0))

        super()._render()
