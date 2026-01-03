from typing import cast, Sequence

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent, QKeyEvent, QCursor
from PySide6.QtWidgets import QWidget

from tinycam.globals import GLOBALS
from tinycam.types import Vector2, Vector3, Vector4
from tinycam.ui.commands import CreatePolylineCommand
from tinycam.ui.tools import CncTool
from tinycam.ui.utils import vector2
from tinycam.ui.view import SnapFlags, SnapResult
from tinycam.ui.view_items.core import Line2D, Node3D
from tinycam.ui.view_items.core.canvas import Canvas, CanvasItem, Circle, VerticalCross, DiagonalCross


class PolylineTool(CncTool):
    SNAP_THRESHOLD = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drawing = False
        self._points: list[Vector2] = []
        self._last_point = Vector2() # last added point in screen coordinates

        self._canvas = None
        self._marker = None
        self._snap_marker = None

        self._polyline = None
        self._point_controls = []

    def activate(self):
        super().activate()

        if self._canvas is None:
            self._canvas = Canvas(self.view.ctx)
            self._canvas.priority = 5
        self.view.add_item(self._canvas)

        if self._marker is None:
            self._marker = self._make_marker()
            self._canvas.add_item(self._marker)

        if self._snap_marker is None:
            self._snap_marker = self._make_snap_marker()
            self._canvas.add_item(self._snap_marker)

        self._marker.position = vector2(self.view.mapFromGlobal(QCursor.pos()))
        self._marker.visible = True
        self._snap_marker.visible = False

        self.view.update()

    def deactivate(self):
        self.cancel()
        assert self._canvas is not None
        self.view.remove_item(self._canvas)
        super().deactivate()

    def commit(self, closed: bool = False):
        if self._polyline:
            if closed:
                self._create_polyline(self._points[:-2], closed=True)
            else:
                self._create_polyline(self._points[:-1], closed=False)

            self.view.remove_item(self._polyline)
            self._polyline = None

        # self._points = []
        self._drawing = False

    def cancel(self):
        if self._polyline:
            self.view.remove_item(self._polyline)
            self._polyline = None

        if self._point_controls:
            assert self._canvas is not None
            for control in self._point_controls:
                self._canvas.remove_item(control)
            self._point_controls = []

        self._points = []
        self._drawing = False

    def eventFilter(self, widget: QWidget, event: QEvent) -> bool:
        mouse_event = cast(QMouseEvent, event)

        if (event.type() == QEvent.Type.MouseButtonPress and
                mouse_event.button() & Qt.MouseButton.LeftButton):
            screen_point = self._snap_point(vector2(mouse_event.position())).point

            if not self._drawing:
                world_point = self.view.camera.screen_to_world_point(screen_point).xy
                self._points.append(world_point)
                self._points.append(world_point)
                self._last_point = screen_point

                self._polyline = self._make_polyline()
                self.view.add_item(self._polyline)

                self._point_controls = [self._make_point_control(world_point)]
                assert self._canvas is not None
                self._canvas.add_item(self._point_controls[-1])

                self._drawing = True
            else:
                if mouse_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    d = screen_point - self._last_point
                    if abs(d.x) > abs(d.y):
                        screen_point = Vector2(screen_point.x, self._last_point.y)
                    else:
                        screen_point = Vector2(self._last_point.x, screen_point.y)

                world_point = self.view.camera.screen_to_world_point(screen_point).xy

                self._points[-1] = world_point
                self._point_controls.append(
                    self._make_point_control(world_point)
                )
                assert self._canvas is not None
                self._canvas.add_item(self._point_controls[-1])
                self._points.append(world_point)
                self._last_point = screen_point

                if (self._points[-1] - self._points[0]).length < 0.001:
                    self.commit(closed=True)

            self.view.update()

            return True
        elif (event.type() == QEvent.Type.MouseButtonPress and
                mouse_event.button() & Qt.MouseButton.RightButton):
            self.commit()
            return True

        elif event.type() == QEvent.Type.MouseMove:
            assert self._marker is not None
            assert self._snap_marker is not None

            screen_point = vector2(mouse_event.position())
            if not self._drawing:
                p1 = self.view.camera.screen_to_world_point(Vector2(0, 0))
                p2 = self.view.camera.screen_to_world_point(Vector2(1, 0))
                squared_trigger_distance = (p1 - p2).squared_length *  100

                world_point = self.view.camera.screen_to_world_point(screen_point).xy
                for point in self._points:
                    if (point - world_point).squared_length < squared_trigger_distance:
                        self.view.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
                        break
                else:
                    self.view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

            if mouse_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                d = screen_point - self._last_point
                if abs(d.x) > abs(d.y):
                    screen_point = Vector2(screen_point.x, self._last_point.y)
                else:
                    screen_point = Vector2(self._last_point.x, screen_point.y)

            if not (mouse_event.modifiers() & Qt.KeyboardModifier.AltModifier):
                snap_result = self._snap_point(screen_point)
                screen_point = snap_result.point

                self._marker.visible = not snap_result.snapped
                self._snap_marker.visible = snap_result.snapped

            world_point = self.view.camera.screen_to_world_point(screen_point).xy

            self._marker.position = world_point
            self._snap_marker.position = world_point

            if self._drawing:
                self._points[-1] = world_point

                if self._polyline:
                    self.view.remove_item(self._polyline)

                self._polyline = self._make_polyline()
                self.view.add_item(self._polyline)

            self.view.coordinateChanged.emit(world_point)
            self.view.update()
            return True
        elif event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            if key_event.key() == Qt.Key.Key_Escape:
                if self._drawing:
                    self.cancel()
                else:
                    self.deactivate()

                return True
            elif key_event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
                self.commit()
                return True

            elif key_event.key() == Qt.Key.Key_Backspace and self._drawing:
                if len(self._points) <= 2:
                    self.cancel()
                else:
                    del self._points[-2]
                    point_control = self._point_controls[-1]
                    assert self._canvas is not None
                    self._canvas.remove_item(point_control)
                    del self._point_controls[-1]

                    if self._polyline:
                        self.view.remove_item(self._polyline)

                    self._polyline = self._make_polyline()
                    self.view.add_item(self._polyline)

                    self.view.update()

            if key_event.modifiers() & Qt.KeyboardModifier.AltModifier:
                if self._marker is not None:
                    self._marker.visible = True
                if self._snap_marker is not None:
                    self._snap_marker.visible = False

        return False

    def _snap_point(self, point: Vector2) -> SnapResult:
        if self._points:
            world_point = self.view.camera.screen_to_world_point(point).xy
            world_closest_point = min(self._points[:-1], key=lambda p: float((p - world_point).length))
            screen_closest_point = self.view.camera.world_to_screen_point(Vector3.from_vector2(world_closest_point))
            if (screen_closest_point - point).length < self.SNAP_THRESHOLD:
                return SnapResult(screen_closest_point, snapped=True)

        return self.view.snap_point(point, SnapFlags.GRID_EDGES | SnapFlags.GRID_CORNERS)

    def _make_polyline(self) -> Node3D:
        assert self.view.ctx is not None

        line = Line2D(
            context=self.view.ctx,
            points=self._points,
            closed=False,
        )
        line.priority = 1
        return line

    def _make_marker(self) -> CanvasItem:
        marker = VerticalCross(
            self.view.ctx,
            size=Vector2(40, 40),
            screen_space_size=True,
            screen_space_edge_width=True,
            fill_color=Vector4(1, 1, 1, 1),
            edge_color=Vector4(1, 1, 1, 1),
            edge_width=2,
        )
        marker.priority = 10
        return marker

    def _make_snap_marker(self) -> CanvasItem:
        marker = DiagonalCross(
            self.view.ctx,
            size=Vector2(30, 30),
            screen_space_size=True,
            screen_space_edge_width=True,
            fill_color=Vector4(1, 1, 1, 1),
            edge_width=2,
        )
        marker.priority = 10
        return marker

    def _make_point_control(self, point: Vector2) -> Circle:
        return Circle(
            self.view.ctx,
            radius=8,
            position=point,
            screen_space_size=True,
            fill_color=Vector4(1, 0, 0, 1),
            edge_color=Vector4(1, 0, 0, 1),
        )

    def _activate_horizontal_snap_line(self, y: float):
        pass

    def _activate_vertical_snap_line(self, x: float):
        pass

    def _create_polyline(self, points: Sequence[Vector2], closed: bool = False):
        GLOBALS.APP.undo_stack.push(CreatePolylineCommand(
            points=points,
            closed=closed,
        ))
