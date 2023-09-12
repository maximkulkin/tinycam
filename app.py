import contextlib
from enum import Enum
from functools import reduce
import math
import os.path
import sys

import numpy as np
from PySide6.QtCore import Qt, QSettings, Signal, QObject, QPointF, QRect, QRectF, \
    QMarginsF, QSizeF, QAbstractListModel, QModelIndex, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QDockWidget, \
    QMenuBar, QToolBar, QStatusBar, QListWidget, QListWidgetItem, \
    QVBoxLayout, QFileDialog
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPen, QMouseEvent, \
    QPainterPath, QCursor
from geometry import Geometry
from gerber_parser import parse_gerber


GEOMETRY = Geometry()


class CncPainter(QPainter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._offset = QPointF(0, 0)
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


class GerberItem:
    def __init__(self, name, geometry):
        self.name = name
        self.color = QColor.fromRgbF(0.0, 0.65, 0.0, 0.6)
        self.visible = True
        self.selected = False
        self._geometry = geometry
        self._geometry_cache = None

    def clone(self):
        return GerberItem(self.name, self._geometry)

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, value):
        self._geometry = value
        self._geometry_cache = None

    def _precache_geometry(self):
        path = QPainterPath()

        for polygon in GEOMETRY.polygons(self._geometry):
            p = QPainterPath()

            for exterior in GEOMETRY.exteriors(polygon):
                p.addPolygon(
                    QPolygonF.fromList([
                        QPointF(x, y)
                        for x, y in GEOMETRY.points(exterior)
                    ])
                )

            for interior in GEOMETRY.interiors(polygon):
                pi = QPainterPath()
                pi.addPolygon(
                    QPolygonF.fromList([
                        QPointF(x, y)
                        for x, y in GEOMETRY.points(interior)
                    ])
                )
                p = p.subtracted(pi)

            path = path.united(p)

        self._geometry_cache = path

    def draw(self, painter):
        if not self.visible:
            return

        if not self._geometry_cache:
            self._precache_geometry()

        with painter:
            color = self.color
            if self.selected:
                color = color.lighter(150)

            painter.setBrush(QBrush(color))
            pen = QPen(color.darker(150), 2.0)
            pen.setCosmetic(True)
            painter.setPen(pen)

            painter.drawPath(self._geometry_cache)

    @staticmethod
    def from_file(path):
        with open(path, 'rt') as f:
            geometry = parse_gerber(f.read(), geometry=GEOMETRY)
            name, ext = os.path.splitext(os.path.basename(path))
            return GerberItem(name, geometry)


class CncJob:
    def __init__(self):
        self._geometry = None

    @property
    def geometry(self):
        return self._geometry

    def update(self):
        pass

    def draw(self, painter):
        pass


class CncIsolateJob(CncJob):
    def __init__(self, source_geometry, tool_diameter, cut_depth, feed_rate, spindle_speed):
        super().__init__()
        self._source_geometry = source_geometry
        self._tool_diameter = tool_diameter
        self._cut_depth = cut_depth
        self._feed_rate = feed_rate
        self._spindle_speed = spindle_speed

        self._geometry = None

    @property
    def geometry(self):
        return self._isolation_geometry

    @property
    def tool_diameter(self):
        return self._tool_diameter

    @tool_diameter.setter
    def tool_diameter(self, value):
        self._tool_diameter = value
        self.update()

    @property
    def feed_rate(self):
        return self._feed_rate

    @feed_rate.setter
    def feed_rate(self, value):
        self._feed_rate = value
        self.update()

    @property
    def spindle_speed(self):
        return self._spindle_speed

    @spindle_speed.setter
    def spindle_speed(self, value):
        self._spindle_speed = value
        self.update()

    def update(self):
        self._geometry = s


