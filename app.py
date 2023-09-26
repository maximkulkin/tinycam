from collections.abc import Sequence
import contextlib
from enum import Enum
from functools import reduce
import math
import os.path
import sys

import numpy as np
from PySide6.QtCore import Qt, QSettings, Signal, QObject, QPoint, QPointF, \
    QRect, QRectF, QMarginsF, QSize, QSizeF, QAbstractListModel, QModelIndex, \
    QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QDockWidget, \
    QMenu, QMenuBar, QToolBar, QStatusBar, QListWidget, QListWidgetItem, \
    QVBoxLayout, QFileDialog, QWidgetAction, QAbstractItemView, \
    QAbstractItemDelegate, QLabel, QStyle, QStyleOptionButton
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPen, QMouseEvent, \
    QPainterPath, QCursor
from geometry import Geometry
from excellon_parser import parse_excellon
from gerber_parser import parse_gerber


GEOMETRY = Geometry()


class Point:
    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            if hasattr(args[0], 'x') and hasattr(args[0], 'y'):
                self._data = (args[0].x(), args[0].y())
            elif hasattr(args[0], 'width') and hasattr(args[0], 'height'):
                self._data = (args[0].width(), args[0].height())
            elif isinstance(args[0], (int, float)):
                self._data = (args[0], args[0])
            elif isinstance(args[0], Sequence) and len(args[0]) == 2:
                self._data = (args[0][0], args[0][1])
            else:
                raise ValueError('Invalid point data')
        elif len(args) == 2:
            self._data = (args[0], args[1])
        elif len(args) == 0 and 'x' in kwargs and 'y' in kwargs:
            self._data = (kwargs['x'], kwargs['y'])
        else:
            raise ValueError('Invalid point data')

    def __str__(self):
        return '(%g, %g)' % (self._data[0], self._data[1])

    def __repr__(self):
        return 'Point(%g, %g)' % (self._data[0], self._data[1])

    def __neg__(self):
        return self.__class__(-self._data[0], -self._data[1])

    def __add__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] + o, self._data[1] + o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] + o[0], self._data[1] + o[1])
        else:
            return self + Point(o)

    def __radd__(self, o):
        return Point(o) + self

    def __sub__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] - o, self._data[1] - o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] - o[0], self._data[1] - o[1])
        else:
            return self - Point(o)

    def __rsub__(self, o):
        return Point(o) - self

    def __mul__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] * o, self._data[1] * o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] * o[0], self._data[1] * o[1])
        else:
            return self * Point(o)

    def __rmul__(self, o):
        return Point(o) * self

    def __truediv__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] / o, self._data[1] / o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] / o[0], self._data[1] / o[1])
        else:
            return self / Point(o)

    def __rtruediv__(self, o):
        return Point(o) / self

    def __floordiv__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] // o, self._data[1] // o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] // o[0], self._data[1] // o[1])
        else:
            return self // Point(o)

    def __rfloordiv__(self, o):
        return Point(o) // self

    def __mod__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] % o, self._data[1] % o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] % o[0], self._data[1] % o[1])
        else:
            return self % Point(o)

    def __rmod__(self, o):
        return Point(o) % self

    def __iter__(self):
        yield self._data[0]
        yield self._data[1]

    def __len__(self):
        return 2

    def __getitem__(self, index):
        if index < 0 or index > 1:
            raise ValueError('Invalid index')

        return self._data[index]

    def x(self):
        return self._data[0]

    def y(self):
        return self._data[1]

    def abs(self):
        return self.__class__(abs(self._data[0]), abs(self._data[1]))

    def toTuple(self):
        return self._data

    def toPoint(self):
        return QPoint(self._data[0], self._data[1])

    def toPointF(self):
        return QPointF(self._data[0], self._data[1])

Point.ZERO = Point(0.0, 0.0)
Point.ONES = Point(1.0, 1.0)


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


class CncProjectItem(QObject):

    def __init__(self, name, color=Qt.black):
        super().__init__()
        self._name = name
        self._color = color
        self._visible = True
        self._selected = False
        self._updating = False
        self._updated = False

    def clone(self):
        clone = self.__class__(self.name, self.color)
        clone.visible = self.visible
        clone.selected = self.selected
        return clone

    def __enter__(self):
        self._updating = True
        self._updated = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._updating = False
        if self._updated:
            self.changed.emit(self)

    def _changed(self):
        if self._updating:
            self._updated = True
        else:
            self.changed.emit(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if self._name == value:
            return
        self._name = value
        self._changed()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        if self._color == value:
            return
        self._color = value
        self._changed()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        if self._visible == value:
            return
        self._visible = value
        self._changed()

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        if self._selected == value:
            return
        self._selected = value
        self._changed()

    def draw(self, painter):
        pass

CncProjectItem.changed = Signal(CncProjectItem)


class GerberItem(CncProjectItem):
    def __init__(self, name, geometry):
        super().__init__(name, QColor.fromRgbF(0.0, 0.6, 0.0, 0.6))
        self._geometry = geometry
        self._geometry_cache = None

    def clone(self):
        clone = GerberItem(self.name, self._geometry)
        clone.color = self.color
        clone.selected = self.selected
        return clone

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, value):
        self._geometry = value
        self._geometry_cache = None
        self._changed()

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
            # name, ext = os.path.splitext(os.path.basename(path))
            name = os.path.basename(path)
            return GerberItem(name, geometry)


