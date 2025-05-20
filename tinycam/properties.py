from collections.abc import Callable
from typing import cast

from tinycam.types import Vector2, Vector3


class Property[T]:
    def __init__(self, *,
                 label: str | None = None,
                 on_update: Callable[[object], None] = lambda _: None):
        self._name: str | None = None
        self._label: str | None = label
        self._on_update: Callable[[object], None] = on_update

    @property
    def name(self) -> str:
        return self._name or ''

    @property
    def label(self) -> str:
        return self._label or ''

    def __set_name__(self, objtype, name):
        self._name = name
        self._variable_name = f'_{name}'
        if self._label is None:
            self._label = name.replace('_', ' ').capitalize()

    def __get__(self, instance: object, objtype: type | None = None) -> T:
        if instance is None:
            raise ValueError('Property object is None')
        return cast(T, instance.__dict__.get(self._variable_name))

    def __set__(self, instance: object, value: T):
        instance.__dict__[self._variable_name] = value
        self._on_update(instance)


class StringProperty(Property[str]):
    pass


class BoolProperty(Property[bool]):
    pass


class IntProperty(Property[int]):
    def __init__(self, *,
                 min_value: int | None = None,
                 max_value: int | None = None,
                 suffix: str | None = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.min_value: int | None = min_value
        self.max_value: int | None = max_value
        self.suffix: str | None = suffix


class FloatProperty(Property[float]):
    def __init__(self, *,
                 min_value: float | None = None,
                 max_value: float | None = None,
                 suffix: str | None = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.min_value: float | None = min_value
        self.max_value: float | None = max_value
        self.suffix: str | None = suffix


class Vector2Property(Property[Vector2]):
    pass


class Vector3Property(Property[Vector3]):
    pass
