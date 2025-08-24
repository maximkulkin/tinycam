from typing import cast, Sequence

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QWidget

from tinycam.globals import GLOBALS
from tinycam.types import Vector2, Vector3
from tinycam.ui.commands import CreatePolylineCommand
from tinycam.ui.tools import CncTool
from tinycam.ui.view_items.core import Line2D, Node3D


class PolylineTool(CncTool):
    SNAP_THRESHOLD = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drawing = False
        self._points: list[Vector2] = []

        self._polyline = None

    def activate(self):
        super().activate()
        self.view.setCursor(Qt.CursorShape.CrossCursor)

    def deactivate(self):
        self.cancel()
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        super().deactivate()

    def commit(self):
        if self._polyline:
            self._create_polyline(self._points[:-1])

            self.view.remove_item(self._polyline)
            self._polyline = None

        self._points = []
        self._drawing = False

    def cancel(self):
        if self._polyline:
            self.view.remove_item(self._polyline)
            self._polyline = None

        self._points = []
        self._drawing = False

    def eventFilter(self, widget: QWidget, event: QEvent) -> bool:
        mouse_event = cast(QMouseEvent, event)

        if (event.type() == QEvent.Type.MouseButtonRelease and
                mouse_event.button() & Qt.MouseButton.LeftButton):
            p = self._adjust_point(self._screen_to_world_point(mouse_event.position()).xy)

            if not self._drawing:
                self._points.append(p)
                self._points.append(p)
                self._polyline = self._make_polyline()
                self.view.add_item(self._polyline)
                self._drawing = True
            else:
                if mouse_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    d = p - self._points[-2]
                    if abs(d.x) > abs(d.y):
                        p = Vector2(p.x, self._points[-2].y)
                    else:
                        p = Vector2(self._points[-2].x, p.y)

                self._points[-1] = p
                self._points.append(p)

            return True
        elif self._drawing and event.type() == QEvent.Type.MouseMove:
            p = self._adjust_point(self._screen_to_world_point(mouse_event.position()).xy)
            if mouse_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                d = p - self._points[-2]
                if abs(d.x) > abs(d.y):
                    p = Vector2(p.x, self._points[-2].y)
                else:
                    p = Vector2(self._points[-2].x, p.y)

            self._points[-1] = p

            if self._polyline:
                self.view.remove_item(self._polyline)

            self._polyline = self._make_polyline()
            self.view.add_item(self._polyline)

            widget.update()
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

        return False

    def _adjust_point(self, point: Vector2) -> Vector2:
        if self._points:
            closest_point = min(self._points[:-1], key=lambda p: float((p - point).length))
            p1 = self.view.camera.world_to_screen_point(Vector3.from_vector2(closest_point))
            p2 = self.view.camera.world_to_screen_point(Vector3.from_vector2(point))
            if (p1 - p2).length < self.SNAP_THRESHOLD:
                point = closest_point

        return point

    def _make_polyline(self) -> Node3D:
        assert self.view.ctx is not None

        return Line2D(
            context=self.view.ctx,
            points=self._points,
            closed=False,
        )

    def _create_polyline(self, points: Sequence[Vector2]):
        GLOBALS.APP.undo_stack.push(CreatePolylineCommand(points=points))