class ExcellonItem(CncProjectItem):
    def __init__(self, name, geometry):
        super().__init__(name, color=QColor.fromRgbF(0.65, 0.0, 0.0, 0.6))
        self._geometry = geometry
        self._geometry_cache = None

    def clone(self):
        clone = ExcellonItem(self.name, self._geometry)
        clone.color = self.color
        clone.selected = self.selected
        return clone

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
            geometry = parse_excellon(f.read(), geometry=GEOMETRY)
            # name, ext = os.path.splitext(os.path.basename(path))
            name = os.path.basename(path)
            return ExcellonItem(name, geometry)


class CncJob(CncProjectItem):
    def __init__(self, name):
        super().__init__(name)
        self._geometry = None

    @property
    def geometry(self):
        return self._geometry


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

    @property
    def selection(self):
        return self._selection

    @property
    def selectedItems(self):
        return [self._items[idx] for idx in self._selection]

    @selectedItems.setter
    def selectedItems(self, items):
        self._selection.set([
            idx for idx, item in enumerate(self._items)
            if item in items
        ])


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
            margin = QMarginsF() + 10
            self._bounds = total_bounds([item.geometry for item in items]) # .marginsAdded(margin / self.view.scale)
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
        delta = position - self._original_manipulation_position
        match self._manipulation:
            case self.Manipulation.NONE:
                pass

            case self.Manipulation.MOVE:
                for item, temp_item in zip(self.project.selectedItems, self._items):
                    temp_item.geometry = GEOMETRY.translate(item.geometry, (delta.x(), delta.y()))
                self._update()
                self.view.update()

            case self.Manipulation.RESIZE_TOP:
                self._scale((0, delta.y()), (0, -1))

            case self.Manipulation.RESIZE_BOTTOM:
                self._scale((0, delta.y()), (0, 1))

            case self.Manipulation.RESIZE_LEFT:
                self._scale((delta.x(), 0), (-1, 0))

            case self.Manipulation.RESIZE_RIGHT:
                self._scale((delta.x(), 0), (1, 0))

            case self.Manipulation.RESIZE_TOP_LEFT:
                self._scale(delta.toTuple(), (-1, -1))

            case self.Manipulation.RESIZE_TOP_RIGHT:
                self._scale(delta.toTuple(), (1, -1))

            case self.Manipulation.RESIZE_BOTTOM_LEFT:
                self._scale(delta.toTuple(), (-1, 1))

            case self.Manipulation.RESIZE_BOTTOM_RIGHT:
                self._scale(delta.toTuple(), (1, 1))


    def _scale(self, delta, sign=(0, 0)):
        if self._shift_pressed:
            m = delta[0] if abs(delta[0]) > abs(delta[1]) else delta[1]
            delta = (m * abs(sign[0]), m * abs(sign[1]))

        offset = (delta[0] * 0.5, delta[1] * 0.5)
        if self._alt_pressed:
            offset = (0.0, 0.0)
            delta = (delta[0] * 2, delta[1] * 2)

        scale = (
            1.0 + sign[0] * delta[0] / self._original_bounds.width(),
            1.0 + sign[1] * delta[1] / self._original_bounds.height()
        )

        for item, temp_item in zip(self.project.selectedItems, self._items):
            temp_item.geometry = GEOMETRY.translate(
                GEOMETRY.scale(item.geometry, scale),
                offset
            )
        self._update()
        self.view.update()

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

        for item in self._items:
            item.draw(painter)

        items = self._items or self.project.selectedItems
        self._draw_selection_handles(painter, [item.geometry for item in items])

    def _draw_selection_handles(self, painter, geometries):
        with painter:
            painter.resetTransform()
            pen = QPen(Qt.white, 2)
            pen.setCosmetic(True)
            painter.setPen(pen)
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
        self._x_label_size = QSize(30, 30)
        self._y_label_size = QSize(40, 25)

        self._panning = False
        self._last_mouse_position = QPointF(0.0, 0.0)
        self._hide_selected_geometry = False

        # self.current_tool = CncTool(self.project, self)
        self.current_tool = CncManipulateTool(self.project, self)
        self.current_tool.activate()

        self.project.items.added.connect(self._on_item_added)
        self.project.items.removed.connect(self._on_item_removed)
        self.project.items.changed.connect(self._on_item_changed)

        self.project.selection.changed.connect(self.update)

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
                popup = QMenu(self)
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
            self._offset += (event.position() - self._last_mouse_position)
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
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        clipRect = QRect(
            self._y_label_size.width() + 5, 0,
            self.width() - self._y_label_size.width() - 5,
            self.height() - self._x_label_size.height()
        )
        painter.setPen(QColor('black'))
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

            painter.setPen(QPen(Qt.red, 2.0))
            painter.drawLine(QPointF(0, self._offset.y()), QPointF(self.width(), self._offset.y()))

            painter.setPen(QPen(Qt.green, 2.0))
            painter.drawLine(QPointF(self._offset.x(), 0), QPointF(self._offset.x(), self.height()))

    def _draw_grid_with_step(self, painter, step):
        pmin = self.screen_to_canvas_point((0, 0))
        pmax = self.screen_to_canvas_point((self.width(), self.height()))
        # pmax = (self.width() - self._offset) / self._scale

        with painter:
            xs = np.arange(pmin.x() - pmin.x() % step + step, pmax.x(), step) * self._scale + self._offset.x()
            ys = np.arange(pmin.y() - pmin.y() % step + step, pmax.y(), step) * self._scale + self._offset.y()

            # draw horizontal lines
            for sy in ys:
                painter.drawLine(QPointF(0, sy), QPointF(self.width(), sy))

            # draw vertical lines
            for sx in xs:
                painter.drawLine(QPointF(sx, 0), QPointF(sx, self.height()))

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

                r = QRect(sx - self._x_label_size.width()*0.5, horizontal_text_y, self._x_label_size.width(), self._x_label_size.height())
                painter.drawText(r, Qt.AlignCenter, '%g' % x)

            # draw y axis labels
            painter.setClipRect(
                0, clip_region.y(),
                self._y_label_size.width(), clip_region.height()
            )
            for y in ys:
                sy = y * self._scale + self._offset.y()

                r = QRect(0, sy - self._y_label_size.height()*0.5, self._y_label_size.width(), self._y_label_size.height())
                painter.drawText(r, Qt.AlignRight | Qt.AlignVCenter, '%g' % y)


    def _draw_grid(self, painter):
        with painter:
            painter.resetTransform()

            pen = QPen(QColor("grey"))

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
        if not isinstance(point, QPointF):
            point = QPointF(point[0], point[1])
        return (point - self._offset) / self._scale

    def canvas_to_screen_point(self, point):
        if not isinstance(point, QPointF):
            point = QPointF(point[0], point[1])
        return point * self._scale + self._offset

    def _find_geometry_at(self, point):
        found = []
        for idx, item in enumerate(self.project.items):
            if not item.visible:
                continue

            if GEOMETRY.contains(item.geometry, (point.x(), point.y())):
                found.append(idx)

        return found

    def _on_item_added(self, index):
        self.update()

    def _on_item_removed(self, index):
        self.update()

    def _on_item_changed(self, index):
        self.update()


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
        def __init__(self, project, item):
            super().__init__(item.name, type=QListWidgetItem.UserType + 1)
            self.project = project
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

        self.project.items.added.connect(self._on_item_added)
        self.project.items.removed.connect(self._on_item_removed)
        self.project.items.changed.connect(self._on_item_changed)
        self.project.selection.changed.connect(self._on_project_selection_changed)

        self._updating_selection = False

        self._view = QListWidget()
        self._view.itemSelectionChanged.connect(
            self._on_list_widget_item_selection_changed)
        self._view.itemChanged.connect(self._on_list_widget_item_changed)

        self.setWidget(self._view)
        for item in self.project.items:
            self._view.addItem(self.ItemWidget(self.project, item))

    def _on_item_added(self, index):
        item = self.project.items[index]
        self._view.insertItem(index, self.ItemWidget(self.project, item))

    def _on_item_removed(self, index):
        self._view.removeItem(index)

    def _on_item_changed(self, index):
        pass

    def _on_project_selection_changed(self):
        if self._updating_selection:
            return

        self._updating_selection = True

        model_index = lambda idx: self._view.model().createIndex(idx, 0)

        selection_model = self._view.selectionModel()
        selection_model.clear()
        for idx in self.project.selection:
            selection_model.select(model_index(idx), QItemSelectionModel.Select)

        self._updating_selection = False

    def _on_list_widget_item_selection_changed(self):
        if self._updating_selection:
            return

        self.project.selectedItems = [
            view_item.item
            for view_item in self._view.selectedItems()
        ]

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


class CncApplication(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = CncProject()
        self.undo_stack = QUndoStack()


APP = CncApplication(sys.argv)
APP.project.items.append(GerberItem.from_file('sample.gbr'))
APP.project.items.append(ExcellonItem.from_file('sample.drl'))

main_window = CncMainWindow()
main_window.show()

APP.exec()