class Project(QObject):
    items_changed = Signal()
    selection_changed = Signal()

    def __init__(self):
        super().__init__()
        self._items = []
        self._selection = set()

        self._jobs = []

    @property
    def items(self):
        return self._items

    @property
    def jobs(self):
        return self._jobs

    def add_item(self, item):
        self._items.append(item)
        self.items_changed.emit()

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        if not isinstance(value, set):
            raise ValueError('Selection should be a set')

        self._selection = set(value)

        for idx, item in enumerate(self._items):
            item.selected = idx in self._selection

        self.selection_changed.emit()

    @property
    def selectedItems(self):
        return [self._items[idx] for idx in self._selection]


def combine_bounds(b1, b2):
    return (min(b1[0], b2[0]), min(b1[1], b2[1]), max(b1[2], b2[2]), max(b1[3], b2[3]))

def total_bounds(shapes):
    coords = reduce(combine_bounds, [shape.bounds for shape in shapes])
    return QRectF(coords[0], coords[1], coords[2] - coords[0], coords[3] - coords[1])


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
    class Manipulation(Enum):
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
        self._original_manipulation_position = QPointF()
        self._shift_pressed = False
        self.view.view_updated.connect(self._update)

    def activate(self):
        self.project.selection_changed.connect(self._update)
        self._manipulation = self.Manipulation.NONE

    def deactivate(self):
        self.project.selection_changed.disconnect(self._udpate)

    def _update(self):
        items = self._items or self.project.selectedItems
        if items:
            margin = QMarginsF() + 10
            self._bounds = total_bounds([item.geometry for item in items]).marginsAdded(margin / self.view.scale)
        else:
            self._bounds = None

    def _within_handle(self, point, handle_position):
        size = 10.0
        offset = point - self.view.canvas_to_screen_point(handle_position)
        return abs(offset.x()) <= size and abs(offset.y()) <= size

    def _update_manipulation(self):
        position = self.view.screen_to_canvas_point(
            self.view.mapFromGlobal(QCursor.pos()).toPointF()
        )
        match self._manipulation:
            case self.Manipulation.NONE:
                pass
            case self.Manipulation.MOVE:
                delta = position - self._original_manipulation_position
                for item, temp_item in zip(self.project.selectedItems, self._items):
                    temp_item.geometry = GEOMETRY.translate(item.geometry, (delta.x(), delta.y()))
                self._update()
                self.view.update()
            case self.Manipulation.RESIZE_TOP:
                pass
            case self.Manipulation.RESIZE_BOTTOM:
                delta = position.y() - self._original_manipulation_position.y()
                scale = 1.0 + delta / self._bounds.height()
                offset = delta * 0.5
                if self._shift_pressed:
                    offset = 0.0

                for item, temp_item in zip(self.project.selectedItems, self._items):
                    temp_item.geometry = GEOMETRY.translate(
                        GEOMETRY.scale(item.geometry, (1.0, scale)),
                        (0.0, offset)
                    )
                self._update()
                self.view.update()
            case self.Manipulation.RESIZE_LEFT:
                pass
            case self.Manipulation.RESIZE_RIGHT:
                pass
            case self.Manipulation.RESIZE_TOP_LEFT:
                pass
            case self.Manipulation.RESIZE_TOP_RIGHT:
                pass
            case self.Manipulation.RESIZE_BOTTOM_LEFT:
                pass
            case self.Manipulation.RESIZE_BOTTOM_RIGHT:
                pass

    def _accept_manipulation(self):
        for item, new_item in zip(self.project.selectedItems, self._items):
            item.geometry = new_item.geometry

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

    def keyReleaseEvent(self, event):
        event.ignore()
        if self._manipulation != self.Manipulation.NONE:
            if event.key() == Qt.Key_Shift:
                self._shift_pressed = False
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
        elif self._within_handle(event.position(), QPointF(center.x(), self._bounds.top())):
            self._manipulation = self.Manipulation.RESIZE_TOP
        elif self._within_handle(event.position(), QPointF(center.x(), self._bounds.bottom())):
            self._manipulation = self.Manipulation.RESIZE_BOTTOM
        elif self._within_handle(event.position(), QPointF(self._bounds.left(), center.y())):
            self._manipulation = self.Manipulation.RESIZE_LEFT
        elif self._within_handle(event.position(), QPointF(self._bounds.right(), center.y())):
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
            elif (self._within_handle(event.position(), QPointF(center.x(), self._bounds.top())) or
                  self._within_handle(event.position(), QPointF(center.x(), self._bounds.bottom()))):
                self.view.setCursor(Qt.SizeVerCursor)
            elif (self._within_handle(event.position(), QPointF(self._bounds.left(), center.y())) or
                  self._within_handle(event.position(), QPointF(self._bounds.right(), center.y()))):
                self.view.setCursor(Qt.SizeHorCursor)
            elif self._within_handle(event.position(), self._bounds.center()):
                self.view.setCursor(Qt.SizeAllCursor)
            else:
                self.view.setCursor(Qt.ArrowCursor)

    def paint(self, painter):
        if self._bounds is None:
            return

        with painter:
            painter.translate(self.view.offset)
            painter.scale(self.view.scale)

            for item in self._items:
                item.draw(painter)

        items = self._items or self.project.selectedItems
        self._draw_selection_handles(painter, [item.geometry for item in items])

    def _draw_selection_handles(self, painter, geometries):
        with painter:
            painter.setPen(QColor('white'))
            painter.setBrush(QColor('dimgrey'))

            self._draw_box_handle(painter, self._bounds.topLeft())
            self._draw_box_handle(painter, self._bounds.topRight())
            self._draw_box_handle(painter, self._bounds.bottomLeft())
            self._draw_box_handle(painter, self._bounds.bottomRight())

            center = self._bounds.center()

            self._draw_box_handle(painter, QPointF(center.x(), self._bounds.top()))
            self._draw_box_handle(painter, QPointF(center.x(), self._bounds.bottom()))

            self._draw_box_handle(painter, QPointF(self._bounds.left(), center.y()))
            self._draw_box_handle(painter, QPointF(self._bounds.right(), center.y()))

            self._draw_box_handle(painter, center)

    def _draw_box_handle(self, painter, position, size=QSizeF(10, 10)):
        """Draws box handle, position in canvas and size is in screen coordinates."""
        p = self.view.canvas_to_screen_point(position)
        painter.drawRect(p.x() - size.width()*0.5, p.y() - size.height()*0.5, size.width(), size.height());


