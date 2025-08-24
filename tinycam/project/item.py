from collections.abc import Sequence
import inspect
from typing import ForwardRef

from PySide6 import QtGui
from PySide6.QtCore import Qt

from tinycam.geometry import Shape
from tinycam.globals import GLOBALS
from tinycam.signals import Signal
from tinycam.types import Rect
import tinycam.properties as p
from tinycam.utils import index_if


class CncProjectItem(p.EditableObject):
    # Signal used to signal when asynchronous operation on the item has finished
    #
    # E.g. if changing parameter of a job that causes expensive computations,
    # first changed signal will be emitted to signal that the property has changed.
    # When asynchronous update will finish, updated signal will be emitted, so that
    # e.g. UI can update item geometry.
    updated = Signal[ForwardRef('CncProjectItem')]()

    def __init__(self):  # pyright: ignore[reportAttributeAccessIssue]
        super().__init__()

        self._name = 'Item'
        self._color = Qt.black
        self._visible = True
        self._debug = False
        self._selected = False
        self._parent = None
        self._children = CncProjectItemCollection(self)
        self._geometry = GLOBALS.GEOMETRY.group([])
        self._bounds = None

    def _update(self):
        self._signal_changed()

    @property
    def geometry(self) -> Shape:
        return self._geometry

    @geometry.setter
    def geometry(self, value: Shape):
        self._geometry = value
        self._bounds = None
        self._signal_updated()

    @property
    def bounds(self) -> Rect:
        if self._bounds is None:
            self._bounds = GLOBALS.GEOMETRY.bounds(self.geometry)

        return self._bounds

    def clone(self) -> 'CncProjectItem':
        clone = self.__class__()

        for attr in dir(self):
            if attr.startswith('_') or attr == 'children':
                continue

            value = getattr(self, attr, None)
            if inspect.ismethod(value):
                continue

            try:
                setattr(clone, attr, value)
            except AttributeError:
                # Attribute is readonly
                pass

        for child in self.children:
            clone.children.append(child)

        return clone

    def _signal_updated(self):
        self.updated.emit(self)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if self._name == value:
            return
        self._name = value
        self._signal_changed()

    @property
    def color(self) -> QtGui.QColor:
        return self._color

    @color.setter
    def color(self, value: QtGui.QColor):
        if self._color == value:
            return
        self._color = value
        self._signal_changed()

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        if self._visible == value:
            return
        self._visible = value
        self._signal_changed()

    @property
    def debug(self) -> bool:
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        if self._debug == value:
            return
        self._debug = value
        self._signal_changed()

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        if self._selected == value:
            return
        self._selected = value
        self._signal_changed()

    @property
    def parent(self) -> 'CncProjectItem | None':
        return self._parent

    @parent.setter
    def parent(self, value: 'CncProjectItem | None'):
        if self._parent == value:
            return
        self._parent = value
        self._signal_changed()

    @property
    def children(self) -> 'CncProjectItemCollection':
        return self._children


class CncProjectItemCollection:
    added = Signal[CncProjectItem]()
    removed = Signal[CncProjectItem]()
    changed = Signal[CncProjectItem]()
    updated = Signal[CncProjectItem]()

    def __init__(self, owner: CncProjectItem | None = None):
        self._owner = owner
        self._items = []
        self._item_changed_callbacks = {}

    def insert(self, index: int, item: CncProjectItem):
        if index < 0:
            index += len(self)
            if index < 0:
                raise KeyError()

        self._items.insert(index, item)
        item.parent = self._owner

        self.added.emit(item)

        item.changed.connect(self._on_item_changed)
        item.updated.connect(self._on_item_updated)

    def append(self, item: CncProjectItem):
        self._items.append(item)
        item.parent = self._owner

        self.added.emit(item)

        item.changed.connect(self._on_item_changed)
        item.updated.connect(self._on_item_updated)

    def extend(self, items: Sequence[CncProjectItem]):
        for item in items:
            self.append(item)

    def remove(self, item: CncProjectItem):
        item.changed.disconnect(self._on_item_changed)
        item.updated.disconnect(self._on_item_updated)
        self._items.remove(item)
        self.removed.emit(item)
        if item.parent == self._owner:
            item.parent = None

    def clear(self):
        for i in reversed(range(len(self))):
            del self[i]

    def index(self, item: CncProjectItem) -> int:
        return index_if(self._items, lambda i: i is item, -1)

    def __iter__(self):
        yield from self._items

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int):
        return self._items[index]

    def __setitem__(self, index: int, item: CncProjectItem):
        if index < 0:
            index += len(self)
            if index < 0:
                raise KeyError()

        old_item = self._items[index]
        if old_item.parent == self._owner:
            old_item.parent = None
        old_item.changed.disconnect(self._on_item_changed)
        old_item.updated.disconnect(self._on_item_updated)

        self._items[index] = item
        item.parent = self._owner
        item.changed.connect(self._on_item_changed)
        item.updated.connect(self._on_item_updated)

        self.removed.emit(old_item)
        self.added.emit(item)

    def __delitem__(self, index: int):
        if index < 0:
            index += len(self)
            if index < 0:
                raise KeyError()

        item = self._items[index]
        if item.parent == self._owner:
            item.parent = None
        item.changed.disconnect(self._on_item_changed)
        item.updated.disconnect(self._on_item_updated)
        del self._items[index]
        self.removed.emit(item)

    def __contains__(self, item: CncProjectItem):
        return item in self._items

    def _on_item_changed(self, item: CncProjectItem):
        index = self._items.index(item)
        if index == -1:
            return
        self.changed.emit(item)

    def _on_item_updated(self, item: CncProjectItem):
        index = self._items.index(item)
        if index == -1:
            return
        self.updated.emit(item)
