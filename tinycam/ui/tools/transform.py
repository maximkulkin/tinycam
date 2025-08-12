import enum
from functools import reduce
from typing import cast

from PySide6 import QtWidgets
from PySide6.QtCore import QEvent
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from tinycam.globals import GLOBALS
from tinycam.ui.commands import MoveItemsCommand, ScaleItemsCommand
from tinycam.types import Vector2, Vector3, Vector4
from tinycam.project import CncProjectItem
from tinycam.ui.tools import CncTool
from tinycam.ui.utils import vector2
from tinycam.ui.view_items.canvas import Circle, Rectangle
from tinycam.ui.view_items.core import Node3D


class ControlType(enum.Enum):
    RESIZE_TOP_LEFT = enum.auto()
    RESIZE_TOP = enum.auto()
    RESIZE_TOP_RIGHT = enum.auto()
    RESIZE_LEFT = enum.auto()
    RESIZE_RIGHT = enum.auto()
    RESIZE_BOTTOM_LEFT = enum.auto()
    RESIZE_BOTTOM = enum.auto()
    RESIZE_BOTTOM_RIGHT = enum.auto()
    MOVE = enum.auto()


CURSOR_FOR_CONTROL = {
    ControlType.RESIZE_TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    ControlType.RESIZE_TOP: Qt.CursorShape.SizeVerCursor,
    ControlType.RESIZE_TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    ControlType.RESIZE_LEFT: Qt.CursorShape.SizeHorCursor,
    ControlType.RESIZE_RIGHT: Qt.CursorShape.SizeHorCursor,
    ControlType.RESIZE_BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    ControlType.RESIZE_BOTTOM: Qt.CursorShape.SizeVerCursor,
    ControlType.RESIZE_BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    ControlType.MOVE: Qt.CursorShape.SizeAllCursor,
}


