from collections.abc import Sequence
from typing import Iterator

from PySide6 import QtCore

from tinycam.project.item import CncProjectItem


class CncProject(QtCore.QObject):
    class ItemCollection(QtCore.QObject):
        added = QtCore.Signal(CncProjectItem)
        removed = QtCore.Signal(CncProjectItem)
        changed = QtCore.Signal(CncProjectItem)
        updated = QtCore.Signal(CncProjectItem)

        def __init__(self):
            super().__init__()
            self._items = []
            self._item_changed_callbacks = {}

        def insert(self, index: int, item: CncProjectItem):
            if index < 0:
                index += len(self)
                if index < 0:
                    raise KeyError()

            item.changed.connect(self._on_item_changed)
            item.updated.connect(self._on_item_updated)

            self._items.insert(index, item)
            self.added.emit(item)

        def append(self, item: CncProjectItem):
            item.changed.connect(self._on_item_changed)
            item.updated.connect(self._on_item_updated)

            self._items.append(item)
            self.added.emit(item)

        def extend(self, items: Sequence[CncProjectItem]):
            for item in items:
                self.append(item)

        def remove(self, item: CncProjectItem):
            index = self.index(item)
            item.changed.disconnect(self._on_item_changed)
            item.updated.disconnect(self._on_item_updated)
            self._items.remove(item)
            self.removed.emit(item)

        def clear(self):
            for i in reversed(range(len(self))):
                del self[i]

        def index(self, item: CncProjectItem) -> int:
            return self._items.index(item)

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
            old_item.changed.disconnect(self._on_item_changed)
            old_item.updated.disconnect(self._on_item_updated)

            self._items[index] = item
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

    class Selection(QtCore.QObject):
        changed = QtCore.Signal()

        def __init__(self, project: 'CncProject'):
            super().__init__()
            self._project: CncProject = project
            self._items: list[CncProjectItem] = []

        def _signal_changed(self):
            self.changed.emit()

        def set(self, items: Sequence[CncProjectItem]):
            for item in self._items:
                if item not in items:
                    self.remove(item)

            self.add_all(items)

        def add(self, item: CncProjectItem):
            if item in self._items:
                return

            self._items.append(item)
            item.selected = True

            self._signal_changed()

        def add_all(self, items: Sequence[CncProjectItem]):
            if not items:
                return

            for item in items:
                if item in self._items:
                    continue

                self._items.append(item)
                item.selected = True

            self._signal_changed()

        def remove(self, item: CncProjectItem):
            if item not in self._items:
                return

            self._items.remove(item)
            item.selected = False

            self._signal_changed()

        def remove_all(self, items: Sequence[CncProjectItem]):
            changed = False

            for item in items:
                if item not in self._items:
                    continue

                self._items.remove(item)
                item.selected = False
                changed = True

            if changed:
                self._signal_changed()

        def clear(self):
            if not self._items:
                return

            for item in self._items:
                item.selected = False

            self._items = []
            self._signal_changed()

        def __iter__(self) -> Iterator[CncProjectItem]:
            yield from self._items

        def __len__(self) -> int:
            return len(self._items)

        def __getitem__(self, index: int) -> CncProjectItem:
            if index < 0 or index >= len(self._items):
                raise IndexError('Selection index is out of range')

            return self._items[index]

        def __contains__(self, item: CncProjectItem):
            return item in self._items

    def __init__(self):
        super().__init__()
        self._items = self.ItemCollection()
        self._selection = self.Selection(self)

    @property
    def items(self) -> 'CncProject.ItemCollection':
        return self._items

    @property
    def selection(self) -> 'CncProject.Selection':
        return self._selection
