from PySide6 import QtCore


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


