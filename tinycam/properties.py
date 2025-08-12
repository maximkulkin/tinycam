from dataclasses import dataclass
from collections.abc import Callable
from numbers import Number
from typing import cast

import tinycam.settings as s
from tinycam.signals import Signal


METADATA_ATTRIBUTE = '_cnc_metadata'


class EditableObject:
    changed = Signal[object]()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._updating = False
        self._updated = False

    def __enter__(self):
        """A context to withhold update events for an item if multiple updates are planned

        Example:

            with item:
                item.color = color1
                item.visible = True

        """
        self._updating = True
        self._updated = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._updating = False
        if self._updated:
            self.changed.emit(self)

    def _signal_changed(self):
        if self._updating:
            self._updated = True
        else:
            self.changed.emit(self)


class ReferenceType:

    @classmethod
    def all_instances(cls) -> list[object]:
        raise NotImplementedError()


class Metadata:
    def __init__(self, items: list[object] | None = None):
        self._items = items[:] if items is not None else []

    def append(self, metadata: object):
        self._items.append(metadata)

    def extend(self, metadata: list[object]):
        self._items.extend(metadata)

    def has(self, type: type) -> bool:
        return self.find(type) is not None

    def find(self, type: type) -> object | None:
        for item in self._items:
            if isinstance(item, type):
                return item
        return None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(items={self._items})'


class Property[T]:
    def __init__(self, *,
                 default: T | None = None,
                 metadata: list[object] = [],
                 order: int | None = None,
                 on_update: Callable[[object], None] = lambda _: None):
        self.default = default
        self._on_update: Callable[[object], None] = on_update

        metadata = Metadata(metadata[:])
        if order is not None:
            metadata.append(Order(order))

        setattr(self, METADATA_ATTRIBUTE, metadata)

    def __set_name__(self, objtype, name):
        self._variable_name = f'_{name}'

    def __get__(self, instance: object, objtype: type | None = None) -> T:
        if instance is None:
            return self
        return cast(T, instance.__dict__.get(self._variable_name, self.default))

    def __set__(self, instance: object, value: T):
        instance.__dict__[self._variable_name] = value
        self._on_update(instance)

    def type(self):
        return self.__orig_class__.__args__[0]


def metadata(metadata: list[object]):
    def decorator(func):
        return extend_metadata(func, metadata)
    return decorator


def get_all(obj_type: type) -> list[str]:
    names = [
        name
        for name in dir(obj_type)
        for prop in [getattr(obj_type, name, None)]
        if not name.startswith('_') and hasattr(prop, METADATA_ATTRIBUTE)
    ]

    def order_or_name(name: str):
        metadata = get_metadata(obj_type, name)
        order = metadata.find(Order)
        return (order.order if order is not None else 10000, name)

    return sorted(names, key=order_or_name)


def get_metadata(obj: object, property_name: str | None = None) -> Metadata | None:
    if property_name is None:
        if not hasattr(obj, METADATA_ATTRIBUTE):
            return None
        return getattr(obj, METADATA_ATTRIBUTE)

    if not hasattr(obj, property_name):
        return None
    prop = getattr(obj, property_name)

    if isinstance(prop, property):
        prop = prop.fget

    if not hasattr(prop, METADATA_ATTRIBUTE):
        return None

    return getattr(prop, METADATA_ATTRIBUTE)


def extend_metadata(func, metadata: list[object]):
    if isinstance(func, property):
        func = func.fget
    if not hasattr(func, METADATA_ATTRIBUTE):
        setattr(func, METADATA_ATTRIBUTE, Metadata())

    getattr(func, METADATA_ATTRIBUTE).extend(metadata)

    return func


def add_metadata(func, metadata: object):
    return extend_metadata(func, [metadata])


def format_suffix(suffix: str) -> str:
    units = 'mm'
    match s.SETTINGS.get('general/units'):
        case s.Units.MM:
            units = 'mm'
        case s.Units.IN:
            units = 'in'

    return ' ' + suffix.format(units=units)


class Hidden:
    pass


class ReadOnly:
    pass


@dataclass
class Label:
    label: str


@dataclass
class Description:
    description: str


@dataclass
class Suffix:
    suffix: str

    @property
    def formatted_suffix(self) -> str:
        return format_suffix(self.suffix)


@dataclass
class MinValue:
    value: Number


@dataclass
class MaxValue:
    value: Number


@dataclass
class Order:
    order: int


@dataclass
class VisibleIf:
    condition: Callable[[object], bool]