class CncVisualization(QWidget):
    view_updated = Signal()

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)

        self._scale = 1.0
        self._offset = QPointF(0.0, 0.0)

        self._panning = False
        self._last_mouse_position = QPointF(0.0, 0.0)
        self._hide_selected_geometry = False

        # self.current_tool = CncTool(self.project, self)
        self.current_tool = CncManipulateTool(self.project, self)
        self.current_tool.activate()

        self.project.items_changed.connect(self.update)
        self.project.selection_changed.connect(self.update)

        self.setCursor(Qt.CrossCursor)

    @property
    def scale(self):
        return self._scale

    @property
    def offset(self):
        return self._offset

    def _zoom(self, k, position=None):
        self._scale *= k
        self._offset = self._offset * k + position * (1 - k)
        self.view_updated.emit()
        self.update()

    def zoom_in(self):
        self._zoom(1.0 / 0.8, QPointF(self.width()/2, self.height()/2))

    def zoom_out(self):
        self._zoom(0.8, QPointF(self.width()/2, self.height()/2))

    def zoom_to_fit(self):
        bounds = reduce(combine_bounds, [item.geometry.bounds for item in self.project.items])

        self._scale = min((self.width() - 20) / (bounds[2] - bounds[0]),
                          (self.height() - 20) / (bounds[3] - bounds[1]))
        w = (bounds[2] - bounds[0]) * self._scale
        h = (bounds[3] - bounds[1]) * self._scale
        self._offset = self.canvas_to_screen_point(
            self.screen_to_canvas_point(
                QPointF((self.width() - w) * 0.5, (self.height() - h) * 0.5)
            ) - QPointF(bounds[0], bounds[1])
        )
        self.view_updated.emit()
        self.repaint()

    def hide_selected_geometry(self, state):
        self._hide_selected_geometry = bool(state)

    def keyPressEvent(self, event):
        self.current_tool.keyPressEvent(event)
        if event.isAccepted():
            return

    def keyReleaseEvent(self, event):
        self.current_tool.keyReleaseEvent(event)
        if event.isAccepted():
            return

    def mousePressEvent(self, event):
        self.current_tool.mousePressEvent(event)
        if event.isAccepted():
            return

        if event.buttons() == Qt.LeftButton:
            idx = self._find_geometry_at(
                self.screen_to_canvas_point(event.position())
            )
            if event.modifiers() & Qt.ShiftModifier:
                if idx != -1:
                    if idx in self.project.selection:
                        self.project.selection -= {idx}
                    else:
                        self.project.selection |= {idx}
            else:
                self.project.selection = set() if idx == -1 else {idx}
            self.repaint()
        elif (event.buttons() == Qt.MiddleButton) or (event.buttons() == Qt.RightButton):
            self._panning = True
            self.setCursor(Qt.ClosedHandCursor)
            self._last_mouse_position = event.position()
        event.accept()

    def mouseReleaseEvent(self, event):
        self.current_tool.mouseReleaseEvent(event)
        if event.isAccepted():
            return

        if self._panning and ((event.button() == Qt.MiddleButton) or (event.button() == Qt.RightButton)):
            self._panning = False
            self.setCursor(Qt.CrossCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        self.current_tool.mouseMoveEvent(event)
        if event.isAccepted():
            return

        if self._panning:
            self._offset += (event.position() - self._last_mouse_position)
            self.view_updated.emit()
            self.repaint()

        self._last_mouse_position = event.position()
        event.accept()

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
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        self._draw_grid(painter)

        clipRect = QRect(50, 0, self.width() - 50, self.height() - 30)
        painter.setPen(QColor('black'))
        painter.drawRect(clipRect)
        painter.setClipRegion(clipRect)

        self._draw_axis(painter)
        self._draw_items(painter)

        self.current_tool.paint(painter)

    def _draw_axis(self, painter):
        with painter:
            painter.setOpacity(0.5)

            painter.setPen(QPen(Qt.red, 2.0))
            painter.drawLine(QPointF(0, self._offset.y()), QPointF(self.width(), self._offset.y()))

            painter.setPen(QPen(Qt.green, 2.0))
            painter.drawLine(QPointF(self._offset.x(), 0), QPointF(self._offset.x(), self.height()))

    def _draw_grid_with_step(self, painter, step):
        pmin = self.screen_to_canvas_point((0, 0))
        pmax = self.screen_to_canvas_point((self.width(), self.height()))
        # pmax = (self.width() - self._offset) / self._scale

        with painter:
            # xs = np.arange(pmin.x() - pmin.x() % step + step, pmax.x(), step) * self._scale + self._offset.x()
            xs = np.arange(pmin.x() - pmin.x() % step + step, pmax.x(), step) * self._scale + self._offset.x()
            ys = np.arange(pmin.y() - pmin.y() % step + step, pmax.y(), step) * self._scale + self._offset.y()

            # draw horizontal lines
            for sy in ys:
                painter.drawLine(QPointF(0, sy), QPointF(self.width(), sy))

            # draw vertical lines
            for sx in xs:
                painter.drawLine(QPointF(sx, 0), QPointF(sx, self.height()))

    def _draw_grid_scale(self, painter, step):
        pmin = self.screen_to_canvas_point((0, 0))
        pmax = self.screen_to_canvas_point((self.width(), self.height()))

        edge_offset = 10  # offset 10 pixels from the edge

        left_margin = edge_offset

        with painter:
            xs = np.arange(pmin.x() - pmin.x() % step + step, pmax.x(), step)
            ys = np.arange(pmin.y() - pmin.y() % step + step, pmax.y(), step)

            text_height = painter.fontMetrics().height()
            x_text_width = painter.fontMetrics().maxWidth() * int(math.ceil(math.log10(max(abs(xs[0]), abs(xs[-1])))) + 1.0)
            y_text_width = painter.fontMetrics().maxWidth() * int(math.ceil(math.log10(max(abs(ys[0]), abs(ys[-1])))) + 1.0)

            grid_screen_size = step * self._scale
            if grid_screen_size < max(x_text_width, y_text_width):
                # paint only every even line
                if (xs[0] % (10 * step) / step) % 2 == 1:
                    xs = xs[1::2]
                else:
                    xs = xs[::2]

                if (ys[0] % (10 * step) / step) % 2 == 1:
                    ys = ys[1::2]
                else:
                    ys = ys[::2]

            left_margin = y_text_width + edge_offset
            bottom_margin = self.height() - edge_offset - text_height * 2

            background_color = QColor('white')
            painter.setOpacity(1.0)
            painter.fillRect(0, 0, y_text_width + edge_offset, self.height(), background_color)
            painter.fillRect(0, self.height() - edge_offset - text_height, self.width(), text_height + edge_offset, background_color)

            painter.setOpacity(0.5)
            # draw horizontal lines
            for y in ys:
                sy = y * self._scale + self._offset.y()
                if sy >= bottom_margin:
                    continue

                r = QRect(edge_offset, sy - text_height*0.5, y_text_width, text_height)
                painter.drawText(r, Qt.AlignRight | Qt.AlignVCenter, '%g' % y)


            # draw vertical lines
            horizontal_text_y = self.height() - edge_offset - text_height
            for x in xs:
                sx = x * self._scale + self._offset.x()
                if sx - x_text_width*0.5 <= left_margin:
                    continue

                r = QRect(sx - x_text_width*0.5, horizontal_text_y, x_text_width, text_height)
                painter.drawText(r, Qt.AlignCenter, '%g' % x)

    def _draw_grid(self, painter):
        with painter:
            pen = QPen()
            pen.setColor(QColor("grey"))

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

            self._draw_grid_scale(painter, grid_step)

    def _draw_items(self, painter):
        with painter:
            painter.translate(self._offset)
            painter.scale(self._scale)

            for item in self.project.items:
                if item.selected:
                    continue

                item.draw(painter)

            if self.project.selection and not self._hide_selected_geometry:
                for item in self.project.selectedItems:
                    item.draw(painter)

    def screen_to_canvas_point(self, point):
        if not isinstance(point, QPointF):
            point = QPointF(point[0], point[1])
        return (point - self._offset) / self._scale

    def canvas_to_screen_point(self, point):
        if not isinstance(point, QPointF):
            point = QPointF(point[0], point[1])
        return point * self._scale + self._offset

    def _find_geometry_at(self, point):
        for idx, item in enumerate(self.project.items):
            if not item.visible:
                continue

            if GEOMETRY.contains(item.geometry, (point.x(), point.y())):
                return idx

        return -1


class CncWindow(QDockWidget):
    visibilityChanged = Signal()

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project
        self.setMinimumSize(200, 200)

    def showEvent(self, event):
        self.visibilityChanged.emit()
        super().showEvent(event)

    def hideEvent(self, event):
        self.visibilityChanged.emit()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.hide()
        event.accept()


class CncProjectWindow(CncWindow):
    class ItemWidget(QListWidgetItem):
        def __init__(self, item):
            super().__init__(item.name, type=QListWidgetItem.UserType + 1)
            self.item = item

            self.visible_checkbox = QCheckBox()
            self.label = QLabel(item.name)

            layout = QHBoxLayout()
            layout.addWidget(self.visible_checkbox)
            layout.addWidget(self.label)

            self.setLayout(layout)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("project_window")
        self.setWindowTitle("Project")

        self.project.items_changed.connect(self._update_items)
        self.project.selection_changed.connect(self._on_project_selection_changed)

        self._view = QListWidget()
        self._view.itemChanged.connect(self._on_list_widget_item_changed)

        self._updating_selection = False

        self.setWidget(self._view)
        self._update_items()

    def _update_items(self):
        self._view.clear()
        for item in self.project.items:
            item_widget = QListWidgetItem(item.name)
            item_widget.setCheckState(Qt.Checked if item.visible else Qt.Unchecked)

            self._view.addItem(item_widget)

    def _on_project_selection_changed(self):
        selectionModel = self._view.selectionModel()
        self._updating_selection = True
        selectionModel.clear()
        for idx in self.project.selection:
            selectionModel.select(
                QItemSelection(self._view.model().createIndex(idx, 0),
                               self._view.model().createIndex(idx, 0)),
                QItemSelectionModel.Select
            )
        self._updating_selection = False

    def _on_list_widget_item_changed(self, item):
        self.project.items[self._view.row(item)].visible = item.checkState() == Qt.Checked
        self.project.items_changed.emit()


class CncJobsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("jobs_window")
        self.setWindowTitle("Jobs")


class CncToolOptionsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("tool_options_window")
        self.setWindowTitle("Tool options")


class CncMainWindow(QMainWindow):
    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(600, 400)

        self.project = project
        self.project_view = CncVisualization(self.project, self)
        self.setCentralWidget(self.project_view)

        self.menu = QMenuBar()
        self.file_menu = self.menu.addMenu("File")
        self.file_menu.addAction('Import Gerber', self._import_gerber,
                                 shortcut='Ctrl+o')

        self.view_menu = self.menu.addMenu("View")

        self.setMenuBar(self.menu)

        self.toolbar = QToolBar()
        self.toolbar.setObjectName('Toolbar')
        self.addToolBar(self.toolbar)
        self.toolbar.addAction('Import', self._import_gerber)
        self.toolbar.addAction('Zoom To Fit', self.project_view.zoom_to_fit)

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self._windows = []
        self._windows_menu = {}

        self._add_dock_window(
            CncProjectWindow(self.project), Qt.LeftDockWidgetArea,
            shortcut='Ctrl+1',
        )
        self._add_dock_window(
            CncJobsWindow(self.project), Qt.LeftDockWidgetArea,
            shortcut='Ctrl+2',
        )
        self._add_dock_window(
            CncToolOptionsWindow(self.project), Qt.RightDockWidgetArea,
            shortcut='Ctrl+3',
        )

        self.view_menu.addSeparator()
        self.view_menu.addAction('Zoom In', self.project_view.zoom_in,
                                 shortcut='Ctrl++')
        self.view_menu.addAction('Zoom Out', self.project_view.zoom_out,
                                 shortcut='Ctrl+-')
        self.view_menu.addAction('Zoom To Fit', self.project_view.zoom_to_fit,
                                 shortcut='Ctrl+=')
        self.view_menu.addSeparator()

        self._load_settings()

    def _import_gerber(self):
        result = QFileDialog.getOpenFileName(
            parent=self, caption='Import Gerber',
            # filter='Gerber (*.gbr);Excellon (*.drl)'
        )
        if result[0] != '':
            self.project.import_gerber(result[0])

    def _add_dock_window(self, window, area, shortcut=''):
        self._windows.append(window)
        self.addDockWidget(area, window)
        action = self.view_menu.addAction(
            window.windowTitle(), lambda: self._toggle_window(window),
            shortcut=shortcut)
        action.setCheckable(True)
        self._windows_menu[window] = action

    def _toggle_window(self, window):
        if window.isVisible():
            window.hide()
        else:
            window.show()

        if window in self._windows_menu:
            self._windows_menu.get(window).setChecked(window.isVisible())

    def showEvent(self, event):
        super().showEvent(event)

        for window in self._windows:
            self._windows_menu[window].setChecked(window.isVisible())

        self.project_view.zoom_to_fit()

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    def _save_settings(self):
        settings = QSettings()
        settings.beginGroup("main_window")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.endGroup()

    def _load_settings(self):
        settings = QSettings()
        settings.beginGroup("main_window")
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("windowState"))
        settings.endGroup()


PROJECT = Project()
PROJECT.add_item(GerberItem.from_file('sample.gbr'))

app = QApplication(sys.argv)

main_window = CncMainWindow(PROJECT)
main_window.show()

app.exec()
