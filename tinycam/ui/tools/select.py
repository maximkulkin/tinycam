import enum
from typing import cast

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QEvent, Qt
from PySide6.QtGui import QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QWidget

from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.types import Vector2, Vector4, Rect
from tinycam.ui.tools import CncTool
from tinycam.ui.view_items.canvas import Rectangle
from tinycam.ui.view_items.project_item import CncProjectItemView


def vector2(point: QPoint | QPointF) -> Vector2:
    return Vector2(point.x(), point.y())


class SelectionModifier(enum.Flag):
    NONE = 0
    ADDITIVE = enum.auto()
    TOGGLE = enum.auto()


class SelectTool(CncTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selecting = False
        self._p1: Vector2 | None = None
        self._p2: Vector2 | None = None

        self._box = None

    def cancel(self):
        if self._box:
            self.view.remove_item(self._box)
            self._box = None
        self._p1 = None
        self._p2 = None
        self._selecting = False

    def deactivate(self):
        self.cancel()
        super().deactivate()

    def eventFilter(self, widget: QWidget, event: QEvent) -> bool:
        mouse_event = cast(QMouseEvent, event)

        if (event.type() == QEvent.Type.MouseButtonPress and
                mouse_event.button() & Qt.MouseButton.LeftButton):
            self._p1 = vector2(mouse_event.position())
            self._p2 = self._p1
            self._selecting = True
            return True
        elif (event.type() == QEvent.Type.MouseButtonRelease and
                mouse_event.button() & Qt.MouseButton.LeftButton):

            modifiers = self._make_selection_modifiers(mouse_event.modifiers())
            if self._box:
                assert self._p1 is not None
                assert self._p2 is not None
                self._select_items_in_box(self._p1, self._p2, modifiers)

                self.view.remove_item(self._box)
                self._box = None
            else:
                self._select_item_at_point(vector2(mouse_event.position()), modifiers)

            self._selecting = False
            return True
        elif self._selecting and event.type() == QEvent.Type.MouseMove:
            self._p2 = vector2(mouse_event.position())

            if self._box is None and (self._p1 - self._p2).length > 10:
                self._box = self._make_box()
                self.view.add_item(self._box)
            elif self._box is not None:
                self._box.center = (self._p1 + self._p2) * 0.5
                self._box.size = Vector2(np.abs(self._p1 - self._p2))

            widget.update()
            return True
        elif event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            if key_event.key() == Qt.Key.Key_Escape:
                self.cancel()
                return True

        return False

    def _make_box(self) -> Rectangle:
        assert self.view.ctx is not None
        assert self._p1 is not None
        assert self._p2 is not None

        return Rectangle(
            context=self.view.ctx,
            center=(self._p1 + self._p2) * 0.5,
            size=np.abs(self._p1 - self._p2),
            fill_color=Vector4(1, 1, 0, 0.1),
            edge_color=Vector4(1, 1, 0, 0.4),
            edge_width=2,
        )

    def _select_item_at_point(self, point: Vector2, modifiers: SelectionModifier):
        project = GLOBALS.APP.project

        picked = self.view.pick_item(point)
        if picked is not None:
            obj, _ = picked
            if isinstance(obj, CncProjectItemView):
                item = obj.model
            else:
                item = None
        else:
            item = None

        self._select_with_modifiers([item] if item is not None else [], modifiers)

    def _select_items_in_box(self, p1: Vector2, p2: Vector2, modifiers: SelectionModifier):
        if not self.project.items:
            return

        wp1 = self.view.camera.screen_to_world_point(p1)
        wp2 = self.view.camera.screen_to_world_point(p2)

        rect = Rect.from_coords(wp1.x, wp1.y, wp2.x, wp2.y)

        selection = []
        for item in self.view.items:
            if not isinstance(item, CncProjectItemView):
                continue

            if not item.visible:
                continue

            bounds = item.bounds.xy

            if rect.contains(bounds):
                selection.append(item.model)

        self._select_with_modifiers(selection, modifiers)

    def _select_with_modifiers(self, items: list[CncProjectItem], modifiers: SelectionModifier):
        project = GLOBALS.APP.project

        if items:
            match modifiers:
                case SelectionModifier.NONE:
                    project.selection.set(items)
                case SelectionModifier.ADDITIVE:
                    project.selection.add_all(items)
                case SelectionModifier.TOGGLE:
                    if len(items) == 1 and items[0] in project.selection:
                        project.selection.remove(items[0])
                    else:
                        project.selection.add(items[0])
        else:
            match modifiers:
                case SelectionModifier.NONE:
                    project.selection.clear()
                case SelectionModifier.ADDITIVE | SelectionModifier.TOGGLE:
                    pass

    def _make_selection_modifiers(
        self,
        keyboard_modifiers: Qt.KeyboardModifier,
    ) -> SelectionModifier:
        modifiers = SelectionModifier.NONE
        if keyboard_modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifiers |= SelectionModifier.ADDITIVE
        if keyboard_modifiers & Qt.KeyboardModifier.AltModifier:
            modifiers |= SelectionModifier.TOGGLE
        return modifiers
