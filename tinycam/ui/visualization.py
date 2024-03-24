import enum
import math
from functools import reduce

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt
import numpy as np

from tinycam.globals import CncGlobals
from tinycam.ui.utils import Point
from tinycam.ui.commands import MoveItemsCommand, ScaleItemsCommand


def combine_bounds(b1, b2):
    return (min(b1[0], b2[0]), min(b1[1], b2[1]), max(b1[2], b2[2]), max(b1[3], b2[3]))

def total_bounds(shapes):
    coords = reduce(combine_bounds, [shape.bounds for shape in shapes])
    return QtCore.QRectF(
        coords[0],
        coords[1],
        coords[2] - coords[0],
        coords[3] - coords[1],
    )


class CncPainter(QtGui.QPainter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._offset = QtCore.QPointF(0, 0)
        self._scale = 1.0

    @property
    def current_scale(self):
        return self._scale

    @property
    def current_offset(self):
        return self._offset

    def translate(self, offset):
        self._offset = offset
        super().translate(offset)

    def scale(self, factor):
        self._scale = factor
        super().scale(factor, factor)

    def __enter__(self):
        self.save()

    def __exit__(self, exc_type, exc_value, traceback):
        self.restore()


class CncHandle:
    def __init__(self, position):
        self.position = position

    def draw(self, painter):
        pass

    def contains(self, point):
        return False


class CncBoxHandle(CncHandle):
    def draw(self, painter):
        painter.drawRect(self.position.x(), self.position.y(),
                         self.size.x(), self.size.y())

    def contains(self, point):
        return (
            abs(point.x() - self.position.x()) <= self.size.x() and
            abs(point.y() - self.position.y()) <= self.size.y()
        )


class CncTool:
    def __init__(self, project, view):
        self.project = project
        self.view = view

    def activate(self):
        pass

    def deactivate(self):
        pass

    def keyPressEvent(self, event):
        event.ignore()

    def keyReleaseEvent(self, event):
        event.ignore()

    def mousePressEvent(self, event):
        event.ignore()

    def mouseReleaseEvent(self, event):
        event.ignore()

    def mouseMoveEvent(self, event):
        event.ignore()

    def wheelEvent(self, event):
        event.ignore()

    def paint(self, painter):
        pass


class CncManipulateTool(CncTool):
    class Manipulation(enum.Enum):
        NONE = 0
        MOVE = 1

        RESIZE_TOP = 2
        RESIZE_BOTTOM = 3
        RESIZE_LEFT = 4
        RESIZE_RIGHT = 5

        RESIZE_TOP_LEFT = 6
        RESIZE_TOP_RIGHT = 7
        RESIZE_BOTTOM_LEFT = 8
        RESIZE_BOTTOM_RIGHT = 9

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bounds = None
        self._items = []
        self._original_manipulation_position = QtCore.QPointF()
        self._original_bounds = None
        self._shift_pressed = False
        self._alt_pressed = False
        self._command = None
        self.view.view_updated.connect(self._update)

    def activate(self):
        self.project.selection.changed.connect(self._update)
        self.project.items.changed.connect(self._update)
        self._manipulation = self.Manipulation.NONE
        self._update()

    def deactivate(self):
        self.project.items.changed.disconnect(self._update)
        self.project.selection.changed.disconnect(self._udpate)

    def _update(self):
        items = self._items or self.project.selectedItems
        if items:
            self._bounds = total_bounds([item.geometry for item in items])
        else:
            self._bounds = None

    def _within_handle(self, point, handle_position):
        size = 10.0
        # TODO: change to use of CncHandle subclasses
        offset = point - self.view.canvas_to_screen_point(handle_position)
        return abs(offset.x()) <= size and abs(offset.y()) <= size

    def _get_delta(self):
        return Point(self.view.screen_to_canvas_point(
            self.view.mapFromGlobal(QtGui.QCursor.pos()).toPointF()
        )) - self._original_manipulation_position

    def _move_command(self, items, delta):
        return MoveItemsCommand(items, delta)

    def _scale_command(self, items, delta, sign=Point(0, 0)):
        sign = Point(sign)
        if self._shift_pressed:
            m = delta[0] if abs(delta[0]) > abs(delta[1]) else delta[1]
            delta = sign.abs() * m

        offset = delta * 0.5
        if self._alt_pressed:
            offset = Point.ZERO
            delta *= 2

        scale = Point.ONES + delta * sign / self._original_bounds.size()

        return ScaleItemsCommand(items, scale, offset)

    def _make_command(self, items):
        delta = self._get_delta()

        match self._manipulation:
            case self.Manipulation.NONE:
                return None

            case self.Manipulation.MOVE:
                return self._move_command(items, delta)

            case self.Manipulation.RESIZE_TOP:
                return self._scale_command(items, Point(0, delta.y()), (0, -1))

            case self.Manipulation.RESIZE_BOTTOM:
                return self._scale_command(items, Point(0, delta.y()), (0, 1))

            case self.Manipulation.RESIZE_LEFT:
                return self._scale_command(items, Point(delta.x(), 0), (-1, 0))

            case self.Manipulation.RESIZE_RIGHT:
                return self._scale_command(items, Point(delta.x(), 0), (1, 0))

            case self.Manipulation.RESIZE_TOP_LEFT:
                return self._scale_command(items, delta, (-1, -1))

            case self.Manipulation.RESIZE_TOP_RIGHT:
                return self._scale_command(items, delta, (1, -1))

            case self.Manipulation.RESIZE_BOTTOM_LEFT:
                return self._scale_command(items, delta, (-1, 1))

            case self.Manipulation.RESIZE_BOTTOM_RIGHT:
                return self._scale_command(items, delta, (1, 1))

    def _update_manipulation(self):
        self._items = [item.clone() for item in self.project.selectedItems]
        command = self._make_command(self._items or self.project.selectedItems)
        if command is not None:
            command.redo()
        self._update()
        self.view.update()

    def _accept_manipulation(self):
        command = self._make_command(self.project.selectedItems)
        if command is not None:
            CncGlobals.APP.undo_stack.push(command)

        self._items = []

        self._manipulation = self.Manipulation.NONE
        self.view.hide_selected_geometry(False)
        self._update()
        self.view.update()

    def _cancel_manipulation(self):
        self._manipulation = self.Manipulation.NONE
        self._items = []
        self.view.hide_selected_geometry(False)
        self.view.setCursor(Qt.ArrowCursor)
        self._update()
        self.view.update()

    def keyPressEvent(self, event):
        event.ignore()
        if self._manipulation != self.Manipulation.NONE:
            if event.key() == Qt.Key_Escape:
                self._cancel_manipulation()
                event.accept()
            elif event.key() == Qt.Key_Shift:
                self._shift_pressed = True
                self._update_manipulation()
                event.accept()
            elif event.key() == Qt.Key_Alt:
                self._alt_pressed = True
                self._update_manipulation()
                event.accept()

    def keyReleaseEvent(self, event):
        event.ignore()
        if self._manipulation != self.Manipulation.NONE:
            if event.key() == Qt.Key_Shift:
                self._shift_pressed = False
                self._update_manipulation()
                event.accept()
            elif event.key() == Qt.Key_Alt:
                self._alt_pressed = False
                self._update_manipulation()
                event.accept()

    def mousePressEvent(self, event):
        event.ignore()
        if event.buttons() != Qt.LeftButton:
            return

        if self._bounds is None:
            return

        center = self._bounds.center()

        if self._within_handle(event.position(), self._bounds.center()):
            self._manipulation = self.Manipulation.MOVE
        elif self._within_handle(event.position(), QtCore.QPointF(center.x(), self._bounds.top())):
            self._manipulation = self.Manipulation.RESIZE_TOP
        elif self._within_handle(event.position(), QtCore.QPointF(center.x(), self._bounds.bottom())):
            self._manipulation = self.Manipulation.RESIZE_BOTTOM
        elif self._within_handle(event.position(), QtCore.QPointF(self._bounds.left(), center.y())):
            self._manipulation = self.Manipulation.RESIZE_LEFT
        elif self._within_handle(event.position(), QtCore.QPointF(self._bounds.right(), center.y())):
            self._manipulation = self.Manipulation.RESIZE_RIGHT
        elif self._within_handle(event.position(), self._bounds.topLeft()):
            self._manipulation = self.Manipulation.RESIZE_TOP_LEFT
        elif self._within_handle(event.position(), self._bounds.topRight()):
            self._manipulation = self.Manipulation.RESIZE_TOP_RIGHT
        elif self._within_handle(event.position(), self._bounds.bottomLeft()):
            self._manipulation = self.Manipulation.RESIZE_BOTTOM_LEFT
        elif self._within_handle(event.position(), self._bounds.bottomRight()):
            self._manipulation = self.Manipulation.RESIZE_BOTTOM_RIGHT
        else:
            self._manipulation = self.Manipulation.NONE

        if self._manipulation != self.Manipulation.NONE:
            event.accept()
            self._items = [
                item.clone()
                for item in self.project.selectedItems
            ]
            self.view.hide_selected_geometry(True)
            self._original_manipulation_position = self.view.screen_to_canvas_point(event.position())
            self._original_bounds = self._bounds

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        self._accept_manipulation()
        event.accept()

    def mouseMoveEvent(self, event):
        event.ignore()

        if self._bounds is None:
            self.view.setCursor(Qt.ArrowCursor)
            return

        if self._manipulation != self.Manipulation.NONE:
            self._shift_pressed = bool(event.modifiers() & Qt.ShiftModifier)
            self._update_manipulation()
        else:
            center = self._bounds.center()

            if (self._within_handle(event.position(), self._bounds.topLeft()) or
                self._within_handle(event.position(), self._bounds.bottomRight())):
                self.view.setCursor(Qt.SizeFDiagCursor)
            elif (self._within_handle(event.position(), self._bounds.topRight()) or
                  self._within_handle(event.position(), self._bounds.bottomLeft())):
                self.view.setCursor(Qt.SizeBDiagCursor)
            elif (self._within_handle(event.position(), QtCore.QPointF(center.x(), self._bounds.top())) or
                  self._within_handle(event.position(), QtCore.QPointF(center.x(), self._bounds.bottom()))):
                self.view.setCursor(Qt.SizeVerCursor)
            elif (self._within_handle(event.position(), QtCore.QPointF(self._bounds.left(), center.y())) or
                  self._within_handle(event.position(), QtCore.QPointF(self._bounds.right(), center.y()))):
                self.view.setCursor(Qt.SizeHorCursor)
            elif self._within_handle(event.position(), self._bounds.center()):
                self.view.setCursor(Qt.SizeAllCursor)
            else:
                self.view.setCursor(Qt.ArrowCursor)

    def paint(self, painter):
        if self._bounds is None:
            return

        for item in self._items:
            item.draw(painter)

        items = self._items or self.project.selectedItems
        self._draw_selection_handles(painter, [item.geometry for item in items])

    def _draw_selection_handles(self, painter, geometries):
        with painter:
            painter.resetTransform()
            pen = QtGui.QPen(Qt.white, 2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(QtGui.QColor('dimgrey'))

            self._draw_box_handle(painter, self._bounds.topLeft())
            self._draw_box_handle(painter, self._bounds.topRight())
            self._draw_box_handle(painter, self._bounds.bottomLeft())
            self._draw_box_handle(painter, self._bounds.bottomRight())

            center = self._bounds.center()

            self._draw_box_handle(painter, QtCore.QPointF(center.x(), self._bounds.top()))
            self._draw_box_handle(painter, QtCore.QPointF(center.x(), self._bounds.bottom()))

            self._draw_box_handle(painter, QtCore.QPointF(self._bounds.left(), center.y()))
            self._draw_box_handle(painter, QtCore.QPointF(self._bounds.right(), center.y()))

            self._draw_box_handle(painter, center)

    def _draw_box_handle(self, painter, position, size=QtCore.QSizeF(10, 10)):
        """Draws box handle, position in canvas and size is in screen coordinates."""
        # TODO: change to use of CncHandle subclasses
        p = self.view.canvas_to_screen_point(position)
        painter.drawRect(p.x() - size.width()*0.5, p.y() - size.height()*0.5, size.width(), size.height());


class CncVisualization(QtWidgets.QWidget):
    view_updated = QtCore.Signal()

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)

        self._scale = 1.0
        self._offset = QtCore.QPointF(0.0, 0.0)
        self._x_label_size = QtCore.QSize(30, 30)
        self._y_label_size = QtCore.QSize(40, 25)

        self._panning = False
        self._last_mouse_position = QtCore.QPointF(0.0, 0.0)
        self._hide_selected_geometry = False

        # self.current_tool = CncTool(self.project, self)
        self.current_tool = CncManipulateTool(self.project, self)
        self.current_tool.activate()

        self.project.items.added.connect(self._on_item_added)
        self.project.items.removed.connect(self._on_item_removed)
        self.project.items.changed.connect(self._on_item_changed)

        self.project.selection.changed.connect(self.update)

        self.setCursor(Qt.CrossCursor)

        self._update_graph_rect()

    @property
    def scale(self):
        return self._scale

    @property
    def offset(self):
        return self._offset

    def _zoom(self, k, position=None):
        self._scale *= k
        self._offset = self._offset * k + (position * (1 - k)).toPoint()
        self.view_updated.emit()
        self.update()

    def zoom_in(self):
        self._zoom(1.0 / 0.8, QtCore.QPointF(self.width()/2, self.height()/2))

    def zoom_out(self):
        self._zoom(0.8, QtCore.QPointF(self.width()/2, self.height()/2))

    def zoom_to_fit(self):
        if not self.project.items:
            return

        bounds = reduce(combine_bounds, [
            item.geometry.bounds for item in self.project.items
        ])

        w, h = bounds[2] - bounds[0], bounds[3] - bounds[1]

        self._scale = min(float(self._graph_rect.width()) / w,
                          float(self._graph_rect.height()) / h) * 0.9

        target_point = QtCore.QPoint(
            (self._graph_rect.width() - w * self._scale) * 0.5,
            (self._graph_rect.height() - h * self._scale) * 0.5
        )
        self._offset = self._graph_rect.topLeft() + target_point - QtCore.QPoint(bounds[0], bounds[1]) * self._scale
        self.view_updated.emit()
        self.repaint()

    def hide_selected_geometry(self, state):
        self._hide_selected_geometry = bool(state)

    def keyPressEvent(self, event):
        if self._panning:
            return

        self.current_tool.keyPressEvent(event)
        if event.isAccepted():
            return

    def keyReleaseEvent(self, event):
        if self._panning:
            return

        self.current_tool.keyReleaseEvent(event)
        if event.isAccepted():
            return

    def resizeEvent(self, event):
        self._update_graph_rect()

    def _update_graph_rect(self):
        self._graph_rect = QtCore.QRect(
            self._y_label_size.width(), 0,
            self.width() - self._y_label_size.width(),
            self.height() - self._x_label_size.height()
        )

    def _select_items_at(self, idxs, modifiers=0):
        if modifiers & Qt.ShiftModifier:
            if idxs:
                if any(idx in self.project.selection for idx in idxs):
                    self.project.selection.remove_all(idxs)
                else:
                    self.project.selection.add_all(idxs)
        else:
            self.project.selection.set(idxs)
        self.repaint()

    def mousePressEvent(self, event):
        if self._panning:
            return

        self.current_tool.mousePressEvent(event)
        if event.isAccepted():
            return

        if event.buttons() == Qt.LeftButton:
            idxs = self._find_geometry_at(
                self.screen_to_canvas_point(event.position())
            )
            if len(idxs) > 1:
                popup = QtWidgets.QMenu(self)
                for idx in idxs:
                    popup.addAction(
                        self.project.items[idx].name,
                        (lambda x: lambda: self._select_items_at(x, modifiers=event.modifiers()))([idx])
                    )
                popup.exec(event.globalPosition().toPoint())
            else:
                self._select_items_at(idxs, modifiers=event.modifiers())

        elif (event.buttons() == Qt.MiddleButton) or (event.buttons() == Qt.RightButton):
            self._panning = True
            self.setCursor(Qt.ClosedHandCursor)
            self._last_mouse_position = event.position()

    def mouseReleaseEvent(self, event):
        if self._panning and ((event.button() == Qt.MiddleButton) or (event.button() == Qt.RightButton)):
            self._panning = False
            self.setCursor(Qt.CrossCursor)
            return

        self.current_tool.mouseReleaseEvent(event)
        if event.isAccepted():
            return

        event.ignore()

    def mouseMoveEvent(self, event):
        if self._panning:
            self._offset += (event.position() - self._last_mouse_position).toPoint()
            self._last_mouse_position = event.position()
            self.view_updated.emit()
            self.repaint()
            return

        self.current_tool.mouseMoveEvent(event)
        if event.isAccepted():
            return

        event.ignore()

    def wheelEvent(self, event):
        self.current_tool.wheelEvent(event)
        if event.isAccepted():
            return

        dy = event.pixelDelta().y()
        if dy == 0:
            return

        self._zoom(0.9 if dy < 0 else 1.0 / 0.9, event.position())

    def paintEvent(self, event):
        painter = CncPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("white"))

        clipRect = QtCore.QRect(
            self._y_label_size.width() + 5, 0,
            self.width() - self._y_label_size.width() - 5,
            self.height() - self._x_label_size.height()
        )
        painter.setPen(QtGui.QColor('black'))
        painter.drawRect(clipRect)
        painter.setClipRegion(clipRect)

        painter.translate(self._offset)
        painter.scale(self._scale)

        self._draw_grid(painter)
        self._draw_axis(painter)
        self._draw_items(painter)

        self.current_tool.paint(painter)

    def _draw_axis(self, painter):
        with painter:
            painter.resetTransform()

            painter.setOpacity(0.5)

            painter.setPen(QtGui.QPen(Qt.red, 2.0))
            painter.drawLine(QtCore.QPointF(0, self._offset.y()), QtCore.QPointF(self.width(), self._offset.y()))

            painter.setPen(QtGui.QPen(Qt.green, 2.0))
            painter.drawLine(QtCore.QPointF(self._offset.x(), 0), QtCore.QPointF(self._offset.x(), self.height()))

    def _draw_grid_with_step(self, painter, step):
        pmin = self.screen_to_canvas_point((0, 0))
        pmax = self.screen_to_canvas_point((self.width(), self.height()))
        # pmax = (self.width() - self._offset) / self._scale

        with painter:
            xs = np.arange(pmin.x() - pmin.x() % step + step, pmax.x(), step) * self._scale + self._offset.x()
            ys = np.arange(pmin.y() - pmin.y() % step + step, pmax.y(), step) * self._scale + self._offset.y()

            # draw horizontal lines
            for sy in ys:
                painter.drawLine(QtCore.QPointF(0, sy), QtCore.QPointF(self.width(), sy))

            # draw vertical lines
            for sx in xs:
                painter.drawLine(QtCore.QPointF(sx, 0), QtCore.QPointF(sx, self.height()))

    def _draw_grid_labels(self, painter, step):
        pmin = self.screen_to_canvas_point((0, 0))
        pmax = self.screen_to_canvas_point((self.width(), self.height()))

        with painter:
            xs = np.arange(pmin.x() - pmin.x() % step + step, pmax.x(), step)
            ys = np.arange(pmin.y() - pmin.y() % step + step, pmax.y(), step)

            text_height = painter.fontMetrics().height()
            y_text_width = 30

            grid_screen_size = step * self._scale
            if grid_screen_size < max(self._x_label_size.width(), self._y_label_size.height()):
                # paint only every even line
                if (xs[0] % (10 * step) / step) % 2 == 1:
                    xs = xs[1::2]
                else:
                    xs = xs[::2]

                if (ys[0] % (10 * step) / step) % 2 == 1:
                    ys = ys[1::2]
                else:
                    ys = ys[::2]

            painter.setOpacity(0.5)

            clip_region = painter.clipRegion().boundingRect()

            # draw x axis labels
            painter.setClipRect(
                clip_region.x(), clip_region.y() + clip_region.height(),
                clip_region.width(), self._x_label_size.height()
            )
            horizontal_text_y = self.height() - self._x_label_size.height()
            for x in xs:
                sx = x * self._scale + self._offset.x()

                r = QtCore.QRect(
                    sx - self._x_label_size.width()*0.5,
                    horizontal_text_y,
                    self._x_label_size.width(),
                    self._x_label_size.height(),
                )
                painter.drawText(r, Qt.AlignCenter, '%g' % x)

            # draw y axis labels
            painter.setClipRect(
                0, clip_region.y(),
                self._y_label_size.width(), clip_region.height()
            )
            for y in ys:
                sy = y * self._scale + self._offset.y()

                r = QtCore.QRect(
                    0,
                    sy - self._y_label_size.height()*0.5,
                    self._y_label_size.width(),
                    self._y_label_size.height(),
                )
                painter.drawText(r, Qt.AlignRight | Qt.AlignVCenter, '%g' % y)


    def _draw_grid(self, painter):
        with painter:
            painter.resetTransform()

            pen = QtGui.QPen(QtGui.QColor("grey"))

            painter.setOpacity(0.5)

            grid_step = 10 ** math.ceil(math.log10(20 / self._scale))

            # draw minor lines
            pen.setWidth(1.0)
            painter.setPen(pen)
            self._draw_grid_with_step(painter, grid_step)

            # draw major lines
            pen.setWidth(2.0)
            painter.setPen(pen)
            self._draw_grid_with_step(painter, 10 * grid_step)

            painter.setPen(Qt.black)
            self._draw_grid_labels(painter, grid_step)

    def _draw_items(self, painter):
        with painter:
            for item in self.project.items:
                if item.selected:
                    continue

                item.draw(painter)

            if self.project.selection and not self._hide_selected_geometry:
                for item in self.project.selectedItems:
                    item.draw(painter)

    def screen_to_canvas_point(self, point):
        if not isinstance(point, QtCore.QPointF):
            point = QtCore.QPointF(point[0], point[1])
        return (point - self._offset) / self._scale

    def canvas_to_screen_point(self, point):
        if not isinstance(point, QtCore.QPointF):
            point = QtCore.QPointF(point[0], point[1])
        return point * self._scale + self._offset

    def _find_geometry_at(self, point):
        found = []
        for idx, item in enumerate(self.project.items):
            if not item.visible:
                continue

            if item.contains(point):
                found.append(idx)

        return found

    def _on_item_added(self, index):
        self.update()

    def _on_item_removed(self, index):
        self.update()

    def _on_item_changed(self, index):
        self.update()
