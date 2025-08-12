from typing import cast

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QWidget

from tinycam.globals import GLOBALS
from tinycam.types import Vector2, Rect
from tinycam.ui.commands import CreateRectangleCommand
from tinycam.ui.tools import CncTool
from tinycam.ui.view_items.core import Line2D, Node3D


class RectangleTool(CncTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drawing: bool = False
        self._p1: Vector2 = Vector2()
        self._p2: Vector2 = Vector2()

        self._rect: Rect | None = None

    def activate(self):
        super().activate()
        self.view.grabKeyboard()
        self.view.setCursor(Qt.CursorShape.CrossCursor)

    def deactivate(self):
        self.cancel()
        self.view.releaseKeyboard()
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        super().deactivate()

    def cancel(self):
        if self._rect:
            self.view.remove_item(self._rect)
            self._rect = None

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
                if self._rect:
                    self._create_rectangle(self._p1, self._p2)

                    self.view.remove_item(self._rect)
                    self._rect = None

                self._drawing = False
                return True
        elif self._drawing and event.type() == QEvent.Type.MouseMove:
            self._p2 = self._screen_to_world_point(mouse_event.position()).xy

            if self._rect is None and (self._p1 - self._p2).length > 10:
                self._rect = self._make_box()
                self.view.add_item(self._rect)
            elif self._rect is not None:
                self.view.remove_item(self._rect)

                self._rect = self._make_box()
                self.view.add_item(self._rect)

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

    def _make_box(self) -> Node3D:
        assert self.view.ctx is not None

        rect = Rect.from_two_points(self._p1, self._p2)
        G = GLOBALS.GEOMETRY

        return Line2D(
            context=self.view.ctx,
            points=list(G.points(G.box(rect.pmin, rect.pmax).exterior)),
            closed=True,
        )

    def _create_rectangle(self, p1: Vector2, p2: Vector2):
        rect = Rect.from_two_points(self._p1, self._p2)

        GLOBALS.APP.undo_stack.push(CreateRectangleCommand(rect=rect))
