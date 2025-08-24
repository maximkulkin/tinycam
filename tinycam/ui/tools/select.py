import enum
from typing import cast

import numpy as np
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QWidget

from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem
from tinycam.types import Vector2, Vector3, Vector4, Rect
from tinycam.ui.commands import DeleteItemsCommand
from tinycam.ui.tools import CncTool
from tinycam.ui.view_items.canvas import Rectangle
from tinycam.ui.view_items.project_item import CncProjectItemView
from tinycam.ui.utils import vector2


class SelectionModifier(enum.Flag):
    NONE = enum.auto()
    ADD = enum.auto()
    SUBTRACT = enum.auto()


class SelectTool(CncTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selecting = False
        self._p1: Vector2 = Vector2()
        self._p2: Vector2 = Vector2()

        self._box = None
        self._last_modifiers = SelectionModifier.NONE

    def deactivate(self):
        self.cancel()
        super().deactivate()

    def cancel(self):
        if self._box:
            self.view.remove_item(self._box)
            self._box = None

        self._selecting = False
        self._last_modifiers = SelectionModifier.NONE

    def eventFilter(self, widget: QWidget, event: QEvent) -> bool:
        mouse_event = cast(QMouseEvent, event)

        if (event.type() == QEvent.Type.MouseButtonPress and
                mouse_event.button() & Qt.MouseButton.LeftButton):
            self._p1 = vector2(mouse_event.position())
            self._p2 = self._p1
            self._selecting = True
            return True
        elif (event.type() == QEvent.Type.MouseButtonRelease and
              mouse_event.button() & Qt.MouseButton.LeftButton and
              self._selecting):

            modifiers = self._make_selection_modifiers(mouse_event.modifiers())
            if self._box:
                self._select_items_in_box(self._p1, self._p2, modifiers)

                self.view.remove_item(self._box)
                self._box = None
            else:
                self._select_item_at_point(vector2(mouse_event.position()), modifiers)

            self._selecting = False
            return True
        elif self._selecting and event.type() == QEvent.Type.MouseMove:
            self._p2 = vector2(mouse_event.position())

            modifiers = self._make_selection_modifiers(mouse_event.modifiers())
            if self._box is None and (self._p1 - self._p2).length > 10:
                self._box = self._make_box()
                self.view.add_item(self._box)
            elif self._box is not None:
                self._box.center = (self._p1 + self._p2) * 0.5
                self._box.size = Vector2(np.abs(self._p1 - self._p2))

            if self._box is not None:
                color = self._get_modifier_color(modifiers)
                self._box.fill_color = Vector4.from_vector3(color, 0.1)
                self._box.edge_color = Vector4.from_vector3(color, 0.4)

            widget.update()
            return True
        elif event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            if key_event.key() == Qt.Key.Key_Escape:
                self.cancel()
                return True
            elif key_event.key() in [Qt.Key.Key_Delete, Qt.Key.Key_Backspace]:
                self._delete_selected_items()
                return True

            if self._box is not None:
                modifiers = self._make_selection_modifiers(mouse_event.modifiers())
                if modifiers != self._last_modifiers:
                    color = self._get_modifier_color(modifiers)
                    self._box.fill_color = Vector4.from_vector3(color, 0.1)
                    self._box.edge_color = Vector4.from_vector3(color, 0.4)
                    self._last_modifiers = modifiers
                    self.view.update()

        elif event.type() == QEvent.Type.KeyRelease:
            key_event = cast(QKeyEvent, event)

            if self._box is not None:
                modifiers = self._make_selection_modifiers(mouse_event.modifiers())
                if modifiers != self._last_modifiers:
                    color = self._get_modifier_color(modifiers)
                    self._box.fill_color = Vector4.from_vector3(color, 0.1)
                    self._box.edge_color = Vector4.from_vector3(color, 0.4)
                    self._last_modifiers = modifiers
                    self.view.update()

        return False

    def _make_box(self) -> Rectangle:
        assert self.view.ctx is not None

        color = self._get_modifier_color(SelectionModifier.NONE)

        return Rectangle(
            context=self.view.ctx,
            center=(self._p1 + self._p2) * 0.5,
            size=np.abs(self._p1 - self._p2),
            fill_color=Vector4.from_vector3(color, 0.1),
            edge_color=Vector4.from_vector3(color, 0.4),
            edge_width=2,
        )

    def _get_modifier_color(self, modifiers: SelectionModifier) -> Vector3:
        if modifiers & SelectionModifier.SUBTRACT:
            return Vector3(1, 0, 0)

        if modifiers & SelectionModifier.ADD:
            return Vector3(0, 1, 0)

        return Vector3(1, 1, 0)

    def _select_item_at_point(self, point: Vector2, modifiers: SelectionModifier):
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
        shape = GLOBALS.GEOMETRY.box(rect.pmin, rect.pmax)

        selection = []
        for item in self.view.items:
            if not isinstance(item, CncProjectItemView):
                continue

            if not item.visible:
                continue

            if hasattr(item.model, 'geometry'):
                if GLOBALS.GEOMETRY.intersects(item.model.geometry, shape):
                    selection.append(item.model)
            else:
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
                case SelectionModifier.ADD:
                    project.selection.add_all(items)
                case SelectionModifier.SUBTRACT:
                    project.selection.remove_all(items)
        else:
            match modifiers:
                case SelectionModifier.NONE:
                    project.selection.clear()
                case SelectionModifier.ADD | SelectionModifier.SUBTRACT:
                    pass

    def _make_selection_modifiers(
        self,
        keyboard_modifiers: Qt.KeyboardModifier,
    ) -> SelectionModifier:
        modifiers = SelectionModifier.NONE
        if keyboard_modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifiers |= SelectionModifier.ADD
        if keyboard_modifiers & Qt.KeyboardModifier.AltModifier:
            modifiers |= SelectionModifier.SUBTRACT
        return modifiers

    def _delete_selected_items(self):
        if len(self.project.selection) == 0:
            return

        GLOBALS.APP.undo_stack.push(
            DeleteItemsCommand(list(self.project.selection))
        )
