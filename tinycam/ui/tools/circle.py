from typing import cast

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QWidget

from tinycam.globals import GLOBALS
from tinycam.types import Vector2, Vector4
from tinycam.ui.commands import CreateCircleCommand
from tinycam.ui.tools import CncTool
from tinycam.ui.view import ViewItem
from tinycam.ui.view_items.canvas import CrossedCircle
from tinycam.ui.view_items.core import Node3D, Line2D


class CircleTool(CncTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drawing: bool = False
        self._p1: Vector2 = Vector2()
        self._p2: Vector2 = Vector2()

        self._circle: Node3D | None = None
        self._center_marker: Node3D | None = None

    def activate(self):
        super().activate()
        self.view.setCursor(Qt.CursorShape.CrossCursor)

    def deactivate(self):
        self.cancel()
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        super().deactivate()

    def commit(self):
        if self._circle:
            self._create_circle(self._p1, (self._p2 - self._p1).length)

            self.view.remove_item(self._circle)
            self._circle = None

        if self._center_marker:
            self.view.remove_item(self._center_marker)
            self._center_marker = None

        self._drawing = False

    def cancel(self):
        if self._circle:
            self.view.remove_item(self._circle)
            self._circle = None

        if self._center_marker:
            self.view.remove_item(self._center_marker)
            self._center_marker = None

        self._drawing = False

    def eventFilter(self, widget: QWidget, event: QEvent) -> bool:
        mouse_event = cast(QMouseEvent, event)

        if (event.type() == QEvent.Type.MouseButtonRelease and
                mouse_event.button() & Qt.MouseButton.LeftButton):
            if not self._drawing:
                self._p1 = self._screen_to_world_point(mouse_event.position()).xy
                self._p2 = self._p1
                self._drawing = True
                return True
            else:
                self.commit()
                return True
        elif self._drawing and event.type() == QEvent.Type.MouseMove:
            self._p2 = self._screen_to_world_point(mouse_event.position()).xy

            if self._circle is None and (self._p1 - self._p2).length > 10:
                self._circle = self._make_circle(self._p1, (self._p1 - self._p2).length)
                self.view.add_item(self._circle)
                self._center_marker = self._make_center_marker(self._p1)
                self.view.add_item(self._center_marker)
            elif self._circle is not None:
                self.view.remove_item(self._circle)
                self._circle = self._make_circle(self._p1, (self._p1 - self._p2).length)
                self.view.add_item(self._circle)

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

        return False

    def _make_circle(self, center: Vector2, radius: float) -> Node3D:
        assert self.view.ctx is not None

        G = GLOBALS.GEOMETRY

        return Line2D(
            context=self.view.ctx,
            points=list(G.points(G.circle(
                center=center,
                diameter=2 * radius,
            ).exterior)),
            closed=True,
        )

    def _make_center_marker(self, center: Vector2) -> ViewItem:
        assert self.view.ctx is not None

        return CrossedCircle(
            context=self.view.ctx,
            center=center,
            radius=5,
            fill_color=Vector4(1, 0, 0, 0.5),
            edge_color=Vector4(1, 0, 0, 0.5),
            edge_width=1,
        )

    def _create_circle(self, center: Vector2, radius: float):
        GLOBALS.APP.undo_stack.push(
            CreateCircleCommand(center=center, radius=radius,)
        )

