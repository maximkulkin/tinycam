import enum
import numpy as np
from tinycam.globals import GLOBALS
from tinycam.types import Vector2, Vector4
from tinycam.ui.tools import CncTool
from tinycam.ui.view_items.canvas import Rectangle
from tinycam.ui.view_items.project_item import CncProjectItemView
from PySide6 import QtCore
from PySide6.QtCore import Qt


def vector2(point: QtCore.QPoint | QtCore.QPointF) -> Vector2:
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
            self.view.remove(self._box)
            self._box = None
        self._p1 = None
        self._p2 = None
        self._selecting = False

    def deactivate(self):
        self.cancel()
        super().deactivate()

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (event.type() == QtCore.QEvent.MouseButtonPress and
                event.button() & Qt.LeftButton):
            self._p1 = vector2(event.position())
            self._p2 = self._p1
            self._selecting = True
            return True
        elif (event.type() == QtCore.QEvent.MouseButtonRelease and
                event.button() & Qt.LeftButton):

            modifiers = self._make_selection_modifiers(event.modifiers())
            if self._box:
                self._select_items_in_box(self._p1, self._p2, modifiers)

                self.view.remove_item(self._box)
                self._box = None
            else:
                self._select_item_at_point(vector2(event.position()), modifiers)

            self._selecting = False
            return True
        elif self._selecting and event.type() == QtCore.QEvent.MouseMove:
            self._p2 = vector2(event.position())

            if self._box is None and (self._p1 - self._p2).length > 10:
                self._box = self._make_box()
                self.view.add_item(self._box)
            elif self._box is not None:
                self._box.center = (self._p1 + self._p2) * 0.5
                self._box.size = np.abs(self._p1 - self._p2)

            widget.update()
            return True
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.code() == Qt.Key_Escape:
                self.cancel()
                return True

        return False

    def _make_box(self) -> Rectangle:
        return Rectangle(
            context=self.view.ctx,
            center=(self._p1 + self._p2) * 0.5,
            size=np.abs(self._p1 - self._p2),
            fill_color=Vector4(1, 1, 0, 0.1),
            edge_color=Vector4(1, 1, 0, 0.4),
            edge_width=2,
        )

    def _select_item_at_point(self, point: QtCore.QPointF, modifiers: SelectionModifier):
        project = GLOBALS.APP.project

        picked = self.view.pick_item(point)
        if picked is not None:
            obj, tag = picked
            if isinstance(obj, CncProjectItemView):
                obj_index = obj.index
            else:
                obj_index = None
        else:
            obj_index = None

        if obj_index is not None:
            match modifiers:
                case SelectionModifier.ADDITIVE:
                    project.selection.add(obj_index)
                case SelectionModifier.TOGGLE:
                    if obj_index in project.selection:
                        project.selection.remove(obj_index)
                    else:
                        project.selection.add(obj_index)
                case _:
                    project.selection.set([obj_index])
        else:
            match modifiers:
                case SelectionModifier.ADDITIVE | SelectionModifier.TOGGLE:
                    pass
                case _:
                    project.selection.clear()

    def _select_items_in_box(self, p1: Vector2, p2: Vector2, modifiers: SelectionModifier):
        # TODO: implement box selection
        pass

    def _make_selection_modifiers(
        self,
        keyboard_modifiers: Qt.KeyboardModifier,
    ) -> SelectionModifier:
        modifiers = SelectionModifier.NONE
        if keyboard_modifiers & Qt.ShiftModifier:
            modifiers |= SelectionModifier.ADDITIVE
        if keyboard_modifiers & Qt.AltModifier:
            modifiers |= SelectionModifier.TOGGLE
        return modifiers