class TransformTool(CncTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._controls = []
        self._controls_shown = False

        self._selected_items = []

        self._bounds = None
        self._offsets = None
        self._scales = None

        self._applied_offset = None
        self._applied_scale = None
        self._applied_scale_pivot = None

        self._dragging = False
        self._control_type = None
        self._start_point = Vector2()

    def activate(self):
        super().activate()

        self.view.grabKeyboard()
        if not self._controls:
            self._init_controls()

        if self.project.selection:
            # self._selected_items = list(self.project.selection)
            self._on_selection_changed()
            self._show_controls(True)
            self._update_control_positions()
        else:
            self._show_controls(False)

        self.project.selection.changed.connect(self._on_selection_changed)
        self.view.camera.changed.connect(self._on_camera_changed)

    def deactivate(self):
        self._show_controls(False)
        self.view.camera.changed.disconnect(self._on_camera_changed)
        self.project.selection.changed.disconnect(self._on_selection_changed)
        for item in self._selected_items:
            item.changed.disconnect(self._on_selected_item_changed)

        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        self.view.releaseKeyboard()

        super().deactivate()

    def _control_under(self, point: Vector2) -> ControlType | None:
        if self._is_over_control(point, self._tl_control):
            return ControlType.RESIZE_TOP_LEFT
        elif self._is_over_control(point, self._br_control):
            return ControlType.RESIZE_BOTTOM_RIGHT
        elif self._is_over_control(point, self._tr_control):
            return ControlType.RESIZE_TOP_RIGHT
        elif self._is_over_control(point, self._bl_control):
            return ControlType.RESIZE_BOTTOM_LEFT
        elif self._is_over_control(point, self._t_control):
            return ControlType.RESIZE_TOP
        elif self._is_over_control(point, self._b_control):
            return ControlType.RESIZE_BOTTOM
        elif self._is_over_control(point, self._l_control):
            return ControlType.RESIZE_LEFT
        elif self._is_over_control(point, self._r_control):
            return ControlType.RESIZE_RIGHT
        elif self._is_over_control(point, self._c_control):
            return ControlType.MOVE
        else:
            return None

    def eventFilter(self, widget: QtWidgets.QWidget, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseMove:
            point = vector2(event.position())
            if self._dragging:
                assert self._control_type is not None
                end_point = self.view.camera.unproject(point).xy

                is_proportional = bool(
                    event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                )

                match self._control_type:
                    case ControlType.RESIZE_TOP_LEFT:
                        scale = Vector2(
                            (self._bounds.width - end_point.x + self._start_point.x) / self._bounds.width,
                            (self._bounds.height + end_point.y - self._start_point.y) / self._bounds.height,
                        )
                        if is_proportional:
                            scale = Vector2(1, 1) * max(scale.x, scale.y)

                        self._resize_items(
                            scale,
                            Vector2(self._bounds.xmax, self._bounds.ymin),
                        )

                    case ControlType.RESIZE_TOP:
                        scale = Vector2(1.0, (self._bounds.height - self._start_point.y + end_point.y) / self._bounds.height)
                        if is_proportional:
                            scale = Vector2(1, 1) * scale.y

                        self._resize_items(
                            scale,
                            Vector2(self._bounds.xmid, self._bounds.ymin),
                        )

                    case ControlType.RESIZE_TOP_RIGHT:
                        scale = Vector2(
                            (self._bounds.width + end_point.x - self._start_point.x) / self._bounds.width,
                            (self._bounds.height + end_point.y - self._start_point.y) / self._bounds.height,
                        )
                        if is_proportional:
                            scale = Vector2(1, 1) * max(scale.x, scale.y)

                        self._resize_items(
                            scale,
                            Vector2(self._bounds.xmin, self._bounds.ymin),
                        )

                    case ControlType.RESIZE_LEFT:
                        scale = Vector2((self._bounds.width - end_point.x + self._start_point.x) / self._bounds.width, 1.0)
                        if is_proportional:
                            scale = Vector2(1, 1) * scale.x

                        self._resize_items(
                            scale,
                            Vector2(self._bounds.xmax, self._bounds.ymid),
                        )

                    case ControlType.RESIZE_RIGHT:
                        scale = Vector2((self._bounds.width + end_point.x - self._start_point.x) / self._bounds.width, 1.0)
                        if is_proportional:
                            scale = Vector2(1, 1) * scale.x

                        self._resize_items(
                            scale,
                            Vector2(self._bounds.xmin, self._bounds.ymid),
                        )

                    case ControlType.RESIZE_BOTTOM_LEFT:
                        scale = Vector2(
                            (self._bounds.width - end_point.x + self._start_point.x) / self._bounds.width,
                            (self._bounds.height - end_point.y + self._start_point.y) / self._bounds.height,
                        )
                        if is_proportional:
                            scale = Vector2(1, 1) * max(scale.x, scale.y)

                        self._resize_items(
                            scale,
                            Vector2(self._bounds.xmax, self._bounds.ymax),
                        )

                    case ControlType.RESIZE_BOTTOM:
                        scale = Vector2(1.0, (self._bounds.height - end_point.y + self._start_point.y) / self._bounds.height)
                        if is_proportional:
                            scale = Vector2(1, 1) * scale.y

                        self._resize_items(
                            scale,
                            Vector2(self._bounds.xmid, self._bounds.ymax),
                        )

                    case ControlType.RESIZE_BOTTOM_RIGHT:
                        scale = Vector2(
                            (self._bounds.width + end_point.x - self._start_point.x) / self._bounds.width,
                            (self._bounds.height - end_point.y + self._start_point.y) / self._bounds.height,
                        )
                        if is_proportional:
                            scale = Vector2(1, 1) * max(scale.x, scale.y)

                        self._resize_items(
                            scale,
                            Vector2(self._bounds.xmin, self._bounds.ymax),
                        )

                    case ControlType.MOVE:
                        self._move_items(end_point - self._start_point)

                return True
            else:
                control_type = self._control_under(point)
                cursor = CURSOR_FOR_CONTROL.get(control_type, Qt.CursorShape.ArrowCursor)
                self.view.setCursor(cursor)
        elif event.type() == QEvent.Type.MouseButtonPress:
            point = vector2(event.position())
            self._control_type = self._control_under(point)
            if self._control_type is not None:
                self._dragging = True
                self._start_point = self.view.camera.unproject(point).xy
                self._bounds = reduce(
                    lambda a, b: a.merge(b),
                    [item.bounds for item in self._selected_items]
                )
            return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self._dragging:
                self._commit()
                self._dragging = False
                self._bounds = None
            else:
                self.deactivate()

            return True
        elif event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            if key_event.key() == Qt.Key.Key_Escape:
                if self._dragging:
                    self._cancel()
                else:
                    self.deactivate()

                return True

        return super().eventFilter(widget, event)

    def _is_over_control(self, point: Vector2, control: Rectangle) -> bool:
        return (
            abs(point.x - control.center.x) <= control.size.x // 2 and
            abs(point.y - control.center.y) <= control.size.y // 2
        )

    def _init_controls(self):
        self._tl_control = self._make_rect_control()
        self._tr_control = self._make_rect_control()
        self._bl_control = self._make_rect_control()
        self._br_control = self._make_rect_control()
        self._t_control = self._make_rect_control()
        self._b_control = self._make_rect_control()
        self._l_control = self._make_rect_control()
        self._r_control = self._make_rect_control()
        self._c_control = self._make_circle_control()

        self._controls = [
            self._tl_control,
            self._tr_control,
            self._bl_control,
            self._br_control,
            self._t_control,
            self._b_control,
            self._l_control,
            self._r_control,
            self._c_control,
        ]

    def _show_controls(self, show: bool):
        if self._controls_shown == show:
            return

        if show:
            for control in self._controls:
                self.view.add_item(control)
        else:
            for control in self._controls:
                self.view.remove_item(control)

        self._controls_shown = show

    def _make_rect_control(self) -> Rectangle:
        return Rectangle(
            self.view.ctx,
            size=Vector2(10, 10),
            fill_color=Vector4(1, 0, 0, 1),
            edge_color=Vector4(0, 0, 0, 1),
            edge_width=2,
        )

    def _make_circle_control(self) -> Rectangle:
        return Circle(
            self.view.ctx,
            radius=5,
            fill_color=Vector4(1, 0, 0, 1),
            edge_color=Vector4(0, 0, 0, 1),
            edge_width=2,
        )

    def _update_control_positions(self):
        if len(self._selected_items) == 0:
            return

        all_bounds = [
            item.bounds
            for item in self._selected_items
        ]
        if self._applied_scale is not None:
            pivot = self._applied_scale_pivot
            all_bounds = [
                bounds.scaled(self._applied_scale)
                .translated(pivot - (pivot - bounds.pmin) * self._applied_scale - bounds.pmin)
                for bounds in all_bounds
            ]
        if self._applied_offset is not None:
            all_bounds = [bounds.translated(self._applied_offset) for bounds in all_bounds]

        bounds = reduce(lambda a, b: a.merge(b), all_bounds)

        def transform(x, y) -> Vector2:
            return self.view.camera.world_to_screen_point(Vector3(x, y, 0.0))

        self._tl_control.center = transform(bounds.xmin, bounds.ymax) + Vector2(-5, -5)
        self._tr_control.center = transform(bounds.xmax, bounds.ymax) + Vector2(5, -5)
        self._bl_control.center = transform(bounds.xmin, bounds.ymin) + Vector2(-5, 5)
        self._br_control.center = transform(bounds.xmax, bounds.ymin) + Vector2(5, 5)
        self._t_control.center = transform(bounds.center.x, bounds.ymax) + Vector2(0, -5)
        self._b_control.center = transform(bounds.center.x, bounds.ymin) + Vector2(0, 5)
        self._l_control.center = transform(bounds.xmin, bounds.center.y) + Vector2(-5, 0)
        self._r_control.center = transform(bounds.xmax, bounds.center.y) + Vector2(5, 0)
        self._c_control.center = transform(bounds.center.x, bounds.center.y)

    def _on_selection_changed(self):
        for item in self._selected_items:
            if item not in self.project.selection:
                item.changed.disconnect(self._on_selected_item_changed)

        for item in self.project.selection:
            item.changed.connect(self._on_selected_item_changed)

        self._selected_items = list(self.project.selection)
        self._selected_views = [
            view
            for item in self._selected_items
            for view in [self._find_view(item)]
            if view is not None
        ]

        self._show_controls(len(self._selected_items) > 0)
        self._update_control_positions()

    def _find_view(self, item: CncProjectItem) -> Node3D | None:
        for view in self.view.items:
            if getattr(view, 'model', None) == item:
                return view
        return None

    def _on_selected_item_changed(self, item: CncProjectItem):
        self._update_control_positions()

    def _on_camera_changed(self):
        self._update_control_positions()

    def _ensure_item_states_saved(self):
        if self._offsets is None:
            self._offsets = [item.world_position for item in self._selected_views]

        if self._scales is None:
            self._scales = [item.world_scale for item in self._selected_views]

    def _restore_items_states(self):
        for view, offset, scale in zip(self._selected_views, self._offsets, self._scales):
            view.world_position = offset
            view.world_scale = scale

    def _reset(self):
        self._offsets = None
        self._scales = None

        self._applied_offset = None
        self._applied_scale = None
        self._applied_scale_pivot = None

    def _move_items(self, offset: Vector2):
        self._ensure_item_states_saved()

        self._applied_offset = offset

        for view, item_offset, item_scale in zip(self._selected_views, self._offsets, self._scales):
            view.world_position = item_offset + Vector3.from_vector2(offset)

        self._update_control_positions()
        self.view.update()

    def _resize_items(self, scale: Vector2, pivot: Vector2):
        self._ensure_item_states_saved()

        self._applied_offset = None
        self._applied_scale = scale
        self._applied_scale_pivot = pivot

        scale3 = Vector3.from_vector2(scale, 1)
        pivot3 = Vector3.from_vector2(pivot)

        for view, item_offset, item_scale in zip(self._selected_views, self._offsets, self._scales):
            view.world_scale = item_scale * scale3
            view.world_position = pivot3 - (pivot3 - item_offset) * scale3

        self._update_control_positions()
        self.view.update()

    def _commit(self):
        # Restore original offsets and scales to allow command to apply them
        self._restore_items_states()

        if self._applied_offset is not None:
            GLOBALS.APP.undo_stack.push(MoveItemsCommand(
                items=list(self._selected_items),
                offset=self._applied_offset,
            ))
        elif self._applied_scale is not None:
            GLOBALS.APP.undo_stack.push(ScaleItemsCommand(
                items=list(self._selected_items),
                scale=self._applied_scale,
                pivot=self._applied_scale_pivot
            ))

        self._reset()

    def _cancel(self):
        self._restore_items_states()
        self._reset()
        self._dragging = False
        self._bounds = None
