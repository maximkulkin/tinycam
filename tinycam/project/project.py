from PySide6 import QtCore
from collections.abc import Sequence
from tinycam.project.item import CncProjectItem
from typing import Generator


class CncProject(QtCore.QObject):
    class ItemCollection(QtCore.QObject):
        added = QtCore.Signal(int)
        removed = QtCore.Signal(int)
        changed = QtCore.Signal(int)
        updated = QtCore.Signal(int)

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
            self.added.emit(index)

        def append(self, item: CncProjectItem):
            item.changed.connect(self._on_item_changed)
            item.updated.connect(self._on_item_updated)

            self._items.append(item)
            self.added.emit(len(self._items) - 1)

        def extend(self, items: Sequence[CncProjectItem]):
            for item in items:
                self.append(item)

        def remove(self, item: CncProjectItem):
            index = self.index(item)
            item.changed.disconnect(self._on_item_changed)
            item.updated.disconnect(self._on_item_updated)
            self._items.remove(item)
            self.removed.emit(index)

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

            self._items[index].changed.disconnect(self._on_item_changed)
            self._items[index].updated.disconnect(self._on_item_updated)
            self._items[index] = item
            item.changed.connect(self._on_item_changed)
            item.updated.connect(self._on_item_updated)
            self.changed.emit(index)

        def __delitem__(self, index: int):
            if index < 0:
                index += len(self)
                if index < 0:
                    raise KeyError()
            self._items[index].changed.disconnect(self._on_item_changed)
            self._items[index].updated.disconnect(self._on_item_updated)
            del self._items[index]
            self.removed.emit(index)

        def __contains__(self, item: CncProjectItem):
            return item in self._items

        def _on_item_changed(self, item: CncProjectItem):
            index = self._items.index(item)
            if index == -1:
                return
            self.changed.emit(index)

        def _on_item_updated(self, item: CncProjectItem):
            index = self._items.index(item)
            if index == -1:
                return
            self.updated.emit(index)

    class Selection(QtCore.QObject):
        changed = QtCore.Signal()

        def __init__(self, project: 'CncProject'):
            super().__init__()
            self._project = project
            self._indexes = set()

        def _signal_changed(self):
            self.changed.emit()

        def set(self, indexes: Sequence[int]):
            indexes = set(indexes)

            for index in (self._indexes - indexes):
                self.remove(index)

            self.add_all(indexes)

        def add(self, index: int):
            if index < 0 or index >= len(self._project.items):
                raise ValueError("Selection index is out of range")

            if index in self._indexes:
                return

            self._indexes.add(index)
            self._project.items[index].selected = True
            self._signal_changed()

        def add_all(self, indexes: Sequence[int]):
            if not indexes:
                return

            for index in indexes:
                if index < 0 or index >= len(self._project.items):
                    raise ValueError("Selection index is out of range")

                if index in self._indexes:
                    continue

                self._indexes.add(index)
                self._project.items[index].selected = True

            self._signal_changed()

        def remove(self, index: int):
            if index not in self._indexes:
                return

            self._project.items[index].selected = False
            self._indexes.remove(index)
            self._signal_changed()

        def remove_all(self, indexes: Sequence[int]):
            changed = False
            for index in indexes:
                if index not in self._indexes:
                    continue

                self._indexes.remove(index)
                self._project.items[index].selected = False
                changed = True

            if changed:
                self._signal_changed()

        def clear(self):
            if not self._indexes:
                return

            for index in self._indexes:
                self._project.items[index].selected = False

            self._indexes = set()
            self._signal_changed()

        def __iter__(self):
            yield from self._indexes

        def __len__(self) -> int:
            return len(self._indexes)

        def __contains__(self, index: int):
            return index in self._indexes

        def items(self) -> Generator[CncProjectItem, None, None]:
            for index in self._indexes:
                yield self._project.items[index]

    def __init__(self):
        super().__init__()
        self._items = self.ItemCollection()
        self._selection = self.Selection(self)

    @property
    def items(self) -> Sequence[CncProjectItem]:
        return self._items

    @property
    def selection(self) -> 'CncProject.Selection':
        return self._selection

    @property
    def selectedItems(self) -> Sequence[CncProjectItem]:
        return [self._items[idx] for idx in self._selection]

    @selectedItems.setter
    def selectedItems(self, items: Sequence[CncProjectItem]):
        self._selection.set([
            idx for idx, item in enumerate(self._items)
            if item in items
        ])
