from dataclasses import dataclass
from collections.abc import Callable
from numbers import Number
from typing import cast


METADATA_ATTRIBUTE = '_property_metadata'


class PropertyMetadata:
    def __init__(self, items: list[object] | None = None):
        self._items = items[:] if items is not None else []

    def append(self, metadata: object):
        self._items.append(metadata)

    def find(self, type: type) -> object | None:
        for item in self._items:
            if isinstance(item, type):
                return item
        return None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(items={self._items})'


class Property[T]:
    def __init__(self, *,
                 metadata: list[object] = [],
                 on_update: Callable[[object], None] = lambda _: None):
        self.type = T
        self._on_update: Callable[[object], None] = on_update
        self._property_metadata = PropertyMetadata(metadata)

    def __set_name__(self, objtype, name):
        self._variable_name = f'_{name}'

    def __get__(self, instance: object, objtype: type | None = None) -> T:
        if instance is None:
            return self
        return cast(T, instance.__dict__.get(self._variable_name))

    def __set__(self, instance: object, value: T):
        instance.__dict__[self._variable_name] = value
        self._on_update(instance)


def metadata(metadata: list[object]):
    def decorator(func):
        return extend_metadata(func, metadata)
    return decorator


def get_all(obj: object) -> list[str]:
    obj_type = type(obj)
    return [
        name
        for name in dir(obj_type)
        for prop in [getattr(obj_type, name)]
        if not name.startswith('_') and hasattr(prop, METADATA_ATTRIBUTE)
    ]


def get_metadata(obj: object, property_name: str) -> PropertyMetadata | None:
    if not hasattr(type(obj), property_name):
        return PropertyMetadata()
    prop = getattr(type(obj), property_name)
    if isinstance(prop, property):
        prop = prop.fget
    if not hasattr(prop, METADATA_ATTRIBUTE):
        return None
    return prop._property_metadata


def extend_metadata(func, metadata: list[object]):
    if isinstance(func, property):
        func = func.fget
    if not hasattr(func, METADATA_ATTRIBUTE):
        func._property_metadata = PropertyMetadata()
    func._property_metadata.extend(metadata)
    return func


def add_metadata(func, metadata: object):
    return extend_metadata(func, [metadata])


class Hidden:
    pass


class ReadOnly:
    pass


@dataclass
class Label:
    label: str


@dataclass
class Suffix:
    suffix: str


@dataclass
class MinValue:
    value: Number


@dataclass
class MaxValue:
    value: Number
