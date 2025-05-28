from collections.abc import Sequence
from typing import Iterator

from tinycam.project.item import CncProjectItem, CncProjectItemCollection
from tinycam.signals import Signal


class CncProject(CncProjectItem):
    class Selection:
        changed = Signal()

        def __init__(self, project: 'CncProject'):
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
        super().__init__('Project')
        self._selection = self.Selection(self)

    @property
    def items(self) -> CncProjectItemCollection:
        return self.children

    @property
    def selection(self) -> 'CncProject.Selection':
        return self._selection
