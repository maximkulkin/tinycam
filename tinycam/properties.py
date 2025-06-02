from dataclasses import dataclass
from collections.abc import Callable
from numbers import Number
from typing import cast

from tinycam.types import Vector2, Vector3


class PropertyMetadata:
    def __init__(self):
        self._items = []

    def append(self, metadata: object):
        self._items.append(metadata)

    def find(self, type: type) -> object | None:
        for item in self._items:
            if isinstance(item, type):
                return item
        return None

    def __repr__(self) -> str:
        return f'PropertyMetdata(items={self._items})'


def get_property_metadata(obj: object, property_name: str) -> PropertyMetadata:
    if not hasattr(type(obj), property_name):
        return PropertyMetadata()
    prop = getattr(type(obj), property_name)
    if isinstance(prop, property):
        prop = prop.fget
    if not hasattr(prop, '_property_metadata'):
        return PropertyMetadata()
    return prop._property_metadata


get_metadata = get_property_metadata


def add_property_metadata(func, metadata):
    if isinstance(func, property):
        func = func.fget
    if not hasattr(func, '_property_metadata'):
        func._property_metadata = PropertyMetadata()
    func._property_metadata.append(metadata)


def property_metadata_decorator(metadata):
    def decorator(func):
        add_property_metadata(func, metadata)
        return func

    return decorator


class Hidden:
    pass


def hidden(func):
    add_property_metadata(func, Hidden())
    return func


class ReadOnly:
    pass


def readonly(func):
    add_property_metadata(func, ReadOnly())
    return func


@dataclass
class Label:
    label: str


def label(label: str):
    return property_metadata_decorator(Label(label))


@dataclass
class Suffix:
    suffix: str


def suffix(suffix: str):
    return property_metadata_decorator(Suffix(suffix))


@dataclass
class MinValue:
    value: Number


@dataclass
class MaxValue:
    value: Number


def min_value(value: Number):
    return property_metadata_decorator(MinValue(value))


def max_value(value: Number):
    return property_metadata_decorator(MaxValue(value))


def value_range(min: Number, max: Number):
    def decorator(func):
        add_property_metadata(func, MinValue(min))
        add_property_metadata(func, MaxValue(max))
        return func
    return decorator


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
            return self
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
