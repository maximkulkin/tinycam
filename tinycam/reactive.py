from typing import Type

from tinycam.signals import Signal


class ReactiveVar[T]:
    changed = Signal[T]()

    def __init__(self, type: Type[T]):
        self._value = type()

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, value: T):
        if self._value == value:
            return

        self._value = value
        self.changed.emit(value)
