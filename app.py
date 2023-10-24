from collections.abc import Sequence
import contextlib
from enum import Enum
from functools import reduce
import math
import os.path
import sys

import numpy as np
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

from commands import CncCommandBuilder
from gcode import GcodeRenderer
from geometry import Geometry
from formats import excellon
from formats import gerber


GEOMETRY = Geometry()
APP = None

ITEM_COLORS = [
    QtGui.QColor.fromRgbF(0.6, 0.0, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.0, 0.6, 0.6),
    QtGui.QColor.fromRgbF(0.6, 0.0, 0.6, 0.6),
    QtGui.QColor.fromRgbF(0.6, 0.6, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.6, 0.6, 0.6),
]


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
        return QtCore.QPoint(self._data[0], self._data[1])

    def toPointF(self):
        return QtCore.QPointF(self._data[0], self._data[1])

Point.ZERO = Point(0.0, 0.0)
Point.ONES = Point(1.0, 1.0)


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


class CncProjectItem(QtCore.QObject):

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

CncProjectItem.changed = QtCore.Signal(CncProjectItem)


class GerberItem(CncProjectItem):
    def __init__(self, name, geometry):
        super().__init__(name, QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6))
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
        path = QtGui.QPainterPath()

        for polygon in GEOMETRY.polygons(self._geometry):
            p = QtGui.QPainterPath()

            for exterior in GEOMETRY.exteriors(polygon):
                p.addPolygon(
                    QtGui.QPolygonF.fromList([
                        QtCore.QPointF(x, y)
                        for x, y in GEOMETRY.points(exterior)
                    ])
                )

            for interior in GEOMETRY.interiors(polygon):
                pi = QtGui.QPainterPath()
                pi.addPolygon(
                    QtGui.QPolygonF.fromList([
                        QtCore.QPointF(x, y)
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

            painter.setBrush(QtGui.QBrush(color))
            pen = QtGui.QPen(color.darker(150), 2.0)
            pen.setCosmetic(True)
            painter.setPen(pen)

            painter.drawPath(self._geometry_cache)

    @staticmethod
    def from_file(path):
        with open(path, 'rt') as f:
            geometry = gerber.parse_gerber(f.read(), geometry=GEOMETRY)
            # name, ext = os.path.splitext(os.path.basename(path))
            name = os.path.basename(path)
            return GerberItem(name, geometry)


class ExcellonItem(CncProjectItem):
    def __init__(self, name, excellon_file):
        super().__init__(name, color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6))
        self._excellon_file = excellon_file
        self._geometry = self._excellon_file.geometry
        self._geometry_cache = None

    def clone(self):
        clone = ExcellonItem(self.name, self._excellon_file)
        clone.color = self.color
        clone.selected = self.selected
        return clone

    @property
    def tools(self):
        return self._excellon_file.tools

    @property
    def drills(self):
        return self._excellon_file.drills

    @property
    def mills(self):
        return self._excellon_file.mills

    @property
    def geometry(self):
        return self._excellon_file.geometry

    @geometry.setter
    def geometry(self, value):
        self._geometry = value
        self._geometry_cache = None

    def _precache_geometry(self):
        path = QtGui.QPainterPath()

        for polygon in GEOMETRY.polygons(self._geometry):
            p = QtGui.QPainterPath()

            for exterior in GEOMETRY.exteriors(polygon):
                p.addPolygon(
                    QtGui.QPolygonF.fromList([
                        QtCore.QPointF(x, y)
                        for x, y in GEOMETRY.points(exterior)
                    ])
                )

            for interior in GEOMETRY.interiors(polygon):
                pi = QtGui.QPainterPath()
                pi.addPolygon(
                    QtGui.QPolygonF.fromList([
                        QtCore.QPointF(x, y)
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

            painter.setBrush(QtGui.QBrush(color))
            pen = QtGui.QPen(color.darker(150), 2.0)
            pen.setCosmetic(True)
            painter.setPen(pen)

            painter.drawPath(self._geometry_cache)

    @staticmethod
    def from_file(path):
        with open(path, 'rt') as f:
            excellon_file = excellon.parse_excellon(f.read(), geometry=GEOMETRY)
            name = os.path.basename(path)
            return ExcellonItem(name, excellon_file)


class CncJob(CncProjectItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._geometry = None

    @property
    def geometry(self):
        return self._geometry

    def generate_commands(self):
        raise NotImplemented()


class CncIsolateJob(CncJob):
    def __init__(self,
                 source_item,
                 tool_diameter=0.1,
                 spindle_speed=1000,
                 cut_depth=0.1,
                 cut_speed=120,
                 travel_height=2,
                 pass_count=1,
                 pass_overlap=10):
        super().__init__(
            'Isolate %s' % source_item.name,
            color=QtGui.QColor.fromRgbF(0.65, 0.0, 0.0, 0.6),
        )

        self._source_item = source_item

        self._tool_diameter = tool_diameter
        self._cut_depth = cut_depth
        self._pass_count = pass_count
        self._pass_overlap = pass_overlap
        self._spindle_speed = spindle_speed
        self._cut_speed = cut_speed
        self._travel_height = travel_height

        self._geometry = None
        self._geometry_cache = None
        # TODO:
        # self._source_item.changed.connect(self._on_source_item_changed)
        self._calculate_geometry()

    @property
    def geometry(self):
        return self._geometry

    @property
    def tool_diameter(self):
        return self._tool_diameter

    @tool_diameter.setter
    def tool_diameter(self, value):
        self._tool_diameter = value
        self._update()

    @property
    def cut_depth(self):
        return self._cut_depth

    @cut_depth.setter
    def cut_depth(self, value):
        self._cut_depth = value
        self._update()

    @property
    def pass_count(self):
        return self._pass_count

    @pass_count.setter
    def pass_count(self, value):
        self._pass_count = value
        self._update()

    @property
    def pass_overlap(self):
        return self._pass_overlap

    @pass_overlap.setter
    def pass_overlap(self, value):
        self._pass_overlap = value
        self._update()

    @property
    def cut_speed(self):
        return self._cut_speed

    @cut_speed.setter
    def cut_speed(self, value):
        self._cut_speed = value
        self._update()

    @property
    def spindle_speed(self):
        return self._spindle_speed

    @spindle_speed.setter
    def spindle_speed(self, value):
        self._spindle_speed = value
        self._update()

    @property
    def travel_height(self):
        return self._travel_height

    @travel_height.setter
    def travel_height(self, value):
        self._travel_height = value
        self._update()

    def _on_source_item_changed(self, _item):
        self._update()

    def _update(self):
        self._calculate_geometry()
        self._changed()

    def _calculate_geometry(self):
        tool_radius = self._tool_diameter * 0.5
        pass_offset = self._tool_diameter * (1 - self._pass_overlap / 100.0)

        geometry = None

        g = GEOMETRY.simplify(
            GEOMETRY.buffer(self._source_item.geometry, tool_radius),
            # TODO: parametrize into settings
            tolerance=0.01,
        )

        for pass_index in range(self._pass_count):
            for polygon in GEOMETRY.polygons(g):
                for exterior in GEOMETRY.exteriors(polygon):
                    geometry = GEOMETRY.union(geometry, exterior)
                for interior in GEOMETRY.interiors(polygon):
                    geometry = GEOMETRY.union(geometry, interior)
            g = GEOMETRY.buffer(g, pass_offset)

        self._geometry = geometry
        self._geometry_cache = None

    def _precache_geometry(self):
        path = QtGui.QPainterPath()
        count = 0
        for line in GEOMETRY.lines(self._geometry):
            path.addPolygon(
                QtGui.QPolygonF.fromList([
                    QtCore.QPointF(x, y)
                    for x, y in GEOMETRY.points(line)
                ])
            )
            count += len(GEOMETRY.points(line))

        self._geometry_cache = path

    def draw(self, painter):
        if not self.visible:
            return

        if self._geometry_cache is None:
            self._precache_geometry()

        with painter:
            color = self.color
            if self.selected:
                color = color.lighter(150)

            painter.setBrush(Qt.NoBrush)
            pen = QtGui.QPen(color.darker(150), 2.0)
            pen.setCosmetic(True)
            painter.setPen(pen)

            painter.drawPath(self._geometry_cache)

            color.setAlphaF(0.2)
            pen = QtGui.QPen(color, self._tool_diameter)
            pen.setJoinStyle(Qt.RoundJoin)

            painter.setPen(pen)

            painter.drawPath(self._geometry_cache)

    def _find_closest(self, lines, point):
        # TODO: implement finding closest line
        return 0

    def generate_commands(self):
        # TODO: allow selecting different starting positions
        builder = CncCommandBuilder(start_position=(0, 0, 0))

        lines = list(GEOMETRY.lines(self._geometry))
        while lines:
            line_idx = self._find_closest(lines, builder.current_position)
            line = lines.pop(line_idx)

            points = line.coords[:]
            # if line.is_closed:
            #     p, _ = shapely.ops.nearest_points(line, shapely.Point(builder.current_position[:2]))
            #     print(points)
            #     start_index = points.index(p)
            #     points = points[start_index:] + points[:start_index]

            builder.travel(z=self._travel_height)
            builder.travel(x=points[0][0], y=points[0][1])
            builder.cut(z=-self._cut_depth)

            for p in points[1:]:
                builder.cut(x=p[0], y=p[1])

        return builder.build()


class CncProject(QtCore.QObject):
    class ItemCollection(QtCore.QObject):
        added = QtCore.Signal(int)
        removed = QtCore.Signal(int)
        changed = QtCore.Signal(int)

        def __init__(self):
            super().__init__()
            self._items = []
            self._item_changed_callbacks = {}

        def insert(self, index, item):
            if index < 0:
                index += len(self)
                if index < 0:
                    raise KeyError()

            item.changed.connect(self._on_item_changed)

            self._items.insert(index, item)
            self.added.emit(index)

        def append(self, item):
            item.changed.connect(self._on_item_changed)

            self._items.append(item)
            self.added.emit(len(self._items) - 1)

        def extend(self, items):
            for item in items:
                self.append(item)

        def remove(self, item):
            index = self.index(item)
            item.changed.disconnect(self._on_item_changed)
            self._items.remove(item)
            self.removed.emit(index)

        def clear(self):
            for i in reversed(range(len(self))):
                del self[i]

        def index(self, item):
            return self._items.index(item)

        def __iter__(self):
            yield from self._items

        def __len__(self):
            return len(self._items)

        def __getitem__(self, index):
            return self._items[index]

        def __setitem__(self, index, item):
            if index < 0:
                index += len(self)
                if index < 0:
                    raise KeyError()

            self._items[index].changed.disconnect(self._on_item_changed)
            self._items[index] = item
            item.changed.connect(self._on_item_changed)
            self.changed.emit(index)

        def __delitem__(self, index):
            if index < 0:
                index += len(self)
                if index < 0:
                    raise KeyError()
            self._items[index].changed.disconnect(self._on_item_changed)
            del self._items[index]
            self.removed.emit(index)

        def __contains__(self, item):
            return item in self._items

        def _on_item_changed(self, item):
            index = self._items.index(item)
            if index == -1:
                return
            self.changed.emit(index)

    class Selection(QtCore.QObject):
        changed = QtCore.Signal()

        def __init__(self, project):
            super().__init__()
            self._project = project
            self._indexes = set()

        def _changed(self):
            self.changed.emit()

        def set(self, indexes):
            indexes = set(indexes)

            for index in (self._indexes - indexes):
                self.remove(index)

            self.add_all(indexes)

        def add(self, index):
            if index < 0 or index >= len(self._project.items):
                raise ValueError("Selection index is out of range")

            if index in self._indexes:
                return

            self._indexes.add(index)
            self._project.items[index].selected = True
            self._changed()

        def add_all(self, indexes):
            if not indexes:
                return

            for index in indexes:
                if index < 0 or index >= len(self._project.items):
                    raise ValueError("Selection index is out of range")

                if index in self._indexes:
                    continue

                self._indexes.add(index)
                self._project.items[index].selected = True

            self._changed()

        def remove(self, index):
            if index not in self._indexes:
                return

            self._indexes.remove(index)
            self._project.items[index].selected = False
            self._changed()

        def remove_all(self, indexes):
            changed = False
            for index in indexes:
                if index not in self._indexes:
                    continue

                self._indexes.remove(index)
                self._project.items[index].selected = False
                changed = True

            if changed:
                self._changed()

        def clear(self):
            if not self._items:
                return

            for index in self._indexes:
                self._project.items[index].selected = False

            self._indexes = set()
            self._changed()

        def __iter__(self):
            yield from self._indexes

        def __len__(self):
            return len(self._indexes)

        def __contains__(self, index):
            return index in self._indexes

        def items(self):
            for index in self._indexes:
                yield self._project.items[index]

    def __init__(self):
        super().__init__()
        self._items = self.ItemCollection()
        self._selection = self.Selection(self)

    @property
    def items(self):
        return self._items

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


class UpdateItemEditorCommand(QtGui.QUndoCommand):
    def __init__(self, item, updates, parent=None):
        super().__init__('Update item', parent=parent)
        self._item = item
        self._updates = updates
        self._previous_values = {}

    def redo(self):
        self._previous_values = {
            k: getattr(self._item, k)
            for k in self._updates
        }
        for k, v in self._updates.items():
            setattr(self._item, k, v)

    def undo(self):
        for k, v in self._previous_values.items():
            setattr(self._item, k, v)
        self._previous_values = {}


class MoveItemsEditorCommand(QtGui.QUndoCommand):
    def __init__(self, items, offset, parent=None):
        super().__init__('Move', parent=parent)
        self._items = items
        self._offset = offset

    def _move(self, offset):
        for item in self._items:
            item.geometry = GEOMETRY.translate(item.geometry, offset)

    def redo(self):
        self._move(self._offset)

    def undo(self):
        self._move((-self._offset[0], -self._offset[1]))


class ScaleItemsEditorCommand(QtGui.QUndoCommand):
    def __init__(self, items, scale, offset=Point(0.0, 0.0), parent=None):
        super().__init__('Scale', parent=parent)
        self._items = items
        self._scale = scale
        self._offset = offset

    def redo(self):
        for item in self._items:
            item.geometry = GEOMETRY.translate(
                GEOMETRY.scale(item.geometry, self._scale),
                self._offset
            )

    def undo(self):
        for item in self._items:
            item.geometry = GEOMETRY.scale(
                GEOMETRY.translate(item.geometry, -self._offset),
                1.0/self._scale
            )


class SetItemsColorEditorCommand(QtGui.QUndoCommand):
    def __init__(self, items, color, parent=None):
        super().__init__('Set color', parent=parent)
        self._items = items
        self._color = color

        self._old_colors = {}

    def redo(self):
        for item in self._items:
            self._old_colors[item] = item.color
            item.color = self._color

    def undo(self):
        for item, color in self._old_colors.items():
            item.color = color


class DeleteItemsEditorCommand(QtGui.QUndoCommand):
    def __init__(self, items, parent=None):
        super().__init__('Delete', parent=parent)
        self._items = items
        self._item_indexes = []

    def redo(self):
        self._item_indexes = [
            (APP.project.items.index(item), item)
            for item in self._items
        ]
        self._item_indexes.sort()

        for item in self._items:
            APP.project.items.remove(item)

    def undo(self):
        for idx, item in self._item_indexes:
            APP.project.items.insert(idx, item)


class CreateIsolateJobEditorCommand(QtGui.QUndoCommand):
    def __init__(self, item, parent=None):
        super().__init__('Create Isolate Job', parent=parent)
        self._source_item = item
        self._result_item = None

    @property
    def source_item(self):
        return self._source_item

    @property
    def result_item(self):
        return self._result_item

    def redo(self):
        self._result_item = CncIsolateJob(self._source_item)
        APP.project.items.append(self._result_item)

    def undo(self):
        APP.project.items.remove(self._result_item)


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
        offset = point - self.view.canvas_to_screen_point(handle_position)
        return abs(offset.x()) <= size and abs(offset.y()) <= size

    def _get_delta(self):
        return Point(self.view.screen_to_canvas_point(
            self.view.mapFromGlobal(QtGui.QCursor.pos()).toPointF()
        )) - self._original_manipulation_position

    def _move_command(self, items, delta):
        return MoveItemsEditorCommand(items, delta)

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

        return ScaleItemsEditorCommand(items, scale, offset)

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
            APP.undo_stack.push(command)

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

            if GEOMETRY.contains(item.geometry, (point.x(), point.y())):
                found.append(idx)

        return found

    def _on_item_added(self, index):
        self.update()

    def _on_item_removed(self, index):
        self.update()

    def _on_item_changed(self, index):
        self.update()


class CncWindow(QtWidgets.QDockWidget):
    visibilityChanged = QtCore.Signal()

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
    class ItemWidget(QtWidgets.QListWidgetItem):
        def __init__(self, project, item):
            super().__init__(item.name, type=QtWidgets.QListWidgetItem.UserType + 1)
            self.project = project
            self.item = item
            self.setFlags(
                  Qt.ItemIsEnabled
                | Qt.ItemIsEditable
                | Qt.ItemIsSelectable
                | Qt.ItemIsUserCheckable
            )
            self.setCheckState(Qt.Checked if self.item.visible else Qt.Unchecked)

    class ColorBox(QtWidgets.QWidget):
        def __init__(self, color, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.color = color
            self.set = QtCore.QPoint(30, 0)
            self.setMinimumSize(QtCore.QSize(70, 20))
            self.checked = False

        def paintEvent(self, event):
            super().paintEvent(event)

            painter = QtGui.QPainter(self)

            if self.checked:
                style = QtWidgets.QStyleOptionButton(1)
                style.rect = QtCore.QRect(5, 2, 20, self.size().height() - 4)
                style.state = QtWidgets.QStyle.State_Enabled | QtWidgets.QStyle.State_On

                QtWidgets.QApplication.style().drawPrimitive(
                    QtWidgets.QStyle.PE_IndicatorItemViewItemCheck,
                    style, painter, self
                )

            color = QtGui.QColor(self.color)
            color.setAlphaF(1.0)
            painter.fillRect(
                QtCore.QRect(25, 2, self.size().width() - 30, self.size().height() - 4),
                color
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("project_window")
        self.setWindowTitle("Project")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        self.project.items.added.connect(self._on_item_added)
        self.project.items.removed.connect(self._on_item_removed)
        self.project.items.changed.connect(self._on_item_changed)
        self.project.selection.changed.connect(self._on_project_selection_changed)

        self._updating_selection = False

        self._view = QtWidgets.QListWidget()
        self._view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._view.setEditTriggers(
              QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
        )
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
            selection_model.select(model_index(idx), QtCore.QItemSelectionModel.Select)

        self._updating_selection = False

    def _on_list_widget_item_selection_changed(self):
        if self._updating_selection:
            return

        self.project.selectedItems = [
            view_item.item
            for view_item in self._view.selectedItems()
        ]

    def _on_list_widget_item_changed(self, item):
        with self.project.items[self._view.row(item)] as view_item:
            view_item.name = item.text()
            view_item.visible = item.checkState() == Qt.Checked

    def _on_context_menu(self, position):
        if self._view.currentItem() is None:
            return

        item = self._view.currentItem().item

        popup = QtWidgets.QMenu(self)

        color_menu = popup.addMenu('Color')
        for color in ITEM_COLORS:
            widget = self.ColorBox(color)
            widget.checked = item.color == color
            set_color_action = QtWidgets.QWidgetAction(self)
            set_color_action.setDefaultWidget(widget)
            set_color_action.triggered.connect(
                (lambda c: lambda _checked: self._set_color(c))(color)
            )
            color_menu.addAction(set_color_action)

        popup.addAction('Delete', self._delete_items)
        if isinstance(item, GerberItem):
            popup.addAction('Create Isolate Job', self._isolate_job)
        elif isinstance(item, CncJob):
            popup.addAction('Export G-code', self._export_gcode)

        popup.exec(self.mapToGlobal(position))

    def _set_color(self, color):
        APP.undo_stack.push(SetItemsColorEditorCommand(self.project.selectedItems, color))

    def _delete_items(self):
        APP.undo_stack.push(DeleteItemsEditorCommand(self.project.selectedItems))

    def _isolate_job(self):
        if len(self.project.selection) == 0:
            return

        command = CreateIsolateJobEditorCommand(self.project.selectedItems[0])
        APP.undo_stack.push(command)
        APP.project.selectedItems = [command.result_item]

    def _export_gcode(self):
        if len(self.project.selection) == 0:
            return

        result = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption='Export Gcode',
            filter='Gerber (*.gcode)',
        )
        if result[0] == '':
            # cancelled
            return

        commands = self.project.selectedItems[0].generate_commands()
        renderer = GcodeRenderer()
        gcode = renderer.render(commands)

        try:
            with open(result[0], 'wt') as f:
                f.write(gcode)
        except Exception as e:
            print('Failed to export Gcode to %s: %s' % (result[0], e))

            info_box = QtWidgets.QMessageBox(self)
            info_box.setWindowTitle('Export Gcode')
            info_box.setText('Failed to export Gcode to %s' % result[0])
            info_box.exec()


class StringEdit(QtWidgets.QLineEdit):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editingFinished.connect(self.value_changed.emit)

    @property
    def value(self):
        return self.text()

    @value.setter
    def value(self, value):
        self.setText(value)


class IntEdit(QtWidgets.QSpinBox):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self):
        self.value_changed.emit()


class FloatEdit(QtWidgets.QDoubleSpinBox):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.setValue(self._last_value)
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self):
        self.value_changed.emit()


class Vector2Edit(QtWidgets.QWidget):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('X'))
        self._x_edit = FloatEdit(self)
        layout.addWidget(self._x_edit)
        layout.addWidget(QtWidgets.QLabel('Y'))
        self._y_edit = FloatEdit(self)
        layout.addWidget(self._y_edit)
        self.setLayout(layout)

        self._x_edit.value_changed.connect(self.value_changed.emit)
        self._y_edit.value_changed.connect(self.value_changed.emit)

    @property
    def value(self):
        return (float(self._x_edit.text()), float(self._y_edit.text()))

    @value.setter
    def value(self, value):
        self._x_edit.setText(str(value[0]))
        self._y_edit.setText(str(value[1]))

    def _on_value_changed(self, s):
        self.value_changed.emit()


class CncOptionsView(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._items = []
        layout = QtWidgets.QFormLayout()
        # layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.hide()

    def matches(self):
        return False

    def activate(self):
        for item in self._items:
            item.changed.connect(self._on_item_changed)
            self._items.append(item)

        self.update()
        APP.project.selection.changed.connect(self._on_selection_changed)
        self.show()

    def deactivate(self):
        for item in self._items:
            item.changed.disconnect(self._on_item_changed)

        APP.project.selection.changed.disconnect(self._on_selection_changed)
        self.hide()

    def update(self):
        pass

    def _on_item_changed(self, item):
        self._update()

    def _on_selection_changed(self):
        for item in self._items:
            item.changed.disconnect(self._on_selection_changed)

        self._items = APP.project.selectedItems

        for item in self._items:
            item.changed.connect(self._on_selection_changed)

    def _add_label(self, text):
        label = QtWidgets.QLabel(text)
        self.layout().addRow(label)
        return label

    def _add_custom_edit(self, label, widget):
        self.layout().addRow(label, widget)
        return widget

    def _add_string_edit(self, label):
        return self._add_custom_edit(label, StringEdit())

    def _add_int_edit(self, label):
        return self._add_custom_edit(label, IntEdit())

    def _add_float_edit(self, label):
        return self._add_custom_edit(label, FloatEdit())

    def _add_vector_edit(self, label):
        return self._add_custom_edit(label, Vector2Edit())


class CncProjectItemOptionsView(CncOptionsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._scale_edit = self._add_vector_edit("Scale")
        self._offset_edit = self._add_vector_edit("Offset")

    def matches(self, items):
        return all(isinstance(item, CncProjectItem) for item in items)


class CncIsolateJobOptionsView(CncOptionsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._add_label('Isolation Job')

        self._tool_diameter_edit = self._add_float_edit("Tool Diameter")
        self._tool_diameter_edit.setSingleStep(0.05)
        self._tool_diameter_edit.value_changed.connect(self._on_tool_diameter_changed)

        self._cut_depth_edit = self._add_float_edit("Cut Depth")
        self._cut_depth_edit.setSingleStep(0.05)
        self._cut_depth_edit.value_changed.connect(self._on_cut_depth_changed)

        self._pass_count_edit = self._add_int_edit("Pass Count")
        self._pass_count_edit.setMinimum(1)
        self._pass_count_edit.setMaximum(10)
        self._pass_count_edit.value_changed.connect(self._on_pass_count_changed)

        self._pass_overlap_edit = self._add_int_edit("Pass Overlap")
        self._pass_overlap_edit.setRange(0, 100)
        self._pass_overlap_edit.setSingleStep(5)
        self._pass_overlap_edit.value_changed.connect(self._on_pass_overlap_changed)

        self._cut_speed_edit = self._add_int_edit("Feed Rate")
        self._cut_speed_edit.setRange(10, 10000)
        self._cut_speed_edit.value_changed.connect(self._on_cut_speed_changed)

        self._spindle_speed_edit = self._add_int_edit("Spindle Speed")
        self._spindle_speed_edit.setRange(10, 100000)
        self._spindle_speed_edit.setSingleStep(25)
        self._spindle_speed_edit.value_changed.connect(self._on_spindle_speed_changed)

        self._travel_height_edit = self._add_float_edit("Travel Height")
        self._travel_height_edit.setSingleStep(1)
        self._travel_height_edit.value_changed.connect(self._on_travel_height_changed)

    def matches(self, items):
        return all(isinstance(item, CncIsolateJob) for item in items)

    @property
    def _item(self):
        return APP.project.selectedItems[0]

    def update(self):
        self._tool_diameter_edit.setValue(self._item.tool_diameter)
        self._cut_depth_edit.setValue(self._item.cut_depth)
        self._pass_count_edit.setValue(self._item.pass_count)
        self._pass_overlap_edit.setValue(self._item.pass_overlap)
        self._cut_speed_edit.setValue(self._item.cut_speed)
        self._spindle_speed_edit.setValue(self._item.spindle_speed)
        self._travel_height_edit.setValue(self._item.travel_height)

    def _on_tool_diameter_changed(self):
        APP.undo_stack.push(
            UpdateItemEditorCommand(self._item, {
                'tool_diameter': self._tool_diameter_edit.value(),
            })
        )

    def _on_cut_depth_changed(self):
        APP.undo_stack.push(
            UpdateItemEditorCommand(self._item, {
                'cut_depth': self._cut_depth_edit.value(),
            })
        )

    def _on_pass_count_changed(self):
        APP.undo_stack.push(
            UpdateItemEditorCommand(self._item, {
                'pass_count': self._pass_count_edit.value(),
            })
        )
        self._pass_overlap_edit.enabled = (self._item.pass_count > 1)

    def _on_pass_overlap_changed(self):
        APP.undo_stack.push(
            UpdateItemEditorCommand(self._item, {
                'pass_overlap': self._pass_overlap_edit.value(),
            })
        )

    def _on_cut_speed_changed(self):
        APP.undo_stack.push(
            UpdateItemEditorCommand(self._item, {
                'cut_speed': self._cut_speed_edit.value(),
            })
        )

    def _on_spindle_speed_changed(self):
        APP.undo_stack.push(
            UpdateItemEditorCommand(self._item, {
                'spindle_speed': self._spindle_speed_edit.value(),
            })
        )

    def _on_travel_height_changed(self):
        APP.undo_stack.push(
            UpdateItemEditorCommand(self._item, {
                'travel_height': self._travel_height_edit.value(),
            })
        )


class CncToolOptionsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("tool_options_window")
        self.setWindowTitle("Tool options")

        self._options_views = []
        self._options_views.append(CncIsolateJobOptionsView(self))
        self._options_views.append(CncProjectItemOptionsView(self))

        layout = QtWidgets.QVBoxLayout()
        for view in self._options_views:
            layout.addWidget(view)
        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(layout)
        self.setWidget(main_widget)

        self._current_view = None
        self._items = []
        APP.project.selection.changed.connect(self._on_project_selection_changed)

    def _on_project_selection_changed(self):
        if len(self._items) != 0:
            self._deactivate_view()

        self._items = APP.project.selectedItems
        if len(self._items) != 0:
            for view in self._options_views:
                if view.matches(self._items):
                    self._activate_view(view)
                    break

    def _activate_view(self, view):
        if self._current_view is view:
            return

        if self._current_view is not None:
            self._current_view.deactivate()

        self._current_view = view
        self._current_view.activate()

    def _deactivate_view(self):
        if self._current_view is None:
            return

        self._current_view.deactivate()
        self._current_view = None


class CncMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(600, 400)

        self.project = APP.project
        self.project_view = CncVisualization(self.project, self)
        self.setCentralWidget(self.project_view)

        self.menu = QtWidgets.QMenuBar()
        self.file_menu = self.menu.addMenu("File")
        self.file_menu.addAction('Import Drawing', self._import_file,
                                 shortcut='Ctrl+o')

        undo_action = APP.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setIcon(QtGui.QIcon(":/icons/undo.png"))
        undo_action.setShortcuts(QtGui.QKeySequence.Undo)

        redo_action = APP.undo_stack.createRedoAction(self, "&Redo")
        redo_action.setIcon(QtGui.QIcon(":/icons/redo.png"))
        redo_action.setShortcuts(QtGui.QKeySequence.Redo)

        self.edit_menu = self.menu.addMenu("Edit")
        self.edit_menu.addAction(undo_action)
        self.edit_menu.addAction(redo_action)

        self.view_menu = self.menu.addMenu("View")

        self.setMenuBar(self.menu)

        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setObjectName('Toolbar')
        self.addToolBar(self.toolbar)
        self.toolbar.addAction('Import', self._import_file)
        self.toolbar.addAction('Zoom To Fit', self.project_view.zoom_to_fit)

        self.statusbar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusbar)

        self._windows = []
        self._windows_menu = {}

        self._add_dock_window(
            CncProjectWindow(self.project), Qt.LeftDockWidgetArea,
            shortcut='Ctrl+1',
        )
        self._add_dock_window(
            CncToolOptionsWindow(self.project), Qt.RightDockWidgetArea,
            shortcut='Ctrl+2',
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

    def _import_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption='Import Drawing',
            filter='Gerber (*.gbr);;Excellon (*.drl);;All files (*)'
        )
        if filename == '':
            return

        def critical_error(text):
            QtWidgets.QMessageBox.critical(self, 'Import Drawing', text)

        item = None
        if filename.endswith('.gbr'):
            try:
                item = GerberItem.from_file(filename)
            except gerber.GerberError as e:
                critical_error(f'Error parsing Gerber file: {e}')
                return

        elif filename.endswith('.drl'):
            try:
                item = ExcellonItem.from_file(filename)
            except excellon.ExcellonError as e:
                QtWidgets.QMessageBox.critical(
                    self, 'Import Drawing',
                    f'Error parsing Excellon file: {e}',
                )
                return
        else:
            if item is None:
                try:
                    item = GerberItem.from_file(filename)
                except gerber.GerberError:
                    pass

            if item is None:
                try:
                    item = ExcellonItem.from_file(filename)
                except excellon.ExcellonError:
                    pass

        if item is None:
            QtWidgets.QMessageBox.critical(
                self, 'Import Drawing',
                f'File format is not recognized for {filename}',
            )
            return

        APP.project.items.append(item)

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
        settings = QtCore.QSettings()
        settings.beginGroup("main_window")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.endGroup()

    def _load_settings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("main_window")
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("windowState"))
        settings.endGroup()


class CncApplication(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = CncProject()
        self.undo_stack = QtGui.QUndoStack()


APP = CncApplication(sys.argv)
APP.project.items.append(GerberItem.from_file('sample.gbr'))
APP.project.items.append(ExcellonItem.from_file('sample.drl'))

main_window = CncMainWindow()
main_window.show()

APP.exec()
